from pathlib import Path
import pytest
from radar.config import load_config
from radar.models import Source, validate_snapshot

def test_missing_visibility_is_private():
    assert Source(id='x',type='feed',url='https://example.com/feed').public_metadata is False

def test_reject_naive_time():
    with pytest.raises(ValueError):
        validate_snapshot({'schema_version':1,'revisions':[],'events':[], 'health':{'x':{'last_attempt':'2026-10-08T01:00:00'}},'inbox':[]})

def test_duplicate_source_ids(tmp_path):
    (tmp_path/'sources.yaml').write_text('sources:\n - {id: x, type: feed, url: "https://example.com/feed"}\n - {id: x, type: feed, url: "https://example.com/feed"}\n')
    with pytest.raises(ValueError,match='Duplicate'):
        load_config(tmp_path)

def test_defaults_and_unknown_schema(tmp_path):
    c=load_config(tmp_path)
    assert not c.ai_enabled and not c.publication.publish_enabled
    with pytest.raises(ValueError):
        validate_snapshot({'schema_version':2,'revisions':[],'events':[],'health':{},'inbox':[]})
