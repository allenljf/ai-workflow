from dataclasses import dataclass
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,unquote
import hashlib,io,re,zipfile,yaml
from .registry import validate_manifest
from ..export import read_frontmatter
@dataclass
class BundleReport:
    zip_path: Path
    sha256: str
    included_files: list[str]
    errors: list[str]
OWN_ROOTS=('bundles/android-task/','skills/android-task/','profiles/android/')
def build_bundle(manifest,root,out):
    validate_manifest(manifest.to_dict())
    root=Path(root).resolve();out=Path(out)
    if manifest.visibility!='public' or manifest.review_state!='approved':raise ValueError('Bundle publication approval required')
    payload={}
    for name in manifest.bundle_files:
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:raise ValueError('Unsafe bundle path')
        upstream=name.startswith('upstream/')
        if upstream:
            if manifest.license not in {'MIT','Apache-2.0','BSD-3-Clause'} or not manifest.redistribution_allowed:raise ValueError('Upstream redistribution not approved')
            if 'upstream/LICENSE' not in manifest.bundle_files:raise ValueError('Upstream license notice missing')
        elif not name.startswith(OWN_ROOTS):raise ValueError('Private or unknown bundle root')
        source=root/name
        if any(p.is_symlink() for p in [source,*source.parents] if p.is_relative_to(root)) or not source.is_file():raise ValueError('Missing/symlink bundle file')
        if source.suffix not in {'.md','.yaml','.py','.sh'} and source.name!='LICENSE':raise ValueError('Unsupported bundle asset')
        text=source.read_text()
        if not upstream:
            meta=yaml.safe_load(text) if source.suffix=='.yaml' else read_frontmatter(text)
            if not isinstance(meta,dict) or meta.get('visibility')!='public' or meta.get('review_state')!='approved':raise ValueError('File lacks public review approval')
        for link in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)',text):
            u=urlsplit(link)
            if u.scheme:
                if u.scheme!='https':raise ValueError('Unsafe bundle link')
                continue
            if u.netloc:raise ValueError('Unsafe relative link')
            if not u.path:continue
            target=(source.parent/unquote(u.path)).resolve()
            if not target.is_relative_to(root) or str(target.relative_to(root)) not in manifest.bundle_files:raise ValueError('Missing bundled reference/script')
        payload[name]=source.read_bytes()
    payload['manifest.yaml']=yaml.safe_dump(manifest.to_dict(),sort_keys=True,allow_unicode=True).encode()
    payload['SOURCES.md']=('Upstream: '+manifest.upstream_url+'\nPinned ref: '+manifest.upstream_ref+'\nUpstream license: '+manifest.license+'\nThis archive is an owned adapter; upstream installation is separate.\n').encode()
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,value in sorted(payload.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;info.create_system=3
            z.writestr(info,value)
    if out.is_symlink():raise ValueError('Unsafe bundle output')
    out.mkdir(parents=True,exist_ok=True)
    target=out/(manifest.id+'-'+manifest.version+'.zip')
    if target.is_symlink():raise ValueError('Unsafe bundle target')
    data=buf.getvalue()
    if target.exists() and target.read_bytes()!=data:raise ValueError('Immutable version already differs')
    target.write_bytes(data)
    return BundleReport(target,hashlib.sha256(data).hexdigest(),sorted(payload),[])
