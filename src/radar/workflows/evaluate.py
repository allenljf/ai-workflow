"""Approved local runner bindings and paired, explicitly incomplete comparisons."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json,re,subprocess,time
from .evidence import validate_evidence,read_junit

@dataclass
class ComparisonReport:
    pairs: list[dict]
    unmatched: list[str]
    caveats: list[str]

def compare_runs(baseline,candidate):
    def key(r):return (r.task_id,r.spec_hash,r.base_sha,json.dumps(r.environment,sort_keys=True),r.model_version,r.harness_version,r.provenance)
    left={}
    for r in baseline:left.setdefault(key(r),[]).append(r)
    pairs=[];used=set();unmatched=[]
    for c in candidate:
        matches=left.get(key(c),[])
        if len(matches)!=1 or key(c) in used:
            unmatched.append(c.id);continue
        b=matches[0];used.add(key(c))
        def delta(field):
            x=getattr(b,field);y=getattr(c,field)
            return None if x is None or y is None else y-x
        pairs.append({'baseline_id':b.id,'candidate_id':c.id,'provenance':c.provenance,'duration_delta':delta('duration'),'cost_delta':delta('cost'),'human_minutes_delta':delta('human_minutes'),'baseline_complete':validate_evidence(b,b.head_sha,set(b.acceptance_results)).complete,'candidate_complete':validate_evidence(c,c.head_sha,set(c.acceptance_results)).complete})
    unmatched += [b.id for b in baseline if key(b) not in used]
    return ComparisonReport(pairs,unmatched,['Unknown measurements remain null; synthetic pairs establish no Android effectiveness.','Paired measurements are observations, not a causal efficiency claim.'])

@dataclass
class RunnerBinding:
    target_repo: str
    base_sha: str
    head_sha: str
    commands: list[list[str]]
    environment: dict
    profile_id: str
    profile_review: dict

def _git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.DEVNULL).strip()

def validate_binding(binding):
    repo=Path(binding.target_repo)
    if not repo.is_dir() or not binding.environment or not binding.profile_id:raise ValueError('Missing repo/environment/profile binding')
    if not all(re.fullmatch('[0-9a-f]{40}',s) for s in (binding.base_sha,binding.head_sha)):raise ValueError('Full commit SHA required')
    if not binding.commands or any(not isinstance(c,list) or not c or any(not isinstance(a,str) or not a or '\x00' in a for a in c) for c in binding.commands):raise ValueError('Argument-array commands required')
    review=binding.profile_review
    if review.get('decision')!='approved' or not review.get('owner') or review.get('profile_id')!=binding.profile_id or review.get('commands')!=binding.commands or review.get('environment')!=binding.environment:raise ValueError('Human-reviewed profile/commands/environment required')
    try:
        if _git(repo,'rev-parse','--show-toplevel')!=str(repo.resolve()):raise ValueError('Bind repository root')
        if _git(repo,'rev-parse','HEAD')!=binding.head_sha or _git(repo,'status','--porcelain','--untracked-files=no'):raise ValueError('Clean exact head required')
        if _git(repo,'merge-base',binding.base_sha,binding.head_sha)!=binding.base_sha:raise ValueError('Base not ancestor')
    except subprocess.CalledProcessError as e:raise ValueError('Repository/SHA unavailable') from e
    return repo.resolve()

def run_bound(binding,report_paths,out,timeout_seconds=1800):
    """Execute reviewed commands, retain private outputs, return raw observations.

    The caller supplies manual acceptance, model identity and costs; no auto-accept.
    """
    repo=validate_binding(binding);out=Path(out)
    reports=[]
    for name in report_paths:
        p=repo/name
        if p.is_symlink() or not p.resolve().is_relative_to(repo):raise ValueError('Unsafe report path')
        reports.append(p)
    before={p:(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) if p.exists() else None for p in reports}
    out.mkdir(parents=True,exist_ok=True);commands=[];start=time.monotonic()
    for i,argv in enumerate(binding.commands):
        remaining=timeout_seconds-(time.monotonic()-start)
        if remaining<=0:raise ValueError('Runner time budget exhausted')
        try:r=subprocess.run(argv,cwd=repo,capture_output=True,timeout=remaining)
        except subprocess.TimeoutExpired as e:raise ValueError('Runner command timed out') from e
        (out/f'command-{i}.log').write_bytes(r.stdout+b'\n'+r.stderr)
        commands.append({'argv':argv,'exit_code':r.returncode})
        if r.returncode:break
    validate_binding(binding)
    artifacts=[]
    for p in reports:
        if p.is_symlink() or not p.resolve().is_relative_to(repo) or not p.is_file():raise ValueError('Missing report')
        data=p.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if (digest,p.stat().st_mtime_ns)==before[p]:raise ValueError('Unchanged/stale report; force tests to rerun')
        target=out/f'report-{len(artifacts)}.xml';target.write_bytes(data)
        artifacts.append({'path':str(target),'sha256':digest})
    return dict(commands=commands,**read_junit([a['path'] for a in artifacts]),duration=time.monotonic()-start,artifact_refs=artifacts,provenance='real')
