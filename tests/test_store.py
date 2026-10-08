import pytest
from radar.models import Snapshot
from radar.store import load_snapshot,save_snapshot

def test_roundtrip_and_missing(tmp_path):
    p=tmp_path/'snapshot.json'
    assert load_snapshot(p)==Snapshot()
    save_snapshot(p,Snapshot())
    assert load_snapshot(p)==Snapshot()

def test_corrupt_state_is_not_overwritten(tmp_path):
    p=tmp_path/'snapshot.json';p.write_text('{broken')
    with pytest.raises(ValueError): load_snapshot(p)
    assert p.read_text()=='{broken'

def test_interrupted_save_keeps_previous_file(tmp_path,monkeypatch):
    p=tmp_path/'snapshot.json';save_snapshot(p,Snapshot())
    old=p.read_bytes()
    def fail(*a): raise OSError('interrupted')
    monkeypatch.setattr('radar.store.os.replace',fail)
    with pytest.raises(OSError): save_snapshot(p,Snapshot(inbox=[{'url':'https://example.com'}]))
    assert p.read_bytes()==old
