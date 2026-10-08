from pathlib import Path
import json,socket
import httpx,yaml
from radar.cli import main

def configured(tmp_path):
    c=tmp_path/'config';c.mkdir();(c/'sources.yaml').write_text(yaml.safe_dump({'sources':[{'id':'test','type':'feed','url':'https://example.com/feed','public_metadata':True}]}));return c

def test_collect_twice_and_failure_exit(tmp_path,monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('93.184.216.34',443))])
    c=configured(tmp_path);state=tmp_path/'.build/snapshot.json'
    client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,text=Path('tests/fixtures/feed.xml').read_text())))
    args=['collect','--config',str(c),'--state',str(state)]
    assert main(args,client)==0;assert main(args,client)==0
    assert len(json.loads(state.read_text())['revisions'])==1
    bad=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503)))
    assert main(args,bad)==3
    saved=json.loads(state.read_text());assert len(saved['events'])==1 and saved['health']['test']['status']=='failed'

def test_corrupt_cli_state_unchanged(tmp_path):
    c=configured(tmp_path);p=tmp_path/'.build/state.json';p.parent.mkdir();p.write_text('{bad')
    assert main(['collect','--config',str(c),'--state',str(p)])==2
    assert p.read_text()=='{bad'

def test_validate_export_empty(tmp_path):
    c=configured(tmp_path);p=tmp_path/'.build/state.json'
    assert main(['validate','--state',str(p)])==0
    assert main(['export','--config',str(c),'--state',str(p),'--output',str(tmp_path/'.build/export')])==0
