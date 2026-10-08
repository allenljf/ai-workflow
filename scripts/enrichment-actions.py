#!/usr/bin/env python3
"""Free dispatch after collect; private PR reconciliation never calls a model."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from radar.enrich.store import load_state
from radar.enrich.command import durable_checkpoint
def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['dispatch','review']);p.add_argument('--report',type=Path,required=True);p.add_argument('--state-dir',type=Path)
    a=p.parse_args();report=json.loads(a.report.read_text())
    if a.command=='dispatch':
        if os.environ.get('AI_ENABLED')=='true' and (report.get('reason')=='ready' or report.get('drafts')):
            subprocess.run(['gh','workflow','run','enrich.yml','-f','allow_paid=true'],check=True,capture_output=True)
        return
    state=load_state(a.state_dir);persist=durable_checkpoint(Path.cwd(),a.state_dir)
    for draft in report.get('drafts',[]):
        b=state.batches[draft['batch_id']]
        if b.status not in {'pending_review','succeeded'}:continue
        result=subprocess.run([sys.executable,'scripts/open-digest-pr.py','--batch-id',b.id,'--draft',draft['path']],capture_output=True,text=True)
        if result.returncode:
            b.diagnostic='Review PR unavailable; retry PR only, never model';persist(state);continue
        info=json.loads(result.stdout);b.review_pr_url=info['url']
        b.status={'MERGED':'reviewed','CLOSED':'rejected','OPEN':'pending_review'}[info['state']]
        b.diagnostic=None;persist(state)
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError):print('Enrichment coordination failed; durable records retained',file=sys.stderr);sys.exit(2)
