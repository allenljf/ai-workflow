from datetime import datetime,timezone
from pathlib import Path
import json
import pytest
from radar.retention import compact
from radar.models import Snapshot,ItemRevision,Event,SourceHealth,validate_snapshot
from radar.enrich.models import EnrichmentState,Batch
from radar.enrich.store import save_state
NOW=datetime(2026,10,9,tzinfo=timezone.utc)
def data():
    def rev(id,date):return ItemRevision(id,'source',id,'https://example.com/'+id,id,date,None,'2026-10-09T00:00:00+00:00',id,access_scope='public')
    rows=[rev('old','2025-01-01T00:00:00+00:00'),rev('current','2026-10-01T00:00:00+00:00')]
    return Snapshot(revisions=rows,events=[Event(r.id,None,None,[r.id]) for r in rows],health={'source':SourceHealth(public_metadata=True)})
def test_archive_old_data_even_if_refetched_today(tmp_path):
    result=compact(data(),tmp_path,NOW,180)
    assert [e.id for e in result.events]==['current']
    archive=json.loads((tmp_path/'archives/2025-01.json').read_text())
    assert archive['events']['old']['item_revision_ids']==['old']
    assert archive['revisions']['old']['title']=='old'
    compact(data(),tmp_path,NOW,180)
    assert len(json.loads((tmp_path/'archives/2025-01.json').read_text())['revisions'])==1
    validate_snapshot(result.to_dict())
def test_pending_review_and_ambiguous_evidence_never_pruned(tmp_path):
    save_state(tmp_path,EnrichmentState(batches={'batch':Batch('batch','h',['old'],status='pending_review',request={'event_inputs':[{'source_id':'old'}]})}))
    result=compact(data(),tmp_path,NOW,180)
    assert len(result.events)==2 and not (tmp_path/'archives').exists()
def test_latest_source_item_retained_even_when_all_are_old(tmp_path):
    s=data();s.revisions=s.revisions[:1];s.events=s.events[:1]
    assert compact(s,tmp_path,NOW,180).events[0].id=='old'
def test_corrupt_archive_refuses_pruning(tmp_path):
    (tmp_path/'archives').mkdir();(tmp_path/'archives/2025-01.json').write_text('{}')
    with pytest.raises(ValueError):compact(data(),tmp_path,NOW,180)

def test_website_window_does_not_delete_snapshot():
    from radar.export import public_radar
    s=data();s.revisions[0].published_at='2026-05-01T00:00:00+00:00'
    assert len(public_radar(s,display_days=90,now=NOW)['events'])==1
    assert len(s.events)==2
