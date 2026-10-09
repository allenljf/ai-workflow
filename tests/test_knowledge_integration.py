import copy
import importlib.util
import json
from pathlib import Path
import httpx
import pytest
from radar.cli import main
from radar.enrich.store import save_state,load_state
from radar.enrich.provider import ProviderResult
from radar.store import save_snapshot
from radar.models import Snapshot
from test_enrichment_cli import prepared
from test_enrichment_gate import NOW

class KnowledgeProvider:
    calls=0
    def generate(self,request):
        self.calls+=1
        assert request.knowledge and 'New vendor' in str(request.event_inputs)
        source=next(s for s in request.event_inputs if s['feed_source_id']=='knowledge-discovery')
        return ProviderResult({'stories':[{'event_id':source['event_id'],'why':'New pattern','usage':'Review first','limitations':'Not tested','case_evidence':'unknown','source_ids':[source['source_id']],'claim_evidence':[{'claim':'Bounded loop','kind':'source','source_id':source['source_id'],'quote':'Bounded loop'}]}],
            'landscape_updates':[{'section_heading':'## Loop','replacement':'Use a bounded loop with checks.','why':'New evidence','source_ids':[source['source_id']],'quote':'Bounded loop'}]},100,100,0,'fixture')

def setup(tmp_path,monkeypatch):
    config,state=prepared(tmp_path,True)
    save_snapshot(state/'snapshot.json',Snapshot()) # Discovery must work without any release.
    (config/'knowledge.yaml').write_text('queries: [new workflows]\nmax_results: 2\n')
    baseline=tmp_path/'content/public/knowledge/landscape.md';baseline.parent.mkdir(parents=True)
    baseline.write_text('---\ntitle: Landscape\nvisibility: public\nreview_state: approved\n---\n## Loop\nOld guidance.\n\n## Graph\nKeep this section.\n')
    monkeypatch.setenv('KNOWLEDGE_DISCOVERY_ENABLED','true');monkeypatch.setenv('TAVILY_API_KEY','fixture-key')
    return config,state,baseline

@pytest.mark.parametrize('interval',[7,14,28])
def test_discovery_without_release_single_model_call_and_reviewable_revision(tmp_path,monkeypatch,capsys,interval):
    monkeypatch.setenv('AI_INTERVAL_DAYS',str(interval))
    config,state,baseline=setup(tmp_path,monkeypatch);old=baseline.read_text();searches=[];real=httpx.Client
    def handle(request):
        # State saved before the external paid operation.
        assert json.loads((state/'knowledge-discovery.json').read_text())['attempts'][-1]['status']=='calling'
        searches.append(request)
        return httpx.Response(200,json={'results':[{'title':'New vendor loop','url':'https://newvendor.example/loop','content':'snippet','raw_content':'Bounded loop with checks'}],'usage':{'credits':1}})
    monkeypatch.setattr('radar.enrich.command.httpx.Client',lambda:real(transport=httpx.MockTransport(handle)))
    provider=KnowledgeProvider();args=['enrich','--config',str(config),'--state-dir',str(state),'--allow-paid']
    persist=lambda value:save_state(state,value)
    assert main(args,now=NOW,enrichment_provider=provider,enrichment_persist=persist)==0
    report=json.loads(capsys.readouterr().out)
    assert report['model_calls']==1 and len(report['drafts'])==1
    proposal=list((tmp_path/'content/drafts').glob('landscape-*.md'))[0]
    assert 'Use a bounded loop' in proposal.read_text() and 'Keep this section.' in proposal.read_text()
    assert '新來源候選' in Path(report['drafts'][0]['path']).read_text()
    assert baseline.read_text()==old
    assert main(args,now=NOW,enrichment_provider=provider,enrichment_persist=persist)==0
    capsys.readouterr();assert provider.calls==1 and len(searches)==1
    assert len(load_state(state).batches)==1
    from datetime import timedelta
    assert load_state(state).interval_days==interval
    expected=(NOW+timedelta(days=interval)).isoformat()
    assert load_state(state).next_ai_due_at==expected
    assert json.loads((state/'knowledge-discovery.json').read_text())['next_due_at']==expected

