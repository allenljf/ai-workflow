from dataclasses import dataclass
from importlib.resources import files
import json,re
import jsonschema
from urllib.parse import urlsplit
from .prompt import EnrichRequest
@dataclass
class ValidatedEnrichment:
    payload: dict
    request: EnrichRequest
    verified_claims: list[dict]
    unverified_claims: list[dict]
def validate_result(payload,request):
    schema=json.loads(files('radar.enrich').joinpath('enrichment-result.schema.json').read_text())
    try:jsonschema.validate(payload,schema)
    except jsonschema.ValidationError:raise ValueError('Invalid enrichment schema') from None
    sources={i['source_id']:i for i in request.event_inputs}
    events={i['event_id'] for i in request.event_inputs};seen=set();verified=[];unverified=[]
    for story in payload['stories']:
        event=story['event_id']
        if event not in events or event in seen:raise ValueError('Unknown/duplicate event')
        seen.add(event)
        if story['case_evidence'] in {'reproducible','internal_evaluation'}:raise ValueError('No evaluation record provided')
        for source in story['source_ids']:
            if source not in sources or sources[source]['event_id']!=event:raise ValueError('Unknown/mismatched source')
            url=urlsplit(sources[source]['url'])
            if url.scheme!='https' or not url.hostname or url.username or url.password:raise ValueError('Unsafe source URL')
        for value in [story['why'],story['usage'],story['limitations']]+[c[k] for c in story['claim_evidence'] for k in ('claim','quote')]:
            if re.search(r'<\s*/?\s*[a-zA-Z][^>]*>|\x00|\x1b',value) or re.search(r'\b(?:curl|wget|npm\s+install|pip\s+install|sudo|bash\s+-c)\b|\x60\x60\x60',value,re.I):raise ValueError('Executable/HTML content refused')
        for c in story['claim_evidence']:
            sid=c['source_id']
            if sid not in story['source_ids']:raise ValueError('Claim source not declared')
            quote=c['quote']
            if c['kind']=='source':
                if not quote.strip() or not any(quote in sources[sid][k] for k in ('title','excerpt')):raise ValueError('Quote mismatch')
                verified.append(c)
            else:
                if quote:raise ValueError('Inference must not pretend to quote')
                unverified.append(c)
    if request.knowledge:
        if 'landscape_updates' not in payload:raise ValueError('Landscape comparison missing')
        from ..knowledge.revisions import validate_updates
        validate_updates(payload['landscape_updates'],request.knowledge,sources)
    elif payload.get('landscape_updates'):raise ValueError('Landscape baseline missing')
    return ValidatedEnrichment(payload,request,verified,unverified)
