#!/usr/bin/env python3
"""One final regression; restore pre-existing tracked build artifacts."""
import sys,json,subprocess,tempfile,shutil
from pathlib import Path
import run_comparative_benchmark as r
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression
B=r.B;O=r.OUT

def main():
 r.verify();r.check_lock();assert not (B/'regression_started').exists()
 (B/'regression_started').write_text(r.now());backup=B/'regression_binaries';backup.mkdir()
 names=['virtual_ecu_v7_1','virtual_ecu_v7_2_reference','virtual_ecu_v7_2_optimized','virtual_ecu_v7_3']
 for name in names:shutil.copy2(name,backup/name)
 result={}
 try:
  for name,cmd in [('build',['make','-B','-f','clo_dsf_revised.mk','-j4']),('python_compile',[sys.executable,'-m','compileall','-q','python','scripts','tests']),('tests',[sys.executable,'-m','unittest','discover','-s','tests']),('diff_check',['git','diff','--check'])]:
   print(name,flush=True);p=subprocess.run(cmd,capture_output=True,text=True);(B/(name+'.log')).write_text(p.stdout+p.stderr);result[name]=p.returncode;assert p.returncode==0,(name,p.stderr[-2000:])
  with tempfile.TemporaryDirectory(prefix='comparative-regression-') as tmp:
   result['legacy']=legacy_regression(Path(tmp));print('legacy48 PASS',flush=True)
   result['rtl']=rtl_regression(Path(tmp));print('RTL64 PASS',flush=True)
  protected=json.loads(Path('/tmp/clo-triplex-freeze/historical_hashes.json').read_text())
  assert all(r.sha(Path(p))==v for p,v in protected.items())
  result['historical_Hybrid_HETIA_unchanged']=True;result['historical_files_checked']=len(protected)
  r.verify();r.check_lock();result.update(frozen_Triplex_unchanged=True,previous_final_unseen_unchanged=True,GUI_unchanged=True,method_freeze_unchanged=True)
 finally:
  for name in names:shutil.copy2(backup/name,name)
  r.dump(O/'regression.json',result)
 print('ALL PASS',flush=True)

if __name__=='__main__':main()
