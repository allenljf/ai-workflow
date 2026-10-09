"""Keep a small active snapshot; archive evidence without rewriting Git history."""
from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
import json
import os
import re
import tempfile
import yaml
from .enrich.models import utc
from .enrich.store import load_state
from .models import validate_snapshot

def policy(config):
    path=config/'retention.yaml'
    value=yaml.safe_load(path.read_text()) if path.exists() else {'operational_days':180,'display_days':90}
    if not isinstance(value,dict) or set(value)!={'operational_days','display_days'} or any(type(n) is not int or not 1<=n<=3650 for n in value.values()) or value['display_days']>value['operational_days']:
        raise ValueError('Invalid retention policy')
    return value

def timestamp(revision):
    return utc(revision.updated_at or revision.published_at or revision.fetched_at)

def archive(path,events,revisions):
    if path.is_symlink():raise ValueError('Unsafe archive')
    value=json.loads(path.read_text()) if path.exists() else {'schema_version':1,'events':{},'revisions':{}}
    if not isinstance(value,dict) or set(value)!={'schema_version','events','revisions'} or value['schema_version']!=1 or not isinstance(value['events'],dict) or not isinstance(value['revisions'],dict):raise ValueError('Invalid archive contract')
    for r in revisions:value['revisions'].setdefault(r.id,asdict(r))
    for e in events:
        row=value['events'].setdefault(e.id,asdict(e))
        row['item_revision_ids']=sorted(set(row['item_revision_ids'])|set(e.item_revision_ids))
    if any(r not in value['revisions'] for e in value['events'].values() for r in e['item_revision_ids']):raise ValueError('Archive missing evidence')
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.archive-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def compact(snapshot,state_dir,now,days=180):
    if type(days) is not int or days<1:raise ValueError('Positive retention days required')
    cutoff=utc(now)-timedelta(days=days);state_dir=Path(state_dir)
    if state_dir.is_symlink() or (state_dir/'archives').is_symlink():raise ValueError('Unsafe archive directory')
    state=load_state(state_dir);protected=set();protected_events=set()
    for batch in state.batches.values():
        if batch.status in {'reserved','calling','ambiguous','succeeded','pending_review'}:
            protected_events.update(batch.event_ids)
            protected.update(i['source_id'] for i in (batch.request or {}).get('event_inputs',[]))
    revisions={r.id:r for r in snapshot.revisions}
    # Always retain the latest known item for each source, including inactive sources.
    latest={}
    for r in snapshot.revisions:
        if r.source_id not in latest or timestamp(r)>timestamp(latest[r.source_id]):latest[r.source_id]=r
    protected.update(r.id for r in latest.values())
    kept=[];groups={};removed=set()
    for event in snapshot.events:
        rows=[revisions[r] for r in event.item_revision_ids]
        if event.id in protected_events or any(r.id in protected for r in rows) or not rows or max(timestamp(r) for r in rows)>=cutoff:
            kept.append(event);continue
        month=max(timestamp(r) for r in rows).strftime('%Y-%m')
        group=groups.setdefault(month,{'events':[],'revisions':{}});group['events'].append(event)
        group['revisions'].update({r.id:r for r in rows});removed.update(r.id for r in rows)
    current_ids={rid for e in kept for rid in e.item_revision_ids}
    for r in snapshot.revisions:
        if r.id not in removed and r.id not in current_ids and r.id not in protected and timestamp(r)<cutoff:
            groups.setdefault(timestamp(r).strftime('%Y-%m'),{'events':[],'revisions':{}})['revisions'][r.id]=r;removed.add(r.id)
    # Archive writes must all succeed before the caller replaces active snapshot.
    for month,group in groups.items():archive(state_dir/'archives'/(month+'.json'),group['events'],list(group['revisions'].values()))
    result=deepcopy(snapshot);result.events=kept;result.revisions=[r for r in result.revisions if r.id not in removed or r.id in current_ids]
    return validate_snapshot(result.to_dict())
