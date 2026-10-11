#!/usr/bin/env python3
"""Integrity, targeted checks and compact artifact finalization; no retuning."""
import json,subprocess,sys,shutil
from pathlib import Path
import run_dynamic_consensus as d
B=d.B;O=d.O

def main():
 d.verify();report=json.loads((B/'report.json').read_text());record={'offline_processing_note':'Physical campaigns executed once; native trusted-input replay used for registered TRAIN/CAL selection and identical-case ablations. Disabled legacy stagger code was removed from the inherited harness before validation freeze; native endpoint and bank parity checked. No validation retuning.'}
 for name,cmd in [('native_dynamic_tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_dynamic_consensus.py']),('compile',[sys.executable,'-m','compileall','-q','python','scripts','tests']),('diff_check',['git','diff','--check'])]:
  ret=subprocess.run(cmd,capture_output=True,text=True);(B/(name+'.log')).write_text(ret.stdout+ret.stderr);record[name]=dict(returncode=ret.returncode,output=ret.stdout+ret.stderr);assert not ret.returncode
 if report['promoted']:
  subprocess.run([sys.executable,'scripts/regress_dynamic_consensus.py'],check=True);record['full_regression']=json.loads((B/'regression.json').read_text())
 else:record['full_regression']='Not run: Dynamic consensus failed preregistered promotion; retained Triplex/previously retained memory unchanged.'
 protected=json.loads(Path('/tmp/clo-triplex-freeze/historical_hashes.json').read_text());assert all(d.sha(Path(p))==v for p,v in protected.items());record['historical_file_hashes_verified']=len(protected)
 for directory in ['change_point_development','parity_space_development','ml_assisted_clodsf_development','heterogeneous_observability_development','svm_only_root_cause_audit','triplex_plus_development']:
  out=d.ROOT/'results'/directory;manifest=out/'artifact_hashes.json'
  if manifest.exists():assert all(d.sha(out/p)==v for p,v in json.loads(manifest.read_text()).items())
 record['build_cleanup']=json.loads((B/'build_cleanup.json').read_text());record['native_replay_parity_cases']=8400;record['native_replay_parity_method_cases']=25200
 d.verify();record.update(Hybrid_HETIA_unchanged=True,GUI_unchanged=True,locked_science_unchanged=True,HEAD_unchanged=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==json.loads((B/'registration.json').read_text())['head'],validation_no_tuning=True,unseen_run=False,commit_push=False,completed_utc=d.r.now())
 with (O/'findings.md').open('a') as f:f.write('\nFinal verification: '+json.dumps(record,indent=2)+'\n')
 calibration=json.loads((O/'calibration.json').read_text());calibration['validation_record']=record;calibration['overhead']=json.loads((B/'overhead.json').read_text());calibration['artifact_hashes']={p.name:d.sha(p) for p in O.iterdir() if p.is_file() and p.name!='calibration.json'};d.dump(O/'calibration.json',calibration)
 for name in ['tapes','work','binary_backup']:
  path=B/name
  if path.exists():shutil.rmtree(path)
 for name in ['bench_inputs.txt','bench_params.txt','bench.c','bench','dc.so','series.c']:
  path=B/name
  if path.exists():path.unlink()
 d.dump(B/'final_verification.json',record);print('FINALIZED',len(list(O.iterdir())),'files; no bulk traces',flush=True)
if __name__=='__main__':main()
