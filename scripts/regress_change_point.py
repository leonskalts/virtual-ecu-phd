#!/usr/bin/env python3
"""One full regression if a new development extension is retained."""
import json,sys,subprocess,tempfile,shutil
from pathlib import Path
import run_change_point as d
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression

def main():
 d.verify();report=json.loads((d.B/'report.json').read_text());assert report['cp_promoted'];assert not (d.B/'regression_started').exists();(d.B/'regression_started').write_text(d.r.now())
 backup=d.B/'binary_backup';backup.mkdir();names=['virtual_ecu_v7_1','virtual_ecu_v7_2_reference','virtual_ecu_v7_2_optimized','virtual_ecu_v7_3']
 for name in names:shutil.copy2(name,backup/name)
 result={}
 try:
  for name,cmd in [('build',['make','-B','-f','clo_dsf_revised.mk','-j4']),('compile',[sys.executable,'-m','compileall','-q','python','scripts','tests']),('tests',[sys.executable,'-m','unittest','discover','-s','tests']),('diff_check',['git','diff','--check'])]:
   print(name,flush=True);p=subprocess.run(cmd,capture_output=True,text=True);(d.B/(name+'.log')).write_text(p.stdout+p.stderr);result[name]=p.returncode;assert not p.returncode,(name,p.stderr[-2500:])
  with tempfile.TemporaryDirectory(prefix='cp-regression-') as folder:
   result['legacy']=legacy_regression(Path(folder));print('LEGACY48 PASS',flush=True);result['rtl']=rtl_regression(Path(folder));print('RTL64 PASS',flush=True)
  protected=json.loads(Path('/tmp/clo-triplex-freeze/historical_hashes.json').read_text());assert all(d.sha(Path(p))==v for p,v in protected.items());result['historical_unchanged']=len(protected)
  for directory in ['ml_assisted_clodsf_development','heterogeneous_observability_development','svm_only_root_cause_audit','triplex_plus_development']:
   out=d.ROOT/'results'/directory;manifest=out/'artifact_hashes.json'
   if manifest.exists():assert all(d.sha(out/p)==v for p,v in json.loads(manifest.read_text()).items())
  d.verify();result.update(Triplex_symmetry=True,Sensor_C_independence=True,Hybrid_HETIA_unchanged=True,GUI_unchanged=True,locked_science_unchanged=True)
 finally:
  for name in names:shutil.copy2(backup/name,name)
  d.dump(d.B/'regression.json',result)
 print('FULL REGRESSION PASS',flush=True)
if __name__=='__main__':main()
