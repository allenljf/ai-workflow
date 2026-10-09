"""Exercise the actual deployment guard with fake GitHub responses."""
import os
from pathlib import Path
import subprocess
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('built,latest,expected', [('a'*40, 'a'*40, 'true'), ('a'*40, 'b'*40, 'false'), ('bad', 'b'*40, None), ('a'*40, 'bad', None)])
def test_only_current_main_can_deploy(tmp_path, built, latest, expected):
    workflow = yaml.safe_load((ROOT / '.github/workflows/publish.yml').read_text())
    steps = workflow['jobs']['deploy']['steps']
    guard = next(s for s in steps if s.get('id') == 'freshness')
    artifact = tmp_path / '.build/public-dist'
    artifact.mkdir(parents=True)
    (artifact / 'build-revision.txt').write_text(built)
    gh = tmp_path / 'gh'
    gh.write_text('#!/bin/sh\nprintf "%s\\n" "$LATEST_SHA"\n')
    gh.chmod(0o755)
    output = tmp_path / 'output'
    result = subprocess.run(['bash', '-c', guard['run']], cwd=tmp_path, env={**os.environ, 'PATH': str(tmp_path)+os.pathsep+os.environ['PATH'], 'LATEST_SHA': latest, 'GITHUB_OUTPUT': str(output), 'GITHUB_REPOSITORY': 'example/site'}, capture_output=True, text=True)
    if expected is None:
        assert result.returncode != 0
        assert not output.exists()
    else:
        assert result.returncode == 0
        assert output.read_text().strip() == f'deploy={expected}'
    for step in steps:
        if 'upload-pages-artifact@' in step.get('uses', '') or step.get('id') == 'deployment':
            assert step['if'] == "steps.freshness.outputs.deploy == 'true'"


def test_builds_record_revision_and_callers_grant_read():
    for name in ['collect.yml', 'publish-reviewed.yml']:
        text = (ROOT / '.github/workflows' / name).read_text()
        assert 'git rev-parse HEAD > site/dist/build-revision.txt' in text
        workflow = yaml.safe_load(text)
        assert workflow['jobs']['publish']['permissions']['contents'] == 'read'


def test_state_writers_and_reviewed_builds_share_serialization():
    for name in ['collect.yml', 'enrich.yml', 'enrichment-due.yml', 'publish-reviewed.yml']:
        workflow = yaml.safe_load((ROOT / '.github/workflows' / name).read_text())
        assert workflow['concurrency']['group'] == 'pipeline-state'
        assert workflow['concurrency']['cancel-in-progress'] is False
