import os,json,subprocess,sys
from pathlib import Path
SCRIPT=Path('scripts/enrichment-actions.py').resolve()
def test_dispatch_due_and_pending_but_never_disabled(tmp_path):
    bin=tmp_path/'bin';bin.mkdir();calls=tmp_path/'calls'
    gh=bin/'gh';gh.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\n');gh.chmod(0o755)
    env=os.environ|{'PATH':str(bin)+':'+os.environ['PATH'],'CALLS':str(calls)}
    report=tmp_path/'report.json'
    for reason,drafts,enabled,want in [('ready',[],False,False),('not_due',[],True,False),('ready',[],True,True),('pending_review',[{'batch_id':'b'}],True,True)]:
        calls.unlink(missing_ok=True);report.write_text(json.dumps({'reason':reason,'drafts':drafts}))
        r=subprocess.run([sys.executable,str(SCRIPT),'dispatch','--report',str(report)],env=env|{'AI_ENABLED':str(enabled).lower()},capture_output=True,text=True)
        assert r.returncode==0,r.stderr
        assert calls.exists()==want
