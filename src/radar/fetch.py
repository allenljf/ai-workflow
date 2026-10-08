import ipaddress
import os
import socket
from urllib.parse import urljoin, urlsplit
import httpx
from .models import FetchResult, FetchStatus, Source, SourceHealth
from .adapters.feeds import parse_feed
from .adapters.github import parse_releases
from .adapters.youtube import parse_uploads

MAX_BYTES=2*1024*1024

def public_url(url: str) -> None:
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):
        raise ValueError('HTTPS public URL required')
    try: addresses=[ipaddress.ip_address(u.hostname)]
    except ValueError:
        addresses=[ipaddress.ip_address(row[4][0]) for row in socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)]
    if not addresses or any(not ip.is_global for ip in addresses): raise ValueError('Non-public destination')

def fetch_source(source: Source, previous: SourceHealth | None, client: httpx.Client) -> FetchResult:
    if not source.enabled: return FetchResult(source.id,FetchStatus.DISABLED)
    if source.type=='youtube' and not os.environ.get('YOUTUBE_API_KEY'):
        return FetchResult(source.id,FetchStatus.DISABLED,error='missing_api_key')
    headers={'User-Agent':'ai-workflow-radar/0.1 (+public metadata collector)'}
    if previous and previous.etag: headers['If-None-Match']=previous.etag
    if previous and previous.last_modified: headers['If-Modified-Since']=previous.last_modified
    url=source.url
    params=None
    if source.type=='youtube':
        url='https://www.googleapis.com/youtube/v3/playlistItems'
        params={'part':'snippet,contentDetails','playlistId':source.options.get('uploads_playlist_id',''),
            'maxResults':50,'key':os.environ['YOUTUBE_API_KEY']}
    try:
        for redirects in range(4):
            public_url(url)
            with client.stream('GET',url,headers=headers,params=params,follow_redirects=False,timeout=20) as response:
                if response.status_code in (301,302,303,307,308):
                    if redirects==3: raise ValueError('Redirect limit')
                    destination=urljoin(url,response.headers['location'])
                    # Do not forward API query keys to redirects.
                    if source.type=='youtube': raise ValueError('API redirect refused')
                    url=destination; continue
                if response.status_code==304:
                    return FetchResult(source.id,FetchStatus.NOT_MODIFIED,etag=response.headers.get('etag') or (previous.etag if previous else None),last_modified=response.headers.get('last-modified') or (previous.last_modified if previous else None))
                response.raise_for_status()
                body=bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body)>MAX_BYTES: raise ValueError('Response size limit')
                if source.type=='feed': items=parse_feed(bytes(body))
                elif source.type=='github': items=parse_releases(bytes(body),source.options['repo'])
                else: items=parse_uploads(bytes(body))
                return FetchResult(source.id,FetchStatus.UPDATED,items[:100],response.headers.get('etag'),response.headers.get('last-modified'))
    except (httpx.HTTPError,ValueError,KeyError,TypeError,OSError) as exc:
        # Exception text/response URL may contain API credentials.
        return FetchResult(source.id,FetchStatus.FAILED,error=type(exc).__name__)
    return FetchResult(source.id,FetchStatus.FAILED,error='redirect_limit')
