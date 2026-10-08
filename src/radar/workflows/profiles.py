"""Resolve explicitly declared policy overrides without losing their reasons."""
from dataclasses import dataclass

RULE_FIELDS={'di','architecture','ui_state','flow_collection','dispatcher','test_evidence','max_parallel','max_attempts','sensitive_actions'}
@dataclass
class ResolvedProfile:
    rules: dict
    provenance: dict
    override_reasons: dict
    diagnostics: list[str]

def resolve_profile(upstream,android,company,project):
    result=ResolvedProfile({}, {}, {}, [])
    for name,layer in zip(('upstream','android','company','project'),(upstream,android,company,project)):
        if set(layer)-{'id','visibility','review_state','rules','overrides','sources'}:raise ValueError('Unknown profile field')
        rules=layer.get('rules',{});overrides=layer.get('overrides',{})
        if set(rules)-RULE_FIELDS or set(overrides)-RULE_FIELDS:raise ValueError('Unknown rule field')
        for field,value in rules.items():
            changed=field in result.rules and result.rules[field]!=value
            reason=overrides.get(field)
            if changed and (not isinstance(reason,str) or not reason.strip()):
                result.diagnostics.append(f'{name}.{field}: conflicting override needs reason');continue
            result.rules[field]=value
            result.provenance.setdefault(field,[]).append(name)
            if changed:result.override_reasons.setdefault(field,[]).append(reason)
    return result
