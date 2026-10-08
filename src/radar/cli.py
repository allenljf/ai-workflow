import argparse,json
from contextlib import nullcontext
from datetime import datetime,timezone
from pathlib import Path
import httpx
from .config import load_config
from .models import validate_snapshot
from .store import load_snapshot,save_snapshot
from .pipeline import collect
from .export import export_public
from .adapters.manual import read_manual_links

def main(argv: list[str] | None=None, client: httpx.Client | None=None, *, now=None, enrichment_provider=None, enrichment_persist=None) -> int:
    parser=argparse.ArgumentParser(description='Knowledge radar: no model calls')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('collect','validate','export'):
        cmd=sub.add_parser(name);cmd.add_argument('--config',type=Path,default=Path('config'))
        cmd.add_argument('--state',type=Path,required=True)
        if name=='export': cmd.add_argument('--output',type=Path,required=True)
    enrich=sub.add_parser('enrich');enrich.add_argument('--config',type=Path,default=Path('config'));enrich.add_argument('--state-dir',type=Path,required=True);enrich.add_argument('--dry-run',action='store_true');enrich.add_argument('--allow-paid',action='store_true');enrich.add_argument('--expected-sha')
    args=parser.parse_args(argv)
    try:
        if args.command=='enrich':
            from .enrich.command import execute
            report=execute(args,load_config(args.config),now or datetime.now(timezone.utc),enrichment_provider,enrichment_persist)
            print(json.dumps(report,ensure_ascii=False));return 0
        snapshot=load_snapshot(args.state)
        if args.command=='validate':
            validate_snapshot(snapshot.to_dict());print('State validated');return 0
        config=load_config(args.config);root=args.config.resolve().parent
        if args.command=='export':
            report=export_public(snapshot,root,args.output,config.publication)
            print(json.dumps({'copied':len(report.copied_paths),'excluded':len(report.excluded_paths)}));return 0
        with nullcontext(client) if client is not None else httpx.Client() as actual:
            result=collect(config,snapshot,actual,datetime.now(timezone.utc))
        result.inbox=read_manual_links(root/'content/inbox/links.json')
        save_snapshot(args.state,result)
        enabled=[s for s in config.sources if s.enabled]
        failed=[s.id for s in enabled if result.health[s.id].status=='failed']
        print(json.dumps({'events':len(result.events),'revisions':len(result.revisions),'failed_sources':failed,'model_calls':0}))
        return 3 if enabled and len(failed)==len(enabled) else 0
    except (ValueError,TypeError,OSError) as exc:
        # Exception class only: state/input errors may contain private content.
        print('Configuration/state operation refused: '+type(exc).__name__)
        return 2

if __name__=='__main__': raise SystemExit(main())
