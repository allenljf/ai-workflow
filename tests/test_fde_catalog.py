from pathlib import Path
import json, shutil
import pytest, yaml
from radar.export import export_public
from radar.config import PublicationConfig
from radar.models import Snapshot
ROOT = Path(__file__).parents[1]

def copy_root(tmp_path):
    for name in ('content/public','registry','profiles','bundles','skills'):
        shutil.copytree(ROOT/name,tmp_path/name)
    return tmp_path

def test_fde_export_contains_reachable_approved_guides():
    output=ROOT/'.build/test-fde-catalog'
    export_public(Snapshot(),ROOT,output,PublicationConfig())
    fde=json.loads((output/'fde.json').read_text())
    assert len(fde['skills'])==12
    manifest=json.loads((output/'manifest.json').read_text())
    ids={s['id'] for s in fde['skills']}
    assert 'fde.json' in manifest['files']
    for node in fde['skills']:
        assert 'docs/'+node['guide_path'] in manifest['files']
        assert set(node['prerequisite_ids'])<=ids
        assert node['source_refs'] and all(u.startswith('https://') for u in node['source_refs'])

@pytest.mark.parametrize('bad',['cycle','missing','private','duplicate','path','date'])
def test_cycle_missing_dependency_private_guide_rejected(tmp_path,bad):
    from radar.fde.catalog import load_skills
    root=copy_root(tmp_path)
    path=root/'registry/fde/skills.yaml';data=yaml.safe_load(path.read_text());nodes=data['skills']
    if bad=='cycle':nodes[0]['prerequisite_ids']=[nodes[-1]['id']]
    elif bad=='missing':nodes[0]['prerequisite_ids']=['absent']
    elif bad=='duplicate':nodes.append(nodes[0].copy())
    elif bad=='path':nodes[0]['guide_path']='../../private.md'
    elif bad=='date':nodes[0]['checked_at']='tomorrow'
    elif bad=='private':
        p=root/'content/public'/nodes[0]['guide_path'];p.write_text(p.read_text().replace('visibility: public','visibility: private'))
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError):load_skills(root)

def test_fde_export_failure_preserves_previous(tmp_path):
    root=copy_root(tmp_path);output=root/'.build/export'
    export_public(Snapshot(),root,output,PublicationConfig())
    before=(output/'manifest.json').read_bytes()
    p=root/'registry/fde/skills.yaml';data=yaml.safe_load(p.read_text());data['skills'][0]['prerequisite_ids']=['absent'];p.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError):export_public(Snapshot(),root,output,PublicationConfig())
    assert (output/'manifest.json').read_bytes()==before
