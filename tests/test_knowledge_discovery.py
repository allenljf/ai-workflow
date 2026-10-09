from datetime import datetime, timezone
from pathlib import Path
import httpx
import pytest
from radar.knowledge.discovery import discover

NOW=datetime(2026,10,9,tzinfo=timezone.utc)
CONFIG={'queries':['agent coding new workflows','agent workflow new tools'],'max_results':3}

def test_no_calls_without_explicit_enable_or_before_due():
    def fail(request):raise AssertionError('Unexpected paid request')
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        state={}
        assert discover(CONFIG,state,client,'key',NOW,lambda:None,enabled=False)['reason']=='disabled'
        state={'next_due_at':'2026-10-23T00:00:00+00:00'}
        assert discover(CONFIG,state,client,'key',NOW,lambda:None,enabled=True)['reason']=='not_due'

def test_search_is_open_bounded_deduplicated_and_saved_before_call():
    saved=[];state={};calls=[]
    def handler(request):
        assert saved[-1]['attempts'][-1]['status']=='calling'
        import json
        body=json.loads(request.content);calls.append(body)
        assert 'include_domains' not in body and body['search_depth']=='basic'
        assert body['auto_parameters'] is False and body['max_results']==3
        return httpx.Response(200,json={'results':[{'title':'New graph runtime','url':'https://new-vendor.example/tool?utm_source=x','content':'snippet','raw_content':'First party article body'}],'usage':{'credits':1}})
    import copy
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=discover(CONFIG,state,client,'key',NOW,lambda:saved.append(copy.deepcopy(state)),enabled=True)
    assert len(calls)==2 and len(result['candidates'])==1
    assert result['candidates'][0]['evidence_level']=='retrieved_text_unreviewed'
    assert state['next_due_at']=='2026-10-23T00:00:00+00:00'

def test_ambiguous_search_is_never_retried():
    state={};calls=[]
    def handler(request):calls.append(request);raise httpx.ReadTimeout('secret must not be logged')
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert discover(CONFIG,state,client,'key',NOW,lambda:None,enabled=True)['reason']=='ambiguous'
        assert discover(CONFIG,state,client,'key',NOW,lambda:None,enabled=True)['reason']=='ambiguous'
    assert len(calls)==1

def test_missing_key_does_not_advance_due():
    with httpx.Client() as client:
        state={};assert discover(CONFIG,state,client,'',NOW,lambda:None,enabled=True)['reason']=='missing_search_key'
    assert state=={}

def test_search_estimated_date_is_safe_for_snapshot():
    from radar.knowledge.discovery import source_date
    assert source_date('2026-10-01')=='2026-10-01T00:00:00+00:00'
    assert source_date('October 2026') is None
    assert source_date('2026-10-01T05:00:00Z')=='2026-10-01T05:00:00+00:00'
