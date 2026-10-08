"""Private state; caller must CAS-push the entire checkpoint before provider calls."""
from pathlib import Path
import json,os,re,tempfile
from .models import EnrichmentState
from ..dedup import digest
def atomic_json(path,value):
    if path.is_symlink():raise ValueError('Symlink state refused')
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.enrich-')
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def result_path(root,batch):
    if not re.fullmatch('[a-f0-9]{64}',batch.id):raise ValueError('Unsafe batch id')
    p=root/'batches'/batch.id/'result.json'
    if any(x.is_symlink() for x in (root,root/'batches',p.parent,p)):raise ValueError('Symlink result refused')
    return p
def load_state(root):
    root=Path(root);path=root/'enrichment-state.json'
    if root.is_symlink() or path.is_symlink():raise ValueError('Symlink state refused')
    if not path.exists():
        if (root/'batches').exists():raise ValueError('Missing enrichment ledger')
        return EnrichmentState()
    try:
        state=EnrichmentState.from_dict(json.loads(path.read_text()))
        for b in state.batches.values():
            if b.result_hash:
                saved=json.loads(result_path(root,b).read_text())
                if digest(saved)!=b.result_hash or saved!=b.result:raise ValueError('Result hash mismatch')
        return state
    except (ValueError,TypeError,KeyError,OSError) as exc:raise ValueError('Corrupt enrichment state; refusing reset') from exc
def save_state(root,state):
    root=Path(root);EnrichmentState.from_dict(state.to_dict())
    if root.is_symlink() or (root/'batches').is_symlink():raise ValueError('Unsafe state root')
    for b in state.batches.values():
        if b.result is not None:
            if digest(b.result)!=b.result_hash:raise ValueError('Invalid result hash')
            atomic_json(result_path(root,b),b.result)
    atomic_json(root/'enrichment-state.json',state.to_dict())
