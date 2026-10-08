from datetime import datetime, timezone
from radar.models import Snapshot,FetchResult
from radar.normalize import canonicalize_url
from radar.dedup import merge_fetch
NOW=datetime(2026,10,8,tzinfo=timezone.utc)
def item(**kw): return {'external_id':'one','url':'https://example.com/a','title':'A','excerpt':'Body','published_at':'2026-10-01T00:00:00Z','updated_at':None,'entity':None,'version':None}|kw

def test_preserves_video_identity():
    assert canonicalize_url('https://www.youtube.com/watch?v=abc&utm_source=x')=='https://www.youtube.com/watch?v=abc'

def test_repeated_fetch_not_new_revision():
    first=merge_fetch(Snapshot(),FetchResult('test','updated',[item()]),NOW)
    second=merge_fetch(first,FetchResult('test','updated',[item()]),datetime(2026,10,9,tzinfo=timezone.utc))
    assert len(second.revisions)==1 and len(second.events)==1
    assert second.revisions[0].published_at=='2026-10-01T00:00:00Z'

def test_content_change_creates_revision():
    first=merge_fetch(Snapshot(),FetchResult('test','updated',[item()]),NOW)
    second=merge_fetch(first,FetchResult('test','updated',[item(excerpt='Changed')]),NOW)
    assert len(second.revisions)==2 and len(second.events)==1

def test_distinct_versions_and_multiple_sources():
    s=merge_fetch(Snapshot(),FetchResult('test','updated',[item(entity='org/repo',version='v1'),item(external_id='two',url='https://example.com/b',entity='org/repo',version='v2')]),NOW)
    s=merge_fetch(s,FetchResult('other','updated',[item(external_id='third',entity='org/repo',version='v1')]),NOW)
    assert len(s.events)==2
    assert len(next(e for e in s.events if e.version=='v1').item_revision_ids)==2

def test_failed_and_304_keep_previous_records():
    first=merge_fetch(Snapshot(),FetchResult('test','updated',[item()]),NOW)
    fail=merge_fetch(first,FetchResult('test','failed',error='Timeout'),datetime(2026,10,9,tzinfo=timezone.utc))
    assert fail.events==first.events and fail.health['test'].last_success==NOW.isoformat()
    unchanged=merge_fetch(fail,FetchResult('test','not_modified'),datetime(2026,10,10,tzinfo=timezone.utc))
    assert unchanged.events==first.events
    assert unchanged.health['test'].last_success=='2026-10-10T00:00:00+00:00'
