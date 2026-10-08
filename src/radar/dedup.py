from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json
from .models import Snapshot,FetchResult,SourceHealth,ItemRevision,Event
from .normalize import canonicalize_url,plain_text

def digest(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def merge_fetch(snapshot: Snapshot, result: FetchResult, now: datetime) -> Snapshot:
    if now.tzinfo is None: raise ValueError('Timezone required')
    snap=deepcopy(snapshot);time=now.astimezone(timezone.utc).isoformat()
    health=snap.health.setdefault(result.source_id,SourceHealth())
    health.last_attempt=time;health.status=result.status;health.error=result.error
    if result.status not in ('updated','not_modified'): return snap
    health.last_success=time
    if result.etag: health.etag=result.etag
    if result.last_modified: health.last_modified=result.last_modified
    for raw in result.items:
        url=canonicalize_url(raw['url']); external=str(raw.get('external_id') or url)
        title=plain_text(raw.get('title','Untitled'));excerpt=plain_text(raw.get('excerpt',''))[:600]
        content=digest([url,title,excerpt,raw.get('updated_at'),raw.get('version')])
        rid=digest([result.source_id,external,content])
        if any(r.id==rid for r in snap.revisions): continue
        prior=next((r for r in snap.revisions if r.source_id==result.source_id and (r.external_id==external or r.canonical_url==url)),None)
        revision=ItemRevision(rid,result.source_id,external,url,title,
            prior.published_at if prior else raw.get('published_at'),raw.get('updated_at'),time,content,excerpt,
            'public' if health.public_metadata else 'private',raw.get('entity'),raw.get('version'))
        event_id=digest(['release',revision.entity,revision.version]) if revision.entity and revision.version else digest(['url',url])
        event=next((e for e in snap.events if e.id==event_id),None)
        if event is None:
            event=Event(event_id,revision.entity,revision.version,[],dedup_reason='repo_version' if revision.entity and revision.version else 'canonical_url')
            snap.events.append(event)
        # Keep history in revisions, only current revisions in each event.
        old_ids={r.id for r in snap.revisions if r.source_id==result.source_id and (r.external_id==external or r.canonical_url==url)}
        event.item_revision_ids=[r for r in event.item_revision_ids if r not in old_ids]+[rid]
        snap.revisions.append(revision)
    return snap
