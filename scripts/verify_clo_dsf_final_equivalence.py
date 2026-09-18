#!/usr/bin/env python3
"""Replay every completed confirmation observation through both implementations."""
import csv,gzip,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/cross_layer_safety_v7_2_confirmation'
def run():
 frozen=json.loads((OUT/'clo_dsf_final_scientific_hashes.json').read_text())
 for name,digest in frozen['sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
 cfg=json.loads((OUT/'clo_dsf_final_config.json').read_text())['parameters'];fields=['r_detection','lambda_temporal','suspect_threshold','confirmed_threshold','localization_threshold','localization_margin_threshold','ignorance_limit','confirmation_persistence']
 with tempfile.TemporaryDirectory(prefix='final-equivalence-') as t:
  exe=Path(t)/'replay';sources=['src/v7/ds_evidence.c','src/v7/clo_observability.c','src/v7/clo_dsf.c','src/v7_1/candidate2_evidence.c','src/v7_1/candidate2_observability.c','src/v7_2/clo_dsf_final.c','src/v7_2/final_observation_io.c','src/v7_2/final_sparse_math.c','src/v7_2/clo_dsf_final_optimized.c']
  subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-O2','-Iinclude','tests/clo_final_equivalence.c',*sources,'-o',str(exe)],cwd=ROOT,check=True)
  with (OUT/'confirmation_configuration_manifest.csv').open() as f:specs=list(csv.DictReader(f))
  result=[]
  for i,s in enumerate(specs):
   path=OUT/'observations'/f"{s['run_id']}.csv.gz"
   with gzip.open(path,'rb') as f:payload=f.read()
   p=subprocess.run([str(exe),*[str(cfg[k]) for k in fields]],input=payload,capture_output=True)
   if p.returncode:raise RuntimeError(f"{s['run_id']}: {p.stderr.decode()}")
   result.append(dict(run_id=s['run_id'],rows=int(p.stdout),bit_identical_complete_state=True,observations_sha256=hashlib.sha256(payload).hexdigest()))
   if i%100==0:print(f'Equivalent {i+1}/{len(specs)}',flush=True)
  with (OUT/'benchmark/equivalence_runs.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
  record=dict(status='PASS',runs=len(result),observations=sum(r['rows'] for r in result),bit_identical_complete_state=True,numerical_tolerance_used=0,decision_discrepancies=0,scientific_hashes_verified=True,algorithm_parameters_changed=False,optimization='Sparse nonzero product traversal in unchanged product order; cached logical cardinality/partition map; unchanged validation and normalization')
  (OUT/'benchmark/equivalence.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
if __name__=='__main__':run()
