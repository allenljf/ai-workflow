import pytest
from radar.workflows.profiles import resolve_profile

def layer(di, **extra):
    return {'rules': {'di':di}, **extra}

def test_company_override_keeps_provenance():
    r=resolve_profile(layer('hilt'),{},layer('koin_annotations',overrides={'di':'Existing container'}),{})
    assert r.rules['di']=='koin_annotations'
    assert r.provenance['di']==['upstream','company']
    assert r.override_reasons['di']==['Existing container']
    assert not r.diagnostics

def test_project_requires_explicit_exception_reason():
    r=resolve_profile({},layer('hilt'),layer('koin_annotations',overrides={'di':'Company decision'}),layer('manual',overrides={'di':'Isolated migration module'}))
    assert r.rules['di']=='manual'
    assert r.override_reasons['di'][-1]=='Isolated migration module'
    bad=resolve_profile(layer('hilt'),{},layer('koin_annotations'),{})
    assert bad.rules['di']=='hilt' and bad.diagnostics

def test_unknown_fields_fail_closed():
    with pytest.raises(ValueError):resolve_profile({'rules':{'secret':'x'}},{},{},{})
