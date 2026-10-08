"""Run synthetic local labs; no cloud actions or model downloads."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,os,sys,uuid
from .rag import RagStore,validate_answer
from .providers import FixtureProvider

def rag_demo(output: Path):
    output.mkdir(parents=True,exist_ok=True)
    fixture=Path(__file__).parents[1]/'fixtures/documents.json'
    documents=json.loads(fixture.read_text());store=RagStore(output/'rag.db');store.ingest(documents)
    provider=FixtureProvider();answer=store.query('demo-one','refund',provider)
    refused=store.query('demo-one','unanswerable',provider)
    authorized=[d for d in documents if d['tenant']=='demo-one' and d['version']==2]
    context=validate_answer(provider.generate(authorized,'refund'),authorized)
    report={'evidence_level':'synthetic-contract','provider':'fixture','generated_at':datetime.now(timezone.utc).isoformat(),'dataset_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'answer':answer,'acceptance':{'tenant_isolation':answer['citations']==[{'id':'refund-policy','version':2}],'unknown_refused':refused['status']=='insufficient_evidence'},'comparison':{'rag':answer,'authorized_long_context':context,'model_quality_claim':False},'limitations':['Fixture validates contracts only; no model quality comparison was measured.','SQLite unicode tokenization does not provide full Chinese word segmentation.','Local model and cloud deployment not tested.']}
    (output/'rag-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

def jobs_demo(output: Path):
    from .jobs import JobStore
    output.mkdir(parents=True,exist_ok=True)
    database_path=output/('run-'+uuid.uuid4().hex)/'jobs.db'
    store=JobStore(database_path);job=store.submit('demo-one','import',{'operation':'import'},100,1000)
    script="""from fde_lab.jobs import JobStore
import os
store=JobStore(os.environ['FDE_DEMO_DB'])
job=store.claim('crashed-worker',100,lease_seconds=5)
store.apply_local_step(job['id'],'crashed-worker',job['lease_version'],'import',{'rows':1},101)
os._exit(7)
"""
    exited=subprocess.run([sys.executable,'-c',script],env=os.environ|{'FDE_DEMO_DB':str(database_path)},capture_output=True,text=True)
    if exited.returncode!=7:raise ValueError('Synthetic crash worker failed before checkpoint')
    resumed=store.claim('recovery-worker',106)
    if not resumed:raise ValueError('Synthetic job could not resume')
    store.apply_local_step(resumed['id'],'recovery-worker',resumed['lease_version'],'import',{'rows':1},107)
    store.finish(resumed['id'],'recovery-worker',resumed['lease_version'],108)
    report={'evidence_level':'synthetic-contract','clock':'controlled epoch values; real child process exit','crash_exit_code':exited.returncode,'status':store.get('demo-one',job['id'])['status'],'effect_count':store.effect_count(job['id']),'receipts':store.receipts('demo-one',job['id']),'database':str(database_path),'limitations':['Atomic local effect only; remote calls require begin_external_step and receipt reconciliation.','No model charge, enterprise data or cloud execution.']}
    (output/'jobs-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def dataset_demo(output: Path):
    from .data import prepare_dataset
    fixture=Path(__file__).parents[1]/'fixtures/dataset.jsonl'
    rows=[json.loads(line) for line in fixture.read_text().splitlines() if line.strip()]
    return prepare_dataset(rows,output,'2026-01-15T00:00:00Z')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['rag-demo','jobs-demo','dataset-demo']);parser.add_argument('--state-dir',type=Path,default=Path('.build/fde-labs/rag'));args=parser.parse_args()
    try:print(json.dumps({'rag-demo':rag_demo,'jobs-demo':jobs_demo,'dataset-demo':dataset_demo}[args.command](args.state_dir),ensure_ascii=False,indent=2))
    except ValueError as error:parser.exit(2,str(error)+'\n')

if __name__=='__main__':main()
