from pathlib import Path
import pytest
import yaml
from radar.models import Source, ItemRevision, Snapshot

@pytest.fixture
def source():
    return lambda **kw: Source(**({'id':'test','type':'feed','url':'https://example.com/feed','public_metadata':True,'trust_tier':'A'}|kw))
@pytest.fixture
def revision():
    return lambda **kw: ItemRevision(**({'id':'r1','source_id':'test','external_id':'one','canonical_url':'https://example.com/one','title':'One','published_at':'2026-10-01T00:00:00Z','updated_at':None,'fetched_at':'2026-10-08T00:00:00Z','content_hash':'abc','access_scope':'public'}|kw))
@pytest.fixture
def snapshot(): return lambda: Snapshot()
@pytest.fixture
def approved_doc():
    def make(root: Path, **frontmatter):
        p=root/'content/public/guide.md'; p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('---\n'+yaml.safe_dump({'title':'Guide','visibility':'public','review_state':'approved'}|frontmatter)+'---\n# Guide\n')
        return p
    return make
