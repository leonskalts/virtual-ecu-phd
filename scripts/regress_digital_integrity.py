#!/usr/bin/env python3
import json,subprocess,sys,tempfile,shutil
from pathlib import Path
import run_digital_integrity as t
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression

def main():
 t.verify();assert not (t.B/'regression_started').exists();(t.B/'regression_started').write_text(t.d.r.now());report=json.loads((t.O/'report.json').read_text());result={'retained_candidate':report['promoted']};backup=t.B/'binary_backup';backup.mkdir(exist_ok=True)
 names=['virtual_ecu_v7_1','virtual_ecu_v7_2_reference','virtual_ecu_v7_2_optimized','virtual_ecu_v7_3']
 for n in names:shutil.copy2(n,backup/n)
 objects=list((t.ROOT/'src').rglob('*.o'))
 for p in objects:
  q=backup/p.relative_to(t.ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 try:
  cmds=[('build',['make','-B','-f','clo_dsf_revised.mk','-j4']),('compile',[sys.executable,'-m','compileall','-q','python','scripts','tests']),('tests',[sys.executable,'-m','unittest','discover','-s','tests'] if report['promoted'] else [sys.executable,'-m','unittest','discover','-s','tests','-p','test_digital_sensor_integrity.py']),('diff_check',['git','diff','--check'])]
  for name,cmd in cmds:
   print(name,flush=True);p=subprocess.run(cmd,capture_output=True,text=True);(t.B/(name+'.log')).write_text(p.stdout+p.stderr);result[name]=p.returncode;assert not p.returncode,(name,p.stderr[-2500:])
  if report['promoted']:
   with tempfile.TemporaryDirectory(prefix='di-regression-') as td:result['legacy']=legacy_regression(Path(td));print('LEGACY48 PASS',flush=True);result['rtl']=rtl_regression(Path(td));print('RTL64 PASS',flush=True)
 finally:
  for n in names:shutil.copy2(backup/n,n)
  for p in objects:shutil.copy2(backup/p.relative_to(t.ROOT),p)
  t.dump(t.O/'regression.json',result)
 t.verify();result.update(Hybrid_HETIA_unchanged=True,GUI_unchanged=True,old_scientific_and_results_unchanged=True);t.dump(t.O/'regression.json',result);print('REGRESSION PASS',flush=True)
if __name__=='__main__':main()
