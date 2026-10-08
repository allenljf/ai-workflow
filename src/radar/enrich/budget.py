from copy import deepcopy
from decimal import Decimal
from .models import money,utc
UNRESOLVED={'reserved','calling','ambiguous'}
def estimate_reservation(input_upper_bound,policy):
    if type(input_upper_bound) is not int or input_upper_bound<0:raise ValueError('Invalid token bound')
    return (Decimal(input_upper_bound)*money(policy.input_usd_per_million)+Decimal(policy.max_output_tokens)*money(policy.output_usd_per_million))/Decimal(1000000)
def committed_budget(state,now):
    month=utc(now).strftime('%Y-%m')
    actual=money(state.monthly_ledger.get(month,{'actual_usd':'0'})['actual_usd'])
    # Unresolved calls remain charged against every new month's available budget.
    unresolved=sum((money(b.reserved_usd) for b in state.batches.values() if b.actual_usd is None),Decimal(0))
    return actual+unresolved
def reserve(state,batch,now):
    if batch.id in state.batches:raise ValueError('Batch already reserved')
    amount=money(batch.reserved_usd)
    if amount>money(state.max_batch_usd) or committed_budget(state,now)+amount>money(state.max_monthly_usd):raise ValueError('Budget exceeded')
    result=deepcopy(state);b=deepcopy(batch);b.reservation_month=utc(now).strftime('%Y-%m');result.batches[b.id]=b
    return result
def settle(state,batch,actual):
    amount=money(str(actual))
    if amount>money(batch.reserved_usd):raise ValueError('Usage exceeds reserved cap')
    if batch.actual_usd is not None:raise ValueError('Already settled')
    batch.actual_usd=str(amount)
    month=batch.reservation_month
    entry=state.monthly_ledger.setdefault(month,{'actual_usd':'0'})
    entry['actual_usd']=str(money(entry['actual_usd'])+amount)
