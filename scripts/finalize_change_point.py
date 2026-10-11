#!/usr/bin/env python3
"""Integrity, targeted checks and compact artifact finalization; no retuning."""
import json,subprocess,sys,shutil
from pathlib import Path
import run_change_point as d
B=d.B;O=d.O

def main():
 d.verify();report=json.loads((B/'report.json').read_text());record={'offline_processing_note':'Slope-fit computation interrupted before model completion to remove repeated NPZ decompression; existing physical TRAIN/CAL data reused unchanged. Comparator transform vectorization checked against scalar implementation at 1e-12. Diagnostic parameter replay restarted to parallelize the same six fixed configurations in isolated temporary files; no physical campaign rerun or parameter-rule change.'}
 for name,cmd in [('native_cp_tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_triplex_change_point.py']),('compile',[sys.executable,'-m','compileall','-q','python','scripts','tests']),('diff_check',['git','diff','--check'])]:
  ret=subprocess.run(cmd,capture_output=True,text=True);(B/(name+'.log')).write_text(ret.stdout+ret.stderr);record[name]=dict(returncode=ret.returncode,output=ret.stdout+ret.stderr);assert not ret.returncode
 if report['cp_promoted']:
  subprocess.run([sys.executable,'scripts/regress_change_point.py'],check=True);record['full_regression']=json.loads((B/'regression.json').read_text())
 else:record['full_regression']='Not run: CP failed preregistered promotion; retained Triplex/previously retained memory unchanged.'
 protected=json.loads(Path('/tmp/clo-triplex-freeze/historical_hashes.json').read_text());assert all(d.sha(Path(p))==v for p,v in protected.items());record['historical_file_hashes_verified']=len(protected)
 for directory in ['ml_assisted_clodsf_development','heterogeneous_observability_development','svm_only_root_cause_audit','triplex_plus_development']:
  out=d.ROOT/'results'/directory;manifest=out/'artifact_hashes.json'
  if manifest.exists():assert all(d.sha(out/p)==v for p,v in json.loads(manifest.read_text()).items())
 d.verify();record.update(Hybrid_HETIA_unchanged=True,GUI_unchanged=True,locked_science_unchanged=True,HEAD_unchanged=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==json.loads((B/'registration.json').read_text())['head'],validation_no_tuning=True,unseen_run=False,commit_push=False,completed_utc=d.r.now())
 with (O/'findings.md').open('a') as f:f.write('\nFinal verification: '+json.dumps(record,indent=2)+'\n')
 calibration=json.loads((O/'change_point_calibration.json').read_text());calibration['validation_record']=record;calibration['overhead']=json.loads((B/'overhead.json').read_text());calibration['artifact_hashes']={p.name:d.sha(p) for p in O.iterdir() if p.is_file() and p.name!='change_point_calibration.json'};d.dump(O/'change_point_calibration.json',calibration)
 for name in ['tapes','work','binary_backup']:
  path=B/name
  if path.exists():shutil.rmtree(path)
 for name in ['bench_inputs.txt','bench_params.txt','bench.c','bench','cp.so','series.c']:
  path=B/name
  if path.exists():path.unlink()
 d.dump(B/'final_verification.json',record);print('FINALIZED',len(list(O.iterdir())),'files; no bulk traces',flush=True)
if __name__=='__main__':main()
