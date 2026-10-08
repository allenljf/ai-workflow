from copy import deepcopy
import json
import pytest
from radar.models import Event
from radar.enrich.select import select_events
from radar.enrich.prompt import build_request,request_body,EnrichRequest
from radar.enrich.metadata import digest_metadata
from radar.export import public_radar
from test_enrichment_input import snapshot
from test_enrichment_gate import policy,NOW
from test_enrichment_recovery import FixtureProvider
from radar.enrich.runner import run_batch
from radar.enrich.models import EnrichmentState

def mixed():
    s=snapshot(23)
    for i,h in enumerate(s.health.values()):h.topics=['android' if i<20 else 'fde']
    return s

def test_fair_topics_without_duplicate_events():
    s=mixed();ids=[e.id for e in select_events(s,set(),4)]
    assert ids==['e00','e20','e01','e21'] and len(set(ids))==4
    s.health['s0'].topics.append('fde')
    assert len({e.id for e in select_events(s,set(),4)})==4

def test_single_domain_priority_unchanged():
    s=snapshot(4);s.health['s3'].trust_tier='A';s.events[2].version='1'
    for h in s.health.values():h.topics=['workflow']
    assert [e.id for e in select_events(s,set(),4)]==['e03','e02','e00','e01']

def test_private_topic_cannot_classify_public_story():
    from radar.enrich.topics import event_topics
    s=snapshot(2);s.health['s0'].topics=['android'];s.health['s1'].topics=['fde'];s.revisions[1].access_scope='private'
    s.events=[Event('merged',None,None,['r0','r1'])]
    assert event_topics(s.events[0],s)==['android']
    assert public_radar(s)['events'][0]['topics']==['android']
    s.revisions[1].access_scope='public'
    assert public_radar(s)['events'][0]['topics']==['android','fde']

def test_revision_bound_preserves_both_domains():
    s=mixed();s.events=[Event('android',None,None,[r.id for r in s.revisions[:20]]),s.events[-1]]
    for i in range(20):
        r=deepcopy(s.revisions[i]);r.id+='extra';s.revisions.append(r);s.events[0].item_revision_ids.append(r.id)
    req=build_request(s.events,s,policy())
    assert {i['event_id'] for i in req.event_inputs}=={'android','e22'}
    assert req.topic_map=={'android':['android'],'e22':['fde']}

def test_old_saved_request_recovers_without_model_call_or_new_identity():
    s=snapshot(1);req=build_request(s.events,s,policy());saved=req.to_dict();saved.pop('topic_map',None)
    old=EnrichRequest.from_dict(saved)
    assert old.to_dict()==saved and request_body(old)==request_body(req) and old.batch_id==req.batch_id
    state=EnrichmentState();provider=FixtureProvider()
    run_batch(old,state,provider,lambda s:None,NOW);run_batch(old,state,provider,lambda s:None,NOW)
    assert provider.calls==1 and len(state.batches)==1

def test_fde_digest_metadata_excludes_android_only_and_reports_disabled():
    meta=dict(title='digest',batch_id='a'*64,model='fixture',prompt_version='v1',schema_version='v1',enriched_at='2026-10-08T00:00:00+00:00',reviewed_at='2026-10-08T00:00:00+00:00')
    assert digest_metadata(meta,'d.md')['topics']==['unclassified']
    assert digest_metadata(meta|{'topics':['android']},'d.md')['topics']==['android']
    with pytest.raises(ValueError):digest_metadata(meta|{'topics':['private-secret']},'d.md')
    from radar.enrich.topics import public_update_status
    status=public_update_status(mixed(),[],False)
    assert status['ai_enabled'] is False and status['fde']['enriched_at'] is None and status['next_due_at'] is None
