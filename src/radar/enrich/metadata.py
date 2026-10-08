import re
from .models import utc
def digest_metadata(meta,path):
    required=('title','batch_id','model','prompt_version','schema_version','enriched_at','reviewed_at')
    if any(not isinstance(meta.get(k),str) or not meta[k] for k in required):raise ValueError('Digest provenance/review metadata required')
    if not re.fullmatch('[a-f0-9]{64}',meta['batch_id']):raise ValueError('Invalid digest batch id')
    enriched=utc(meta['enriched_at']);reviewed=utc(meta['reviewed_at'])
    if reviewed<enriched:raise ValueError('Review predates enrichment')
    return {k:meta[k] for k in required}|{'path':path,'demo':meta.get('demo',False)}
