"""Synthetic browser inputs. Never used for public collection."""
from pathlib import Path
from datetime import datetime,timezone
from radar.models import Snapshot,ItemRevision,Event,SourceHealth
from radar.export import export_public
from radar.config import PublicationConfig
now=datetime.now(timezone.utc).isoformat()
s=Snapshot(revisions=[ItemRevision('r1','test','v1','https://example.com/update','<script>alert(1)</script>',now,None,now,'abc',access_scope='public'),ItemRevision('r2','android','v2','https://example.com/android','Android example',now,None,now,'def',access_scope='public')],events=[Event('e1',None,None,['r1']),Event('e2',None,None,['r2'])],health={'test':SourceHealth(last_attempt=now,last_success=now,status='failed',public_metadata=True,topics=['workflow']),'android':SourceHealth(last_attempt=now,last_success=now,status='updated',public_metadata=True,topics=['android'])})
export_public(s,Path('.'),Path('.build/smoke-export'),PublicationConfig())
