import json
import httpx
from .provider import ProviderResult,ProviderError
from .prompt import request_body,MAX_BYTES
from .models import PricePolicy
from .gate import valid_policy
from datetime import datetime,timezone
class DeepSeekProvider:
    def __init__(self,api_key,client):
        self.api_key=api_key;self.client=client
    def generate(self,request):
        policy=PricePolicy(**request.policy)
        # Runner validates price against its clock; provider also refuses unsupported caps.
        if not self.api_key or policy.caps_verified is not True or request.model!=policy.model or request.max_output_tokens!=policy.max_output_tokens or request.input_upper_bound!=policy.input_token_ceiling or policy.policy_version!='deepseek-nonthinking-2026-10-08':
            raise ProviderError('unsupported provider cap')
        body=request_body(request)
        if len(json.dumps(body,ensure_ascii=False).encode())>MAX_BYTES:raise ProviderError('input limit exceeded')
        try:
            with self.client.stream('POST','https://api.deepseek.com/chat/completions',json=body,headers={'Authorization':'Bearer '+self.api_key},timeout=60,follow_redirects=False) as response:
                response.raise_for_status();raw=bytearray()
                for part in response.iter_bytes():
                    raw.extend(part)
                    if len(raw)>512000:raise ProviderError('ambiguous oversized response')
            value=json.loads(raw)
            usage=value['usage'];choice=value['choices'][0];message=choice['message']
            if value['model']!=request.model or choice['finish_reason']!='stop' or message.get('tool_calls') or message.get('reasoning_content'):raise ValueError('Unsupported response')
            inp=usage['prompt_tokens'];out=usage['completion_tokens'];reason=usage.get('completion_tokens_details',{}).get('reasoning_tokens',0)
            if any(type(n) is not int or n<0 for n in (inp,out,reason)) or inp>request.input_upper_bound or out>request.max_output_tokens or reason!=0 or usage['total_tokens']!=inp+out:raise ValueError('Invalid usage')
            payload=json.loads(message['content'])
            if not isinstance(payload,dict):raise ValueError('Object required')
            return ProviderResult(payload,inp,out,reason,value['id'])
        except ProviderError:raise
        except (httpx.HTTPError,ValueError,KeyError,TypeError,IndexError):
            raise ProviderError('ambiguous provider failure; no automatic retry') from None
