from pathlib import Path
import json,os,subprocess
SCRIPT=Path('scripts/setup/github.sh').resolve()

def fake_gh(tmp_path,authenticated=True):
    bin=tmp_path/'bin';bin.mkdir();log=tmp_path/'calls';log.touch();secret=tmp_path/'stdin-secret'
    (bin/'open').write_text('#!/bin/sh\nexit 0\n');(bin/'open').chmod(0o755)
    gh=bin/'gh';gh.write_text('''#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$CALLS"
case "$1 $2" in
 'auth status') exit '''+('0' if authenticated else '1')+''';;
 'repo view') if [[ "$3" == 'owner/source' ]]; then printf 'false\\n'; else exit 1; fi;;
 'secret set') cat > "$SECRET_CAPTURE";;
 'variable set') mkdir -p "$FAKE_VARIABLES"; printf '%s' "$5" > "$FAKE_VARIABLES/$3";;
 'variable get') cat "$FAKE_VARIABLES/$3";;
esac
''');gh.chmod(0o755)
    return os.environ|{'PATH':str(bin)+':'+os.environ['PATH'],'CALLS':str(log),'SECRET_CAPTURE':str(secret),'FAKE_VARIABLES':str(tmp_path/'vars')},log,secret

def prepared(tmp_path):
    b=tmp_path/'.build/export';b.mkdir(parents=True);(b/'manifest.json').write_text('{"files":["radar.json"]}')
    (tmp_path/'.git').mkdir() # --check uses Git for information only; interactive does not write Git.

def test_check_readonly_and_not_logged_in(tmp_path):
    env,log,secret=fake_gh(tmp_path,False)
    result=subprocess.run(['bash',str(SCRIPT),'--root',str(tmp_path),'--check'],env=env,text=True,capture_output=True)
    assert result.returncode!=0
    assert not secret.exists() and not (tmp_path/'.build/setup-state.json').exists()
    assert not any(x in log.read_text() for x in ['secret set','variable set','repo create','workflow run'])

def test_cancel_does_not_enable_publish(tmp_path):
    prepared(tmp_path);env,log,secret=fake_gh(tmp_path)
    values='\nowner/source\n\nhttps://owner.github.io\n/\nn\n'
    r=subprocess.run(['bash',str(SCRIPT),'--root',str(tmp_path)],input=values,env=env,text=True,capture_output=True)
    assert r.returncode==0,r.stderr
    assert not secret.exists()
    state=json.loads((tmp_path/'.build/setup-state.json').read_text())
    assert state['publish_enabled'] is False
    assert 'PUBLISH_ENABLED --body true' not in log.read_text()
    assert 'variable set' not in log.read_text()

def test_public_source_publishes_without_cross_repo_token(tmp_path):
    prepared(tmp_path);env,log,secret=fake_gh(tmp_path)
    values='\nowner/source\n\nhttps://owner.github.io\n/\ny\ny\n'
    r=subprocess.run(['bash',str(SCRIPT),'--root',str(tmp_path)],input=values,env=env,text=True,capture_output=True)
    assert r.returncode==0,r.stderr
    assert not secret.exists()
    assert 'PUBLISH_ENABLED --body true' in log.read_text()
    assert 'Build and deployment → Source 選 GitHub Actions' in r.stdout
    assert not any('secret set' in row for row in log.read_text().splitlines())

def test_custom_domain_root_base_accepted(tmp_path):
    prepared(tmp_path);env,log,secret=fake_gh(tmp_path)
    values='\nowner/source\n\nhttps://example.com\n/\nn\n'
    r=subprocess.run(['bash',str(SCRIPT),'--root',str(tmp_path)],input=values,env=env,text=True,capture_output=True)
    assert r.returncode==0,r.stderr
    assert json.loads((tmp_path/'.build/setup-state.json').read_text())['SITE_BASE']=='/'
