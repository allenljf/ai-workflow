from copy import deepcopy
from decimal import Decimal
from .models import Batch,PricePolicy,money,utc
from .budget import reserve,estimate_reservation,settle
from .gate import valid_policy,complete_at
from .provider import ProviderError
from ..dedup import digest
def run_batch(request,state,provider,persist,now,clock=None):
    if request.batch_id in state.batches:
        b=state.batches[request.batch_id]
        if b.status in {'reserved','calling'}:
            b.status='ambiguous';b.diagnostic='Interrupted call requires manual billing confirmation';persist(state)
        return b
    policy=PricePolicy(**request.policy)
    if not valid_policy(policy,now) or request.model!=policy.model or request.max_output_tokens!=policy.max_output_tokens or request.input_upper_bound!=policy.input_token_ceiling:
        raise ValueError('Invalid pricing/cap contract')
    amount=estimate_reservation(request.input_upper_bound,policy)
    batch=Batch(request.batch_id,request.batch_id,sorted({i['event_id'] for i in request.event_inputs}),reserved_usd=str(amount),request=request.to_dict())
    reserved=reserve(state,batch,now)
    persist(reserved) # Must raise if the durable Git CAS push did not complete.
    state.__dict__.update(deepcopy(reserved.__dict__))
    batch=state.batches[batch.id];batch.status='calling'
    persist(state) # Crash after here is never automatically retried.
    try:result=provider.generate(request)
    except Exception:
        batch.status='ambiguous';batch.diagnostic='Provider failure; verify billing before manual resolution';persist(state)
        return batch
    batch.result=result.payload;batch.result_hash=digest(result.payload)
    batch.usage={'input_tokens':result.input_tokens,'output_tokens':result.output_tokens,'reasoning_tokens':result.reasoning_tokens,'request_id':result.request_id}
    completed=utc(clock() if clock else now)
    try:
        inp=result.input_tokens;out=result.output_tokens;reason=result.reasoning_tokens
        if any(type(n) is not int or n<0 for n in (inp,out,reason)) or inp>request.input_upper_bound or out>request.max_output_tokens or reason!=0:raise ValueError('Unknown or unsupported usage')
        actual=(Decimal(inp)*money(policy.input_usd_per_million)+Decimal(out)*money(policy.output_usd_per_million))/Decimal(1000000)
        settle(state,batch,actual,completed_at=completed)
    except (ValueError,TypeError,ArithmeticError):
        batch.status='ambiguous';batch.diagnostic='Usage unknown/outside cap; reservation retained';persist(state)
        return batch
    batch.status='succeeded';batch.completed_at=completed.isoformat()
    complete_at(state,batch.completed_at)
    persist(state) # payload + cost + next due are atomic in the same Git commit.
    batch.status='pending_review';persist(state)
    return batch
