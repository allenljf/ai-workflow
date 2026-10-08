from pathlib import Path
import json
import pytest
from radar.export import export_public
from radar.config import PublicationConfig
from radar.models import Snapshot,Event,SourceHealth

def test_approved_only_and_no_private_payload(tmp_path,approved_doc,revision):
    approved_doc(tmp_path)
    private=tmp_path/'content/private';private.mkdir();(private/'secret.md').write_text('PRIVATE_SENTINEL')
    snap=Snapshot(revisions=[revision(excerpt='PRIVATE_SENTINEL')],events=[Event('event',None,None,['r1'])],health={'test':SourceHealth(public_metadata=True,error='SECRET_TOKEN')},inbox=[{'url':'https://private.example'}])
    out=tmp_path/'.build/export'
    export_public(snap,tmp_path,out,PublicationConfig())
    assert (out/'docs/guide.md').exists()
    data=json.loads((out/'radar.json').read_text());assert data['events'][0]['title']=='One'
    assert 'PRIVATE_SENTINEL' not in ''.join(p.read_text() for p in out.rglob('*') if p.is_file())
    assert 'SECRET_TOKEN' not in (out/'radar.json').read_text()

@pytest.mark.parametrize('fm',[{'visibility':'private'},{'review_state':'draft'},{'visibility':None}])
def test_unapproved_excluded(tmp_path,approved_doc,fm):
    approved_doc(tmp_path,**fm);out=tmp_path/'.build/export'
    report=export_public(Snapshot(),tmp_path,out,PublicationConfig())
    assert not (out/'docs/guide.md').exists() and report.excluded_paths

def test_symlink_rejected(tmp_path):
    public=tmp_path/'content/public';public.mkdir(parents=True)
    target=tmp_path/'secret.md';target.write_text('secret');(public/'leak.md').symlink_to(target)
    with pytest.raises(ValueError): export_public(Snapshot(),tmp_path,tmp_path/'.build/export',PublicationConfig())

@pytest.mark.parametrize('body',['[secret](../private/secret.md)','<img src="../private/secret.png">','[x][ref]\n\n[ref]: ../../docs/private.md','[bad](javascript:alert(1))'])
def test_private_links_and_html_rejected(tmp_path,approved_doc,body):
    p=approved_doc(tmp_path);p.write_text(p.read_text()+body)
    with pytest.raises(ValueError): export_public(Snapshot(),tmp_path,tmp_path/'.build/export',PublicationConfig())

def test_previous_export_survives_failure(tmp_path,approved_doc):
    p=approved_doc(tmp_path);out=tmp_path/'.build/export'
    export_public(Snapshot(),tmp_path,out,PublicationConfig());old=(out/'docs/guide.md').read_text()
    p.write_text(p.read_text()+'\n[bad](../private/x.md)')
    with pytest.raises(ValueError):export_public(Snapshot(),tmp_path,out,PublicationConfig())
    assert (out/'docs/guide.md').read_text()==old
