#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from radar.fde.deployment import load_deployment,deployment_plan
p=argparse.ArgumentParser(description='Validate or print commands; never execute cloud operations')
p.add_argument('--config',type=Path,default=Path('config/fde-deployment.yaml'))
g=p.add_mutually_exclusive_group(required=True);g.add_argument('--check',action='store_true');g.add_argument('--dry-run',action='store_true')
a=p.parse_args()
try:
 c=load_deployment(a.config);print(json.dumps({'profile':c['profile'],'executed':False,'argv':deployment_plan(c) if a.dry_run else []},ensure_ascii=False))
except (ValueError,OSError,TypeError):print('Configuration refused; supply reviewed non-secret references');raise SystemExit(2)
