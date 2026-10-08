import json,subprocess,sys
from pathlib import Path
import pytest,yaml
ROOT=Path(__file__).parents[1]
def cloud():
 return dict(schema_version=1,profile='gcp-postgres',project='sample-project',region='asia-east1',service='fde-api',image_digest='asia-east1-docker.pkg.dev/sample-project/fde/api@sha256:'+'a'*64,service_account='fde-api@sample-project.iam.gserviceaccount.com',worker_service_account='fde-worker@sample-project.iam.gserviceaccount.com',worker_database_secret='fde-worker-database:1',scheduler_account='fde-scheduler@sample-project.iam.gserviceaccount.com',audience='https://fde-api-123.asia-east1.run.app',database_secret='fde-database:1',auth_secret='fde-auth:1',allow_unauthenticated=False,schedule='0 3 * * *',timezone='Asia/Taipei')
def test_local_profile_requires_no_cloud_account(tmp_path):
 from radar.fde.deployment import load_deployment,deployment_plan
 p=tmp_path/'profile.yaml';p.write_text('schema_version: 1\nprofile: local-sqlite\n')
 assert deployment_plan(load_deployment(p))==[]
def test_cloud_profile_requires_identity_private_api_and_pinned_image(tmp_path):
 from radar.fde.deployment import load_deployment,deployment_plan
 for change in [dict(allow_unauthenticated=True),dict(image_digest='image:latest'),dict(audience='http://public.example'),dict(service_account='root'),dict(timezone='bad/zone')]:
  p=tmp_path/'p.yaml';p.write_text(yaml.safe_dump(cloud()|change))
  with pytest.raises(ValueError):load_deployment(p)
 p.write_text(yaml.safe_dump(cloud()));plan=deployment_plan(load_deployment(p))
 assert all(type(argv) is list and argv[0]=='gcloud' for argv in plan)
 assert '--no-allow-unauthenticated' in plan[0] and any('--oauth-service-account-email' in argv for argv in plan)
@pytest.mark.parametrize('change',[dict(secret_value='hidden'),dict(command='rm -rf /'),dict(profile='unknown'),dict(service='x;evil')])
def test_unknown_field_or_secret_value_rejected(tmp_path,change):
 from radar.fde.deployment import load_deployment
 p=tmp_path/'p.yaml';p.write_text(yaml.safe_dump(cloud()|change))
 with pytest.raises(ValueError):load_deployment(p)
def test_dry_run_never_executes_cloud_or_changes_files(tmp_path):
 p=tmp_path/'p.yaml';p.write_text(yaml.safe_dump(cloud()));before=p.read_bytes()
 fake=tmp_path/'gcloud';fake.write_text('#!/bin/sh\ntouch "'+str(tmp_path/'called')+'"\n');fake.chmod(0o755)
 import os
 result=subprocess.run([sys.executable,str(ROOT/'scripts/fde-deployment.py'),'--config',str(p),'--dry-run'],capture_output=True,text=True,env=os.environ|{'PATH':str(tmp_path)+':'+os.environ['PATH']})
 assert result.returncode==0 and p.read_bytes()==before and not (tmp_path/'called').exists()
 assert 'hidden' not in result.stdout and json.loads(result.stdout)['executed'] is False
