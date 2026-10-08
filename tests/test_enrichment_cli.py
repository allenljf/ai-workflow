import json,os,subprocess,sys
from pathlib import Path
from radar.cli import main
from radar.store import save_snapshot
from radar.enrich.store import save_state,load_state
from radar.enrich.models import EnrichmentState
from test_enrichment_input import snapshot
from test_enrichment_gate import policy,NOW
from test_enrichment_recovery import FixtureProvider
def prepared(tmp_path,enabled=False):
    from dataclasses import asdict
    import yaml
    config=tmp_path/'config';config.mkdir()
    (config/'pipeline.yaml').write_text('ai_enabled: '+str(enabled).lower()+'\n')
    (config/'model-pricing.yaml').write_text(yaml.safe_dump(asdict(policy())))
    state=tmp_path/'.build/state';state.mkdir(parents=True);save_snapshot(state/'snapshot.json',snapshot(1))
    return config,state
def test_dry_run_without_token_success(tmp_path,capsys):
    config,state=prepared(tmp_path)
    assert main(['enrich','--config',str(config),'--state-dir',str(state),'--dry-run'],now=NOW)==0
    report=json.loads(capsys.readouterr().out)
    assert report['model_calls']==0 and report['reason']=='disabled'
    assert not (state/'enrichment-state.json').exists()
def test_default_paid_denied(tmp_path,capsys):
    config,state=prepared(tmp_path,True);p=FixtureProvider()
    assert main(['enrich','--config',str(config),'--state-dir',str(state)],now=NOW,enrichment_provider=p)==0
    assert p.calls==0 and json.loads(capsys.readouterr().out)['mode']=='dry-run'
def test_paid_requires_durable_git_or_injected_cas(tmp_path):
    config,state=prepared(tmp_path,True);p=FixtureProvider()
    assert main(['enrich','--config',str(config),'--state-dir',str(state),'--allow-paid'],now=NOW,enrichment_provider=p)==2
    assert p.calls==0
def test_fake_roundtrip_and_rejected_not_repaid(tmp_path,capsys):
    config,state=prepared(tmp_path,True);p=FixtureProvider()
    durable=lambda s:save_state(state,s)
    args=['enrich','--config',str(config),'--state-dir',str(state),'--allow-paid']
    assert main(args,now=NOW,enrichment_provider=p,enrichment_persist=durable)==0
    report=json.loads(capsys.readouterr().out);assert len(report['drafts'])==1
    draft=Path(report['drafts'][0]['path']);assert 'review_state: draft' in draft.read_text()
    s=load_state(state);b=next(iter(s.batches.values()));b.status='rejected';save_state(state,s)
    assert main(args,now=NOW,enrichment_provider=p,enrichment_persist=durable)==0
    assert p.calls==1
def test_same_batch_pr_one_and_closed_never_reopened(tmp_path):
    script=Path('scripts/open-digest-pr.py').resolve();batch='a'*64
    root=tmp_path/'repo';root.mkdir()
    subprocess.run(['git','init','--initial-branch=main',str(root)],check=True,capture_output=True)
    for args in [('config','user.name','Test'),('config','user.email','test@example.com')]:
        subprocess.run(['git','-C',str(root),*args],check=True)
    (root/'README.md').write_text('base');subprocess.run(['git','-C',str(root),'add','README.md'],check=True);subprocess.run(['git','-C',str(root),'commit','-m','base'],check=True,capture_output=True)
    remote=tmp_path/'remote';subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True);subprocess.run(['git','-C',str(root),'remote','add','origin',str(remote)],check=True)
    draft=tmp_path/'draft.md';draft.write_text('---\nreview_state: draft\nvisibility: private\nbatch_id: '+batch+'\n---\nprivate draft')
    bin=tmp_path/'bin';bin.mkdir();count=tmp_path/'count';record=tmp_path/'pr.json'
    gh=bin/'gh';gh.write_text('#!/usr/bin/env python3\nimport os,json,sys\nfrom pathlib import Path\np=Path(os.environ["PR_RECORD"])\nif sys.argv[1:3]==["repo","view"]:print("true")\nelif sys.argv[1:3]==["pr","list"]:print(p.read_text() if p.exists() else "[]")\nelif sys.argv[1:3]==["pr","create"]:\n Path(os.environ["PR_COUNT"]).write_text("created")\n p.write_text(json.dumps([{"url":"https://github.com/owner/source/pull/1","state":"OPEN","headRefName":"digest/'+batch+'","baseRefName":"main"}]))\n print("https://github.com/owner/source/pull/1")\n');gh.chmod(0o755)
    env=os.environ|{'PATH':str(bin)+':'+os.environ['PATH'],'PR_RECORD':str(record),'PR_COUNT':str(count)}
    def run():return subprocess.run([sys.executable,str(script),'--batch-id',batch,'--draft',str(draft)],cwd=root,env=env,capture_output=True,text=True)
    first=run();assert first.returncode==0,first.stderr
    count.unlink();second=run();assert second.returncode==0,second.stderr
    assert not count.exists()
    record.write_text(json.dumps([{'url':'https://github.com/owner/source/pull/1','state':'CLOSED','headRefName':'digest/'+batch,'baseRefName':'main'}]))
    assert run().returncode==0 and not count.exists()
