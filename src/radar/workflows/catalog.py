"""Export public adapters using immutable package manifests and reviewed state overlays."""
from dataclasses import fields
from pathlib import Path
import json,yaml
from .registry import load_manifest
from .bundle import build_bundle
from .adoption import AdoptionReview,verify_evaluations
from .evidence import EvaluationRun

STATE_FIELDS={'adoption_state','evaluation_ids','replacement_version','deprecation_reason'}
def export_catalog(root,stage):
    directory=root/'registry/workflows'
    if not directory.exists():return []
    if directory.is_symlink():raise ValueError('Unsafe registry')
    histories={};aliases=[]
    for path in sorted(directory.glob('*.yaml')):
        m=load_manifest(path)
        if m.visibility!='public' or m.review_state!='approved':continue
        if path.stem.endswith('-'+m.version):
            key=(m.id,m.version)
            if key in histories:raise ValueError('Duplicate immutable version')
            histories[key]=m
        else:aliases.append(m)
    overlays={}
    for m in aliases:
        key=(m.id,m.version);original=histories.get(key)
        if original is None:raise ValueError('Alias requires immutable version')
        if any(getattr(m,f.name)!=getattr(original,f.name) for f in fields(m) if f.name not in STATE_FIELDS):raise ValueError('Alias altered immutable material')
        if key in overlays:raise ValueError('Duplicate workflow alias')
        overlays[key]=m
    public_profiles={}
    profile_root=root/'profiles'
    if profile_root.is_symlink():raise ValueError('Unsafe profile directory')
    for p in sorted(profile_root.glob('android/*.yaml'))+sorted(profile_root.glob('fde/*.yaml')):
        if p.is_symlink():raise ValueError('Unsafe profile')
        d=yaml.safe_load(p.read_text())
        if d.get('visibility')=='public' and d.get('review_state')=='approved':public_profiles[d['id']]=p
    rows=[]
    for key,original in sorted(histories.items()):
        m=overlays.get(key,original)
        if not set(m.profile_ids)<=set(public_profiles):continue
        domain=m.domain or 'android'
        if any(p.parent.name!=domain for key,p in public_profiles.items() if key in m.profile_ids):raise ValueError('Profile outside workflow domain')
        adoption_scope=[]
        if m.adoption_state in {'evaluated','trial','approved'}:
            review_path=root/'registry/adoptions'/f'{m.id}-{m.version}.json'
            if review_path.is_symlink() or not review_path.is_file():raise ValueError('Missing adoption attestation')
            data=json.loads(review_path.read_text());review=AdoptionReview(**data['review']);runs=[EvaluationRun(**r) for r in data['runs']]
            if set(m.evaluation_ids)!={r.id for r in runs}:raise ValueError('Evaluation IDs differ')
            verify_evaluations(m,runs,review)
            adoption_scope=list(review.profile_scope)
            if not set(review.profile_scope)<=set(m.profile_ids):raise ValueError('Public adoption scope includes private profile')
        if m.adoption_state=='deprecated' and (not m.deprecation_reason or not m.replacement_version or (m.id,m.replacement_version) not in histories or m.replacement_version==m.version):raise ValueError('Unbound deprecation replacement/reason')
        if not (root/'registry/bundle-locks'/f'{m.id}-{m.version}.json').is_file():raise ValueError('Immutable bundle lock required for public export')
        report=build_bundle(original,root,stage/'bundles')
        rows.append({'domain':domain,'id':m.id,'version':m.version,'upstream_url':m.upstream_url,'upstream_ref':m.upstream_ref,'license':m.license,'supported_harnesses':m.supported_harnesses,'profile_ids':m.profile_ids,'adoption_profile_scope':adoption_scope,'adoption_state':m.adoption_state,'evaluation_ids':m.evaluation_ids,'replacement_version':m.replacement_version,'deprecation_reason':m.deprecation_reason,'download_path':'bundles/'+report.zip_path.name,'sha256':report.sha256,'included_files':report.included_files})
    return rows
