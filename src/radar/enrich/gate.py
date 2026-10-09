from dataclasses import dataclass
from datetime import timedelta
from .models import utc,money
from .budget import estimate_reservation,committed_budget
@dataclass
class GateDecision:
    allowed: bool
    reason: str
    reserved_usd: str='0'
def valid_policy(p,now):
    try:
        return (p.model in {'deepseek-flash','deepseek-v4-pro'} and p.caps_verified is True
            and p.policy_version=='deepseek-nonthinking-2026-10-08' and p.input_token_ceiling==1048576
            and type(p.max_output_tokens) is int and 1<=p.max_output_tokens<=6000
            and money(p.input_usd_per_million)>0 and money(p.output_usd_per_million)>0
            and utc(p.checked_at)<=utc(now))
    except (ValueError,TypeError,ArithmeticError):return False
def decide_run(state,now,enabled,eligible_event_ids,policy,input_hash=None):
    now=utc(now)
    if not enabled:return GateDecision(False,'disabled')
    if not eligible_event_ids:return GateDecision(False,'no_new_data')
    if any((b.input_hash==input_hash if input_hash else sorted(b.event_ids)==sorted(eligible_event_ids)) and b.status in {'reserved','calling','ambiguous','succeeded','pending_review','reviewed','rejected'} for b in state.batches.values()):
        return GateDecision(False,'pending_review')
    if state.next_ai_due_at and now<utc(state.next_ai_due_at):return GateDecision(False,'not_due')
    if not valid_policy(policy,now):return GateDecision(False,'invalid_price')
    amount=estimate_reservation(policy.input_token_ceiling,policy)
    if amount>money(state.max_batch_usd) or committed_budget(state,now)+amount>money(state.max_monthly_usd):return GateDecision(False,'budget_exceeded',str(amount))
    return GateDecision(True,'ready',str(amount))
def complete_at(state,completed_at):
    state.next_ai_due_at=(utc(completed_at)+timedelta(days=state.interval_days)).isoformat()
