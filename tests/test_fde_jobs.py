import json,os,subprocess,sys
import pytest
import fde_support

def Store():
    from fde_lab.jobs import JobStore
    return JobStore

def submit(store,**changes):
    args=dict(tenant='one',key='request-1',payload={'operation':'import'},now=100,deadline=1000,max_attempts=3,max_cost_usd='1')
    args.update(changes);return store.submit(**args)

def test_restart_resumes_without_repeating_receipted_side_effect(tmp_path):
    db=tmp_path/'jobs.db';env=os.environ|{'PYTHONPATH':str(fde_support.LAB)}
    script='''from pathlib import Path
from fde_lab.jobs import JobStore
import os
s=JobStore(Path(os.environ['JOB_DB']))
s.submit('one','one',{'operation':'import'},100,1000)
j=s.claim('worker-old',100,lease_seconds=5)
s.apply_local_step(j['id'],'worker-old',j['lease_version'],'import',{'rows':1},101)
os._exit(7)
'''
    run=subprocess.run([sys.executable,'-c',script],env=env|{'JOB_DB':str(db)})
    assert run.returncode==7
    store=Store()(db);job=store.claim('worker-new',106)
    receipt=store.apply_local_step(job['id'],'worker-new',job['lease_version'],'import',{'rows':1},107)
    assert receipt['rows']==1
    store.finish(job['id'],'worker-new',job['lease_version'],108)
    assert store.get('one',job['id'])['status']=='succeeded'
    assert store.receipts('one',job['id'])=={'import':{'rows':1}}
    assert store.effect_count(job['id'])==1


def test_expired_worker_cannot_checkpoint_after_takeover(tmp_path):
    store=Store()(tmp_path/'db');submit(store)
    old=store.claim('old',100,1);new=store.claim('new',102)
    with pytest.raises(ValueError):store.checkpoint(old['id'],'old',old['lease_version'],'step',{'ok':True},103)
    store.checkpoint(new['id'],'new',new['lease_version'],'step',{'ok':True},103)


def test_duplicate_payload_conflict_and_tenant_isolation(tmp_path):
    store=Store()(tmp_path/'db');job=submit(store)
    assert submit(store)['id']==job['id']
    with pytest.raises(ValueError):submit(store,payload={'operation':'delete'})
    with pytest.raises(KeyError):store.get('two',job['id'])
    assert submit(store,tenant='two')['id']!=job['id']


def test_ambiguous_timeout_does_not_retry(tmp_path):
    store=Store()(tmp_path/'db');submit(store);job=store.claim('worker',100)
    store.fail(job['id'],'worker',job['lease_version'],101,kind='ambiguous')
    assert store.claim('new',200) is None
    assert store.get('one',job['id'])['status']=='ambiguous'


def test_attempt_budget_deadline_cancel_stop_work(tmp_path):
    store=Store()(tmp_path/'db');a=submit(store,max_attempts=1);job=store.claim('worker',100,1)
    assert store.claim('new',102) is None and store.get('one',a['id'])['status']=='failed'
    b=submit(store,key='budget',max_cost_usd='0');job=store.claim('worker',103)
    with pytest.raises(ValueError):store.apply_local_step(job['id'],'worker',job['lease_version'],'cost',{'x':1},104,cost_usd='0.01')
    assert store.effect_count(b['id'])==0
    store.fail(job['id'],'worker',job['lease_version'],104,kind='permanent')
    c=submit(store,key='deadline',deadline=110);assert store.claim('new',111) is None
    assert store.get('one',c['id'])['status']=='failed'
    d=submit(store,key='cancel',now=112);store.cancel('one',d['id'])
    assert store.claim('new',113) is None and store.get('one',d['id'])['status']=='cancelled'


def test_transient_backoff_and_safe_checkpoint_cancel(tmp_path):
    store=Store()(tmp_path/'db');j=submit(store);job=store.claim('worker',100)
    store.fail(job['id'],'worker',job['lease_version'],101,kind='transient')
    assert store.claim('new',101) is None
    new=store.claim('new',104);assert new['attempts']==2
    store.cancel('one',j['id']);store.checkpoint(new['id'],'new',new['lease_version'],'receipt',{'ok':True},105)
    assert store.get('one',j['id'])['status']=='cancelled'

def test_cancelled_crashed_worker_settles_at_lease_expiry(tmp_path):
    store=Store()(tmp_path/'db');job=submit(store);running=store.claim('old',100,1)
    store.cancel('one',job['id'])
    assert store.claim('new',102) is None
    assert store.get('one',job['id'])['status']=='cancelled'


def test_inflight_external_call_becomes_ambiguous_after_crash(tmp_path):
    store=Store()(tmp_path/'db');submit(store);job=store.claim('old',100,1)
    store.begin_external_step(job['id'],'old',job['lease_version'],'charge',100)
    assert store.claim('new',102) is None
    assert store.get('one',job['id'])['status']=='ambiguous'


def test_heartbeat_keeps_ownership_and_completed_external_receipt_resumes(tmp_path):
    store=Store()(tmp_path/'db');submit(store);job=store.claim('old',100,3)
    store.heartbeat(job['id'],'old',job['lease_version'],102,5)
    assert store.claim('new',104) is None
    store.begin_external_step(job['id'],'old',job['lease_version'],'call',104)
    store.checkpoint(job['id'],'old',job['lease_version'],'call',{'receipt':'confirmed'},105)
    resumed=store.claim('new',108)
    assert resumed and store.receipts('one',job['id'])=={'call':{'receipt':'confirmed'}}

def test_jobs_demo_report_survives_real_process_exit(tmp_path):
    env=os.environ|{'PYTHONPATH':str(fde_support.LAB)}
    run=subprocess.run([sys.executable,'-m','fde_lab.cli','jobs-demo','--state-dir',str(tmp_path)],env=env,capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    report=json.loads((tmp_path/'jobs-report.json').read_text())
    assert report['crash_exit_code']==7 and report['effect_count']==1
    assert report['status']=='succeeded' and report['evidence_level']=='synthetic-contract'
