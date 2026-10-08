from pathlib import Path
import json,os,tempfile
from .models import Snapshot,validate_snapshot

def load_snapshot(path: Path) -> Snapshot:
    if not path.exists(): return Snapshot()
    try: return validate_snapshot(json.loads(path.read_text()))
    except (ValueError,TypeError) as exc: raise ValueError('Corrupt state; refusing reset') from exc

def save_snapshot(path: Path, snapshot: Snapshot) -> None:
    validate_snapshot(snapshot.to_dict())
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.snapshot-')
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(snapshot.to_dict(),f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
