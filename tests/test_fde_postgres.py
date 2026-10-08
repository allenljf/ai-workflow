"""Explicit opt-in synthetic PostgreSQL integration; never connect implicitly."""
import os,subprocess,sys,uuid
from pathlib import Path
import pytest
import fde_support
DSN=os.environ.get('FDE_TEST_POSTGRES_DSN')
pytestmark=pytest.mark.skipif(not DSN,reason='FDE_TEST_POSTGRES_DSN not supplied; PostgreSQL unverified')
@pytest.fixture
def stores():
 import psycopg
 from psycopg import sql
 from fde_lab.postgres import PostgresJobStore,PostgresRagStore
 schema='lab_'+uuid.uuid4().hex
 with psycopg.connect(DSN,autocommit=True) as c:
  c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
  c.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
  c.execute(Path('examples/fde/deploy/postgres.sql').read_text(),prepare=False)
 # Only test admin session sets ROLE. Runtime DSN must authenticate as that nonowner role.
 dsn=psycopg.conninfo.make_conninfo(DSN,options=f"-c search_path={schema},public -c role=fde_worker")
 try:yield PostgresJobStore(dsn),PostgresRagStore(dsn),dsn,schema
 finally:
  with psycopg.connect(DSN,autocommit=True) as c:c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

def test_postgres_tenant_policies_and_idempotency_constraints(stores):
 import psycopg
 jobs,rag,dsn,schema=stores
 j=jobs.submit('one','key',{'operation':'import'},100,1000)
 assert jobs.submit('one','key',{'operation':'import'},100,1000)['id']==j['id']
 with pytest.raises(ValueError):jobs.submit('one','key',{'operation':'delete'},100,1000)
 with pytest.raises(KeyError):jobs.get('two',j['id'])
 appdsn=psycopg.conninfo.make_conninfo(DSN,options=f"-c search_path={schema},public -c role=fde_app")
 with psycopg.connect(appdsn) as c:
  c.execute("SELECT set_config('fde.tenant',%s,true)",('two',))
  assert c.execute('SELECT count(*) FROM jobs').fetchone()[0]==0
  with pytest.raises(psycopg.errors.InsufficientPrivilege):c.execute("INSERT INTO jobs(id,tenant,key) VALUES('forged','one','x')")

@pytest.mark.parametrize('case',[
 'test_expired_worker_cannot_checkpoint_after_takeover','test_duplicate_payload_conflict_and_tenant_isolation','test_ambiguous_timeout_does_not_retry','test_attempt_budget_deadline_cancel_stop_work','test_transient_backoff_and_safe_checkpoint_cancel','test_cancelled_crashed_worker_settles_at_lease_expiry','test_inflight_external_call_becomes_ambiguous_after_crash','test_heartbeat_keeps_ownership_and_completed_external_receipt_resumes'])
def test_same_job_contract_on_postgres(stores,tmp_path,monkeypatch,case):
 import test_fde_jobs as contracts
 jobs,_,_,_=stores
 monkeypatch.setattr(contracts,'Store',lambda:lambda path:jobs)
 getattr(contracts,case)(tmp_path)

def test_process_crash_receipt_survives(stores):
 jobs,_,dsn,_=stores
 j=jobs.submit('one','crash',{'operation':'import'},100,1000)
 script="from fde_lab.postgres import PostgresJobStore; import os; s=PostgresJobStore(os.environ['FDE_CRASH_DSN']); j=s.claim('old',100,1); s.apply_local_step(j['id'],'old',j['lease_version'],'import',{'rows':1},100); os._exit(7)"
 result=subprocess.run([sys.executable,'-c',script],env=os.environ|{'FDE_CRASH_DSN':dsn,'PYTHONPATH':str(fde_support.LAB)})
 assert result.returncode==7
 new=jobs.claim('new',102);jobs.apply_local_step(new['id'],'new',new['lease_version'],'import',{'rows':1},103);jobs.finish(new['id'],'new',new['lease_version'],104)
 assert jobs.effect_count(j['id'])==1 and jobs.get('one',j['id'])['status']=='succeeded'

@pytest.mark.parametrize('case',['test_rag_never_returns_other_tenant_or_superseded_version','test_no_evidence_and_forged_citation_rejected','test_embedding_model_dimension_mismatch_rejected'])
def test_same_rag_contract_on_postgres(stores,tmp_path,monkeypatch,case):
 import test_fde_rag as contracts
 _,rag,_,_=stores;_,fixture,ollama=contracts.components()
 monkeypatch.setattr(contracts,'components',lambda:(lambda path:rag,fixture,ollama))
 getattr(contracts,case)(tmp_path)

def test_runtime_rejects_owner_or_bypass_role(stores):
 import psycopg
 from fde_lab.postgres import PostgresJobStore
 _,_,_,schema=stores
 owner=psycopg.conninfo.make_conninfo(DSN,options=f'-c search_path={schema},public')
 with pytest.raises(ValueError):PostgresJobStore(owner)

def test_concurrent_idempotency_and_claim_are_serialized(stores):
 from concurrent.futures import ThreadPoolExecutor
 jobs,_,_,_=stores
 with ThreadPoolExecutor(4) as pool:
  rows=list(pool.map(lambda _:jobs.submit('one','race',{'operation':'import'},100,1000),range(4)))
 assert len({row['id'] for row in rows})==1
 with ThreadPoolExecutor(4) as pool:
  claimed=list(pool.map(lambda i:jobs.claim('worker-'+str(i),100),range(4)))
 assert sum(row is not None for row in claimed)==1

def test_remote_database_requires_verified_tls(stores):
 from fde_lab.postgres import PostgresJobStore
 with pytest.raises(ValueError):PostgresJobStore('postgresql://user@untrusted.example/database?sslmode=disable')
