#!/usr/bin/env python3
"""One immutable private review branch per batch; never overwrites human edits."""
import argparse,json,re,subprocess,tempfile,shutil,sys
from pathlib import Path
from radar.export import read_frontmatter
def command(*args,cwd=None):
    return subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True).stdout.strip()
def open_pr(batch,draft,root):
    if not re.fullmatch('[a-f0-9]{64}',batch) or draft.is_symlink() or not draft.is_file():raise ValueError('Invalid batch draft')
    text=draft.read_text();meta=read_frontmatter(text)
    if meta.get('batch_id')!=batch or meta.get('visibility')!='private' or meta.get('review_state')!='draft':raise ValueError('Private draft required')
    private=command('gh','repo','view','--json','isPrivate','--jq','.isPrivate',cwd=root)
    if private!='true':raise ValueError('Review source repository must be private')
    branch='digest/'+batch
    prs=json.loads(command('gh','pr','list','--head',branch,'--base','main','--state','all','--json','url,state,headRefName,baseRefName',cwd=root))
    if prs:
        pr=prs[0]
        return {'url':pr['url'],'state':pr['state'],'batch_id':batch}
    remote=command('git','remote','get-url','origin',cwd=root)
    with tempfile.TemporaryDirectory(prefix='digest-review-') as temp:
        checkout=Path(temp)/'repo'
        command('git','clone','--no-hardlinks','--single-branch','--branch','main',str(root),str(checkout))
        command('git','remote','set-url','origin',remote,cwd=checkout)
        exists=command('git','ls-remote','--heads','origin','refs/heads/'+branch,cwd=checkout)
        if exists:
            command('git','fetch','--depth=1','origin','refs/heads/'+branch,cwd=checkout)
            command('git','checkout','-B',branch,'FETCH_HEAD',cwd=checkout)
        else:
            command('git','checkout','-B',branch,cwd=checkout)
            target=checkout/'content/drafts'/('digest-'+batch+'.md');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
            command('git','config','user.name','workflow-radar[bot]',cwd=checkout);command('git','config','user.email','workflow-radar@users.noreply.github.com',cwd=checkout)
            command('git','add','--',str(target.relative_to(checkout)),cwd=checkout);command('git','commit','-m','docs: propose fortnightly digest '+batch[:12],cwd=checkout)
            command('git','push','origin','HEAD:refs/heads/'+branch,cwd=checkout)
        body=Path(temp)/'body.md';body.write_text('AI 整理草稿，尚未人工核准。請核對引用、推論、案例等級與 Android 適用性。\n\n核准發布需將審閱版本移至 content/public/digests/，設定 visibility: public、review_state: approved 與 reviewed_at。單純 merge 此私有草稿不會發布網站。\n\nBatch: '+batch+'\n')
        url=command('gh','pr','create','--base','main','--head',branch,'--title','docs: 雙週 AI 精選 '+batch[:12],'--body-file',str(body),cwd=root)
        return {'url':url,'state':'OPEN','batch_id':batch}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch-id',required=True);p.add_argument('--draft',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(open_pr(a.batch_id,a.draft,Path.cwd())))
    except (ValueError,OSError,subprocess.CalledProcessError):print('Review PR unavailable; durable result retained, no model retry',file=sys.stderr);sys.exit(2)
