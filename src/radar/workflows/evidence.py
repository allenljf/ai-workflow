"""Version-bound evidence, with synthetic provenance kept visible."""
from dataclasses import dataclass,asdict
from importlib.resources import files
import json,jsonschema
from pathlib import Path
import xml.etree.ElementTree as ET

@dataclass
class EvaluationRun:
    id: str
    workflow_id: str
    workflow_version: str
    task_id: str
    spec_hash: str
    base_sha: str
    head_sha: str
    model_version: str
    harness_version: str
    environment: dict
    commands: list[dict]
    executed: int | None
    failed: int | None
    skipped: int | None
    acceptance_results: dict[str,bool]
    cost: float | None
    human_minutes: float | None
    duration: float | None
    artifact_refs: list[dict]
    provenance: str
    def __post_init__(self):
        try:jsonschema.validate(asdict(self),json.loads(files('radar.workflows').joinpath('evaluation-run.schema.json').read_text()))
        except jsonschema.ValidationError as e:raise ValueError(e.message) from e
@dataclass
class EvidenceVerdict:
    complete: bool
    eligible_for_adoption: bool
    reasons: list[str]

def validate_evidence(run,expected_head,acceptance_ids):
    reasons=[]
    if run.head_sha!=expected_head:reasons.append('stale head')
    if run.executed is None or run.executed<=0:reasons.append('no executed tests')
    if run.failed is None or run.failed!=0:reasons.append('failed/unknown tests')
    if run.skipped is None:reasons.append('unknown skipped count')
    if not run.commands or any(c['exit_code']!=0 for c in run.commands):reasons.append('failed/unknown command')
    if not acceptance_ids or any(run.acceptance_results.get(id) is not True for id in acceptance_ids):reasons.append('missing/failed acceptance')
    if not run.artifact_refs:reasons.append('missing artifacts')
    if not run.environment:reasons.append('missing environment')
    return EvidenceVerdict(not reasons,not reasons and run.provenance=='real',reasons)

def read_junit(paths):
    counts=dict(executed=0,failed=0,skipped=0)
    for path in paths:
        raw=Path(path).read_bytes()
        if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:raise ValueError('Unsupported XML entities')
        try:root=ET.fromstring(raw)
        except ET.ParseError as e:raise ValueError('Invalid JUnit report') from e
        if root.tag not in {'testsuite','testsuites'}:raise ValueError('Not a JUnit report')
        for case in root.iter('testcase'):
            if case.find('skipped') is not None:counts['skipped']+=1
            else:
                counts['executed']+=1
                if case.find('failure') is not None or case.find('error') is not None:counts['failed']+=1
    return counts
