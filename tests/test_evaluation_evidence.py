from dataclasses import replace
import pytest
from radar.workflows.evidence import EvaluationRun,validate_evidence,read_junit
from radar.workflows.evaluate import compare_runs,RunnerBinding,validate_binding

def run(**kw):
    d=dict(id='run-1',workflow_id='superpowers-android-adapter',workflow_version='0.2.0',task_id='retry',spec_hash='a'*64,base_sha='b'*40,head_sha='c'*40,model_version='model-pinned',harness_version='harness-pinned',environment={'jdk':'17','sdk':'35','profile':'android-baseline'},commands=[{'argv':['./gradlew','test'],'exit_code':0}],executed=2,failed=0,skipped=1,acceptance_results={'retry':True},cost=None,human_minutes=None,duration=None,artifact_refs=[{'path':'report.xml','sha256':'d'*64}],provenance='real')
    d.update(kw);return EvaluationRun(**d)

@pytest.mark.parametrize('kw',[{'executed':0},{'failed':1},{'head_sha':'d'*40},{'acceptance_results':{}},{'commands':[{'argv':['./gradlew','test'],'exit_code':1}]}])
def test_bad_evidence_never_complete(kw):
    assert not validate_evidence(run(**kw),'c'*40,{'retry'}).complete

def test_synthetic_can_test_contract_but_not_promote():
    v=validate_evidence(run(provenance='synthetic'),'c'*40,{'retry'})
    assert v.complete and not v.eligible_for_adoption

def test_comparison_pairs_spec_base_environment_and_preserves_unknown_cost():
    a=run(id='baseline',duration=10);b=run(id='candidate',duration=6)
    c=compare_runs([a],[b])
    assert c.pairs[0]['duration_delta']==-4 and c.pairs[0]['cost_delta'] is None
    for different in (replace(b,spec_hash='e'*64),replace(b,base_sha='e'*40),replace(b,environment={'jdk':'21'})):
        assert not compare_runs([a],[different]).pairs

def test_junit_actual_cases_not_success_exit_or_summary(tmp_path):
    p=tmp_path/'test.xml';p.write_text('<testsuites><testsuite tests="99"><testcase name="works"/><testcase name="bad"><failure/></testcase><testcase name="skip"><skipped/></testcase></testsuite></testsuites>')
    assert read_junit([p])=={'executed':2,'failed':1,'skipped':1}
    p.write_text('<testsuite tests="50"/>')
    assert read_junit([p])['executed']==0

def test_binding_needs_existing_fixed_repo_profile_commands_and_env(tmp_path):
    b=RunnerBinding(target_repo=str(tmp_path),base_sha='b'*40,head_sha='c'*40,commands=[['./gradlew','test']],environment={},profile_id='android-baseline',profile_review={'owner':'reviewer','decision':'approved'})
    with pytest.raises(ValueError):validate_binding(b)

def test_bound_runner_collects_fresh_reports_and_rejects_stale(tmp_path):
    import subprocess,sys
    from radar.workflows.evaluate import run_bound
    repo=tmp_path/'repo';repo.mkdir()
    subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(repo),'config','user.name','Fixture'],check=True)
    subprocess.run(['git','-C',str(repo),'config','user.email','fixture@example.invalid'],check=True)
    (repo/'README').write_text('fixture')
    subprocess.run(['git','-C',str(repo),'add','README'],check=True)
    subprocess.run(['git','-C',str(repo),'commit','-m','fixture'],check=True,capture_output=True)
    sha=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    argv=[sys.executable,'-c',"from pathlib import Path;Path('report.xml').write_text('<testsuite><testcase name=\"observed\"/></testsuite>')"]
    env={'fixture':'local process only'}
    b=RunnerBinding(str(repo),sha,sha,[argv],env,'fixture',{'owner':'test','decision':'approved','profile_id':'fixture','commands':[argv],'environment':env})
    result=run_bound(b,['report.xml'],tmp_path/'private')
    assert result['executed']==1 and result['commands'][0]['exit_code']==0
    assert run_bound(b,['report.xml'],tmp_path/'private2')['executed']==1
    b.commands=[[sys.executable,'-c','pass']];b.profile_review['commands']=b.commands
    with pytest.raises(ValueError,match='stale'):run_bound(b,['report.xml'],tmp_path/'private3')
