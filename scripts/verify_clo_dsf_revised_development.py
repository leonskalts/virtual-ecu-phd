#!/usr/bin/env python3
"""One final regression pass; generated legacy replay data stays temporary."""
import csv,hashlib,json,py_compile,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_revised_development import OUT,OLD,read,sha,write_json
from virtual_ecu.final_evidence import verify_frozen
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression

def checked(args,name):
 p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
 (OUT/'validation'/name).write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(name+': '+p.stderr)
 return p.stdout+p.stderr

def bank_parity():
 rows=read(OUT/'train_runs.csv');chosen=[]
 for origin in ['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR','NORMAL']:
  chosen.append(next(r['run_id'] for r in rows if r['origin']==origin))
 commands={r['run_id']:r['command'] for r in (json.loads(line) for line in (OUT/'commands.jsonl').read_text().splitlines())}
 tested=[]
 with tempfile.TemporaryDirectory(prefix='clo-revised-bank-') as t:
  for rid in chosen:
   cmd=[v.replace('--revised-','--final-') for v in commands[rid]];cmd[0]=str(ROOT/'virtual_ecu_v7_2_reference');cmd[1]=str(Path(t)/(rid+'.csv'))
   for flag,suffix in [('--final-evidence','.trace.csv'),('--final-observations','.obs.csv'),('--final-metrics','.metrics.csv')]:cmd[cmd.index(flag)+1]=str(Path(t)/(rid+suffix))
   p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
   if p.returncode:raise RuntimeError(p.stderr)
   old={r['method']:r for r in read(Path(t)/(rid+'.metrics.csv'))};new={r['method']:r for r in read(OUT/'metrics'/(rid+'.csv'))}
   for method in ['Candidate 2','Plain DS','Simple OR','Weighted Sum','Hybrid','Timing Monitor','v7.2 CLO-DSF']:
    left=old['Final CLO-DSF' if method=='v7.2 CLO-DSF' else method];right=new[method]
    for key in left:
     if key!='method' and left[key]!=right[key]:raise ValueError(f'{rid} {method} {key}: {left[key]} != {right[key]}')
   tested.append(rid)
 return dict(status='PASS',runs=tested,methods_per_run=7,comparison='Every historical online metric string matches its frozen v7.2 executable')

def run():
 report=OUT/'validation/regression.json'
 if report.exists():raise ValueError('Final regression already recorded; do not repeat')
 checked(['make'],'legacy_build.log');checked(['make','-f','clo_dsf_revised.mk'],'revised_build.log')
 paths=[ROOT/'scripts/virtual_ecu_gui.py',*sorted((ROOT/'python/virtual_ecu').glob('*.py')),*sorted((ROOT/'scripts').glob('*clo_dsf_revised*.py')),*sorted((ROOT/'tests').glob('*clo_dsf_revised*.py'))]
 for path in paths:py_compile.compile(str(path),doraise=True)
 tests=checked([sys.executable,'-m','unittest','discover','-s','tests'],'complete_tests.log')
 require=tests.rstrip().endswith('OK')
 if not require:raise ValueError('Tests not successful')
 print('Full unit suite passed.',flush=True)
 bank=bank_parity();write_json(OUT/'validation/baseline_bank_parity.json',bank)
 with tempfile.TemporaryDirectory(prefix='clo-revised-final-regression-') as t:
  destination=Path(t);legacy=legacy_regression(destination);rtl=rtl_regression(destination)
  for name in ['legacy','rtl']:shutil.copyfile(destination/f'validation/{name}/verification.json',OUT/f'validation/{name}_verification.json')
  write_json(OUT/'validation/regression_replay_hashes.json',{str(p.relative_to(destination)):sha(p) for p in sorted(destination.rglob('*.csv'))})
 print('48 legacy and 64 RTL cases unchanged.',flush=True)
 accepted=verify_frozen();checked([sys.executable,'scripts/package_clo_dsf_final.py','--verify'],'historical_manifests.log')
 initial=json.loads((OUT/'validation/initial_hashes.json').read_text());changed=[name for name,digest in initial.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=digest]
 if changed:raise ValueError('Pre-existing files changed: '+repr(changed))
 checked(['git','diff','--check'],'diff_check.log');checked(['git','diff','--cached','--quiet'],'staged_check.log')
 write_json(report,dict(status='PASS',legacy_cases=legacy,rtl_cases=rtl,accepted=accepted,preexisting_files_verified=len(initial),changed_files=changed,session_preserved=True,baseline_bank_parity=bank,build='PASS',python_compile='PASS',tests='PASS',git_diff_check='PASS',nothing_staged=True))
 print('Final regression and complete historical preservation PASS.',flush=True)
if __name__=='__main__':run()