def test_dry_run_and_invalid_price_never_search(tmp_path,monkeypatch,capsys):
    config,state,_=setup(tmp_path,monkeypatch)
    monkeypatch.setattr('radar.enrich.command.httpx.Client',lambda:(_ for _ in ()).throw(AssertionError('No API')))
    args=['enrich','--config',str(config),'--state-dir',str(state)]
    assert main(args+['--dry-run'],now=NOW)==0
    assert json.loads(capsys.readouterr().out)['reason']=='ready'
    monkeypatch.setenv('AI_ENABLED','false')
    assert main(args+['--allow-paid'],now=NOW,enrichment_persist=lambda s:save_state(state,s))==0
    assert json.loads(capsys.readouterr().out)['reason']=='disabled'

def test_approval_requires_explicit_review_and_current_baseline(tmp_path,monkeypatch):
    from radar.knowledge.revisions import context,proposed_landscape
    config,state,baseline=setup(tmp_path,monkeypatch)
    script=Path('scripts/approve-landscape.py');spec=importlib.util.spec_from_file_location('approve',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    draft=tmp_path/'content/drafts/landscape-test.md';draft.parent.mkdir(parents=True)
    change={'section_heading':'## Loop','replacement':'Reviewed guidance.','why':'Update','source_ids':['s'],'quote':'Reviewed'}
    draft.write_text(proposed_landscape(context(baseline.read_text()),[change],'a'*64,NOW.isoformat()))
    with pytest.raises(ValueError):module.approve(draft,tmp_path,False)
    baseline.write_text(baseline.read_text()+'\nHuman edit\n')
    with pytest.raises(ValueError,match='Stale'):module.approve(draft,tmp_path,True)

def test_missing_model_key_never_spends_search_credits(tmp_path,monkeypatch,capsys):
    config,state,_=setup(tmp_path,monkeypatch)
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    monkeypatch.setattr('radar.enrich.command.httpx.Client',lambda:(_ for _ in ()).throw(AssertionError('No search')))
    assert main(['enrich','--config',str(config),'--state-dir',str(state),'--allow-paid'],now=NOW,enrichment_persist=lambda s:save_state(state,s))==0
    assert json.loads(capsys.readouterr().out)['reason']=='missing_model_key'
    assert not (state/'knowledge-discovery.json').exists()

def test_ambiguous_model_never_retries_same_discovered_evidence(tmp_path,monkeypatch,capsys):
    config,state,_=setup(tmp_path,monkeypatch);real=httpx.Client;searches=[]
    def handler(request):
        searches.append(request)
        return httpx.Response(200,json={'results':[{'title':'New vendor','url':'https://newvendor.example/loop','content':'Bounded loop'}]})
    monkeypatch.setattr('radar.enrich.command.httpx.Client',lambda:real(transport=httpx.MockTransport(handler)))
    class AmbiguousProvider:
        calls=0
        def generate(self,request):self.calls+=1;raise TimeoutError('uncertain model billing')
    provider=AmbiguousProvider();args=['enrich','--config',str(config),'--state-dir',str(state),'--allow-paid']
    persist=lambda s:save_state(state,s)
    assert main(args,now=NOW,enrichment_provider=provider,enrichment_persist=persist)==0
    capsys.readouterr()
    assert main(args,now=NOW,enrichment_provider=provider,enrichment_persist=persist)==0
    assert json.loads(capsys.readouterr().out)['reason']=='ambiguous_model'
    assert provider.calls==1 and len(searches)==1

def test_appended_candidate_uses_same_snapshot_revision_identity():
    from radar.knowledge.integration import add_candidates,attach
    from radar.enrich.prompt import build_request
    from radar.enrich.select import select_events
    from radar.enrich.models import EnrichmentState
    from test_enrichment_input import snapshot
    from test_enrichment_gate import policy
    candidates=[{'id':'c','url':'https://newvendor.example/tool','title':'New tool','excerpt':'Bounded loop','published_at':None,'evidence_level':'search_snippet_only'}]
    s=add_candidates(snapshot(25),candidates,NOW)
    request=attach(build_request(select_events(s,set()),s,policy()),candidates,'## Loop\nOld.\n',s)
    source=next(i for i in request.event_inputs if i['url']==candidates[0]['url'])
    revision=next(r for r in s.revisions if r.canonical_url==candidates[0]['url'])
    assert (source['source_id'],source['content_hash'])==(revision.id,revision.content_hash)
