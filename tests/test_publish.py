import importlib.util
from pathlib import Path
import subprocess
import pytest
SPEC=importlib.util.spec_from_file_location('publisher',Path('scripts/publish-static.py'))

def module():
    m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m);return m

def test_static_export_updates_only_target_and_noop(tmp_path):
    m=module();remote=tmp_path/'remote';remote.mkdir();subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
    dist=tmp_path/'dist';dist.mkdir();(dist/'index.html').write_text('<h1>Public</h1>')
    first=m.publish(dist,str(remote),tmp_path/'one')
    second=m.publish(dist,str(remote),tmp_path/'two')
    assert first==second
    checkout=tmp_path/'check';subprocess.run(['git','clone','--branch','main',str(remote),str(checkout)],check=True,capture_output=True)
    assert (checkout/'.nojekyll').exists() and (checkout/'index.html').read_text()=='<h1>Public</h1>'
    assert not (checkout/'src').exists()

def test_dist_symlink_and_private_file_refused(tmp_path):
    m=module();dist=tmp_path/'dist';dist.mkdir();(dist/'index.html').write_text('public')
    secret=tmp_path/'secret';secret.write_text('token');(dist/'link').symlink_to(secret)
    with pytest.raises(ValueError): m.validate_dist(dist)
    (dist/'link').unlink();(dist/'.env').write_text('token')
    with pytest.raises(ValueError): m.validate_dist(dist)

def test_managed_custom_domain_survives_daily_publication(tmp_path):
    m=module();remote=tmp_path/'remote';remote.mkdir();subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
    dist=tmp_path/'dist';dist.mkdir();(dist/'index.html').write_text('first')
    m.publish(dist,str(remote),tmp_path/'first')
    configured=tmp_path/'configured';subprocess.run(['git','clone','--branch','main',str(remote),str(configured)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(configured),'config','user.name','Test'],check=True)
    subprocess.run(['git','-C',str(configured),'config','user.email','test@example.com'],check=True)
    (configured/'CNAME').write_text('radar.example.com\n')
    subprocess.run(['git','-C',str(configured),'add','CNAME'],check=True)
    subprocess.run(['git','-C',str(configured),'commit','-m','configure domain'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(configured),'push','origin','main'],check=True,capture_output=True)
    (dist/'index.html').write_text('second')
    m.publish(dist,str(remote),tmp_path/'second')
    checkout=tmp_path/'check';subprocess.run(['git','clone','--branch','main',str(remote),str(checkout)],check=True,capture_output=True)
    assert (checkout/'CNAME').read_text()=='radar.example.com\n'
    assert (checkout/'index.html').read_text()=='second'
