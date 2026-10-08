from dataclasses import dataclass,asdict
from importlib.resources import files
import json
from .select import public_revisions
from ..dedup import digest
PROMPT_VERSION='enrichment-v1'
SCHEMA_VERSION='enrichment-result-v1'
MAX_BYTES=50000
@dataclass
class EnrichRequest:
    batch_id: str
    model: str
    prompt_version: str
    schema_version: str
    event_inputs: list[dict]
    max_output_tokens: int
    policy: dict
    input_upper_bound: int
    topic_map: dict | None=None
    def to_dict(self):
        value=asdict(self)
        if self.topic_map is None:value.pop('topic_map')
        return value
    @classmethod
    def from_dict(cls,value):return cls(**value)
def request_body(request):
    system=files('radar.enrich').joinpath('enrichment-v1.md').read_text()
    return {'model':request.model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps({'untrusted_sources':request.event_inputs},ensure_ascii=False)}],
        'thinking':{'type':'disabled'},'reasoning_effort':'none','max_tokens':request.max_output_tokens,
        'response_format':{'type':'json_object'},'stream':False}
def build_request(events,snapshot,policy,seen_revision_keys=None):
    from .gate import valid_policy
    inputs=[];seen_revision_keys=seen_revision_keys or set()
    req=EnrichRequest('',policy.model,PROMPT_VERSION,SCHEMA_VERSION,inputs,policy.max_output_tokens,asdict(policy),policy.input_token_ceiling)
    from .topics import domains,event_topics
    selected=events[:30]
    multi=len({d for e in selected for d in domains(e,snapshot)})>1
    groups=[[(e,r) for r in public_revisions(e,snapshot) if (r.id,r.content_hash) not in seen_revision_keys] for e in selected]
    pairs=[]
    if multi:
        while any(groups):
            for group in groups:
                if group:pairs.append(group.pop(0))
    else:pairs=[pair for group in groups for pair in group]
    for e,r in pairs:
        if len(inputs)>=40:break
        value={'event_id':e.id,'source_id':r.id,'feed_source_id':r.source_id,'content_hash':r.content_hash,'title':r.title[:300],'excerpt':r.excerpt[:600],'url':r.canonical_url,'kind':'youtube' if 'youtube.com' in r.canonical_url or 'youtu.be' in r.canonical_url else 'text'}
        inputs.append(value)
        if len(json.dumps(request_body(req),ensure_ascii=False).encode())>MAX_BYTES:inputs.pop()
    included={i['event_id'] for i in inputs}
    req.topic_map={e.id:sorted(set(event_topics(e,snapshot)) & {'android','fde','workflow'}) for e in selected if e.id in included}
    identity=[sorted((i['source_id'],i['content_hash']) for i in inputs),req.model,req.prompt_version,req.schema_version]
    req.batch_id=digest(identity)
    if not inputs:raise ValueError('No bounded public inputs')
    return req
