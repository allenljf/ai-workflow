from dataclasses import replace
from pathlib import Path
import hashlib, shutil, zipfile
import pytest, yaml
from radar.workflows.registry import load_manifest,validate_manifest
from radar.workflows.bundle import build_bundle
ROOT=Path(__file__).parents[1]

def test_legacy_zip_hashes_unchanged(tmp_path):
    for version,sha in [('0.1.0','4f2322e9be952869f21cf87951fe91cd62eb9650eef9eafcbfb522d9ee8467c7'),('0.2.0','ed9649b990da98b2f425806806ab00a12040405973ff83eaf62bdde80ebeb230')]:
        m=load_manifest(ROOT/f'registry/workflows/superpowers-{version}.yaml')
        assert build_bundle(m,ROOT,tmp_path).sha256==sha
        assert 'domain' not in m.to_dict() and 'asset_approvals' not in m.to_dict()

def fde_manifest(root,names,**changes):
    values=dict(id='fde-test',version='0.1.0',domain='fde',upstream_url='https://github.com/allenljf/ai-workflow',upstream_ref='9a4763c694704a76121d44147f6d28893e9f43dd',license='MIT',redistribution_allowed=False,supported_harnesses=['codex'],profile_ids=['fde-general'],bundle_files=names,visibility='public',review_state='approved',adoption_state='candidate',evaluation_ids=[])
    values.update(changes);return validate_manifest(values)

def test_fde_bundle_references_and_domain_isolation(tmp_path):
    p=tmp_path/'skills/fde-solution/SKILL.md';p.parent.mkdir(parents=True);p.write_text('---\nname: fde-solution\ndescription: Use when delivering enterprise AI solutions.\nmetadata:\n  visibility: public\n  review_state: approved\n---\n[contract](references/contract.md)\n')
    r=p.parent/'references/contract.md';r.parent.mkdir();r.write_text('---\nvisibility: public\nreview_state: approved\n---\nReviewed contract\n')
    names=[str(v.relative_to(tmp_path)) for v in (p,r)];m=fde_manifest(tmp_path,names)
    result=build_bundle(m,tmp_path,tmp_path/'.build/zip')
    with zipfile.ZipFile(result.zip_path) as z:assert set(names)<=set(z.namelist())
    for domain in ('android',):
        with pytest.raises(ValueError):build_bundle(replace(m,domain=domain),tmp_path,tmp_path/'.build/other')
    m.bundle_files.append('profiles/company/private.yaml')
    with pytest.raises(ValueError):build_bundle(m,tmp_path,tmp_path/'.build/private')

def test_asset_hash_and_approval_required(tmp_path):
    p=tmp_path/'examples/fde/python/fixtures/sample.json';p.parent.mkdir(parents=True);p.write_text('{"synthetic":true}')
    name=str(p.relative_to(tmp_path));m=fde_manifest(tmp_path,[name])
    with pytest.raises(ValueError):build_bundle(m,tmp_path,tmp_path/'.build/no')
    m.asset_approvals={name:hashlib.sha256(p.read_bytes()).hexdigest()}
    assert build_bundle(m,tmp_path,tmp_path/'.build/yes').included_files
    p.write_text('{"synthetic":false}')
    with pytest.raises(ValueError):build_bundle(m,tmp_path,tmp_path/'.build/tamper')
    p2=tmp_path/'examples/fde/python/runtime/private.json';p2.parent.mkdir();p2.write_text('{}');n2=str(p2.relative_to(tmp_path))
    m.bundle_files=[n2];m.asset_approvals={n2:hashlib.sha256(p2.read_bytes()).hexdigest()}
    with pytest.raises(ValueError):build_bundle(m,tmp_path,tmp_path/'.build/runtime')

def test_owned_lab_package_is_installable_and_historical_retained(tmp_path):
    m=load_manifest(ROOT/'registry/workflows/fde-solution-adapter-0.2.0.yaml')
    report=build_bundle(m,ROOT,tmp_path)
    with zipfile.ZipFile(report.zip_path) as z:
        assert 'bundles/fde/labs-0.2/pyproject.toml' in z.namelist()
        assert 'bundles/fde/labs-0.2/fixtures/dataset.jsonl' in z.namelist()
        assert 'bundles/fde/labs-0.2/fde_lab/jobs.py' in z.namelist()
        z.extractall(tmp_path/'extracted')
    import os,subprocess,sys,json
    env=os.environ|{'PYTHONPATH':str(tmp_path/'extracted/bundles/fde/labs-0.2')}
    for command,filename in [('rag-demo','rag-report.json'),('jobs-demo','jobs-report.json'),('dataset-demo','manifest.json')]:
        output=tmp_path/command
        run=subprocess.run([sys.executable,'-m','fde_lab.cli',command,'--state-dir',str(output)],env=env,capture_output=True,text=True)
        assert run.returncode==0,run.stderr
        assert json.loads((output/filename).read_text())['evidence_level']=='synthetic-contract'
    old=load_manifest(ROOT/'registry/workflows/fde-solution-adapter-0.1.0.yaml')
    assert build_bundle(old,ROOT,tmp_path).sha256=='d062458da74f421bbe294ebbf1f49b8908f2f087f1bde8ed910673dee1a65ff9'

def test_code_asset_is_not_parsed_as_markdown(tmp_path):
    p=tmp_path/'examples/fde/python/fde_lab/sample.py';p.parent.mkdir(parents=True);p.write_text('message = "[notes](not-a-markdown-link)"\n')
    name=str(p.relative_to(tmp_path));m=fde_manifest(tmp_path,[name],asset_approvals={name:hashlib.sha256(p.read_bytes()).hexdigest()})
    assert build_bundle(m,tmp_path,tmp_path/'.build/zip').included_files
