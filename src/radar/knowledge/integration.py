"""Attach bounded discovered evidence to the existing one-call enrichment batch."""
from pathlib import Path
import json
from ..models import SourceHealth, FetchResult
from ..dedup import merge_fetch, digest
from .revisions import context

def add_candidates(snapshot,candidates,now):
    snapshot.health['knowledge-discovery']=SourceHealth(public_metadata=True,trust_tier='C',topics=['workflow','android','fde'])
    items=[{'external_id':c['id'],'url':c['url'],'title':c['title'],'excerpt':c['excerpt'],'published_at':c.get('published_at')} for c in candidates]
    return merge_fetch(snapshot,FetchResult('knowledge-discovery','updated',items),now)

def attach(request,candidates,baseline,snapshot,seen_revision_keys=None):
    request.knowledge=context(baseline)
    seen_revision_keys=seen_revision_keys or set()
    # Preserve source revision IDs; enrich their excerpts from retrieved public text.
    by_url={c['url']:c for c in candidates}
    for item in request.event_inputs:
        if item['url'] in by_url:
            row=by_url[item['url']];item['excerpt']=row['excerpt'];item['evidence_level']=row['evidence_level'];item['published_at']=row.get('published_at');item['fetched_at']=row.get('fetched_at');item['source_date_kind']='search_estimate'
    # Older trusted releases must not crowd out newly discovered concepts.
    represented={i['url'] for i in request.event_inputs}
    for row in candidates[:12]:
        if row['url'] in represented:continue
        revision=next(r for r in snapshot.revisions if r.source_id=='knowledge-discovery' and r.canonical_url==row['url'])
        if (revision.id,revision.content_hash) in seen_revision_keys:continue
        event=next(e for e in snapshot.events if revision.id in e.item_revision_ids)
        request.event_inputs.append({'event_id':event.id,'source_id':revision.id,'feed_source_id':'knowledge-discovery',
            'content_hash':revision.content_hash,'title':row['title'],'excerpt':row['excerpt'],'url':row['url'],'kind':'text','evidence_level':row['evidence_level'],'published_at':row.get('published_at'),'fetched_at':row.get('fetched_at'),'source_date_kind':'search_estimate'})
        request.topic_map[event.id]=['workflow']
    from ..enrich.prompt import request_body,KNOWLEDGE_MAX_BYTES
    # Reduce evidence text deterministically to fit provider's bounded input contract.
    while len(json.dumps(request_body(request),ensure_ascii=False).encode())>KNOWLEDGE_MAX_BYTES:
        longest=max(request.event_inputs,key=lambda i:len(i['excerpt']))
        if len(longest['excerpt'])<=200:raise ValueError('Landscape exceeds bounded input')
        longest['excerpt']=longest['excerpt'][:max(200,len(longest['excerpt'])//2)]
    request.batch_id=digest([sorted((i['source_id'],i['content_hash']) for i in request.event_inputs),request.model,request.prompt_version,request.schema_version,request.knowledge['sha256']])
    return request
