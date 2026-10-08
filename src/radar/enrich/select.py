def public_revisions(event,snapshot):
    ids=set(event.item_revision_ids)
    return sorted((r for r in snapshot.revisions if r.id in ids and r.access_scope=='public' and snapshot.health.get(r.source_id) and snapshot.health[r.source_id].public_metadata),key=lambda r:r.id)
def select_events(snapshot,done_ids,limit=20):
    if type(limit) is not int or not 1<=limit<=30:raise ValueError('Event limit must be 1..30')
    eligible=[e for e in snapshot.events if e.id not in done_ids and public_revisions(e,snapshot)]
    def priority(e):
        trust=min({'A':0,'B':1,'C':2}.get(snapshot.health[r.source_id].trust_tier,2) for r in public_revisions(e,snapshot))
        return trust,0 if e.version or e.dedup_reason=='capability' else 1,e.id
    ordered=sorted(eligible,key=priority)
    from .topics import domains
    buckets={domain:[e for e in ordered if domain in domains(e,snapshot)] for domain in ('android','fde')}
    if not all(buckets.values()):return ordered[:limit]
    if limit<2:
        shared=[e for e in ordered if domains(e,snapshot)=={'android','fde'}]
        if shared:return shared[:1]
        raise ValueError('Mixed domains require at least two events per batch')
    chosen=[];seen=set()
    while any(buckets.values()) and len(chosen)<limit:
        for bucket in buckets.values():
            while bucket and bucket[0].id in seen:bucket.pop(0)
            if bucket and len(chosen)<limit:
                e=bucket.pop(0);chosen.append(e);seen.add(e.id)
    return chosen
