def public_revisions(event,snapshot):
    ids=set(event.item_revision_ids)
    return sorted((r for r in snapshot.revisions if r.id in ids and r.access_scope=='public' and snapshot.health.get(r.source_id) and snapshot.health[r.source_id].public_metadata),key=lambda r:r.id)
def select_events(snapshot,done_ids,limit=20):
    if type(limit) is not int or not 1<=limit<=30:raise ValueError('Event limit must be 1..30')
    eligible=[e for e in snapshot.events if e.id not in done_ids and public_revisions(e,snapshot)]
    def priority(e):
        trust=min({'A':0,'B':1,'C':2}.get(snapshot.health[r.source_id].trust_tier,2) for r in public_revisions(e,snapshot))
        return trust,0 if e.version or e.dedup_reason=='capability' else 1,e.id
    return sorted(eligible,key=priority)[:limit]
