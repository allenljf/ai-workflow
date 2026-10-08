from copy import deepcopy
from datetime import datetime,timezone
import json
import importlib.util
from pathlib import Path
import pytest
from radar.enrich.runner import run_batch
from radar.enrich.store import load_state,save_state
from radar.enrich.models import EnrichmentState
from radar.enrich.provider import ProviderResult,ProviderError
from test_enrichment_input import snapshot
from test_enrichment_gate import policy,NOW
from radar.enrich.prompt import build_request
class FixtureProvider:
    def __init__(self,fail=False):self.calls=0;self.fail=fail
    def generate(self,request):
        self.calls+=1
        if self.fail:raise ProviderError('ambiguous timeout')
        return ProviderResult(json.loads(Path('tests/fixtures/enrichment-result.json').read_text()),100,30,0,'fixture')
def request():return build_request(snapshot(1).events,snapshot(1),policy())
def test_reservation_persist_failure_no_provider_call():
    p=FixtureProvider()
    def fail(s):raise OSError('durability failed')
    with pytest.raises(OSError):run_batch(request(),EnrichmentState(),p,fail,NOW)
    assert p.calls==0
def test_calling_crash_never_calls_again(tmp_path):
    s=EnrichmentState();p=FixtureProvider()
    def persist(state):
        save_state(tmp_path,state)
        if state.batches[request().batch_id].status=='calling':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_batch(request(),s,p,persist,NOW)
    recovered=load_state(tmp_path)
    b=run_batch(request(),recovered,p,lambda s:save_state(tmp_path,s),NOW)
    assert p.calls==0 and b.status=='ambiguous' and b.reserved_usd!='0'
def test_timeout_keeps_reservation():
    s=EnrichmentState();p=FixtureProvider(True);saved=[]
    b=run_batch(request(),s,p,lambda s:saved.append(deepcopy(s)),NOW)
    assert b.status=='ambiguous' and b.actual_usd is None and p.calls==1
    run_batch(request(),s,p,lambda s:None,NOW)
    assert p.calls==1
def test_saved_result_only_restores_draft(tmp_path):
    s=EnrichmentState();p=FixtureProvider()
    b=run_batch(request(),s,p,lambda s:save_state(tmp_path,s),NOW)
    assert b.status=='pending_review' and b.actual_usd=='0.000066'
    recovered=load_state(tmp_path)
    again=run_batch(request(),recovered,p,lambda s:save_state(tmp_path,s),NOW)
    assert again.result==b.result and p.calls==1
    assert recovered.monthly_ledger['2026-10']['actual_usd']=='0.000066'
def test_unknown_usage_keeps_result_and_reservation():
    class Unknown(FixtureProvider):
        def generate(self,r):return ProviderResult({'stories':[]},None,None,None,None)
    s=EnrichmentState();b=run_batch(request(),s,Unknown(),lambda s:None,NOW)
    assert b.status=='ambiguous' and b.actual_usd is None and b.result is not None
def test_result_and_ledger_are_cas_persisted(tmp_path):
    from test_state_sync import git,write_state
    spec=importlib.util.spec_from_file_location('state_sync',Path('scripts/state-sync.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    remote=tmp_path/'remote';remote.mkdir();git(remote,'init','--bare')
    checkout=tmp_path/'state';head=m.load(checkout,str(remote));write_state(checkout)
    def durable(state):
        nonlocal head
        save_state(checkout,state);head=m.persist(checkout,head)
    s=EnrichmentState();p=FixtureProvider();run_batch(request(),s,p,durable,NOW)
    restored=tmp_path/'restored';m.load(restored,str(remote))
    assert load_state(restored).batches[request().batch_id].result
    # Collection updates snapshot alone but must carry enrichment state through push.
    write_state(restored,'new collect');newhead=git(restored,'rev-parse','HEAD');m.persist(restored,newhead)
    final=tmp_path/'final';m.load(final,str(remote))
    run_batch(request(),load_state(final),p,lambda s:None,NOW)
    assert p.calls==1
