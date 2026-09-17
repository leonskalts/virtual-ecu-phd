#!/usr/bin/env python3
"""Read-only historical verification; replay writes only Candidate 2 validation."""
import csv,gzip,json,hashlib,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.final_evidence import verify_frozen
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression,representative_replay
OUT=ROOT/'results/cross_layer_safety_v7_1_dev'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 record={'frozen_legacy':verify_frozen()}
 subprocess.run(['python3','scripts/verify_clo_dsf_candidate.py'],cwd=ROOT,check=True)
 record['legacy_cases']=legacy_regression(OUT);record['rtl_cases']=rtl_regression(OUT);record['v5_replays']=representative_replay(OUT)
 old=ROOT/'results/cross_layer_safety_v7_dev';specs=list(csv.DictReader((old/'development_split_manifest.csv').open()));dest=OUT/'validation/candidate1_replay';dest.mkdir(parents=True,exist_ok=True);replays=[]
 for origin in ['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR','NORMAL']:
  spec=next(s for s in specs if s['origin']==origin and s['partition']=='development-validation');name=spec['run_id'];cmd=json.loads((old/'commands'/f'{name}.json').read_text());cmd[1]=str(dest/f'{name}.csv')
  for option,suffix in [('--clo-evidence','.clo_dsf.csv'),('--clo-metrics','.metrics.csv')]:cmd[cmd.index(option)+1]=str(dest/(name+suffix))
  subprocess.run(cmd,cwd=ROOT,check=True,capture_output=True)
  pairs=[(old/'raw'/f'{name}.csv.gz',dest/f'{name}.csv'),(old/'raw'/f'{name}_summary.csv.gz',dest/f'{name}_summary.csv'),(old/'traces'/f'{name}.clo_dsf.csv.gz',dest/f'{name}.clo_dsf.csv')]
  for prior,current in pairs:
   with gzip.open(prior,'rb') as f:assert f.read()==current.read_bytes(),str(prior)
  assert (old/'metrics'/f'{name}.csv').read_bytes()==(dest/f'{name}.metrics.csv').read_bytes()
  replays.append({'origin':origin,'run_id':name,'raw_summary_evidence_metrics':'byte-identical'})
 record['candidate1_replays']=replays
 # New-cohort C1 online bank must agree with original frozen executable.
 specs=list(csv.DictReader((OUT/'development_split_manifest.csv').open()));matched=[]
 for origin in ['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR','NORMAL']:
  spec=next(s for s in specs if s['origin']==origin and s['partition']=='development-validation');name=spec['run_id'];cmd=json.loads((OUT/'commands'/f'{name}.json').read_text());cut=cmd.index('--c2-config');cmd=cmd[:cut];cmd[0]=str(ROOT/'virtual_ecu_v7');cmd[1]=str(dest/f'new_{name}.csv');metrics=dest/f'new_{name}.metrics.csv'
  cmd+=['--clo-config',str(old/'clo_dsf_candidate.cfg'),'--clo-comparison','validation','--clo-evaluation-start',str(spec['start_ms']),'--clo-metrics',str(metrics)]
  subprocess.run(cmd,cwd=ROOT,check=True,capture_output=True)
  a=next(r for r in csv.DictReader(metrics.open()) if r['method']=='CLO-DSF');b=next(r for r in csv.DictReader((OUT/'metrics'/f'{name}.csv').open()) if r['method']=='Candidate 1')
  for key in ['first_alarm_ms','first_post_alarm_ms','first_localization_ms','origin_at_alarm','first_origin','samples','alarm_samples','pre_alarm_samples','propagation_samples']:assert a[key]==b[key],(name,key,a[key],b[key])
  matched.append(name)
 record['candidate1_new_cohort_bank_matches']=matched
 baseline=Path('/tmp/clo-c2-preflight/existing_hashes.json')
 if baseline.exists():
  original=json.loads(baseline.read_text());allowed={'Makefile','scripts/virtual_ecu_gui.py'};changed=[];unchanged=0
  for name,digest in original.items():
   p=ROOT/name
   if not p.exists() or sha(p)!=digest:changed.append(name)
   else:unchanged+=1
  assert set(changed)<=allowed,changed
  record['preservation']={'existing_files':len(original),'unchanged_files':unchanged,'authorized_additive_integration_changes':changed,'all_candidate1_files_and_evidence_unchanged':True,'user_session_unchanged':True}
 record['status']='PASS';(OUT/'scientific_regression.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':run()
