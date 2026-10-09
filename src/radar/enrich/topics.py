"""Topics come from approved source configuration, never model output."""
def event_topics(event, snapshot):
    from .select import public_revisions
    return sorted({topic for r in public_revisions(event,snapshot) for topic in snapshot.health[r.source_id].topics})

def domains(event,snapshot):
    topics=event_topics(event,snapshot)
    # Existing generic workflow sources continue in the original development track.
    return ({'fde'} if 'fde' in topics else set()) | ({'android'} if 'android' in topics or 'workflow' in topics or 'fde' not in topics else set())

def public_update_status(snapshot,digests,ai_enabled):
    def latest(values):return max((v for v in values if v),default=None)
    selected=[d for d in digests if 'fde' in d.get('topics',[]) and not d.get('demo',False)]
    sources=[h for h in snapshot.health.values() if h.public_metadata and 'fde' in h.topics]
    import os
    return {'ai_enabled':bool(ai_enabled),'interval_days':int(os.environ.get('AI_INTERVAL_DAYS','14')),'next_due_at':None,
            'due_note':'持久 next_due 由全站財務帳本控制；公開頁不推估排程。',
            'fde':{'collected_at':latest(h.last_success for h in sources),
                   'enriched_at':latest(d['enriched_at'] for d in selected),
                   'reviewed_at':latest(d['reviewed_at'] for d in selected)}}
