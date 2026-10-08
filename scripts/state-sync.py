#!/usr/bin/env python3
"""Persist state on an independent Git branch with optimistic concurrency."""
import argparse,json,subprocess,sys
from pathlib import Path
from radar.store import load_snapshot
BRANCH='pipeline-state'

def git(path: Path,*args: str,check=True):
    return subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True,check=check)

def remote_head(path: Path) -> str:
    result=git(path,'ls-remote','--heads','origin','refs/heads/'+BRANCH)
    return result.stdout.split()[0] if result.stdout.strip() else 'NONE'

def load(checkout: Path,repo: str) -> str:
    if checkout.is_symlink(): raise ValueError('Symlink checkout refused')
    if checkout.exists() and any(checkout.iterdir()): raise ValueError('State checkout must be new')
    checkout.mkdir(parents=True,exist_ok=True);git(checkout,'init','--initial-branch='+BRANCH)
    git(checkout,'remote','add','origin',repo)
    # CI configures gh credential helper with a short-lived token in environment.
    head=remote_head(checkout)
    if head!='NONE':
        git(checkout,'fetch','--depth=1','origin','refs/heads/'+BRANCH)
        git(checkout,'checkout','-B',BRANCH,'FETCH_HEAD')
        path=checkout/'snapshot.json'
        if not path.is_file() or path.is_symlink():raise ValueError('Existing state branch missing safe snapshot')
        load_snapshot(path)
    return head

def persist(checkout: Path,expected: str) -> str:
    if checkout.is_symlink():raise ValueError('Symlink checkout refused')
    if remote_head(checkout)!=expected:raise ValueError('Remote state changed; refusing overwrite')
    local=git(checkout,'rev-parse','HEAD',check=False)
    actual=local.stdout.strip() if local.returncode==0 else 'NONE'
    if actual!=expected:raise ValueError('Local state base changed')
    path=checkout/'snapshot.json'
    if not path.is_file() or path.is_symlink():raise ValueError('Missing safe snapshot')
    load_snapshot(path)
    git(checkout,'config','user.name','workflow-radar[bot]')
    git(checkout,'config','user.email','workflow-radar@users.noreply.github.com')
    git(checkout,'add','--','snapshot.json')
    changed=git(checkout,'diff','--cached','--quiet',check=False).returncode
    if not changed and expected!='NONE':return expected
    git(checkout,'commit','-m','data: update knowledge radar snapshot')
    git(checkout,'push','origin','HEAD:refs/heads/'+BRANCH)
    return git(checkout,'rev-parse','HEAD').stdout.strip()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['load','persist']);p.add_argument('--checkout',type=Path,required=True);p.add_argument('--repo');p.add_argument('--expected-sha')
    a=p.parse_args()
    try:
        if a.command=='load':
            repo=a.repo or git(Path.cwd(),'remote','get-url','origin').stdout.strip()
            head=load(a.checkout,repo)
        else:
            if not a.expected_sha:raise ValueError('Expected SHA required')
            head=persist(a.checkout,a.expected_sha)
        print(json.dumps({'head':head}))
    except (ValueError,subprocess.CalledProcessError,OSError) as e:
        msg=str(e) if isinstance(e,ValueError) else 'Git state operation failed; no publication allowed'
        print(msg,file=sys.stderr);sys.exit(2)
