import json

def parse_releases(body: bytes, repo: str) -> list[dict]:
    releases=json.loads(body)
    if not isinstance(releases,list): raise ValueError('Invalid release payload')
    return [{'external_id':str(r['id']),'url':r['html_url'],'title':r.get('name') or r['tag_name'],
        'excerpt':r.get('body') or '', 'published_at':r.get('published_at'),
        'updated_at':r.get('updated_at'),'entity':repo,'version':r['tag_name']}
        for r in releases if not r.get('draft')]
