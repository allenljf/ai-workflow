import pytest
from radar.workflows.tasks import TaskContract,TaskRecord,ready_tasks

def task(id,**kw):
    d=dict(id=id,spec_hash='a'*64,base_sha='b'*40,depends_on=[],read_paths=[],write_paths=[id],resource_locks=[],acceptance=[{'id':'works','description':'Observed behavior'}],validation_commands=[['./gradlew','test']],max_attempts=3,time_budget_minutes=30,token_budget=10000,checkpoint=None,handoff_summary=None)
    d.update(kw)
    return TaskRecord(TaskContract(**d),'pending',None,None,[])

def test_review_and_unintegrated_dependencies_block():
    a=task('a');b=task('b',depends_on=['a'])
    a.status='ready_for_review'
    assert ready_tasks([a,b],'b'*40,set())==[]
    a.status='accepted';a.head_sha='c'*40;a.evidence_ids=['real']
    assert ready_tasks([a,b],'b'*40,set())==[]
    a.integrated_sha='b'*40
    assert ready_tasks([a,b],'b'*40,set())==['b']

def test_cycle_and_missing_dependencies_rejected():
    with pytest.raises(ValueError):ready_tasks([task('a',depends_on=['b']),task('b',depends_on=['a'])],'b'*40,set())
    with pytest.raises(ValueError):ready_tasks([task('a',depends_on=['absent'])],'b'*40,set())

def test_ancestor_paths_and_emulator_conflicts_and_two_limit():
    a=task('a',write_paths=['feature/order'],resource_locks=['emulator:1'])
    b=task('b',read_paths=['feature/order/ui'])
    c=task('c',resource_locks=['emulator:1'])
    assert ready_tasks([a,b,c,task('d'),task('e')],'b'*40,{'emulator:1'})==['a','d']
    assert ready_tasks([a],'b'*40,set())==[]

def test_running_task_reserves_paths_and_resources():
    a=task('a',write_paths=['feature']);a.status='running'
    assert ready_tasks([a,task('b',write_paths=['feature/ui'])],'b'*40,set())==[]

def test_contract_rejects_traversal_shell_and_unbounded_retries():
    for kw in ({'write_paths':['../x']},{'validation_commands':['bash x']},{'max_attempts':4}):
        with pytest.raises(ValueError):task('a',**kw)
