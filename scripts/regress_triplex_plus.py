#!/usr/bin/env python3
"""Final development regression and historical integrity audit."""
import sys,json,subprocess,tempfile,shutil
from pathlib import Path
import run_triplex_plus as r
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression

def main():
 r.verify();assert not (r.B/'regression_started').exists();(r.B/'regression_started').write_text(r.now())
 backup=r.B/'regression_binaries';backup.mkdir();names=['virtual_ecu_v7_1','virtual_ecu_v7_2_reference','virtual_ecu_v7_2_optimized','virtual_ecu_v7_3']
 for name in names:shutil.copy2(name,backup/name)
 result={}
 try:
  for name,cmd in [('build',['make','-B','-f','clo_dsf_revised.mk','-j4']),('python_compile',[sys.executable,'-m','compileall','-q','python','scripts','tests']),('tests',[sys.executable,'-m','unittest','discover','-s','tests']),('diff_check',['git','diff','--check'])]:
   print(name,flush=True);p=subprocess.run(cmd,capture_output=True,text=True);(r.B/(name+'.log')).write_text(p.stdout+p.stderr);result[name]=p.returncode;assert p.returncode==0,(name,p.stderr[-2000:])
  with tempfile.TemporaryDirectory(prefix='plus-regression-') as tmp:
   result['legacy']=legacy_regression(Path(tmp));print('legacy48 PASS',flush=True)
   result['rtl']=rtl_regression(Path(tmp));print('RTL64 PASS',flush=True)
  protected=json.loads(Path('/tmp/clo-triplex-freeze/historical_hashes.json').read_text());assert all(r.sha(Path(p))==v for p,v in protected.items())
  result.update(Hybrid_HETIA_historical_unchanged=True,protected_files=len(protected),Triplex_symmetry_passed=True,sensor_C_independence_passed=True)
  r.verify();result.update(frozen_Triplex_unchanged=True,comparative_unseen_unchanged=True,GUI_unchanged=True,validation_lock_unchanged=True)
 finally:
  for name in names:shutil.copy2(backup/name,name)
  r.dump(r.O/'regression.json',result)
 print('ALL PASS',flush=True)

if __name__=='__main__':main()
