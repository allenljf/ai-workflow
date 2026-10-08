from dataclasses import dataclass,asdict,field
from pathlib import Path
from importlib.resources import files
import json,yaml,jsonschema
@dataclass
class WorkflowManifest:
    id: str
    version: str
    upstream_url: str
    upstream_ref: str
    license: str
    redistribution_allowed: bool
    supported_harnesses: list[str]
    profile_ids: list[str]
    bundle_files: list[str]
    visibility: str
    review_state: str
    adoption_state: str
    evaluation_ids: list[str]
    replacement_version: str | None=None
    deprecation_reason: str | None=None
    domain: str | None=None
    asset_approvals: dict[str,str]=field(default_factory=dict)
    def to_dict(self):
        data=asdict(self)
        if self.domain is None:data.pop('domain')
        if not self.asset_approvals:data.pop('asset_approvals')
        return data
def validate_manifest(value):
    try:jsonschema.validate(value,json.loads(files('radar.workflows').joinpath('workflow-manifest.schema.json').read_text()))
    except jsonschema.ValidationError:raise ValueError('Invalid workflow manifest') from None
    return WorkflowManifest(**value)
def load_manifest(path):
    path=Path(path)
    if path.is_symlink():raise ValueError('Symlink manifest refused')
    return validate_manifest(yaml.safe_load(path.read_text()))
