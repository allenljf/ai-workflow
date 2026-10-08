"""Validate a closed, reviewed skill graph before publication."""
from datetime import date
from pathlib import Path, PurePosixPath
import re
import yaml
from radar.export import read_frontmatter
from radar.normalize import canonicalize_url

FIELDS={'id','title','level','prerequisite_ids','guide_path','source_refs','checked_at','practice_ids','evidence_level','visibility','review_state','skill_bundle_ids'}

def load_skills(root: Path) -> list[dict]:
    root=Path(root).resolve();path=root/'registry/fde/skills.yaml'
    if not path.exists():return []
    if any(p.is_symlink() for p in (path,*path.parents) if p.is_relative_to(root)):raise ValueError('Unsafe FDE index')
    data=yaml.safe_load(path.read_text())
    if not isinstance(data,dict) or set(data)!={'schema_version','skills'} or data['schema_version']!=1 or not isinstance(data['skills'],list):raise ValueError('Invalid FDE index')
    nodes=data['skills'];ids=set()
    for n in nodes:
        if not isinstance(n,dict) or set(n)!=FIELDS:raise ValueError('Invalid FDE node fields')
        if not isinstance(n['id'],str) or not re.fullmatch('[a-z][a-z0-9-]*',n['id']) or n['id'] in ids:raise ValueError('Duplicate/invalid skill id')
        ids.add(n['id'])
        if not isinstance(n['title'],str) or not n['title'].strip():raise ValueError('Missing skill title')
        if n['level'] not in {'foundation','intermediate','advanced'} or n['evidence_level'] not in {'primary-research','synthetic-contract','local-observed','enterprise-observed'}:raise ValueError('Invalid skill level/evidence')
        if n['visibility']!='public' or n['review_state']!='approved':raise ValueError('Unapproved skill')
        try:
            if not isinstance(n['checked_at'],str) or date.fromisoformat(n['checked_at']).isoformat()!=n['checked_at']:raise ValueError()
        except (ValueError,TypeError):raise ValueError('Invalid checked date') from None
        for key in ('prerequisite_ids','practice_ids','skill_bundle_ids','source_refs'):
            values=n[key]
            if not isinstance(values,list) or any(not isinstance(v,str) or not v.strip() for v in values) or len(set(values))!=len(values):raise ValueError('Invalid skill list')
        if not n['source_refs']:raise ValueError('Missing primary source')
        for url in n['source_refs']:
            if not url.startswith('https://'):raise ValueError('Source requires HTTPS')
            canonicalize_url(url)
        name=n['guide_path']
        if not isinstance(name,str):raise ValueError('Invalid guide path')
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or not name.startswith('fde/') or relative.suffix!='.md':raise ValueError('Unsafe guide path')
        guide=root/'content/public'/name
        if any(p.is_symlink() for p in (guide,*guide.parents) if p.is_relative_to(root)) or not guide.is_file():raise ValueError('Missing/unsafe guide')
        meta=read_frontmatter(guide.read_text())
        if meta.get('visibility')!='public' or meta.get('review_state')!='approved':raise ValueError('Private/unreviewed guide')
    graph={n['id']:n['prerequisite_ids'] for n in nodes};visited=set();active=set()
    def visit(node):
        if node not in graph:raise ValueError('Missing prerequisite')
        if node in active:raise ValueError('Skill dependency cycle')
        if node in visited:return
        active.add(node)
        for dep in graph[node]:visit(dep)
        active.remove(node);visited.add(node)
    for node in graph:visit(node)
    return nodes
