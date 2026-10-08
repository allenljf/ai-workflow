"""Run synthetic local labs; no cloud actions or model downloads."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess
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

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['rag-demo']);parser.add_argument('--state-dir',type=Path,default=Path('.build/fde-labs/rag'));args=parser.parse_args()
    try:print(json.dumps(rag_demo(args.state_dir),ensure_ascii=False,indent=2))
    except ValueError as error:parser.exit(2,str(error)+'\n')

if __name__=='__main__':main()
