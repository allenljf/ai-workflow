#!/usr/bin/env python3
"""Run a human-reviewed local binding and save private observations, not acceptance."""
import argparse,json
from pathlib import Path
from radar.workflows.evaluate import RunnerBinding,run_bound
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--binding',required=True,type=Path)
p.add_argument('--report',action='append',required=True,help='Repository-relative JUnit report; tests must regenerate it')
p.add_argument('--out',required=True,type=Path,help='Private output directory')
p.add_argument('--timeout-seconds',type=int,default=1800)
a=p.parse_args()
result=run_bound(RunnerBinding(**json.loads(a.binding.read_text())),a.report,a.out,a.timeout_seconds)
(a.out/'observations.json').write_text(json.dumps(result,indent=2)+'\n')
print('Private observations saved; supply acceptance and identity metadata before validation.')
