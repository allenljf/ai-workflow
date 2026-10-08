#!/usr/bin/env python3
"""Prepare site inputs exclusively from reviewed export."""
import argparse,json,shutil,hashlib,re
from pathlib import Path

def prepare(export: Path, site: Path):
    if export.is_symlink(): raise ValueError('Symlink export refused')
    manifest=json.loads((export/'manifest.json').read_text())
    for name in manifest['files']:
        p=export/name
        if p.is_symlink() or not p.resolve().is_relative_to(export.resolve()) or not p.is_file():
            raise ValueError('Unsafe export file')
    if 'workflows.json' not in manifest['files']:raise ValueError('Missing workflow catalog')
    workflows=json.loads((export/'workflows.json').read_text())
    bundles=set()
    for row in workflows:
        name=row['download_path']
        if not re.fullmatch(r'bundles/[a-z0-9-]+-[0-9]+\.[0-9]+\.[0-9]+\.zip',name) or name not in manifest['files']:raise ValueError('Bundle outside catalog allowlist')
        if hashlib.sha256((export/name).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Bundle hash differs')
        bundles.add(name)
    if {n for n in manifest['files'] if n.endswith('.zip')}!=bundles:raise ValueError('Unlisted attachment')
    docs=site/'src/content/docs';generated=site/'src/generated';downloads=site/'public/downloads'
    for p in (docs,generated,downloads):
        if p.is_symlink():raise ValueError('Unsafe generated destination')
        if p.exists():shutil.rmtree(p)
        p.mkdir(parents=True)
    (docs/'404.md').write_text('---\ntitle: 頁面不存在\n---\n這個頁面尚未發布。請回到知識雷達。\n')
    for name in manifest['files']:
        if name.startswith('docs/') and name.endswith('.md'):
            relative=Path(name).relative_to('docs')
            for dest in (docs/'guides'/relative, downloads/relative):
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(export/name,dest)
    for name in bundles:
        dest=downloads/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(export/name,dest)
    shutil.copyfile(export/'workflows.json',generated/'workflows.json')
    if 'fde.json' not in manifest['files']:raise ValueError('Missing FDE catalog')
    shutil.copyfile(export/'fde.json',generated/'fde.json')
    shutil.copyfile(export/'radar.json',generated/'radar.json')
    shutil.copyfile(export/'digests.json',generated/'digests.json')
    (generated/'guides.json').write_text(json.dumps([n.removeprefix('docs/') for n in manifest['files'] if n.startswith('docs/')]))
    print('Prepared reviewed site inputs')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path,required=True);parser.add_argument('--site',type=Path,required=True)
    args=parser.parse_args();prepare(args.export,args.site)
