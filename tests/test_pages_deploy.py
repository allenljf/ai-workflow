from pathlib import Path


def test_pages_deployment_uses_github_oidc_without_cross_repo_secret():
    publish = Path('.github/workflows/publish.yml').read_text()
    collect = Path('.github/workflows/collect.yml').read_text()

    assert 'pages: write' in publish
    assert 'id-token: write' in publish
    assert 'actions/upload-pages-artifact@' in publish
    assert 'actions/deploy-pages@' in publish
    assert 'PUBLIC_EXPORT_TOKEN' not in publish + collect
    assert 'PUBLIC_EXPORT_REPO' not in publish + collect
    assert 'secrets:' not in collect.split('  publish:', 1)[1]
