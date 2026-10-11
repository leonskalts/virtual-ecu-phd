#!/usr/bin/env python3
"""Reproduce v8 reduction challenge; never write v6/v7 or production files."""
import sys
sys.dont_write_bytecode=True
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()

def verify_import():
 imported=json.loads((HERE/'research_import.json').read_text())
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==imported['git_commit']
 for f in imported['files_read']:assert sha(ROOT/f['path'])==f['sha256'],f['path']
 manifest=json.loads((ROOT/'research/clover_cert_v6_audit/fault_provenance_manifest.json').read_text())
 for f in manifest['source_files']:assert sha(ROOT/f['path'])==f['sha256'],f['path']
 for a in manifest['anchors']:assert a['token'] in (ROOT/a['path']).read_text().splitlines()[a['line']-1],a['id']
 assert len(imported['unresolved_findings'])==41

def preserve():
 baseline=json.loads((HERE/'workspace_baseline.json').read_text());now={}
 for base,dirs,names in os.walk(ROOT):
  dirs[:]=[d for d in dirs if d!='.git' and Path(base)/d!=HERE]
  for name in names:
   p=Path(base)/name;key=str(p.relative_to(ROOT))
   now[key]={'symlink':os.readlink(p)} if p.is_symlink() else {'sha256':sha(p),'size':p.stat().st_size}
 changed=sorted(k for k in baseline.keys()&now.keys() if baseline[k]!=now[k]);added=sorted(now.keys()-baseline.keys());missing=sorted(baseline.keys()-now.keys())
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 same=head==json.loads((HERE/'research_import.json').read_text())['git_commit']
 report=dict(status='PASS' if not(changed or added or missing) and same else 'FAIL',files_checked=len(baseline),changed=changed,added_outside_v8=added,missing=missing,git_commit=head,git_commit_unchanged=same)
 (HERE/'preservation_report.json').write_text(json.dumps(report,indent=2)+'\n')
 (HERE/'git_status_after.txt').write_text(subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,text=True))
 print('Preservation:',report['status'],len(baseline),'files',flush=True);assert report['status']=='PASS'

def main():
 verify_import();commands=[]
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(HERE))
 for name in ('compare_methods.py','report_results.py'):
  cmd=[sys.executable,str(HERE/name)];commands.append(cmd);subprocess.run(cmd,cwd=ROOT,env=env,check=True)
 import test_reduction
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_reduction))
 (HERE/'tests.log').write_text(stream.getvalue());print(stream.getvalue(),flush=True)
 (HERE/'test_results.json').write_text(json.dumps(dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors)),indent=2)+'\n')
 (HERE/'run_metadata.json').write_text(json.dumps(dict(command=[sys.executable,'research/clover_cert_v8/run_validation.py'],subprocess_commands=commands,
   seed=None,tolerance=0,write_boundary=str(HERE),environment_overrides={'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(HERE)},
   research_import_sha256=sha(HERE/'research_import.json')),indent=2)+'\n')
 assert result.wasSuccessful();preserve()

if __name__=='__main__':main()
