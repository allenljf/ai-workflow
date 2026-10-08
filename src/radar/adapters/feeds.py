from datetime import datetime, timezone
import calendar
import feedparser

def parse_feed(body: bytes) -> list[dict]:
    feed=feedparser.parse(body)
    if feed.bozo and not feed.entries: raise ValueError('Invalid feed')
    def date(e,key):
        value=e[key] if key in e else None
        return datetime.fromtimestamp(calendar.timegm(value),timezone.utc).isoformat() if value else None
    return [{'external_id':str(e.get('id',e.get('link',''))),'url':e.get('link',''),
        'title':e.get('title','Untitled'),'excerpt':e.get('summary',''),
        'published_at':date(e,'published_parsed'),'updated_at':date(e,'updated_parsed'),
        'entity':None,'version':None} for e in feed.entries if e.get('link')]
