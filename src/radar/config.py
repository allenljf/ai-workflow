from dataclasses import dataclass, field
from pathlib import Path
import yaml
from .models import Source

@dataclass
class PublicationConfig:
    allowed_content_roots: list[str]=field(default_factory=lambda:['content/public'])
    site_url: str='http://localhost:4321'
    site_base: str='/'
    export_repo: str=''
    publish_enabled: bool=False
@dataclass
class RadarConfig:
    sources: list[Source]=field(default_factory=list)
    interval_days: int=14
    ai_enabled: bool=False
    max_events_per_batch: int=20
    max_batch_usd: str='0.50'
    max_monthly_usd: str='2'
    max_items_per_source: int=100
    request_timeout_seconds: int=20
    publication: PublicationConfig=field(default_factory=PublicationConfig)

def load_config(root: Path) -> RadarConfig:
    def read(name):
        path=root/name
        data=yaml.safe_load(path.read_text()) if path.exists() else {}
        if data is not None and not isinstance(data,dict): raise ValueError('Config must be a mapping')
        return data or {}
    sources=[Source(**s) for s in read('sources.yaml').get('sources',[])]
    if len({s.id for s in sources})!=len(sources): raise ValueError('Duplicate source ids')
    publication=PublicationConfig(**read('publication.yaml'))
    config=RadarConfig(sources=sources,publication=publication,**read('pipeline.yaml'))
    if config.max_items_per_source<=0 or config.request_timeout_seconds<=0: raise ValueError('Positive limits required')
    if type(config.max_events_per_batch) is not int or not 1<=config.max_events_per_batch<=30 or config.interval_days!=14:raise ValueError('Invalid enrichment limits')
    from .enrich.models import money
    money(config.max_batch_usd);money(config.max_monthly_usd)
    return config
