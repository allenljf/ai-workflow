"""Strict, non-secret deployment configuration; never executes commands."""
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import re,yaml
LOCAL={'schema_version','profile'}
CLOUD=LOCAL|{'project','region','service','image_digest','service_account','worker_service_account','scheduler_account','audience','database_secret','worker_database_secret','auth_secret','allow_unauthenticated','schedule','timezone'}
def load_deployment(path:Path)->dict:
    if path.is_symlink():raise ValueError('Symlink configuration refused')
    value=yaml.safe_load(path.read_text())
    return validate(value)
def validate(value):
    if not isinstance(value,dict) or value.get('schema_version')!=1:raise ValueError('Invalid deployment schema')
    if value.get('profile')=='local-sqlite':
        if set(value)!=LOCAL:raise ValueError('Unexpected local fields')
        return value
    if value.get('profile')!='gcp-postgres' or set(value)!=CLOUD:raise ValueError('Invalid cloud fields; secret values are forbidden')
    def matches(key,pattern):
        if not isinstance(value[key],str) or not re.fullmatch(pattern,value[key]):raise ValueError('Invalid '+key)
    matches('project',r'[a-z][a-z0-9-]{4,28}[a-z0-9]')
    matches('region',r'[a-z]+-[a-z]+[0-9]')
    matches('service',r'[a-z][a-z0-9-]{0,40}[a-z0-9]')
    matches('image_digest',r'[a-z0-9-]+-docker\.pkg\.dev/[a-z0-9/-]+@sha256:[a-f0-9]{64}')
    for key in ('service_account','worker_service_account','scheduler_account'):matches(key,r'[a-z][a-z0-9-]+@'+re.escape(value['project'])+r'\.iam\.gserviceaccount\.com')
    for key in ('database_secret','worker_database_secret','auth_secret'):matches(key,r'[a-zA-Z0-9_-]+:[1-9][0-9]*')
    if value['service_account']==value['worker_service_account'] or value['database_secret']==value['worker_database_secret']:raise ValueError('Separate API and worker identities/secrets required')
    uri=urlsplit(value['audience']) if isinstance(value['audience'],str) else None
    if not uri or uri.scheme!='https' or not uri.hostname or not uri.hostname.endswith('.run.app') or uri.username or uri.password or uri.query or uri.fragment or uri.path not in ('','/'):raise ValueError('Invalid API audience')
    if value['allow_unauthenticated'] is not False:raise ValueError('API must require IAM')
    matches('schedule',r'[0-9*/,-]+(?: [0-9*/,-]+){4}')
    try:ZoneInfo(value['timezone'])
    except (ZoneInfoNotFoundError,TypeError):raise ValueError('Invalid timezone') from None
    return value
def deployment_plan(config:dict)->list[list[str]]:
    c=validate(config)
    if c['profile']=='local-sqlite':return []
    common=['--project',c['project'],'--region',c['region']]
    secrets='FDE_DATABASE_URL='+c['database_secret']+',FDE_AUTH_TOKENS='+c['auth_secret']
    job=c['service']+'-worker'
    plan=[
      ['gcloud','run','deploy',c['service'],*common,'--image',c['image_digest'],'--service-account',c['service_account'],'--no-allow-unauthenticated','--set-secrets',secrets,'--set-env-vars','FDE_STORE=postgres','--max-instances','2'],
      ['gcloud','run','jobs','create',job,*common,'--image',c['image_digest'],'--service-account',c['worker_service_account'],'--set-secrets','FDE_DATABASE_URL='+c['worker_database_secret'],'--set-env-vars','FDE_STORE=postgres','--args=--worker','--tasks','1','--max-retries','0','--task-timeout','300s'],
      ['gcloud','scheduler','jobs','create','http',job,'--project',c['project'],'--location',c['region'],'--schedule',c['schedule'],'--time-zone',c['timezone'],'--uri',f"https://run.googleapis.com/v2/projects/{c['project']}/locations/{c['region']}/jobs/{job}:run",'--http-method','POST','--oauth-service-account-email',c['scheduler_account']],
    ]
    plan.append(['gcloud','run','jobs','add-iam-policy-binding',job,*common,'--member','serviceAccount:'+c['scheduler_account'],'--role','roles/run.invoker'])
    for key,account in [('database_secret','service_account'),('auth_secret','service_account'),('worker_database_secret','worker_service_account')]:
        plan.append(['gcloud','secrets','add-iam-policy-binding',c[key].split(':')[0],'--project',c['project'],'--member','serviceAccount:'+c[account],'--role','roles/secretmanager.secretAccessor'])
    return plan
