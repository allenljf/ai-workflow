from dataclasses import replace
from pathlib import Path
import hashlib,json,shutil,zipfile
import pytest
from radar.workflows.registry import load_manifest
from radar.workflows.adoption import AdoptionReview,transition
from test_evaluation_evidence import run
from radar.export import export_public
from radar.config import PublicationConfig
from radar.models import Snapshot
ROOT=Path(__file__).parents[1]

def review(r=None,**kw):
    r=r or run()
    d=dict(owner='human-owner',decision_at='2026-10-08T00:00:00+00:00',reason='Representative sandbox observations reviewed',profile_scope=['android-baseline'],rollback_version='0.1.0',actor_type='human',evaluation_contracts={r.id:{'spec_hash':r.spec_hash,'base_sha':r.base_sha,'head_sha':r.head_sha,'environment':r.environment,'acceptance_ids':['retry']}})
    d.update(kw);return AdoptionReview(**d)

def manifest():return load_manifest(ROOT/'registry/workflows/superpowers.yaml')

def test_empty_or_synthetic_evidence_cannot_evaluate_or_approve():
    for evidence in ([],[run(provenance='synthetic')]):
        with pytest.raises(ValueError):transition(manifest(),'evaluated',evidence,review())
    with pytest.raises(ValueError):transition(replace(manifest(),adoption_state='trial'),'approved',[run(provenance='synthetic')],review())

def test_order_human_decision_and_immutable_version_binding():
    original=manifest();r=run()
    evaluated=transition(original,'evaluated',[r],review())
    assert original.adoption_state=='candidate' and original.evaluation_ids==[]
    trial=transition(evaluated,'trial',[r],review())
    with pytest.raises(ValueError):transition(trial,'approved',[r],review(actor_type='automation'))
    assert transition(trial,'approved',[r],review()).adoption_state=='approved'
    with pytest.raises(ValueError):transition(replace(original,version='0.3.0'),'evaluated',[r],review())
    with pytest.raises(ValueError):transition(original,'evaluated',[replace(r,spec_hash='e'*64)],review(r))

def test_deprecation_requires_visible_substitute_and_reason():
    with pytest.raises(ValueError):transition(manifest(),'deprecated',[],review())
    d=replace(manifest(),replacement_version='0.3.0',deprecation_reason='Replaced after review')
    assert transition(d,'deprecated',[],review()).replacement_version=='0.3.0'

def test_public_export_pinned_bundle_hash_and_private_exclusion(tmp_path):
    for directory in ['registry','profiles','skills','bundles','content/public']:
        shutil.copytree(ROOT/directory,tmp_path/directory)
    private=tmp_path/'profiles/company/secret.yaml';private.write_text('PRIVATE_PROFILE_SENTINEL')
    case=tmp_path/'content/public/cases/internal.md';case.write_text('---\nvisibility: private\nreview_state: approved\n---\nINTERNAL_CASE_SENTINEL')
    out=tmp_path/'.build/export'
    export_public(Snapshot(),tmp_path,out,PublicationConfig())
    catalog=json.loads((out/'workflows.json').read_text())
    assert len(catalog)==2 and all(r['adoption_state']=='candidate' for r in catalog)
    for row in catalog:
        package=out/row['download_path'];assert hashlib.sha256(package.read_bytes()).hexdigest()==row['sha256']
        with zipfile.ZipFile(package) as z:
            assert not any('company' in n for n in z.namelist())
            assert json.loads(json.dumps(row))['upstream_ref']==manifest().upstream_ref
            assert 'PRIVATE_PROFILE_SENTINEL' not in ''.join(z.read(n).decode() for n in z.namelist())
    assert not (out/'docs/cases/internal.md').exists()

def test_alias_revision_does_not_rewrite_historical_bundle(tmp_path):
    for directory in ['registry','profiles','skills','bundles']:shutil.copytree(ROOT/directory,tmp_path/directory)
    import yaml
    alias=tmp_path/'registry/workflows/superpowers.yaml';data=yaml.safe_load(alias.read_text());data['adoption_state']='deprecated';data['replacement_version']='0.1.0';data['deprecation_reason']='Contract example replacement';alias.write_text(yaml.safe_dump(data))
    out=tmp_path/'.build/export';export_public(Snapshot(),tmp_path,out,PublicationConfig())
    row=next(r for r in json.loads((out/'workflows.json').read_text()) if r['version']=='0.2.0')
    assert row['adoption_state']=='deprecated' and row['deprecation_reason']
    with zipfile.ZipFile(out/row['download_path']) as z:assert yaml.safe_load(z.read('manifest.yaml'))['adoption_state']=='candidate'
