import threading,json
import httpx,pytest
import fde_support

def test_real_http_auth_idempotency_and_tenant_schema(tmp_path):
 from fde_lab.api import create_server
 from fde_lab.jobs import JobStore
 from fde_lab.rag import RagStore
 server=create_server('127.0.0.1',0,JobStore(tmp_path/'jobs.db'),RagStore(tmp_path/'rag.db'),{'synthetic-one':'one','synthetic-two':'two'})
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}') as c:
   assert c.get('/health').status_code==200
   assert c.post('/jobs',json={'operation':'import'}).status_code==401
   h={'Authorization':'Bearer synthetic-one','Idempotency-Key':'a'}
   first=c.post('/jobs',headers=h,json={'operation':'import'});assert first.status_code==201
   assert c.post('/jobs',headers=h,json={'operation':'import'}).json()==first.json()
   assert c.post('/jobs',headers=h,json={'operation':'analyze'}).status_code==409
   assert c.post('/jobs',headers=h,json={'tenant':'two','operation':'import'}).status_code==400
   assert c.get('/jobs/'+first.json()['id'],headers={'Authorization':'Bearer synthetic-two'}).status_code==404
   assert c.post('/jobs/'+first.json()['id']+'/cancel',headers=h,json={}).json()['status']=='cancelled'
   assert c.post('/jobs/'+first.json()['id']+'/cancel',headers=h).status_code==200
   assert c.post('/rag/query',headers=h,json={'query':'unknown'}).json()['status']=='insufficient_evidence'
 finally:server.shutdown();server.server_close();thread.join()
