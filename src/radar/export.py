from dataclasses import dataclass
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,unquote
import json,os,re,shutil,tempfile
import yaml
from .config import PublicationConfig
from .models import Snapshot
from .normalize import canonicalize_url

@dataclass
class ExportReport:
    copied_paths: list[str]
    excluded_paths: list[str]
    errors: list[str]

def read_frontmatter(text: str) -> dict:
    if not text.startswith('---\n'): return {}
    parts=text.split('---',2)
    if len(parts)!=3: raise ValueError('Invalid frontmatter')
    data=yaml.safe_load(parts[1])
    return data if isinstance(data,dict) else {}

def check_links(text: str, path: Path, approved: set[Path]):
    # No raw HTML/MDX or executable content in exportable human markdown.
    body=text.split('---',2)[-1] if text.startswith('---\n') else text
    if re.search(r'<\s*/?\s*[a-zA-Z][^>]*>',body): raise ValueError('Raw HTML is not exportable')
    links=re.findall(r'!?\[[^\]]*\]\(([^\s)]+)',body)
    links+=re.findall(r'^\s*\[[^\]]+\]:\s*(\S+)',body,re.M)
    for link in links:
        link=link.strip('<>');u=urlsplit(link)
        if u.scheme:
            canonicalize_url(link);continue
        if u.netloc: raise ValueError('Protocol-relative links refused')
        if not u.path: continue
        decoded=unquote(u.path)
        if decoded.startswith('/') or '\\' in decoded: raise ValueError('Absolute content link refused')
        target=(path.parent/decoded).resolve()
        if target not in approved: raise ValueError('Link outside approved export')

def public_radar(snapshot: Snapshot) -> dict:
    revisions={r.id:r for r in snapshot.revisions};events=[]
    for e in snapshot.events:
        visible=[revisions[r] for r in e.item_revision_ids if r in revisions and revisions[r].access_scope=='public' and snapshot.health.get(revisions[r].source_id) and snapshot.health[revisions[r].source_id].public_metadata]
        if not visible: continue
        latest=max(visible,key=lambda r:r.fetched_at)
        try: url=canonicalize_url(latest.canonical_url)
        except ValueError: continue
        sources=[]
        for r in visible:
            try: sources.append({'id':r.source_id,'url':canonicalize_url(r.canonical_url)})
            except ValueError: continue
        h=snapshot.health[latest.source_id]
        events.append({'id':e.id,'title':latest.title,'url':url,'published_at':latest.published_at,
            'fetched_at':latest.fetched_at,'entity':e.entity,'version':e.version,'sources':sources,
            'topics':h.topics,'trust_tier':h.trust_tier,'status':'unreviewed'})
    health=[{'id':key,'last_attempt':h.last_attempt,'last_success':h.last_success,'status':h.status}
        for key,h in snapshot.health.items() if h.public_metadata]
    return {'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),'last_enriched_at':None,
        'last_reviewed_at':None,'events':sorted(events,key=lambda e:e['published_at'] or '',reverse=True),'sources':health}

def export_public(snapshot: Snapshot, content_root: Path, output: Path, publication: PublicationConfig) -> ExportReport:
    root=content_root.resolve();output=output.absolute()
    if output.is_symlink() or not output.resolve().is_relative_to(root/'.build'):
        raise ValueError('Export destination must be under project .build')
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists() and not (output/'manifest.json').is_file(): raise ValueError('Refusing unmanaged export destination')
    selected=[];excluded=[]
    for name in publication.allowed_content_roots:
        directory=root/name
        if directory.is_symlink() or not directory.resolve().is_relative_to(root/'content/public'):
            raise ValueError('Public root outside allowlist')
        if not directory.exists():continue
        for p in directory.rglob('*'):
            if p.is_symlink():raise ValueError('Symlinks are not exportable')
            if not p.is_file():continue
            if p.suffix!='.md': raise ValueError('Attachment requires explicit future approval policy')
            text=p.read_text();meta=read_frontmatter(text)
            if meta.get('visibility')=='public' and meta.get('review_state')=='approved': selected.append(p)
            else:excluded.append(str(p.relative_to(root)))
    approved={p.resolve() for p in selected}
    stage=Path(tempfile.mkdtemp(prefix='.export-',dir=output.parent));backup=None
    try:
        (stage/'docs').mkdir()
        copied=[]
        for p in selected:
            text=p.read_text();check_links(text,p,approved)
            relative=p.relative_to(root/'content/public')
            target=stage/'docs'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
            copied.append(str(relative))
        (stage/'radar.json').write_text(json.dumps(public_radar(snapshot),ensure_ascii=False,indent=2)+'\n')
        (stage/'manifest.json').write_text(json.dumps({'schema_version':1,'files':['radar.json']+['docs/'+p for p in copied]},ensure_ascii=False,indent=2)+'\n')
        if output.exists():
            backup=output.parent/(output.name+'.previous')
            if backup.exists():raise ValueError('Previous export recovery required')
            os.replace(output,backup)
        try:os.replace(stage,output)
        except OSError:
            if backup:os.replace(backup,output)
            raise
        if backup:shutil.rmtree(backup)
        return ExportReport(copied,excluded,[])
    finally:
        if stage.exists():shutil.rmtree(stage)
