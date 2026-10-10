#!/usr/bin/env python3
"""Prepare site inputs exclusively from reviewed export."""
import argparse,json,shutil,hashlib,re,zipfile,os
from pathlib import Path,PurePosixPath

BUNDLE_TEXT_SUFFIXES={'.md','.py','.sh','.yaml','.yml','.json','.jsonl','.toml','.csv'}
MAX_BUNDLE_PREVIEW_BYTES=1_000_000

def starlight_route_path(path):
    return PurePosixPath(*(re.sub(r'[^a-z0-9_-]','',part.lower()) for part in PurePosixPath(path).parts)).as_posix()

def site_link(target,base='/'):
    if not re.fullmatch(r'(?:/|/[a-zA-Z0-9._~-]+(?:/[a-zA-Z0-9._~-]+)*/)',base):raise ValueError('Invalid site base')
    return base.rstrip('/')+'/'+target.strip('/')

def bundle_markdown_pages(docs,row,archive_path,base='/'):
    archive_slug=Path(row['download_path']).stem
    if not re.fullmatch(r'[a-z0-9-]+-[0-9]+\.[0-9]+\.[0-9]+',archive_slug):
        raise ValueError('Invalid bundle preview id')
    slug=archive_slug.replace('.','')
    bundle_root=docs/'guides'/'bundles'/slug
    expected=set(row['included_files'])
    pages=[]
    total=0
    with zipfile.ZipFile(archive_path) as package:
        members={info.filename:info for info in package.infolist() if not info.is_dir()}
        if set(members)!=expected:raise ValueError('Bundle contents differ from catalog')
        for name in sorted(expected):
            member=PurePosixPath(name)
            if member.is_absolute() or '..' in member.parts or chr(92) in name or member.as_posix()!=name:
                raise ValueError('Unsafe bundle preview path')
            suffix=member.suffix.lower()
            if suffix not in BUNDLE_TEXT_SUFFIXES:continue
            info=members[name]
            total+=info.file_size
            if info.file_size>256_000 or total>MAX_BUNDLE_PREVIEW_BYTES:
                raise ValueError('Bundle text preview exceeds size limit')
            try:source=package.read(name).decode('utf-8')
            except UnicodeDecodeError:raise ValueError('Bundle text file is not UTF-8') from None
            route_path=PurePosixPath('files')/member.with_suffix('.md')
            destination=bundle_root/route_path
            destination.parent.mkdir(parents=True,exist_ok=True)
            title=name.replace('"','\\"')
            index_route=(PurePosixPath('guides/bundles')/slug).as_posix()+'/'
            index_link=site_link(index_route,base)
            language={'.py':'python','.sh':'bash','.yaml':'yaml','.yml':'yaml','.json':'json','.jsonl':'json','.toml':'toml','.csv':'csv'}.get(suffix,'')
            if suffix=='.md':
                if source.startswith('---\n') and '\n---\n' in source[4:]:
                    source=source.split('\n---\n',1)[1].lstrip('\n')
                body=f'## {name}\n\n[返回套件內容索引]({index_link})\n\n{source}'
            else:
                runs=[len(m.group(0)) for m in re.finditer(r'\x60+',source)]
                fence=chr(96)*max(3,max(runs,default=0)+1)
                body=f'## {name}\n\n[返回套件內容索引]({index_link})\n\n{fence}{language}\n{source.rstrip()}\n{fence}'
            destination.write_text(f'---\ntitle: "{title}"\n---\n\n{body}\n')
            link=site_link((PurePosixPath('guides/bundles')/slug/'files'/starlight_route_path(member.with_suffix(''))).as_posix()+'/',base)
            pages.append((name,link))
    if not pages:raise ValueError('Bundle contains no readable files')
    download=site_link('downloads/'+row['download_path'],base)
    intro=[
        '---',f'title: "{slug} 套件內容"','---','',
        f'# {row["id"]} · {row["version"]} 套件內容','',
        f'版本狀態：{row["adoption_state"]}。上游固定版本：[查看來源]({row["upstream_url"]}/tree/{row["upstream_ref"]})。','',
        f'SHA-256：{chr(96)}{row["sha256"]}{chr(96)}。','',
        f'[下載原始 ZIP]({download})','',
        '## 包內檔案',''
    ]
    intro.extend(f'- [`{name.replace(chr(96),chr(92)+chr(96))}`]({link})' for name,link in pages)
    (bundle_root/'index.md').write_text('\n'.join(intro)+'\n')

def prepare(export: Path, site: Path):
    if export.is_symlink(): raise ValueError('Symlink export refused')
    manifest=json.loads((export/'manifest.json').read_text())
    for name in manifest['files']:
        p=export/name
        if p.is_symlink() or not p.resolve().is_relative_to(export.resolve()) or not p.is_file():
            raise ValueError('Unsafe export file')
    if 'workflows.json' not in manifest['files']:raise ValueError('Missing workflow catalog')
    workflows=json.loads((export/'workflows.json').read_text())
    bundles=set()
    for row in workflows:
        name=row['download_path']
        if not re.fullmatch(r'bundles/[a-z0-9-]+-[0-9]+\.[0-9]+\.[0-9]+\.zip',name) or name not in manifest['files']:raise ValueError('Bundle outside catalog allowlist')
        if hashlib.sha256((export/name).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Bundle hash differs')
        bundles.add(name)
    if {n for n in manifest['files'] if n.endswith('.zip')}!=bundles:raise ValueError('Unlisted attachment')
    base=os.environ.get('SITE_BASE','/')
    docs=site/'src/content/docs';generated=site/'src/generated';downloads=site/'public/downloads'
    for p in (docs,generated,downloads):
        if p.is_symlink():raise ValueError('Unsafe generated destination')
        if p.exists():shutil.rmtree(p)
        p.mkdir(parents=True)
    (docs/'404.md').write_text('---\ntitle: 頁面不存在\n---\n這個頁面尚未發布。請回到知識雷達。\n')
    for name in manifest['files']:
        if name.startswith('docs/') and name.endswith('.md'):
            relative=Path(name).relative_to('docs')
            for dest in (docs/'guides'/relative, downloads/relative):
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(export/name,dest)
            download_link=site_link('downloads/'+relative.as_posix(),base)
            with (docs/'guides'/relative).open('a') as page:
                page.write(f'\n\n---\n\n[下載本文 Markdown]({download_link})\n')
    for name in bundles:
        dest=downloads/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(export/name,dest)
    for row in workflows:bundle_markdown_pages(docs,row,export/row['download_path'],base)
    shutil.copyfile(export/'workflows.json',generated/'workflows.json')
    if 'fde.json' not in manifest['files']:raise ValueError('Missing FDE catalog')
    shutil.copyfile(export/'fde.json',generated/'fde.json')
    shutil.copyfile(export/'radar.json',generated/'radar.json')
    shutil.copyfile(export/'digests.json',generated/'digests.json')
    (generated/'guides.json').write_text(json.dumps([n.removeprefix('docs/') for n in manifest['files'] if n.startswith('docs/')]))
    print('Prepared reviewed site inputs')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path,required=True);parser.add_argument('--site',type=Path,required=True)
    args=parser.parse_args();prepare(args.export,args.site)
