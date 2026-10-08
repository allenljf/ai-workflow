"""Tenant-scoped, current-version retrieval with explicit evidence boundaries."""
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
import json, math, re, sqlite3

@contextmanager
def database(path):
    connection=sqlite3.connect(path,timeout=10);connection.row_factory=sqlite3.Row
    try:
        with connection:yield connection
    finally:connection.close()

def vector(value):
    if not isinstance(value,list) or not value or len(value)>8192 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value):raise ValueError('Invalid embedding vector')
    if not any(value):raise ValueError('Zero embedding vector')
    return value

def validate_answer(answer,chunks):
    if not isinstance(answer,dict) or set(answer)!={'status','answer','citations'} or answer['status'] not in {'answered','insufficient_evidence'} or not isinstance(answer['answer'],str) or not isinstance(answer['citations'],list):raise ValueError('Invalid answer schema')
    allowed={(c['id'],c['version']) for c in chunks}
    for c in answer['citations']:
        if not isinstance(c,dict) or set(c)!={'id','version'} or not isinstance(c['id'],str) or type(c['version']) is not int or (c['id'],c['version']) not in allowed:raise ValueError('Unauthorized citation')
    if answer['status']=='answered' and (not answer['citations'] or not answer['answer'].strip()):raise ValueError('Answered without evidence')
    if answer['status']=='insufficient_evidence' and (answer['citations'] or answer['answer']):raise ValueError('Insufficient evidence must be empty')
    return answer

class RagStore:
    def __init__(self,path: Path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with database(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS documents(tenant TEXT,id TEXT,version INTEGER,text TEXT,source_url TEXT,PRIMARY KEY(tenant,id,version))')
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(text,tenant UNINDEXED,id UNINDEXED,version UNINDEXED)')
            db.execute('CREATE TABLE IF NOT EXISTS embedding_profile(model TEXT,digest TEXT,dimensions INTEGER)')
            db.execute('CREATE TABLE IF NOT EXISTS embeddings(tenant TEXT,id TEXT,version INTEGER,vector TEXT,PRIMARY KEY(tenant,id,version))')
    def ingest(self,documents: list[dict]) -> dict:
        for d in documents:
            if not isinstance(d,dict) or set(d)!={'tenant','id','version','text','source_url'} or any(not isinstance(d[k],str) or not d[k].strip() for k in ('tenant','id','text','source_url')) or type(d['version']) is not int or d['version']<1:raise ValueError('Invalid document schema')
            url=urlsplit(d['source_url'])
            if url.scheme!='https' or not url.hostname or url.username or url.password:raise ValueError('Document source must be HTTPS')
        with database(self.path) as db:
            for d in documents:
                old=db.execute('SELECT text,source_url FROM documents WHERE tenant=? AND id=? AND version=?',(d['tenant'],d['id'],d['version'])).fetchone()
                if old and (old['text']!=d['text'] or old['source_url']!=d['source_url']):raise ValueError('Immutable document version differs')
                if not old:
                    db.execute('INSERT INTO documents VALUES (?,?,?,?,?)',(d['tenant'],d['id'],d['version'],d['text'],d['source_url']))
                    db.execute('INSERT INTO document_fts VALUES (?,?,?,?)',(d['text'],d['tenant'],d['id'],d['version']))
        return {'ingested':len(documents),'evidence_level':'synthetic-contract'}
    def search(self,tenant: str,query: str,limit: int=5) -> list[dict]:
        if not isinstance(tenant,str) or not tenant or type(limit) is not int or not 1<=limit<=20 or not isinstance(query,str) or len(query)>4000:raise ValueError('Invalid query')
        tokens=re.findall(r'\w+',query,flags=re.UNICODE)
        if not tokens:return []
        match=' OR '.join('"'+t+'"' for t in tokens)
        with database(self.path) as db:
            rows=db.execute('SELECT d.* FROM document_fts f JOIN documents d ON d.tenant=f.tenant AND d.id=f.id AND d.version=CAST(f.version AS INTEGER) WHERE document_fts MATCH ? AND d.tenant=? AND d.version=(SELECT MAX(x.version) FROM documents x WHERE x.tenant=d.tenant AND x.id=d.id) ORDER BY bm25(document_fts),d.id LIMIT ?', (match,tenant,limit)).fetchall()
        return [dict(r) for r in rows]
    def query(self,tenant: str,query: str,provider,limit: int=5) -> dict:
        chunks=self.search(tenant,query,limit)
        if not chunks:return {'status':'insufficient_evidence','answer':'','citations':[]}
        return validate_answer(provider.generate(chunks,query),chunks)
    def set_embedding(self,tenant,doc_id,version,model,digest,values):
        vector(values)
        if not all(isinstance(v,str) and v for v in (model,digest)):raise ValueError('Embedding identity required')
        profile=(model,digest,len(values))
        with database(self.path) as db:
            if not db.execute('SELECT 1 FROM documents WHERE tenant=? AND id=? AND version=?',(tenant,doc_id,version)).fetchone():raise ValueError('Unknown document')
            old=db.execute('SELECT * FROM embedding_profile').fetchone()
            if old and tuple(old)!=profile:raise ValueError('Embedding profile mismatch; rebuild a separate index')
            if not old:db.execute('INSERT INTO embedding_profile VALUES (?,?,?)',profile)
            db.execute('INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?)',(tenant,doc_id,version,json.dumps(values)))
    def search_embeddings(self,tenant,values,model,digest,limit=5):
        vector(values)
        if not tenant or type(limit) is not int or not 1<=limit<=20:raise ValueError('Invalid embedding query')
        with database(self.path) as db:
            profile=db.execute('SELECT * FROM embedding_profile').fetchone()
            if not profile or tuple(profile)!=(model,digest,len(values)):raise ValueError('Embedding profile mismatch')
            rows=db.execute('SELECT d.*,e.vector FROM embeddings e JOIN documents d USING(tenant,id,version) WHERE d.tenant=? AND d.version=(SELECT MAX(x.version) FROM documents x WHERE x.tenant=d.tenant AND x.id=d.id)',(tenant,)).fetchall()
        scored=[]
        for row in rows:
            item=dict(row);candidate=json.loads(item.pop('vector'));score=sum(a*b for a,b in zip(values,candidate))/(math.sqrt(sum(a*a for a in values))*math.sqrt(sum(a*a for a in candidate)))
            scored.append((score,item))
        return [d for _,d in sorted(scored,key=lambda r:(-r[0],r[1]['id']))[:limit]]
