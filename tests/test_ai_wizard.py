from pathlib import Path
import os,subprocess,json,shutil
from test_wizard import fake_gh
SCRIPT=Path('scripts/setup/ai.sh').resolve()
def test_ai_check_no_writes(tmp_path):
    env,log,secret=fake_gh(tmp_path)
    r=subprocess.run(['bash',str(SCRIPT),'--root',str(tmp_path),'--check'],env=env,text=True,capture_output=True)
    assert r.returncode==0,r.stderr
    assert not secret.exists() and not (tmp_path/'.build').exists()
def test_cancel_never_sets_secret_or_paid(tmp_path):
    env,log,secret=fake_gh(tmp_path)
    r=subprocess.run(['bash',str(SCRIPT),'--root',str(tmp_path)],input='\nowner/source\nn\n',env=env,text=True,capture_output=True)
    assert r.returncode==0,r.stderr
    assert not secret.exists() and 'workflow run' not in log.read_text() and 'AI_ENABLED --body true' not in log.read_text()
def test_token_stdin_and_resume_no_token(tmp_path):
    env,log,secret=fake_gh(tmp_path);env['PYTHONPATH']=str(Path('src').resolve())
    import sys
    (tmp_path/'.venv').symlink_to(Path(sys.executable).parent.parent,target_is_directory=True)
    shutil.copytree('config',tmp_path/'config')
    from radar.store import save_snapshot
    from test_enrichment_input import snapshot
    save_snapshot(tmp_path/'.build/live/snapshot.json',snapshot(1))
    token='synthetic-deepseek-secret'
    values='\nowner/source\ny\n'+token+'\ndeepseek-flash\n0.30\n1.20\ny\n0.50\n2\nn\n'
    r=subprocess.run(['bash',str(SCRIPT),'--root',str(tmp_path)],input=values,env=env,text=True,capture_output=True)
    assert r.returncode==0,r.stderr
    assert secret.read_text()==token
    persisted=''.join(p.read_text() for p in (tmp_path/'.build').glob('ai-*.env'))
    assert token not in persisted+log.read_text()+r.stdout+r.stderr
    assert 'AI_ENABLED --body true' not in log.read_text() and 'workflow run' not in log.read_text()
