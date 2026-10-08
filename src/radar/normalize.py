from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

class TextExtractor(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style') and self.hidden: self.hidden-=1
    def handle_data(self,data):
        if not self.hidden: self.parts.append(data)

def plain_text(value: str) -> str:
    parser=TextExtractor();parser.feed(str(value))
    return ' '.join(unescape(' '.join(parser.parts)).split())

def canonicalize_url(url: str) -> str:
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password:
        raise ValueError('Unsafe source link')
    query=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    host=u.hostname.lower()
    if u.port not in (None,443): host+=f':{u.port}'
    return urlunsplit(('https',host,u.path or '/',urlencode(query),''))
