from datetime import datetime,timezone
import socket,httpx
from radar.config import RadarConfig
from radar.models import Snapshot
from radar.pipeline import collect

def test_partial_failure_keeps_other_source(source,monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('93.184.216.34',443))])
    def response(r):
        if r.url.path=='/bad': return httpx.Response(503)
        return httpx.Response(200,text='<rss version="2.0"><channel><item><guid>x</guid><title>Hi</title><link>https://example.com/x</link></item></channel></rss>')
    c=RadarConfig(sources=[source(),source(id='bad',url='https://example.com/bad')])
    snap=collect(c,Snapshot(),httpx.Client(transport=httpx.MockTransport(response)),datetime(2026,10,8,tzinfo=timezone.utc))
    assert len(snap.events)==1 and snap.health['bad'].status=='failed'
    assert snap.health['test'].public_metadata
