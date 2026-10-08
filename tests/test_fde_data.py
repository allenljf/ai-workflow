import json, os,subprocess,sys
import pytest
import fde_support

def rows():return [dict(id=str(i),group_id=g,timestamp=t,prompt=p,completion='synthetic-'+str(i)) for i,(g,t,p) in enumerate([('a','2026-01-01T00:00:00Z','order one'),('b','2026-01-02T00:00:00Z','order two'),('c','2026-02-01T00:00:00Z','order three'),('d','2026-03-01T00:00:00Z','order four')])]

def prepare(values,output):
    from fde_lab.data import prepare_dataset
    return prepare_dataset(values,output,'2026-01-15T00:00:00Z')

@pytest.mark.parametrize('kind',['duplicate','group-time','missing','timestamp'])
def test_duplicate_group_and_time_leakage_refused(tmp_path,kind):
    values=rows()
    if kind=='duplicate':values[1]['prompt']=values[0]['prompt'];values[1]['completion']=values[0]['completion']
    elif kind=='group-time':values[3]['group_id']='a'
    elif kind=='missing':values[0].pop('completion')
    elif kind=='timestamp':values[0]['timestamp']='tomorrow'
    with pytest.raises(ValueError):prepare(values,tmp_path/'output')
    assert not (tmp_path/'output').exists()

def test_dataset_hash_and_split_manifest_reproducible(tmp_path):
    first=prepare(rows(),tmp_path/'one');second=prepare(list(reversed(rows())),tmp_path/'two')
    assert first==second
    assert first['counts']=={'train':2,'validation':1,'holdout':1}
    assert json.loads((tmp_path/'one/train.json').read_text())[0]['group_id']=='a'
    assert json.loads((tmp_path/'one/holdout.json').read_text())[0]['group_id']=='d'
    assert len(first['dataset_sha256'])==64
    assert first['training']['dry_run'] is True


def test_training_dry_run_has_no_network_or_weights(tmp_path):
    env=os.environ|{'PYTHONPATH':str(fde_support.LAB),'HF_HUB_OFFLINE':'1'}
    result=subprocess.run([sys.executable,'-m','fde_lab.cli','dataset-demo','--state-dir',str(tmp_path)],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    manifest=json.loads((tmp_path/'manifest.json').read_text())
    assert manifest['training']['dry_run'] is True
    assert not list(tmp_path.rglob('*.safetensors'))
    assert manifest['evidence_level']=='synthetic-contract'
