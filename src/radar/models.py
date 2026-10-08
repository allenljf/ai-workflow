from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from importlib.resources import files
import json
import jsonschema

class SourceType(StrEnum):
    FEED='feed'
    GITHUB='github'
    YOUTUBE='youtube'
class FetchStatus(StrEnum):
    UPDATED='updated'
    NOT_MODIFIED='not_modified'
    FAILED='failed'
    DISABLED='disabled'

def aware(value: str | None):
    if value is not None:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError('Timestamp must include timezone')

@dataclass
class Source:
    id: str
    type: SourceType
    url: str
    trust_tier: str='C'
    topics: list[str]=field(default_factory=list)
    enabled: bool=True
    public_metadata: bool=False
    options: dict=field(default_factory=dict)
    def __post_init__(self):
        self.type=SourceType(self.type)
        if not self.id or self.trust_tier not in ('A','B','C'):
            raise ValueError('Invalid source')

@dataclass
class FetchResult:
    source_id: str
    status: FetchStatus
    items: list[dict]=field(default_factory=list)
    etag: str | None=None
    last_modified: str | None=None
    error: str | None=None

@dataclass
class ItemRevision:
    id: str
    source_id: str
    external_id: str
    canonical_url: str
    title: str
    published_at: str | None
    updated_at: str | None
    fetched_at: str
    content_hash: str
    excerpt: str=''
    access_scope: str='private'
    entity: str | None=None
    version: str | None=None
    def __post_init__(self):
        for value in (self.published_at,self.updated_at,self.fetched_at): aware(value)
        if self.access_scope not in ('public','private'): raise ValueError('Invalid access scope')

@dataclass
class Event:
    id: str
    entity: str | None
    version: str | None
    item_revision_ids: list[str]
    status: str='unreviewed'
    dedup_reason: str='stable_id'

@dataclass
class SourceHealth:
    last_attempt: str | None=None
    last_success: str | None=None
    status: str='never'
    error: str | None=None
    etag: str | None=None
    last_modified: str | None=None
    public_metadata: bool=False
    trust_tier: str='C'
    topics: list[str]=field(default_factory=list)
    def __post_init__(self):
        aware(self.last_attempt); aware(self.last_success)

@dataclass
class Snapshot:
    schema_version: int=1
    revisions: list[ItemRevision]=field(default_factory=list)
    events: list[Event]=field(default_factory=list)
    health: dict[str,SourceHealth]=field(default_factory=dict)
    inbox: list[dict]=field(default_factory=list)
    def to_dict(self): return asdict(self)

def validate_snapshot(value: dict) -> Snapshot:
    schema=json.loads(files('radar').joinpath('snapshot.schema.json').read_text())
    try:
        jsonschema.validate(value,schema)
        snap=Snapshot(value['schema_version'],[ItemRevision(**v) for v in value['revisions']],
            [Event(**v) for v in value['events']],{k:SourceHealth(**v) for k,v in value['health'].items()},value['inbox'])
    except (jsonschema.ValidationError,TypeError,KeyError) as exc:
        raise ValueError('Invalid snapshot contract') from exc
    ids={r.id for r in snap.revisions}
    if len(ids)!=len(snap.revisions) or len({e.id for e in snap.events})!=len(snap.events):
        raise ValueError('Duplicate snapshot identity')
    if any(r not in ids for e in snap.events for r in e.item_revision_ids):
        raise ValueError('Missing event revision')
    return snap
