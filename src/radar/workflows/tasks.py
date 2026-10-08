"""A readiness gate; orchestration and human acceptance remain external."""
from dataclasses import dataclass,asdict
from importlib.resources import files
from pathlib import PurePosixPath
import json,jsonschema

@dataclass
class TaskContract:
    id: str
    spec_hash: str
    base_sha: str
    depends_on: list[str]
    read_paths: list[str]
    write_paths: list[str]
    resource_locks: list[str]
    acceptance: list[dict]
    validation_commands: list[list[str]]
    max_attempts: int
    time_budget_minutes: int
    token_budget: int
    checkpoint: dict | None
    handoff_summary: str | None
    def __post_init__(self):
        try:jsonschema.validate(asdict(self),json.loads(files('radar.workflows').joinpath('task-contract.schema.json').read_text()))
        except jsonschema.ValidationError as e:raise ValueError(e.message) from e
        for p in self.read_paths+self.write_paths:
            path=PurePosixPath(p)
            if path.is_absolute() or '..' in path.parts or '\\' in p or str(path)!=p:raise ValueError('Unsafe task path')
        if len({a['id'] for a in self.acceptance})!=len(self.acceptance):raise ValueError('Duplicate acceptance ID')
@dataclass
class TaskRecord:
    contract: TaskContract
    status: str
    head_sha: str | None
    integrated_sha: str | None
    evidence_ids: list[str]

def _overlap(a,b):
    a=PurePosixPath(a);b=PurePosixPath(b)
    return a==b or a in b.parents or b in a.parents

def _conflict(a,b):
    x=a.contract;y=b.contract
    return bool(set(x.resource_locks)&set(y.resource_locks)) or any(_overlap(p,q) for p in x.write_paths for q in y.write_paths+y.read_paths) or any(_overlap(p,q) for p in y.write_paths for q in x.read_paths)

def ready_tasks(records,integrated_sha,available_resources):
    by_id={r.contract.id:r for r in records}
    if len(by_id)!=len(records):raise ValueError('Duplicate task ID')
    visited=set();active=set()
    def visit(id):
        if id not in by_id:raise ValueError('Missing dependency')
        if id in active:raise ValueError('Dependency cycle')
        if id in visited:return
        active.add(id)
        for dep in by_id[id].contract.depends_on:visit(dep)
        active.remove(id);visited.add(id)
    for id in by_id:visit(id)
    running=[r for r in records if r.status=='running'];chosen=[]
    for r in records:
        c=r.contract
        if len(running)+len(chosen)>=2:break
        if r.status!='pending' or c.base_sha!=integrated_sha or not set(c.resource_locks)<=available_resources:continue
        deps=[by_id[d] for d in c.depends_on]
        if any(d.status!='accepted' or d.integrated_sha!=integrated_sha or not d.head_sha or not d.evidence_ids for d in deps):continue
        if any(_conflict(r,other) for other in running+chosen):continue
        chosen.append(r)
    return [r.contract.id for r in chosen]
