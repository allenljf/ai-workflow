from pathlib import Path
import zipfile
import pytest,yaml
from radar.workflows.registry import load_manifest
from radar.workflows.bundle import build_bundle
def manifest(tmp_path,**changes):
    root=tmp_path/'bundles/android-task';root.mkdir(parents=True,exist_ok=True)
    for name in ('README.md','LICENSE.md'):
        (root/name).write_text('---\nvisibility: public\nreview_state: approved\n---\nOwned adapter guide\n')
    data=dict(id='android-task',version='0.1.0',upstream_url='https://github.com/obra/superpowers',upstream_ref='8ca22dba9a94f28898bbce59f2537ff4d87c747d',license='MIT',redistribution_allowed=False,supported_harnesses=['codex','claude-code'],profile_ids=['android-baseline'],bundle_files=['bundles/android-task/README.md','bundles/android-task/LICENSE.md'],visibility='public',review_state='approved',adoption_state='candidate',evaluation_ids=[])
    data.update(changes);p=tmp_path/'manifest.yaml';p.write_text(yaml.safe_dump(data));return load_manifest(p)
@pytest.mark.parametrize('changes',[{'license':'unknown','redistribution_allowed':True},{'license':'MIT','redistribution_allowed':False}])
def test_unlicensed_upstream_embedding_rejected(tmp_path,changes):
    m=manifest(tmp_path,**changes);vendor=tmp_path/'upstream';vendor.mkdir();(vendor/'SKILL.md').write_text('third party')
    m.bundle_files.append('upstream/SKILL.md')
    with pytest.raises(ValueError):build_bundle(m,tmp_path,tmp_path/'.build/bundles')
def test_missing_reference_script_rejected(tmp_path):
    m=manifest(tmp_path)
    (tmp_path/'bundles/android-task/README.md').write_text('---\nvisibility: public\nreview_state: approved\n---\n[runner](scripts/missing.py)')
    with pytest.raises(ValueError):build_bundle(m,tmp_path,tmp_path/'.build/bundles')
@pytest.mark.parametrize('path',['../secret.md','profiles/company/profile.yaml'])
def test_traversal_and_private_paths_rejected(tmp_path,path):
    m=manifest(tmp_path);m.bundle_files.append(path)
    with pytest.raises(ValueError):build_bundle(m,tmp_path,tmp_path/'.build/bundles')
def test_symlink_refused(tmp_path):
    m=manifest(tmp_path);p=tmp_path/'bundles/android-task/README.md';p.unlink();p.symlink_to(tmp_path/'manifest.yaml')
    with pytest.raises(ValueError):build_bundle(m,tmp_path,tmp_path/'.build/bundles')
def test_reproducible_complete_bundle(tmp_path):
    m=manifest(tmp_path);first=build_bundle(m,tmp_path,tmp_path/'.build/one');second=build_bundle(m,tmp_path,tmp_path/'.build/two')
    assert first.sha256==second.sha256
    with zipfile.ZipFile(first.zip_path) as z:
        assert 'manifest.yaml' in z.namelist() and 'SOURCES.md' in z.namelist()
        assert all(not name.startswith('/') and '..' not in name.split('/') for name in z.namelist())

def test_skill_approval_can_use_standard_skill_metadata(tmp_path):
    import dataclasses
    from pathlib import Path
    root=Path(__file__).parents[1]
    manifest=load_manifest(root/'registry/workflows/superpowers.yaml')
    report=build_bundle(manifest,root,tmp_path)
    assert 'skills/android-task/SKILL.md' in report.included_files
