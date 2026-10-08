"""PostgreSQL contract adapters. Schema migration is an explicit owner operation."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from urllib.parse import urlsplit
import json,re
import psycopg
from psycopg.rows import dict_row
from .jobs import JobStore
from .rag import RagStore,vector

_tenant=ContextVar('fde_tenant',default='')
def scoped(method):
    @wraps(method)
    def call(self,tenant,*args,**kwargs):
        if not isinstance(tenant,str) or not tenant:raise ValueError('Tenant required')
        token=_tenant.set(tenant)
        try:return method(self,tenant,*args,**kwargs)
        finally:_tenant.reset(token)
    return call
class Row(dict):
    def __getitem__(self,key):return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)
    def __iter__(self):return iter(self.values())
class Cursor:
    def __init__(self,cursor):self.cursor=cursor
    def fetchone(self):
        row=self.cursor.fetchone();return Row(row) if row is not None else None
    def fetchall(self):return [Row(r) for r in self.cursor.fetchall()]
    def __iter__(self):return iter(self.fetchall())
class Connection:
    def __init__(self,connection):self.connection=connection
    def execute(self,sql,params=()):
        if sql=='BEGIN IMMEDIATE':sql='SELECT pg_advisory_xact_lock(73412026)'
        else:sql=sql.replace('?','%s')
        return Cursor(self.connection.execute(sql,params))
class Store:
    def __init__(self,dsn:str):
        if not isinstance(dsn,str) or not dsn:raise ValueError('Explicit DSN required')
        connection=psycopg.conninfo.conninfo_to_dict(dsn)
        host=connection.get('host','')
        if host not in {'127.0.0.1','localhost','::1'} and connection.get('sslmode')!='verify-full':raise ValueError('Remote database requires verified TLS')
        self.dsn=dsn
        with self._database() as db:
            role=db.execute('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
            owner=db.execute("SELECT 1 FROM pg_class WHERE oid='jobs'::regclass AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)").fetchone()
            if role[0] or role[1] or owner:raise ValueError('Runtime role must be nonowner without RLS bypass')
            row=db.execute('SELECT version FROM schema_version').fetchone()
            if not row or row[0]!=1:raise ValueError('Apply reviewed schema v1 migration first')
    @contextmanager
    def _database(self):
        # No automatic schema creation or role elevation. Runtime role must be nonowner.
        with psycopg.connect(self.dsn,row_factory=dict_row,connect_timeout=5) as db:
            db.execute("SELECT set_config('fde.tenant',%s,true)",(_tenant.get(),))
            yield Connection(db)
class PostgresJobStore(Store,JobStore):
    submit_with_status=scoped(JobStore.submit_with_status)
    get=scoped(JobStore.get)
    cancel=scoped(JobStore.cancel)
    receipts=scoped(JobStore.receipts)
class PostgresRagStore(Store,RagStore):
    def ingest(self,documents):
        for d in documents:
            if not isinstance(d,dict) or set(d)!={'tenant','id','version','text','source_url'} or any(not isinstance(d[k],str) or not d[k].strip() for k in ('tenant','id','text','source_url')) or type(d['version']) is not int or d['version']<1:raise ValueError('Invalid document schema')
            u=urlsplit(d['source_url'])
            if u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('Document source must be HTTPS')
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            for d in documents:
                db.connection.execute("SELECT set_config('fde.tenant',%s,true)",(d['tenant'],))
                old=db.execute('SELECT text,source_url FROM documents WHERE tenant=? AND id=? AND version=?',(d['tenant'],d['id'],d['version'])).fetchone()
                if old and (old['text']!=d['text'] or old['source_url']!=d['source_url']):raise ValueError('Immutable document version differs')
                if not old:db.execute('INSERT INTO documents VALUES (?,?,?,?,?)',(d['tenant'],d['id'],d['version'],d['text'],d['source_url']))
        return {'ingested':len(documents),'evidence_level':'synthetic-contract'}
    @scoped
    def search(self,tenant,query,limit=5):
        if type(limit) is not int or not 1<=limit<=20 or not isinstance(query,str) or len(query)>4000:raise ValueError('Invalid query')
        tokens=re.findall(r'\w+',query,re.UNICODE)
        if not tokens:return []
        with self._database() as db:
            rows=db.execute("SELECT d.* FROM documents d WHERE tenant=? AND version=(SELECT max(x.version) FROM documents x WHERE x.tenant=d.tenant AND x.id=d.id) AND to_tsvector('simple',d.text) @@ to_tsquery('simple',?) ORDER BY d.id LIMIT ?",(tenant,' | '.join(tokens),limit)).fetchall()
        return [dict(r) for r in rows]
    @scoped
    def set_embedding(self,tenant,doc_id,version,model,digest,values):
        vector(values)
        if not all(isinstance(v,str) and v for v in (model,digest)):raise ValueError('Embedding identity required')
        profile=(model,digest,len(values))
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM documents WHERE tenant=? AND id=? AND version=?',(tenant,doc_id,version)).fetchone():raise ValueError('Unknown document')
            old=db.execute('SELECT model,digest,dimensions FROM embedding_profile').fetchone()
            if old and tuple(old)!=profile:raise ValueError('Embedding profile mismatch; rebuild separate schema')
            if not old:db.execute('INSERT INTO embedding_profile(model,digest,dimensions) VALUES (?,?,?)',profile)
            db.execute('INSERT INTO embeddings VALUES (?,?,?,?::vector) ON CONFLICT(tenant,id,version) DO UPDATE SET vector=excluded.vector',(tenant,doc_id,version,json.dumps(values)))
    @scoped
    def search_embeddings(self,tenant,values,model,digest,limit=5):
        vector(values)
        if type(limit) is not int or not 1<=limit<=20:raise ValueError('Invalid embedding query')
        with self._database() as db:
            profile=db.execute('SELECT model,digest,dimensions FROM embedding_profile').fetchone()
            if not profile or tuple(profile)!=(model,digest,len(values)):raise ValueError('Embedding profile mismatch')
            rows=db.execute('SELECT d.* FROM embeddings e JOIN documents d USING(tenant,id,version) WHERE d.tenant=? AND d.version=(SELECT max(x.version) FROM documents x WHERE x.tenant=d.tenant AND x.id=d.id) ORDER BY e.vector <=> ?::vector,d.id LIMIT ?',(tenant,json.dumps(values),limit)).fetchall()
        return [dict(r) for r in rows]
