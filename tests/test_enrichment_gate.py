from datetime import datetime,timezone,timedelta
from decimal import Decimal
import pytest
from radar.enrich.models import EnrichmentState,PricePolicy,Batch
from radar.enrich.gate import decide_run,complete_at
from radar.enrich.budget import estimate_reservation,reserve
NOW=datetime(2026,10,25,tzinfo=timezone.utc)
def policy(**kw):
    return PricePolicy(**(dict(model='deepseek-flash',input_usd_per_million='0.30',output_usd_per_million='1.20',checked_at=NOW.isoformat(),expires_at=(NOW+timedelta(days=14)).isoformat(),max_output_tokens=6000)|kw))
def test_disabled_no_call():
    assert decide_run(EnrichmentState(),NOW,False,['e'],policy()).reason=='disabled'
def test_empty_no_call():
    s=EnrichmentState();assert decide_run(s,NOW,True,[],policy()).reason=='no_new_data'
    assert s.next_ai_due_at is None
def test_due_is_exact_14_days_across_month():
    s=EnrichmentState();complete_at(s,NOW)
    assert s.next_ai_due_at=='2026-11-08T00:00:00+00:00'
    fresh=policy(checked_at='2026-11-01T00:00:00+00:00',expires_at='2026-11-15T00:00:00+00:00')
    assert decide_run(s,datetime(2026,11,7,23,59,tzinfo=timezone.utc),True,['e'],fresh).reason=='not_due'
    assert decide_run(s,datetime(2026,11,8,tzinfo=timezone.utc),True,['e'],fresh).allowed
def test_pending_same_input_no_call():
    s=EnrichmentState(batches={'b':Batch('b','hash',['e'],status='pending_review')})
    assert decide_run(s,NOW,True,['e'],policy()).reason=='pending_review'
def test_budget_counts_ambiguous_reservation():
    s=EnrichmentState(batches={'b':Batch('b','h',['old'],status='ambiguous',reserved_usd='1.90',reservation_month='2026-09')})
    assert decide_run(s,NOW,True,['new'],policy()).reason=='budget_exceeded'
def test_expired_price_rejected():
    assert decide_run(EnrichmentState(),NOW,True,['e'],policy(expires_at=NOW.isoformat())).reason=='invalid_price'
@pytest.mark.parametrize('changes',[{'input_usd_per_million':'NaN'},{'output_usd_per_million':'-1'},{'model':'unknown'},{'caps_verified':False},{'checked_at':'2026-10-26T00:00:00+00:00'}])
def test_invalid_price_rejected(changes):
    assert decide_run(EnrichmentState(),NOW,True,['e'],policy(**changes)).reason=='invalid_price'
def test_conservative_reservation_and_monthly_actual():
    p=policy();assert estimate_reservation(100000,p)==Decimal('0.0372')
    s=EnrichmentState(monthly_ledger={'2026-10':{'actual_usd':'1.99'}})
    assert decide_run(s,NOW,True,['e'],p).reason=='budget_exceeded'
def test_reserve_never_overwrites_unresolved_batch():
    s=EnrichmentState();b=Batch('b','h',['e'],reserved_usd='0.1')
    updated=reserve(s,b,NOW)
    assert not s.batches and updated.batches['b'].reservation_month=='2026-10'
    with pytest.raises(ValueError):reserve(updated,b,NOW)
