import socket
from pathlib import Path
import httpx
import pytest
from radar.fetch import fetch_source
from radar.adapters.manual import read_manual_links
from radar.models import SourceHealth

@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))])

def client_response(status=200,body='',headers=None):
    return httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(status,text=body,headers=headers or {})))

def test_feed_304_keeps_no_new_items(source):
    result=fetch_source(source(),SourceHealth(etag='abc'),client_response(304))
    assert result.status=='not_modified' and result.items==[]

def test_feed_parses_original_link(source):
    result=fetch_source(source(),None,client_response(body=Path('tests/fixtures/feed.xml').read_text()))
    assert result.items[0]['url']=='https://example.com/one'
    assert result.items[0]['published_at']=='2026-10-01T10:00:00+00:00'

def test_source_timeout_returns_failed(source):
    def fail(r): raise httpx.ReadTimeout('do not expose secrets')
    result=fetch_source(source(),None,httpx.Client(transport=httpx.MockTransport(fail)))
    assert result.status=='failed' and result.items==[]
    assert 'secrets' not in result.error

def test_youtube_no_key_is_disabled(source,monkeypatch):
    monkeypatch.delenv('YOUTUBE_API_KEY',raising=False)
    result=fetch_source(source(type='youtube'),None,client_response())
    assert result.status=='disabled'

def test_manual_url_must_be_https(tmp_path):
    p=tmp_path/'links.json'; p.write_text('[{"url":"http://example.com"}]')
    with pytest.raises(ValueError): read_manual_links(p)

def test_unsafe_redirect_rejected(source):
    r=fetch_source(source(),None,client_response(302,headers={'location':'https://127.0.0.1/admin'}))
    assert r.status=='failed'

def test_oversized_response_rejected(source):
    r=fetch_source(source(),None,client_response(body='x'*(2*1024*1024+1)))
    assert r.status=='failed'
