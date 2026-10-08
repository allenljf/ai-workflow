import json, threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import pytest
import fde_support

def components():
    from fde_lab.rag import RagStore
    from fde_lab.providers import FixtureProvider,OllamaProvider
    return RagStore,FixtureProvider,OllamaProvider

def docs():return [dict(id='manual',version=1,tenant='one',text='refund obsolete policy',source_url='https://example.com/old'),dict(id='manual',version=2,tenant='one',text='refund current policy',source_url='https://example.com/new'),dict(id='private',version=1,tenant='two',text='refund secret payroll',source_url='https://example.com/private')]

def test_rag_never_returns_other_tenant_or_superseded_version(tmp_path):
    Store,Fixture,_=components();store=Store(tmp_path/'rag.db');store.ingest(docs())
    answer=store.query('one','refund',Fixture())
    assert answer['citations']==[{'id':'manual','version':2}]
    assert 'secret' not in json.dumps(answer) and 'obsolete' not in json.dumps(answer)
    assert store.query('two','current',Fixture())['status']=='insufficient_evidence'


def test_no_evidence_and_forged_citation_rejected(tmp_path):
    Store,Fixture,_=components();store=Store(tmp_path/'rag.db');store.ingest(docs())
    assert store.query('one','unknown',Fixture())['status']=='insufficient_evidence'
    class BadProvider:
        def generate(self,chunks,query):return {'status':'answered','answer':'fabrication','citations':[{'id':'private','version':1}]}
    with pytest.raises(ValueError):store.query('one','refund',BadProvider())


def test_embedding_model_dimension_mismatch_rejected(tmp_path):
    Store,Fixture,_=components();store=Store(tmp_path/'rag.db');store.ingest(docs())
    store.set_embedding('one','manual',2,'embed-a','digest-a',[1.,0.])
    assert store.search_embeddings('one',[1.,0.],'embed-a','digest-a')[0]['version']==2
    with pytest.raises(ValueError):store.set_embedding('two','private',1,'embed-b','digest-b',[1.,0.,0.])
    with pytest.raises(ValueError):store.search_embeddings('one',[1.,0.,0.],'embed-a','digest-a')
    assert store.search_embeddings('two',[1.,0.],'embed-a','digest-a')==[]


def test_ollama_truncation_timeout_and_schema_failure():
    _,_,Ollama=components();received=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            value=json.loads(self.rfile.read(int(self.headers['Content-Length'])));received.append(value)
            data={'embeddings':[[1.,0.]]} if self.path=='/api/embed' else {'message':{'content':'{"status":"answered","answer":"x","citations":[]}'}}
            if value.get('input')==['bad']:data={'embeddings':[['invalid']]}
            if 'bad-json' in json.dumps(value):data={'message':{'content':'not-json'}}
            self.send_response(200);self.end_headers();self.wfile.write(json.dumps(data).encode())
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        provider=Ollama(f'http://127.0.0.1:{server.server_port}','local-model','local-embed')
        assert provider.embed(['hello'])==[[1.,0.]]
        assert received[-1]['truncate'] is False
        assert provider.generate([], 'hello')['status']=='answered'
        with pytest.raises(ValueError):provider.embed(['bad'])
        with pytest.raises(ValueError):provider.generate([], 'bad-json')
        with pytest.raises(ValueError):Ollama('https://arbitrary.example','model','embed')
    finally:server.shutdown();server.server_close()
    with pytest.raises(ValueError):provider.embed(['hello'])

@pytest.mark.parametrize('patch',[{'version':0},{'tenant':''},{'source_url':'file:///secret'}])
def test_document_schema_rejected_before_ingest(tmp_path,patch):
    Store,_,_=components();store=Store(tmp_path/'rag.db');values=docs();values[0].update(patch)
    with pytest.raises(ValueError):store.ingest(values)
    assert store.search('one','refund')==[]

def test_rag_demo_report_is_fixture_evidence(tmp_path):
    import subprocess,os,sys
    env=os.environ|{'PYTHONPATH':str(fde_support.LAB)}
    run=subprocess.run([sys.executable,'-m','fde_lab.cli','rag-demo','--state-dir',str(tmp_path)],env=env,capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    report=json.loads((tmp_path/'rag-report.json').read_text())
    assert report['evidence_level']=='synthetic-contract'
    assert report['acceptance']['tenant_isolation'] is True
    assert report['acceptance']['unknown_refused'] is True
    assert report['comparison']['model_quality_claim'] is False
