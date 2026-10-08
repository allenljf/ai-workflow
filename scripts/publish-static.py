#!/usr/bin/env python3
"""Publish validated static output to a dedicated export repository only."""
from pathlib import Path
import argparse,json,re,shutil,subprocess,sys
ALLOWED={'.html','.css','.js','.json','.xml','.md','.svg','.png','.webp','.ico','.woff','.woff2','.wasm','.pf_meta','.pf_index','.pf_fragment','.txt'}

def git(path,*args,check=True):
    return subprocess.run(['git','-C',str(path),*args],check=check,capture_output=True,text=True)

def validate_dist(dist: Path):
    if dist.is_symlink() or not (dist/'index.html').is_file():raise ValueError('Static index required')
    for p in dist.rglob('*'):
        rel=p.relative_to(dist)
        if p.is_symlink() or any(part.startswith('.') for part in rel.parts):raise ValueError('Unsafe static path')
        if p.is_file() and p.suffix not in ALLOWED:raise ValueError('Unexpected static asset')

def publish(dist: Path,repo: str,checkout: Path) -> str:
    validate_dist(dist)
    if checkout.exists():raise ValueError('Publish checkout must be new')
    checkout.mkdir(parents=True);git(checkout,'init','--initial-branch=main');git(checkout,'remote','add','origin',repo)
    head=git(checkout,'ls-remote','--heads','origin','refs/heads/main').stdout.strip()
    if head:
        git(checkout,'fetch','--depth=1','origin','main');git(checkout,'checkout','-B','main','FETCH_HEAD')
        if not (checkout/'.radar-site').is_file():raise ValueError('Target is not a managed radar export repository')
    for p in checkout.iterdir():
        if p.name=='.git':continue
        if p.is_dir() and not p.is_symlink():shutil.rmtree(p)
        else:p.unlink()
    shutil.copytree(dist,checkout,dirs_exist_ok=True)
    (checkout/'.nojekyll').touch();(checkout/'.radar-site').write_text('Managed static export; no private source files.\n')
    git(checkout,'config','user.name','workflow-radar[bot]');git(checkout,'config','user.email','workflow-radar@users.noreply.github.com')
    git(checkout,'add','--all')
    if git(checkout,'diff','--cached','--quiet',check=False).returncode==0:return git(checkout,'rev-parse','HEAD').stdout.strip()
    git(checkout,'commit','-m','site: publish reviewed knowledge radar')
    git(checkout,'push','origin','HEAD:refs/heads/main')
    return git(checkout,'rev-parse','HEAD').stdout.strip()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dist',type=Path,required=True);p.add_argument('--repo',required=True);p.add_argument('--checkout',type=Path,required=True)
    a=p.parse_args()
    try:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repo):raise ValueError('GitHub owner/repo required')
        sha=publish(a.dist,'https://github.com/'+a.repo+'.git',a.checkout)
        print(json.dumps({'published_head':sha}))
    except (ValueError,OSError,subprocess.CalledProcessError):
        print('Static publication refused or failed; inspect configuration without exposing token',file=sys.stderr);sys.exit(2)
