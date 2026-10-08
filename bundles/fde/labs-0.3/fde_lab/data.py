"""Dataset quality and reproducible group/time splitting; no training runtime."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,unicodedata

FIELDS={'id','group_id','timestamp','prompt','completion'}
def instant(value):
    try:
        t=datetime.fromisoformat(value.replace('Z','+00:00'))
        if t.tzinfo is None:raise ValueError()
        return t.astimezone(timezone.utc)
    except (ValueError,TypeError,AttributeError):raise ValueError('Timezone-aware timestamp required') from None

def normalized(value):return re.sub(r'\W+',' ',unicodedata.normalize('NFKC',value).casefold()).strip()
def serialized(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
def sha(value):return hashlib.sha256(value.encode()).hexdigest()

def analyze_dataset(rows: list[dict]) -> dict:
    if not isinstance(rows,list) or not rows:raise ValueError('Dataset must be a nonempty list')
    issues=[];ids=set();texts=set();prompts=[];missing={k:0 for k in sorted(FIELDS)}
    for index,row in enumerate(rows):
        if not isinstance(row,dict) or set(row)!=FIELDS:issues.append({'row':index,'kind':'schema'})
        if not isinstance(row,dict):continue
        invalid=False
        for k in FIELDS:
            if not isinstance(row.get(k),str) or not row[k].strip():missing[k]+=1;invalid=True
        if invalid:continue
        try:instant(row['timestamp'])
        except ValueError:issues.append({'row':index,'kind':'timestamp'})
        text=sha(normalized(row['prompt'])+'\n'+normalized(row['completion']))
        if row['id'] in ids:issues.append({'row':index,'kind':'duplicate_id'})
        if text in texts:issues.append({'row':index,'kind':'normalized_duplicate'})
        prompt=normalized(row['prompt']);tokens=set(prompt.split())
        for previous in prompts:
            prior_tokens=set(previous.split());small=min(len(tokens),len(prior_tokens))
            if prompt==previous or small>=2 and len(tokens & prior_tokens)/small>=.9:
                issues.append({'row':index,'kind':'input_near_duplicate'});break
        prompts.append(prompt)
        ids.add(row['id']);texts.add(text)
    return {'row_count':len(rows),'missingness':missing,'issues':issues}

def prepare_dataset(rows,output: Path,cutoff: str) -> dict:
    quality=analyze_dataset(rows)
    if quality['issues'] or any(quality['missingness'].values()):raise ValueError('Dataset quality checks failed')
    boundary=instant(cutoff);groups={}
    for row in rows:groups.setdefault(row['group_id'],[]).append(row)
    train=[];future=[]
    for group,values in groups.items():
        times=[instant(v['timestamp']) for v in values]
        if min(times)<boundary<=max(times):raise ValueError('Group crosses time boundary')
        if max(times)<boundary:train.extend(values)
        else:future.append((min(times),group,values))
    future.sort(key=lambda v:(v[0],v[1]))
    if not train or len(future)<2:raise ValueError('Need training data and two independent future groups')
    middle=max(1,len(future)//2)
    splits={'train':train,'validation':[r for _,_,values in future[:middle] for r in values],'holdout':[r for _,_,values in future[middle:] for r in values]}
    if max(instant(r['timestamp']) for r in splits['validation'])>=min(instant(r['timestamp']) for r in splits['holdout']):raise ValueError('Validation group crosses holdout time boundary')
    for key in splits:splits[key].sort(key=lambda r:(instant(r['timestamp']),r['group_id'],r['id']))
    all_rows=sorted(rows,key=lambda r:r['id'])
    manifest={'schema_version':1,'evidence_level':'synthetic-contract','dataset_sha256':sha(serialized(all_rows)),'cutoff':boundary.isoformat(),'counts':{k:len(v) for k,v in splits.items()},'split_sha256':{k:sha(serialized(v)) for k,v in splits.items()},'quality':quality,'lineage':{k:sorted({r['group_id'] for r in v}) for k,v in splits.items()},'training':{'dry_run':True,'format':'conversational','method_candidate':'SFT/LoRA; budget/hardware/license/evaluation needed','network_calls':0,'model_downloads':0}}
    output=Path(output)
    files={k+'.json':serialized(v) for k,v in splits.items()}
    files['training-messages.json']=serialized([{'messages':[{'role':'user','content':r['prompt']},{'role':'assistant','content':r['completion']}]} for r in splits['train']])
    files['manifest.json']=serialized(manifest)
    if output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('Unsafe dataset output')
    if output.exists() and any(output.iterdir()):
        if set(p.name for p in output.iterdir())!=set(files) or any((output/k).is_symlink() or not (output/k).is_file() or (output/k).read_text()!=v for k,v in files.items()):raise ValueError('Existing dataset differs; use a new versioned directory')
        return manifest
    output.mkdir(parents=True,exist_ok=True)
    for name,text in files.items():(output/name).write_text(text)
    return manifest
