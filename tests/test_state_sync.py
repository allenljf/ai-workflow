from pathlib import Path
import subprocess,sys,json
SCRIPT=Path('scripts/state-sync.py').resolve()
def git(path,*args):
    return subprocess.run(['git','-C',str(path),*args],check=True,capture_output=True,text=True).stdout.strip()
def run(*args):return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
def write_state(path,label=''):
    (path/'snapshot.json').write_text(json.dumps({'schema_version':1,'revisions':[],'events':[],'health':{},'inbox':[{'label':label}]}))

def test_durable_roundtrip_and_stale_head_rejected(tmp_path):
    remote=tmp_path/'remote';remote.mkdir();git(remote,'init','--bare')
    one=tmp_path/'one';r=run('load','--checkout',one,'--repo',remote)
    assert r.returncode==0,r.stderr;assert json.loads(r.stdout)['head']=='NONE'
    write_state(one,'first');r=run('persist','--checkout',one,'--expected-sha','NONE');assert r.returncode==0,r.stderr
    head=json.loads(r.stdout)['head']
    two=tmp_path/'two';r=run('load','--checkout',two,'--repo',remote);assert r.returncode==0
    assert json.loads((two/'snapshot.json').read_text())['inbox']==[{'label':'first'}]
    write_state(two,'second');assert run('persist','--checkout',two,'--expected-sha',head).returncode==0
    write_state(one,'stale');r=run('persist','--checkout',one,'--expected-sha',head)
    assert r.returncode!=0 and 'changed' in r.stderr.lower()
    three=tmp_path/'three';assert run('load','--checkout',three,'--repo',remote).returncode==0
    assert json.loads((three/'snapshot.json').read_text())['inbox']==[{'label':'second'}]
