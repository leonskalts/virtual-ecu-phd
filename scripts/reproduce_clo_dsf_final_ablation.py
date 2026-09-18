#!/usr/bin/env python3
"""Required historical gate before implementing v7.2; never writes old evidence."""
import csv,gzip,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'results/cross_layer_safety_v7_1_dev';OUT=ROOT/'results/cross_layer_safety_v7_2_confirmation/validation/ablation_reproduction'
sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_candidate2_development import write_csv,write_json

def run():
 if (OUT/'reproduction.json').exists():raise ValueError('Reproduction already recorded; do not overwrite')
 OUT.mkdir(parents=True,exist_ok=True)
 with (OLD/'development_split_manifest.csv').open() as f:specs=[s for s in csv.DictReader(f) if s['partition']=='development-validation']
 rows=[];detected=correct=unknown=wrong=benign=0
 for i,s in enumerate(specs):
  name=s['run_id'];cmd=json.loads((OLD/'commands'/f'{name}.json').read_text());raw=OUT/f'{name}.csv';metrics=OUT/f'{name}.metrics.csv';cmd[1]=str(raw)
  cmd[cmd.index('--c2-evidence')+1]='/dev/null';cmd[cmd.index('--c2-metrics')+1]=str(metrics)
  subprocess.run(cmd,cwd=ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  with metrics.open() as f:new=list(csv.DictReader(f))
  with (OLD/'metrics'/f'{name}.csv').open() as f:prior=list(csv.DictReader(f))
  assert new==prior,('Historical online metric mismatch',name)
  for p in [raw,raw.with_name(raw.stem+'_summary.csv')]:
   with gzip.open(OLD/'raw'/(p.name+'.gz'),'rb') as f:assert f.read()==p.read_bytes(),name
   p.unlink() # Only new reproduction scratch output; old archives are read-only.
  r=next(r for r in new if r['method']=='No origin reliability');fault=s['origin']!='NORMAL';alarm=int(r['first_post_alarm_ms'])>=0
  detected+=fault and alarm;correct+=fault and alarm and r['origin_at_alarm']==s['origin'];unknown+=fault and alarm and r['origin_at_alarm']=='UNKNOWN';wrong+=fault and alarm and r['origin_at_alarm'] not in ['UNKNOWN',s['origin']];benign+=not fault and int(r['first_alarm_ms'])>=0
  rows.append(dict(run_id=name,true_origin_evaluation_only=s['origin'],**r))
  if i%25==0:print(f'Reproduced {i+1}/{len(specs)}',flush=True)
 assert (detected,correct,unknown,wrong)==(262,202,60,0),(detected,correct,unknown,wrong)
 write_csv(OUT/'reproduced_no_origin_discount.csv',rows);write_json(OUT/'reproduction.json',dict(status='PASS',runs=len(specs),detected=detected,correct_origins=correct,unknown=unknown,wrong_nonunknown=wrong,benign_alarms=benign,all_historical_method_metrics_identical=True,all_raw_and_summary_bytes_identical=True,parameters_changed=False))
 print('Ablation gate PASS: 262 detected, 202 correct, 60 UNKNOWN, zero wrong.',flush=True)
if __name__=='__main__':run()
