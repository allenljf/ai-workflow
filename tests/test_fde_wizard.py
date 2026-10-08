import os,subprocess,shutil
from pathlib import Path
SCRIPT=Path('scripts/setup/fde.sh').resolve();ROOT=SCRIPT.parents[2]
def prepared(tmp_path):
 for name in ['scripts/fde-deployment.py','config/fde-deployment.yaml']:
  p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
 (tmp_path/'.venv312/bin').mkdir(parents=True);wrapper=tmp_path/'.venv312/bin/python';wrapper.write_text('#!/bin/sh\nexec '+str(ROOT/'.venv312/bin/python')+' "$@"\n');wrapper.chmod(0o755)
 bin=tmp_path/'fake';bin.mkdir();log=tmp_path/'calls'
 for name in ['gh','gcloud','open','xdg-open']:
  p=bin/name;p.write_text('#!/bin/sh\nprintf "%s\\n" "'+name+' $*" >> "$CALLS"\nexit 1\n');p.chmod(0o755)
 return os.environ|{'PATH':str(bin)+':'+os.environ['PATH'],'CALLS':str(log)},log

def run(root,env,*args,input=''):
 return subprocess.run(['bash',str(SCRIPT),'--root',str(root),*args],input=input,text=True,capture_output=True,env=env)
def test_check_and_cancel_have_no_side_effects(tmp_path):
 env,log=prepared(tmp_path);before=(tmp_path/'config/fde-deployment.yaml').read_bytes()
 r=run(tmp_path,env,'--check');assert r.returncode==0,r.stderr
 r=run(tmp_path,env,input='\ncancel\n');assert r.returncode==0,r.stderr
 assert not log.exists() and not (tmp_path/'.build').exists() and (tmp_path/'config/fde-deployment.yaml').read_bytes()==before

def test_local_does_not_require_gh_gcloud_or_token(tmp_path):
 env,log=prepared(tmp_path);r=run(tmp_path,env,input='\nlocal\n\nn\n')
 assert r.returncode==0,r.stderr
 assert not log.exists() and 'local' in r.stdout

def test_secret_never_appears_in_output_env_or_git(tmp_path):
 env,log=prepared(tmp_path);token='synthetic-secret-dont-store'
 r=run(tmp_path,env,input='\napi-db\n\n'+token+'\n')
 assert r.returncode==0,r.stderr
 assert token not in r.stdout+r.stderr and not (tmp_path/'.env').exists() and not (tmp_path/'.build').exists() and not log.exists()

def test_failed_cloud_checks_never_enable_paid_or_apply(tmp_path):
 env,log=prepared(tmp_path);before=(tmp_path/'config/fde-deployment.yaml').read_bytes()
 r=run(tmp_path,env,input='\ngcp\n');assert r.returncode!=0
 assert (tmp_path/'config/fde-deployment.yaml').read_bytes()==before
 calls=log.read_text();assert 'gcloud auth list' in calls
 assert all(x not in calls for x in ['deploy','create','secret set','variable set','workflow run'])

def test_wizard_library_is_identical_to_template():
 import hashlib
 marker='# STAGES: author this section.'
 assert hashlib.sha256(SCRIPT.read_text().split(marker)[0].encode()).hexdigest()=='36ddf7aa3a7da152768664bddc48451a6a738f44840eb94e1c5cb014c531c02d'

def test_reviewed_cloud_refs_save_only_after_confirmation(tmp_path):
 from test_fde_deployment import cloud
 env,log=prepared(tmp_path)
 gcloud=tmp_path/'fake/gcloud';gcloud.write_text('#!/bin/sh\nprintf "%s\\n" "gcloud $*" >> "$CALLS"\nprintf "synthetic@example.com\\n"\n');gcloud.chmod(0o755)
 fields='project region service image_digest service_account worker_service_account scheduler_account audience database_secret worker_database_secret auth_secret schedule timezone'.split()
 values='\ngcp\n\n'+'\n'.join(cloud()[k] for k in fields)+'\n'
 before=(tmp_path/'config/fde-deployment.yaml').read_bytes()
 cancelled=run(tmp_path,env,input=values+'n\n');assert cancelled.returncode==0,cancelled.stderr
 assert (tmp_path/'config/fde-deployment.yaml').read_bytes()==before
 saved=run(tmp_path,env,input=values+'y\n');assert saved.returncode==0,saved.stderr
 import yaml
 assert yaml.safe_load((tmp_path/'config/fde-deployment.yaml').read_text())==cloud()
 assert all(x not in log.read_text() for x in ['deploy','create','secret set','variable set','workflow run'])
 assert not (tmp_path/'.env').exists() and not (tmp_path/'.build').exists()
