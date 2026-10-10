import hashlib,importlib.util,json
from pathlib import Path
import pytest
from radar.export import export_public
from radar.config import PublicationConfig
from radar.models import Snapshot
ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('build_site',ROOT/'scripts/build-site.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_site_only_copies_catalog_hash_verified_bundles(tmp_path,monkeypatch):
    monkeypatch.setenv('SITE_BASE','/ai-workflow/')
    export=ROOT/'.build/test-workflow-site';export_public(Snapshot(),ROOT,export,PublicationConfig())
    module.prepare(export,tmp_path/'site')
    catalog=json.loads((tmp_path/'site/src/generated/workflows.json').read_text())
    for row in catalog:
        zip=tmp_path/'site/public/downloads'/row['download_path']
        assert hashlib.sha256(zip.read_bytes()).hexdigest()==row['sha256']
        slug=Path(row['download_path']).stem.replace('.','')
        bundle_page=tmp_path/'site/src/content/docs/guides/bundles'/slug/'index.md'
        assert bundle_page.is_file()
        bundle_text=bundle_page.read_text()
        assert '下載原始 ZIP' in bundle_text
        assert f'](/ai-workflow/downloads/{row["download_path"]})' in bundle_text
        for name in row['included_files']:
            if Path(name).suffix.lower() not in {'.md','.py','.sh','.yaml','.yml','.json','.jsonl','.toml','.csv'}:
                continue
            safe=Path(name).with_suffix('.md')
            preview=tmp_path/'site/src/content/docs/guides/bundles'/slug/'files'/safe
            assert preview.is_file(), name
        assert f'(/ai-workflow/guides/bundles/{slug}/files/' in bundle_text
        if 'bundles/fde/labs-0.3/fde_lab/__init__.py' in row['included_files']:
            assert f'/ai-workflow/guides/bundles/{slug}/files/bundles/fde/labs-03/fde_lab/__init__)' in bundle_text
    guide=(tmp_path/'site/src/content/docs/guides/android/getting-started.md').read_text()
    assert '(/ai-workflow/downloads/android/getting-started.md)' in guide
    row=catalog[0];(export/row['download_path']).write_bytes(b'tamper')
    with pytest.raises(ValueError):module.prepare(export,tmp_path/'site')
