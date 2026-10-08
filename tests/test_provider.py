import json
import httpx
import pytest
from radar.enrich.deepseek import DeepSeekProvider
from radar.enrich.provider import ProviderError
from radar.enrich.prompt import build_request
from test_enrichment_input import snapshot
from test_enrichment_gate import policy
def response(**changes):
    return dict(id='request1',model='deepseek-flash',choices=[{'finish_reason':'stop','message':{'content':'{"stories":[]}'}}],usage={'prompt_tokens':100,'completion_tokens':30,'total_tokens':130,'completion_tokens_details':{'reasoning_tokens':0}})|changes
def test_transport_cap_and_usage():
    req=build_request(snapshot(1).events,snapshot(1),policy());observed=[]
    def respond(r):
        observed.append(json.loads(r.content));return httpx.Response(200,json=response())
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result=DeepSeekProvider('fake-secret',client).generate(req)
    assert result.output_tokens==30 and result.reasoning_tokens==0
    assert observed[0]['thinking']=={'type':'disabled'} and observed[0]['max_tokens']==6000
    assert len(observed)==1
@pytest.mark.parametrize('changes',[{'usage':None},{'model':'unknown'},{'usage':{'prompt_tokens':100,'completion_tokens':7000,'total_tokens':7100}},{'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}])
def test_bad_response_not_retried_or_leaked(changes):
    req=build_request(snapshot(1).events,snapshot(1),policy());calls=[]
    with httpx.Client(transport=httpx.MockTransport(lambda r:(calls.append(1) or httpx.Response(200,json=response(**changes))))) as client:
        with pytest.raises(ProviderError) as exc:DeepSeekProvider('fake-secret',client).generate(req)
    assert len(calls)==1 and 'fake-secret' not in str(exc.value)
def test_timeout_once():
    def fail(r):raise httpx.ReadTimeout('private secret body',request=r)
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(ProviderError,match='ambiguous'):DeepSeekProvider('fake-secret',client).generate(build_request(snapshot(1).events,snapshot(1),policy()))
