from pathlib import Path
import importlib.util,json,os
from datetime import datetime,timezone
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
        if not dry and not path.exists():path=write_draft(validated,output,completed_at=b.completed_at)
        # Existing files are human review material; immutable provider result stays in state.

        report['drafts'].append({'batch_id':b.id,'path':str(path),'exists':path.exists()})
    # A paid run and recovery both use the same CAS writer. Token is read only for a new call.
    if not dry and persist is None:persist=durable_checkpoint(root,state_dir,args.expected_sha)
    for b in state.batches.values():recover(b)
    seen={(i['source_id'],i['content_hash']) for b in state.batches.values() if b.request for i in b.request['event_inputs']}
    done={e.id for e in snapshot.events if all((r.id,r.content_hash) in seen for r in public_revisions(e,snapshot))}
    selected=select_events(snapshot,done,config.max_events_per_batch)
    if not selected:
        report['reason']='pending_review' if report['drafts'] else 'no_new_data'
        return report
    request=build_request(selected,snapshot,policy,seen_revision_keys=seen)
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
