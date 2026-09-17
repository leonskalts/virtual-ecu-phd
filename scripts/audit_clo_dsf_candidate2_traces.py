#!/usr/bin/env python3
"""Audit selected-validation frame invariants against archived online C metrics."""
import csv,gzip,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/cross_layer_safety_v7_1_dev'
def run():
 with (OUT/'development_split_manifest.csv').open() as f:specs=[r for r in csv.DictReader(f) if r['partition']=='development-validation']
 count=0;unknown=0
 for spec in specs:
  name=spec['run_id'];first=-1;alarm_samples=0;previous=-1
  with gzip.open(OUT/'traces'/f'{name}.candidate2.csv.gz','rt') as f:
   for row in csv.DictReader(f):
    now=int(row['time_ms']);assert now>previous;previous=now
    masses=[float(row[f'origin_mass_{i}']) for i in range(1,32)];assert all(math.isfinite(m) and 0<=m<=1 for m in masses);assert abs(sum(masses)-1)<1e-7
    assert float(row['detection_mass_normal'])==0;assert abs(float(row['anomaly_belief'])+float(row['anomaly_ignorance'])-1)<1e-7;assert float(row['anomaly_plausibility'])==1;assert float(row['detection_conflict'])==0
    assert (row['alarm']=='1')==(row['detector_state']=='CONFIRMED')
    if row['alarm']=='1':
     alarm_samples+=1
     if first<0:first=now
     unknown+=row['estimated_origin']=='UNKNOWN'
    if row['estimated_origin']!='UNKNOWN':assert row['alarm']=='1' and row['localization_valid']=='1'
    scores=[sum(masses[i-1]/i.bit_count() for i in range(1,32) if i&(1<<j)) for j in range(5)];ordered=sorted(scores,reverse=True)
    assert abs(float(row['origin_score'])-ordered[0])<1e-7;assert abs(float(row['origin_margin'])-(ordered[0]-ordered[1]))<1e-7
    assert not any(k in row for k in ['true_origin','fault_active','fault_model','reference_temperature'])
    count+=1
  with (OUT/'metrics'/f'{name}.csv').open() as f:m=next(r for r in csv.DictReader(f) if r['method']=='Candidate 2')
  assert first==int(m['first_alarm_ms']);assert alarm_samples==int(m['alarm_samples'])
 record=dict(status='PASS',validation_runs=len(specs),runtime_rows=count,confirmed_unknown_rows=unknown,checks=['normalized five-origin masses','logical five-origin pignistic score/margin','positive binary mass and zero conflict','runtime state/localization consistency','online summary match','strict time order','runtime log truth exclusion'])
 (OUT/'validation/trace_audit.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
if __name__=='__main__':run()
