"""Small synthetic HTTP reference. Private Cloud Run IAM remains an outer boundary."""
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import argparse,hmac,json,os,time
from .jobs import JobStore
from .rag import RagStore
from .providers import FixtureProvider

def create_server(host,port,jobs,rag,tokens):
    if not isinstance(tokens,dict) or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in tokens.items()):raise ValueError('Invalid server-side identity mapping')
    class Handler(BaseHTTPRequestHandler):
        def setup(self):super().setup();self.connection.settimeout(10)
        def log_message(self,*args):pass
        def respond(self,status,value):
            text=json.dumps(value,allow_nan=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(text)));self.end_headers();self.wfile.write(text)
        def tenant(self):
            auth=self.headers.get('Authorization','');supplied=auth[7:] if auth.startswith('Bearer ') else ''
            for token,tenant in tokens.items():
                if hmac.compare_digest(supplied.encode(),token.encode()):return tenant
            return None
        def body(self):
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=50000:raise ValueError('invalid_schema')
            value=json.loads(self.rfile.read(length))
            if not isinstance(value,dict):raise ValueError('invalid_schema')
            return value
        def dispatch(self,method):
            if method=='GET' and self.path=='/health':return self.respond(200,{'status':'ok','provider':'fixture'})
            tenant=self.tenant()
            if tenant is None:return self.respond(401,{'error':'unauthorized'})
            try:
                if method=='POST' and self.path=='/jobs':
                    payload=self.body();key=self.headers.get('Idempotency-Key','')
                    if set(payload)!={'operation'} or payload['operation'] not in ('import','analyze'):raise ValueError('invalid_schema')
                    now=time.time();job,created=jobs.submit_with_status(tenant,key,payload,now,now+3600)
                    return self.respond(201 if created else 200,job)
                if method=='GET' and self.path.startswith('/jobs/') and self.path.count('/')==2:return self.respond(200,jobs.get(tenant,self.path[6:]))
                if method=='POST' and self.path.startswith('/jobs/') and self.path.endswith('/cancel') and self.path.count('/')==3:
                    if self.headers.get('Content-Length','0')!='0' and self.body():raise ValueError('invalid_schema')
                    return self.respond(200,jobs.cancel(tenant,self.path.split('/')[2]))
                if method=='POST' and self.path=='/rag/query':
                    body=self.body()
                    if set(body)!={'query'} or not isinstance(body['query'],str) or not body['query'].strip():raise ValueError('invalid_schema')
                    return self.respond(200,rag.query(tenant,body['query'],FixtureProvider()))
                return self.respond(404,{'error':'not_found'})
            except KeyError:return self.respond(404,{'error':'not_found'})
            except (ValueError,TypeError):
                # A key conflict is the only user-visible semantic error.
                import sys
                conflict=str(sys.exception())=='Idempotency payload conflict'
                return self.respond(409 if conflict else 400,{'error':'idempotency_conflict' if conflict else 'invalid_schema'})
            except Exception:return self.respond(503,{'error':'dependency_unavailable'})
        def do_GET(self):self.dispatch('GET')
        def do_POST(self):self.dispatch('POST')
    return HTTPServer((host,port),Handler)

def worker(jobs):
    # Synthetic, bounded work only; replace operations through a reviewed adapter.
    owner='fixture-worker-'+str(os.getpid());stop=time.monotonic()+60
    for _ in range(100):
        if time.monotonic()>=stop:break
        job=jobs.claim(owner,time.time())
        if not job:break
        jobs.apply_local_step(job['id'],owner,job['lease_version'],'synthetic-analysis',{'operation':job['payload']['operation'],'evidence_level':'synthetic-contract'},time.time())
        jobs.finish(job['id'],owner,job['lease_version'],time.time())

def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');args=p.parse_args()
    if os.environ.get('FDE_STORE','sqlite')=='postgres':
        from .postgres import PostgresJobStore,PostgresRagStore
        dsn=os.environ['FDE_DATABASE_URL'];jobs=PostgresJobStore(dsn);rag=PostgresRagStore(dsn)
    elif os.environ.get('FDE_STORE','sqlite')=='sqlite':
        root=Path(os.environ.get('FDE_STATE_DIR','.build/fde-labs/api'));jobs=JobStore(root/'jobs.db');rag=RagStore(root/'rag.db')
    else:raise ValueError('Unknown store profile')
    if args.worker:return worker(jobs)
    tokens=json.loads(os.environ.get('FDE_AUTH_TOKENS','{}'))
    create_server(os.environ.get('FDE_BIND','127.0.0.1'),int(os.environ.get('PORT','8080')),jobs,rag,tokens).serve_forever()
if __name__=='__main__':main()
