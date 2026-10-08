"""Human adoption decisions are independent of document publication approval."""
from dataclasses import dataclass,replace
from datetime import datetime
from .evidence import validate_evidence

@dataclass
class AdoptionReview:
    owner: str
    decision_at: str
    reason: str
    profile_scope: list[str]
    rollback_version: str
    actor_type: str
    evaluation_contracts: dict

def _review(review):
    try:date=datetime.fromisoformat(review.decision_at)
    except (ValueError,TypeError) as e:raise ValueError('Decision timestamp required') from e
    if date.tzinfo is None or review.actor_type!='human' or not all((review.owner.strip(),review.reason.strip(),review.profile_scope,review.rollback_version)):raise ValueError('Human scoped decision with rollback required')

def verify_evaluations(manifest,evidence,review):
    _review(review)
    if not evidence:raise ValueError('Real execution evidence required')
    if len({r.id for r in evidence})!=len(evidence):raise ValueError('Duplicate evaluation ID')
    for r in evidence:
        contract=review.evaluation_contracts.get(r.id,{})
        if (r.workflow_id,r.workflow_version)!=(manifest.id,manifest.version):raise ValueError('Evaluation belongs to another immutable version')
        if any(contract.get(k)!=getattr(r,k) for k in ('spec_hash','base_sha','environment')):raise ValueError('Evidence contract binding differs')
        if not validate_evidence(r,contract.get('head_sha'),set(contract.get('acceptance_ids',[]))).eligible_for_adoption:raise ValueError('Incomplete/synthetic evidence')

def transition(manifest,target,evidence,review):
    edges={'discovered':{'candidate'},'candidate':{'evaluated'},'evaluated':{'trial'},'trial':{'approved'},'approved':set(),'deprecated':set()}
    if target=='deprecated' and manifest.adoption_state!='deprecated':
        _review(review)
        if not manifest.replacement_version or manifest.replacement_version==manifest.version or not manifest.deprecation_reason:raise ValueError('Replacement version and deprecation reason required')
    elif target not in edges.get(manifest.adoption_state,set()):raise ValueError('Invalid adoption transition')
    elif target in {'evaluated','trial','approved'}:verify_evaluations(manifest,evidence,review)
    else:_review(review)
    return replace(manifest,adoption_state=target,evaluation_ids=[r.id for r in evidence] or list(manifest.evaluation_ids))
