#!/usr/bin/env python3
"""Promote a reviewed local proposal only if its baseline is still current."""
import argparse
from datetime import datetime,timezone
import hashlib
import re
from pathlib import Path
import yaml
from radar.export import read_frontmatter,check_links

def approve(draft,root,allowed):
    if not allowed:raise ValueError('Explicit --approve required after human review')
    root=root.resolve();target=root/'content/public/knowledge/landscape.md'
    if draft.is_symlink() or not draft.resolve().is_relative_to(root/'content/drafts'):raise ValueError('Draft outside review directory')
    text=draft.read_text();meta=read_frontmatter(text)
    if meta.get('kind')!='landscape' or meta.get('review_state')!='draft' or meta.get('visibility')!='private':raise ValueError('Invalid landscape draft')
    if hashlib.sha256(target.read_bytes()).hexdigest()!=meta.get('baseline_sha256'):raise ValueError('Stale baseline: rebase proposal before approval')
    meta.update(visibility='public',review_state='approved',reviewed_at=datetime.now(timezone.utc).isoformat())
    approved={p.resolve() for p in (root/'content/public').rglob('*.md') if read_frontmatter(p.read_text()).get('review_state')=='approved'}
    check_links(text,target,approved)
    body=re.sub(r'本節修訂提案：([^；]+)；尚待查核。',r'本節修訂：\1；已人工核准。',text.split('---',2)[-1])
    target.write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False)+'---\n'+body)
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--approve',action='store_true');a=p.parse_args()
    try:print(approve(a.draft,a.root,a.approve))
    except (ValueError,OSError):p.exit(2,'Approval refused: invalid proposal or stale baseline; no publication\n')
