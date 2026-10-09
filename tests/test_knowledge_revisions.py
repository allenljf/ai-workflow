from pathlib import Path
import pytest
from radar.knowledge.revisions import context, validate_updates, proposed_landscape

def test_unknown_sections_and_fabricated_evidence_rejected():
    baseline='## Loop\nOld guidance.\n\n## Graph\nOther guidance.\n'
    c=context(baseline)
    sources={'s':{'url':'https://example.com/article','excerpt':'A bounded loop needs a stop condition.','title':'Loops'}}
    change={'section_heading':'## Loop','replacement':'Use a stop condition.','why':'Update','source_ids':['s'],'quote':'A bounded loop needs a stop condition.'}
    validate_updates([change],c,sources)
    with pytest.raises(ValueError):validate_updates([change|{'quote':'Made up'}],c,sources)
    with pytest.raises(ValueError):validate_updates([change|{'section_heading':'## Missing'}],c,sources)
    with pytest.raises(ValueError):validate_updates([change|{'replacement':'[claim](https://fake.example/)'}],c,sources)
    proposed=proposed_landscape(c,[change],'a'*64,'2026-10-09T00:00:00+00:00')
    assert 'Use a stop condition.' in proposed and 'Other guidance.' in proposed
    assert 'review_state: draft' in proposed and 'visibility: private' in proposed

def test_new_concepts_can_be_proposed_without_existing_section():
    c=context('## Loop\nOld.\n')
    change={'section_heading':'## 新觀念：durable tasks','replacement':'Recover safely.','why':'New concept','source_ids':['s'],'quote':'Recover safely'}
    validate_updates([change],c,{'s':{'url':'https://example.com','title':'Recover safely','excerpt':''}})
    assert '新觀念' in proposed_landscape(c,[change],'a'*64,'2026-10-09T00:00:00+00:00')

def test_fenced_template_heading_is_not_a_landscape_section():
    baseline='## Search\nInstructions.\n```markdown\n## <date>: template heading\nExample\n```\n\n## Next\nKeep.\n'
    c=context(baseline)
    assert c['section_headings']==['## Search','## Next']
    change={'section_heading':'## Search','replacement':'New instructions.','why':'Changed','source_ids':['s'],'quote':'New'}
    result=proposed_landscape(c,[change],'a'*64,'2026-10-09T00:00:00+00:00')
    assert 'template heading' not in result and '```' not in result
    assert '## Next\nKeep.' in result
