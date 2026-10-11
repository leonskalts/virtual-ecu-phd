#!/usr/bin/env python3
"""Reproduce v7 only; validate imported snapshot before executing and preserve all outside files."""
import sys
sys.dont_write_bytecode=True
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

def verify_import():
    report=json.loads((HERE/'v6_import_verification.json').read_text())
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==report['git_commit']
    for f in report['files_read']+report['source_files']:
        assert sha(ROOT/f['path'])==f['sha256'],f['path']+' changed; do not silently reimport'
    assert len(report['preserved_unresolved_findings'])==41

def preservation():
    baseline=json.loads((HERE/'workspace_baseline.json').read_text()); current={}
    for base,dirs,names in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d!='.git' and Path(base)/d!=HERE]
        for name in names:
            p=Path(base)/name; key=str(p.relative_to(ROOT))
            current[key]={'symlink':os.readlink(p)} if p.is_symlink() else {'sha256':sha(p),'size':p.stat().st_size}
    changed=[k for k in baseline.keys()&current.keys() if baseline[k]!=current[k]]
    added=sorted(current.keys()-baseline.keys());missing=sorted(baseline.keys()-current.keys())
    report=dict(status='PASS' if not (changed or added or missing) else 'FAIL',files_checked=len(baseline),
                changed=sorted(changed),added_outside_v7=added,missing=missing,
                git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    expected=json.loads((HERE/'v6_import_verification.json').read_text())['git_commit']
    report['git_commit_unchanged']=report['git_commit']==expected
    if not report['git_commit_unchanged']:report['status']='FAIL'
    (HERE/'preservation_report.json').write_text(json.dumps(report,indent=2)+'\n')
    (HERE/'git_status_after.txt').write_text(subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,text=True))
    print('Preservation:',report['status'],len(baseline),'files')
    assert report['status']=='PASS'

def main():
    verify_import()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(HERE))
    commands=[]
    for script in ('reference_oracle.py','compare_ecu.py','build_reports.py'):
        cmd=[sys.executable,str(HERE/script)];commands.append(cmd)
        subprocess.run(cmd,cwd=ROOT,env=env,check=True)
    import test_reference_oracle
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_reference_oracle)
    stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (HERE/'tests.log').write_text(stream.getvalue());print(stream.getvalue())
    (HERE/'test_results.json').write_text(json.dumps(dict(status='PASS' if result.wasSuccessful() else 'FAIL',
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        method='exhaustive prefix/Cartesian-product checks, separate scan reference, exact actual C component comparison'),indent=2)+'\n')
    (HERE/'run_metadata.json').write_text(json.dumps(dict(command=[sys.executable,'research/clover_cert_v7/run_experiment.py'],
        subprocess_commands=commands,python=sys.version,seed=None,tolerance=0,write_boundary=str(HERE),
        environment_overrides={'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(HERE)}),indent=2)+'\n')
    assert result.wasSuccessful()
    preservation()

if __name__=='__main__':main()
