from copy import deepcopy
from datetime import datetime
import httpx
from .config import RadarConfig
from .models import Snapshot,SourceHealth,FetchResult
from .fetch import fetch_source
from .dedup import merge_fetch

def collect(config: RadarConfig, previous: Snapshot, client: httpx.Client, now: datetime) -> Snapshot:
    snapshot=deepcopy(previous)
    current={s.id for s in config.sources}
    for key,h in snapshot.health.items():
        if key not in current: h.public_metadata=False
    for source in config.sources:
        h=snapshot.health.setdefault(source.id,SourceHealth())
        h.public_metadata=source.public_metadata and source.enabled;h.trust_tier=source.trust_tier;h.topics=source.topics
        result=fetch_source(source,h,client)
        result.items=result.items[:config.max_items_per_source]
        try: snapshot=merge_fetch(snapshot,result,now)
        except (ValueError,KeyError,TypeError):
            snapshot=merge_fetch(snapshot,FetchResult(source.id,'failed',error='invalid_item'),now)
    return snapshot
