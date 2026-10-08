from dataclasses import dataclass,field,asdict
from datetime import datetime,timezone
from decimal import Decimal

def utc(value):
    d=datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
    if d.tzinfo is None:raise ValueError('Timezone required')
    return d.astimezone(timezone.utc)
def money(value):
    if not isinstance(value,str):raise ValueError('Money must be Decimal string')
    d=Decimal(value)
    if not d.is_finite() or d<0:raise ValueError('Invalid money')
    return d
@dataclass
class PricePolicy:
    model: str
    input_usd_per_million: str
    output_usd_per_million: str
    checked_at: str
    expires_at: str
    max_output_tokens: int=6000
    caps_verified: bool=True
    input_token_ceiling: int=1048576
    policy_version: str='deepseek-nonthinking-2026-10-08'
@dataclass
class Batch:
    id: str
    input_hash: str
    event_ids: list[str]
    status: str='reserved'
    reserved_usd: str='0'
    actual_usd: str | None=None
    result_hash: str | None=None
    review_pr_url: str | None=None
    reservation_month: str | None=None
    result: dict | None=None
    request: dict | None=None
    completed_at: str | None=None
    diagnostic: str | None=None
    usage: dict | None=None
@dataclass
class EnrichmentState:
    schema_version: int=1
    next_ai_due_at: str | None=None
    batches: dict[str,Batch]=field(default_factory=dict)
    monthly_ledger: dict[str,dict]=field(default_factory=dict)
    max_batch_usd: str='0.50'
    max_monthly_usd: str='2'
    interval_days: int=14
    def to_dict(self):return asdict(self)
    @classmethod
    def from_dict(cls,v):
        obj=cls(**(v|{'batches':{k:Batch(**b) for k,b in v.get('batches',{}).items()}}))
        if obj.schema_version!=1 or obj.interval_days!=14:raise ValueError('Unsupported state version/interval')
        money(obj.max_batch_usd);money(obj.max_monthly_usd)
        if obj.next_ai_due_at:utc(obj.next_ai_due_at)
        statuses={'reserved','calling','succeeded','ambiguous','failed','pending_review','reviewed','rejected'}
        for k,b in obj.batches.items():
            if k!=b.id or b.status not in statuses:raise ValueError('Invalid batch')
            money(b.reserved_usd)
            if b.actual_usd is not None:money(b.actual_usd)
            if b.completed_at:utc(b.completed_at)
        for month,entry in obj.monthly_ledger.items():
            if len(month)!=7:raise ValueError('Invalid ledger month')
            money(entry['actual_usd'])
        return obj
