import hashlib,importlib.util,json
from pathlib import Path
import pytest
from radar.export import export_public
from radar.config import PublicationConfig
from radar.models import Snapshot
ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('build_site',ROOT/'scripts/build-site.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_site_only_copies_catalog_hash_verified_bundles(tmp_path):
    export=ROOT/'.build/test-workflow-site';export_public(Snapshot(),ROOT,export,PublicationConfig())
    module.prepare(export,tmp_path/'site')
    catalog=json.loads((tmp_path/'site/src/generated/workflows.json').read_text())
    for row in catalog:
        zip=tmp_path/'site/public/downloads'/row['download_path']
        assert hashlib.sha256(zip.read_bytes()).hexdigest()==row['sha256']
    row=catalog[0];(export/row['download_path']).write_bytes(b'tamper')
    with pytest.raises(ValueError):module.prepare(export,tmp_path/'site')
