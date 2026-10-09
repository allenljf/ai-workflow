from pathlib import Path
import importlib.util,json,os
from datetime import datetime,timezone,timedelta
from contextlib import nullcontext
import httpx,yaml
from .models import PricePolicy
from .store import load_state,save_state
from .prompt import build_request,EnrichRequest
from .select import select_events,public_revisions
from .gate import decide_run
from .runner import run_batch
from .validate import validate_result
from .draft import write_draft
from .deepseek import DeepSeekProvider
from ..store import load_snapshot
def durable_checkpoint(root,state_dir,expected=None):
    script=root/'scripts/state-sync.py'
    spec=importlib.util.spec_from_file_location('radar_state_sync',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.git(state_dir,'rev-parse','HEAD',check=False)
    current=result.stdout.strip() if result.returncode==0 else 'NONE'
    if not (state_dir/'.git').exists():raise ValueError('Paid run requires durable Git state')
    base=expected or current
    if module.remote_head(state_dir)!=base or current!=base:raise ValueError('State base mismatch')
    def checkpoint(state):
        nonlocal base
        save_state(state_dir,state);base=module.persist(state_dir,base)
    return checkpoint
def execute(args,config,now,provider=None,persist=None):
    root=args.config.resolve().parent;state_dir=args.state_dir.resolve()
    if args.state_dir.is_symlink() or not (state_dir/'snapshot.json').is_file():raise ValueError('Collection snapshot required')
    snapshot=load_snapshot(state_dir/'snapshot.json');state=load_state(state_dir)
    state.max_batch_usd=config.max_batch_usd;state.max_monthly_usd=config.max_monthly_usd
    interval=int(os.environ.get('AI_INTERVAL_DAYS',str(state.interval_days)))
    if not 1<=interval<=365:raise ValueError('AI_INTERVAL_DAYS must be 1..365')
    if interval!=state.interval_days:
        from .models import utc
        completed=[utc(b.completed_at) for b in state.batches.values() if b.completed_at]
        state.interval_days=interval
        if completed:state.next_ai_due_at=(max(completed)+timedelta(days=interval)).isoformat()
    policy=PricePolicy(**(json.loads(os.environ['AI_PRICE_POLICY']) if os.environ.get('AI_PRICE_POLICY') else yaml.safe_load((args.config/'model-pricing.yaml').read_text())))
    from .models import money
    state.max_batch_usd=os.environ.get('AI_MAX_BATCH_USD',state.max_batch_usd);state.max_monthly_usd=os.environ.get('AI_MAX_MONTHLY_USD',state.max_monthly_usd)
    money(state.max_batch_usd);money(state.max_monthly_usd)
    enabled=config.ai_enabled
    if 'AI_ENABLED' in os.environ:
        if os.environ['AI_ENABLED'] not in {'true','false'}:raise ValueError('Invalid AI_ENABLED')
        enabled=os.environ['AI_ENABLED']=='true'
    dry=args.dry_run or not args.allow_paid
    report={'mode':'dry-run' if dry else 'paid','model_calls':0,'drafts':[],'reason':'no_new_data','reserved_usd':'0','model':policy.model}
    output=root/'content/drafts'
    def recover(b):
        if b.status not in {'succeeded','pending_review'} or not b.result or not b.request:return
        try:validated=validate_result(b.result,EnrichRequest.from_dict(b.request))
        except ValueError:
            if not dry:
                b.status='failed';b.diagnostic='Evidence/schema rejected; private result retained';persist(state)
            return
        path=output/('digest-'+b.id+'.md')
        if path.is_symlink():raise ValueError('Symlink draft refused')
        if not dry and not path.exists():path=write_draft(validated,output,completed_at=b.completed_at,topic_map=validated.request.topic_map)
        # Existing files are human review material; immutable provider result stays in state.

        report['drafts'].append({'batch_id':b.id,'path':str(path),'exists':path.exists()})
    # A paid run and recovery both use the same CAS writer. Token is read only for a new call.
    if not dry and persist is None:persist=durable_checkpoint(root,state_dir,args.expected_sha)
    for b in state.batches.values():recover(b)
    seen={(i['source_id'],i['content_hash']) for b in state.batches.values() if b.request for i in b.request['event_inputs']}
    done={e.id for e in snapshot.events if all((r.id,r.content_hash) in seen for r in public_revisions(e,snapshot))}
    discovery_enabled=os.environ.get('KNOWLEDGE_DISCOVERY_ENABLED','false')=='true'
    candidates=[]
    if discovery_enabled:
        if any(b.status in {'reserved','calling','ambiguous'} for b in state.batches.values()):
            report['reason']='ambiguous_model';return report
        # Free eligibility check before search credits or model tokens can be spent.
        probe=decide_run(state,now,enabled,['knowledge-exploration'],policy,input_hash='knowledge-probe')
        report['discovery_enabled']=True
        if not probe.allowed:
            report['reason']=probe.reason
            return report
        if dry:
            report['reason']='ready';report['discovery_queries']=len(yaml.safe_load((args.config/'knowledge.yaml').read_text())['queries'])
            return report
        if provider is None and not os.environ.get('DEEPSEEK_API_KEY'):
            report['reason']='missing_model_key';return report
        from ..knowledge.discovery import discover
        path=state_dir/'knowledge-discovery.json'
        if path.is_symlink():raise ValueError('Unsafe discovery state')
        search_state=json.loads(path.read_text()) if path.exists() else {}
        def save_discovery():
            # File is staged by the same durable Git CAS writer before each search.
            path.write_text(json.dumps(search_state,ensure_ascii=False,indent=2)+'\n')
            persist(state)
        with httpx.Client() as search_client:
            discovery=discover(yaml.safe_load((args.config/'knowledge.yaml').read_text()),search_state,search_client,
                os.environ.get('TAVILY_API_KEY',''),now,save_discovery,enabled=True,interval_days=state.interval_days)
        if discovery['reason'] not in {'searched','not_due'}:
            report['reason']=discovery['reason'];return report
        candidates=discovery['candidates']
        if not candidates:
            report['reason']='no_discovery_results';return report
        from ..knowledge.integration import add_candidates
        snapshot=add_candidates(snapshot,candidates,now)
        done={e.id for e in snapshot.events if all((r.id,r.content_hash) in seen for r in public_revisions(e,snapshot))}
    selected=select_events(snapshot,done,config.max_events_per_batch)
    if not selected:
        report['reason']='pending_review' if report['drafts'] else 'no_new_data'
        return report
    request=build_request(selected,snapshot,policy,seen_revision_keys=seen)
    if discovery_enabled:
        from ..knowledge.integration import attach
        request=attach(request,candidates,(root/'content/public/knowledge/landscape.md').read_text(),snapshot,seen)
    decision=decide_run(state,now,enabled,sorted({i['event_id'] for i in request.event_inputs}),policy,input_hash=request.batch_id)
    report.update(reason=decision.reason,reserved_usd=decision.reserved_usd,batch_id=request.batch_id,event_count=len({i['event_id'] for i in request.event_inputs}),revision_count=len(request.event_inputs))
    if dry or not decision.allowed:return report
    if provider is not None:
        batch=run_batch(request,state,provider,persist,now,clock=lambda:now)
    else:
        key=os.environ.get('DEEPSEEK_API_KEY','')
        if not key:raise ValueError('No provider credential; refusing paid call')
        with httpx.Client() as client:batch=run_batch(request,state,DeepSeekProvider(key,client),persist,now,clock=lambda:datetime.now(timezone.utc))
    report['model_calls']=1;report['reason']=batch.status;recover(batch)
    return report
