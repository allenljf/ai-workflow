"""Evidence-bound proposals preserve untouched sections and require human review."""
import hashlib
import re
import yaml
from ..export import read_frontmatter

def section_spans(text):
    spans=[];offset=0;fence=None
    for line in text.splitlines(keepends=True):
        marker=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line.rstrip('\n'))
        if marker:
            run=marker.group(1)
            if fence is None:fence=(run[0],len(run))
            elif run[0]==fence[0] and len(run)>=fence[1] and not marker.group(2).strip():fence=None
        elif fence is None and line.startswith('## '):spans.append((line.rstrip('\r\n'),offset))
        offset+=len(line)
    return spans

def context(text):
    sections=[heading for heading,_ in section_spans(text)]
    if len(set(sections))!=len(sections):raise ValueError('Duplicate landscape headings')
    return {'baseline':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'section_headings':sections}

def validate_updates(updates,knowledge,sources):
    if not isinstance(updates,list) or len(updates)>5:raise ValueError('Too many landscape changes')
    seen=set()
    for change in updates:
        if not isinstance(change,dict) or set(change)!={'section_heading','replacement','why','source_ids','quote'}:raise ValueError('Invalid change shape')
        heading=change['section_heading']
        if not isinstance(heading,str) or len(heading)>180 or '\n' in heading or heading in seen or (heading not in knowledge['section_headings'] and not heading.startswith('## 新觀念：')):raise ValueError('Unknown/duplicate landscape section')
        seen.add(heading)
        for key,limit in [('replacement',10000),('why',1500),('quote',500)]:
            value=change[key]
            if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Invalid change text')
            if re.search(r'<\s*/?\s*[a-zA-Z][^>]*>|\x00|\x1b|^---$|^## ',value,re.M):raise ValueError('Unsafe section content')
        ids=change['source_ids']
        if not isinstance(ids,list) or not 1<=len(ids)<=8 or any(not isinstance(s,str) or s not in sources for s in ids):raise ValueError('Unknown change evidence')
        if not any(change['quote'] in sources[s]['title'] or change['quote'] in sources[s]['excerpt'] for s in ids):raise ValueError('Change quote not in retrieved source')
        allowed={sources[s]['url'] for s in ids}
        for link in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)',change['replacement']):
            if link not in allowed:raise ValueError('Invented change citation')

def proposed_landscape(knowledge,updates,batch,completed_at,sources=None):
    text=knowledge['baseline'];meta=read_frontmatter(text)
    body=text.split('---',2)[-1] if text.startswith('---\n') else text
    for change in updates:
        heading=change['section_heading'];replacement=heading+'\n\n'+change['replacement']+'\n\n'
        if sources:
            replacement+='本節修訂提案：'+completed_at[:10]+'；尚待查核。來源：\n\n'
            for sid in change['source_ids']:
                row=sources[sid];title=re.sub(r'([\\`*_{}\[\]()#+.!|<>])',r'\\\1',row['title'])
                replacement+='- ['+title+']('+row['url']+')\n'
            replacement+='\n'
        if heading in knowledge['section_headings']:
            spans=section_spans(body)
            index=next(i for i,(h,_) in enumerate(spans) if h==heading)
            start=spans[index][1];end=spans[index+1][1] if index+1<len(spans) else len(body)
            body=body[:start]+replacement+body[end:]
        else:body=body.rstrip()+'\n\n'+replacement
    meta.update(title='AI 軟體開發工作流知識總覽',visibility='private',review_state='draft',
        kind='landscape',batch_id=batch,baseline_sha256=knowledge['sha256'],proposed_at=completed_at)
    return '---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False)+'---\n'+body
