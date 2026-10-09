from pathlib import Path
import re,yaml
from .models import utc
def escape(value):
    return re.sub(r'([\\\x60*_{}\[\]()#+.!|<>])',r'\\\1',value)
def write_draft(result,output,completed_at, demo=False, topic_map=None):
    output=Path(output)
    if output.is_symlink():raise ValueError('Symlink draft root refused')
    output.mkdir(parents=True,exist_ok=True)
    request=result.request;batch=request.batch_id
    if not re.fullmatch('[a-f0-9]{64}',batch):raise ValueError('Unsafe batch id')
    target=output/('digest-'+batch+'.md')
    if target.is_symlink():raise ValueError('Symlink draft refused')
    meta={'title':'雙週 AI 精選草稿'+('（合成示範）' if demo else ''),'kind':'digest','visibility':'private','review_state':'draft','batch_id':batch,'model':request.model,'prompt_version':request.prompt_version,'schema_version':request.schema_version,'enriched_at':utc(completed_at).isoformat(),'reviewed_at':None,'demo':demo}
    if topic_map is not None:meta['topics']=sorted({t for story in result.payload['stories'] for t in topic_map.get(story['event_id'],[])})
    lines=['---',yaml.safe_dump(meta,allow_unicode=True,sort_keys=False).rstrip(),'---','',('> 合成示範：fixture provider，不是模型實測或成功案例。' if demo else '> AI 草稿：尚未人工核准，引用吻合不等於事實驗證。'),'']
    sources={i['source_id']:i for i in request.event_inputs}
    for story in result.payload['stories']:
        lines+=['## '+escape(story['event_id']),'','**為何關注**：'+escape(story['why']),'','**使用方向**：'+escape(story['usage']),'','**限制**：'+escape(story['limitations']),'','**案例證據類別**：'+story['case_evidence'],'']
        for c in story['claim_evidence']:
            lines+=['- '+('引用吻合（未驗證事實）' if c['kind']=='source' else '推論（未驗證）')+'：'+escape(c['claim'])]
            if c['quote']:lines+=['  > '+escape(c['quote'])]
        lines+=['','### 原始來源','']
        for sid in story['source_ids']:
            source=sources[sid]
            lines+=['- ['+escape(source['title'])+']('+source['url']+') · '+sid]
            if source['kind']=='youtube':lines+=['  - 未檢視影片全文；只有影片 metadata。']
        lines+=['']
    if request.knowledge:
        changes=result.payload['landscape_updates']
        lines+=['## 知識總覽修訂提案','', '本輪未提出章節修訂。' if not changes else '以下修改尚未人工查核；完整替代稿同時附在此 PR。','']
        for change in changes:
            lines += ['### '+escape(change['section_heading']),'',escape(change['why']),'',escape(change['replacement']),'', '來源：'+', '.join(change['source_ids']),'']
        lines+=['## 新來源候選（不自動訂閱）','']
        for source in request.event_inputs:
            if source.get('feed_source_id')=='knowledge-discovery':
                lines+=['- ['+escape(source['title'])+']('+source['url']+') · '+source.get('evidence_level','unreviewed')]
        if changes:
            from ..knowledge.revisions import proposed_landscape
            landscape=output/('landscape-'+batch+'.md')
            if landscape.is_symlink():raise ValueError('Unsafe landscape draft')
            if not landscape.exists():landscape.write_text(proposed_landscape(request.knowledge,changes,batch,utc(completed_at).isoformat(),sources))
    text='\n'.join(lines)
    if target.exists() and target.read_text()!=text:raise ValueError('Existing draft differs; preserve human edits')
    if not target.exists():target.write_text(text)
    return target
