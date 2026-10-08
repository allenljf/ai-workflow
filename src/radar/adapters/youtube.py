import json

def parse_uploads(body: bytes) -> list[dict]:
    return [{'external_id':r['contentDetails']['videoId'],
        'url':'https://www.youtube.com/watch?v='+r['contentDetails']['videoId'],
        'title':r['snippet']['title'],'excerpt':r['snippet'].get('description',''),
        'published_at':r['contentDetails'].get('videoPublishedAt'), 'updated_at':None,
        'entity':None,'version':None} for r in json.loads(body).get('items',[])
        if r.get('contentDetails',{}).get('videoId')]
