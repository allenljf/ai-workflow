"""Bounded web discovery. Search reservations are durable before requests."""
from datetime import timedelta,datetime,timezone
import hashlib
import json
import httpx
from ..enrich.models import utc
from ..normalize import canonicalize_url, plain_text

MAX_RESPONSE_BYTES=2_000_000

def source_date(value):
    if not isinstance(value,str):return None
    try:
        date=datetime.fromisoformat(value.replace('Z','+00:00'))
        if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc).isoformat()
    except ValueError:return None

def discover(config,state,client,api_key,now,persist,*,enabled=False,interval_days=14):
    if not enabled:return {'reason':'disabled','candidates':[]}
    if not api_key:return {'reason':'missing_search_key','candidates':[]}
    now=utc(now)
    if type(interval_days) is not int or not 1<=interval_days<=365:raise ValueError('Invalid discovery interval')
    if state.get('last_searched_at'):
        state['next_due_at']=(utc(state['last_searched_at'])+timedelta(days=interval_days)).isoformat()
    if any(a['status'] in {'calling','ambiguous'} for a in state.get('attempts',[])):
        return {'reason':'ambiguous','candidates':[]}
    if state.get('next_due_at') and now<utc(state['next_due_at']):
        return {'reason':'not_due','candidates':state.get('candidates',[])}
    queries=config['queries'];limit=config['max_results']
    if not isinstance(queries,list) or not 1<=len(queries)<=6 or any(not isinstance(q,str) or not 1<=len(q)<=300 for q in queries):raise ValueError('Bounded queries required')
    if type(limit) is not int or not 1<=limit<=5:raise ValueError('Bounded result limit required')
    month=now.strftime('%Y-%m')
    calls=sum(a['month']==month for a in state.get('attempts',[]))
    # Preserve earlier partial results while recovering a known successful search.
    cycle=state.get('cycle',{})
    if not cycle or cycle.get('config_hash')!=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest():
        cycle={'config_hash':hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),'done':[],'candidates':{}}
        state['cycle']=cycle
    remaining=[q for q in queries if q not in cycle['done']]
    if calls+len(remaining)>12:return {'reason':'search_monthly_limit','candidates':[]}
    for query in queries:
        if query in cycle['done']:continue
        attempt={'month':month,'query':query,'started_at':now.isoformat(),'status':'calling'}
        state.setdefault('attempts',[]).append(attempt);persist()
        try:
            with client.stream('POST','https://api.tavily.com/search',headers={'Authorization':'Bearer '+api_key},json={
                'query':query,'search_depth':'basic','auto_parameters':False,'topic':'general',
                'time_range':'month','max_results':limit,'include_answer':False,
                'include_raw_content':'text','include_published_date':True,'include_usage':True},timeout=60,follow_redirects=False) as response:
                response.raise_for_status();raw=bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw)>MAX_RESPONSE_BYTES:raise ValueError('Search response too large')
            value=json.loads(raw)
            if not isinstance(value.get('results'),list):raise ValueError('Invalid search response')
            for row in value['results'][:limit]:
                try:url=canonicalize_url(row['url'])
                except (ValueError,KeyError,TypeError):continue
                if not url.startswith('https://'):continue
                full=row.get('raw_content');text=full or row.get('content') or ''
                candidate={'id':hashlib.sha256(url.encode()).hexdigest(),'url':url,
                    'title':plain_text(row.get('title') or url)[:300],
                    'excerpt':plain_text(text)[:3500],
                    'published_at':source_date(row.get('published_date')),'fetched_at':now.isoformat(),
                    'source_date_kind':'search_estimate',
                    'evidence_level':'retrieved_text_unreviewed' if full else 'search_snippet_only',
                    'query':query}
                previous=cycle['candidates'].get(url)
                if previous is None or (not previous['excerpt'] or candidate['evidence_level']=='retrieved_text_unreviewed'):
                    cycle['candidates'][url]=candidate
            attempt['status']='succeeded';attempt['credits']=value.get('usage',{}).get('credits')
            cycle['done'].append(query);persist()
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            attempt['status']='ambiguous';persist()
            return {'reason':'ambiguous','candidates':[]}
    state['candidates']=list(cycle['candidates'].values())[:30]
    state['last_searched_at']=now.isoformat();state['next_due_at']=(now+timedelta(days=interval_days)).isoformat()
    state.pop('cycle',None);persist()
    return {'reason':'searched','candidates':state['candidates']}
