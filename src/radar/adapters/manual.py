from pathlib import Path
from urllib.parse import urlsplit
import json

def read_manual_links(path: Path) -> list[dict]:
    if not path.exists(): return []
    items=json.loads(path.read_text())
    if not isinstance(items,list): raise ValueError('Manual inbox must be a list')
    for item in items:
        url=urlsplit(item.get('url',''))
        if url.scheme!='https' or not url.hostname or url.username or url.password:
            raise ValueError('Manual links must be public HTTPS URLs')
        item['review_state']='pending'
    return items
