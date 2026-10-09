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
def test_public_repo_supports_same_batch_pr_and_closed_never_reopened(tmp_path):
    script=Path('scripts/open-digest-pr.py').resolve();batch='a'*64
    root=tmp_path/'repo';root.mkdir()
    subprocess.run(['git','init','--initial-branch=main',str(root)],check=True,capture_output=True)
    for args in [('config','user.name','Test'),('config','user.email','test@example.com')]:
        subprocess.run(['git','-C',str(root),*args],check=True)
    (root/'README.md').write_text('base');subprocess.run(['git','-C',str(root),'add','README.md'],check=True);subprocess.run(['git','-C',str(root),'commit','-m','base'],check=True,capture_output=True)
    remote=tmp_path/'remote';subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True);subprocess.run(['git','-C',str(root),'remote','add','origin',str(remote)],check=True)
    draft=tmp_path/'draft.md';draft.write_text('---\nreview_state: draft\nvisibility: private\nbatch_id: '+batch+'\n---\nprivate draft')
    bin=tmp_path/'bin';bin.mkdir();count=tmp_path/'count';record=tmp_path/'pr.json'
    gh=bin/'gh';gh.write_text('#!/usr/bin/env python3\nimport os,json,sys\nfrom pathlib import Path\np=Path(os.environ["PR_RECORD"])\nif sys.argv[1:3]==["repo","view"]:print("false")\nelif sys.argv[1:3]==["pr","list"]:print(p.read_text() if p.exists() else "[]")\nelif sys.argv[1:3]==["pr","create"]:\n Path(os.environ["PR_COUNT"]).write_text("created")\n p.write_text(json.dumps([{"url":"https://github.com/owner/source/pull/1","state":"OPEN","headRefName":"digest/'+batch+'","baseRefName":"main"}]))\n print("https://github.com/owner/source/pull/1")\n');gh.chmod(0o755)
    env=os.environ|{'PATH':str(bin)+':'+os.environ['PATH'],'PR_RECORD':str(record),'PR_COUNT':str(count)}
    def run():return subprocess.run([sys.executable,str(script),'--batch-id',batch,'--draft',str(draft)],cwd=root,env=env,capture_output=True,text=True)
    first=run();assert first.returncode==0,first.stderr
    count.unlink();second=run();assert second.returncode==0,second.stderr
    assert not count.exists()
    record.write_text(json.dumps([{'url':'https://github.com/owner/source/pull/1','state':'CLOSED','headRefName':'digest/'+batch,'baseRefName':'main'}]))
    assert run().returncode==0 and not count.exists()
def test_human_edited_draft_does_not_block_recovery(tmp_path,capsys):
    config,state=prepared(tmp_path,True);p=FixtureProvider();durable=lambda s:save_state(state,s)
    args=['enrich','--config',str(config),'--state-dir',str(state),'--allow-paid']
    assert main(args,now=NOW,enrichment_provider=p,enrichment_persist=durable)==0
    report=json.loads(capsys.readouterr().out);draft=Path(report['drafts'][0]['path'])
    text=draft.read_text()+'\n人類修正：保留這段審閱意見。\n';draft.write_text(text)
    assert main(args,now=NOW,enrichment_provider=p,enrichment_persist=durable)==0
    assert p.calls==1 and draft.read_text()==text
def test_quoted_false_config_refuses_paid(tmp_path,capsys):
    config,state=prepared(tmp_path,True);(config/'pipeline.yaml').write_text('ai_enabled: "false"\n');p=FixtureProvider()
    assert main(['enrich','--config',str(config),'--state-dir',str(state),'--allow-paid'],now=NOW,enrichment_provider=p,enrichment_persist=lambda s:save_state(state,s))==2
    assert p.calls==0
def test_pr_failure_then_human_edit_and_merge_reconciles(tmp_path,capsys):
    import shutil,importlib.util
    from radar.enrich.command import durable_checkpoint
    from test_state_sync import git
    config,_=prepared(tmp_path,True)
    scripts=tmp_path/'scripts';scripts.mkdir()
    for name in ('state-sync.py','open-digest-pr.py','enrichment-actions.py'):shutil.copyfile(Path('scripts')/name,scripts/name)
    spec=importlib.util.spec_from_file_location('test_sync',scripts/'state-sync.py');sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
    remote=tmp_path/'remote';remote.mkdir();git(remote,'init','--bare')
    state=tmp_path/'.build/state-git';sync.load(state,str(remote));save_snapshot(state/'snapshot.json',snapshot(1))
    p=FixtureProvider();args=['enrich','--config',str(config),'--state-dir',str(state),'--allow-paid']
    assert main(args,now=NOW,enrichment_provider=p,enrichment_persist=durable_checkpoint(tmp_path,state))==0
    first=json.loads(capsys.readouterr().out);report=tmp_path/'.build/report.json';report.write_text(json.dumps(first))
    bin=tmp_path/'bin';bin.mkdir();mode=tmp_path/'mode';mode.write_text('fail')
    gh=bin/'gh';gh.write_text('#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\nif sys.argv[1:3]==["repo","view"]:print("true")\nelif Path(os.environ["PR_MODE"]).read_text()=="fail":sys.exit(1)\nelse:print(json.dumps([{"url":"https://github.com/owner/source/pull/1","state":"MERGED"}]))\n');gh.chmod(0o755)
    env=os.environ|{'PATH':str(bin)+':'+os.environ['PATH'],'PR_MODE':str(mode),'PYTHONPATH':str(Path('src').resolve())}
    def review():
        return subprocess.run([sys.executable,str(scripts/'enrichment-actions.py'),'review','--state-dir',str(state),'--report',str(report)],cwd=tmp_path,env=env,text=True,capture_output=True)
    assert review().returncode==0
    assert next(iter(load_state(state).batches.values())).diagnostic
    draft=Path(first['drafts'][0]['path']);draft.write_text(draft.read_text()+'\n人工審閱修正\n');edited=draft.read_text()
    mode.write_text('merged')
    assert main(args,now=NOW,enrichment_provider=p,enrichment_persist=durable_checkpoint(tmp_path,state))==0
    report.write_text(capsys.readouterr().out)
    r=review();assert r.returncode==0,r.stderr
    assert next(iter(load_state(state).batches.values())).status=='reviewed'
    assert draft.read_text()==edited and p.calls==1
