#!/usr/bin/env python3
"""Read historical evidence only; truth is joined exclusively for this offline audit."""
import csv,gzip,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_development import write_csv,write_json
OUT=ROOT/'results/cross_layer_safety_v7_3_dev'
def rows(path):
 with (gzip.open if path.suffix=='.gz' else open)(path,'rt',newline='') as f:return list(csv.DictReader(f))
def run():
 result=[]
 for version,directory,filename,method in [('v7.2','cross_layer_safety_v7_2_confirmation','final_candidate_runs.csv','Final CLO-DSF'),('Candidate 2','cross_layer_safety_v7_1_dev','candidate2_dev_runs.csv','Candidate 2')]:
  old=ROOT/'results'/directory;allrows=rows(old/filename);by={(r['run_id'],r['method']):r for r in allrows}
  for r in allrows:
   if r['method']!=method or r['injected']!='1' or r['detected']!='0':continue
   rid=r['run_id'];start=int(r['start_ms']);v72=version=='v7.2'
   obs=rows(old/('observations' if v72 else 'raw')/(rid+'.csv.gz'))
   obs=[o for o in obs if int(o['time_ms'])>=start]
   val=lambda o,k:float.fromhex(o[k]) if v72 else float(o[k])
   target='control_target_c' if v72 else 'active_control_target_c'
   age='sample_age_ms' if v72 else 'coolant_sensor_update_age_ms'
   gap=max(max(abs(val(o,'pump_command')-val(o,'pump_actual')),abs(val(o,'fan_command')-val(o,'fan_actual'))) for o in obs)
   deviation=max(abs(val(o,target)-92) for o in obs);maxage=max(int(o[age]) for o in obs)
   ev=rows(old/'traces'/(rid+('.final' if v72 else '.candidate2')+'.csv.gz'));ev=[o for o in ev if int(o['time_ms'])>=start]
   peak=max(float(o['anomaly_belief']) for o in ev)
   if r['origin']=='MEMORY':
    assert deviation==0 and gap==0 and maxage==0
    category='B';reason='Stuck bit agrees with stored nominal target: target remains 92; no changed value or actuator response. Passive value observation cannot reveal a latent stuck-at defect.'
    signal='active control target unchanged';minimum='Trusted independent memory March/BIST write-read result (or redundant integrity syndrome after an actual value error); ordinary checksum cannot reveal a stuck-at bit that still holds the correct value.'
   elif r['origin']=='COMMUNICATION':
    assert maxage>0
    category='A';signal='sample timestamp/age and expected 100 ms reception period'
    reason='Age '+str(maxage)+' ms exposes missed/late periodic delivery, but inherited freshness transform tolerates 300 ms and contributes zero mass. Evidence extraction dead zone, not absence of timestamps.'
    minimum='None: a separately specified periodic delivery contract could use existing timestamp/age; not changed in v7.3.'
   elif r['origin']=='ACTUATOR':
    assert gap>0
    category='A';signal='post-update pump/fan command and realized response'
    reason='Nonzero tracking residual is already visible, but division by .20/.25 limits positive mass. With lambda=.8, constant q has limit q/(.2+.8*q); q<1/6 never reaches belief .5. Observed peak remains below confirmation.'
    minimum='None: use existing synchronous command/response contract. Real hardware would require independently trustworthy response feedback and a specified error/dynamics envelope.'
   else:raise ValueError(r)
   entry=dict(version=version,partition=r['partition'],run_id=rid,origin=r['origin'],model=r['model'],behavior=r['behavior'],magnitude=r['magnitude'],silent_plant=int(r['silent_plant']),classification=category,existing_signal=signal,max_tracking_gap=gap,max_target_deviation=deviation,max_sample_age_ms=maxage,max_post_onset_belief=peak,reason=reason,minimum_trusted_observable=minimum)
   for name in ['Simple OR','Weighted Sum','Plain DS','Hybrid','Timing Monitor']:
    other=by.get((rid,name));entry[name.replace(' ','_')+'_detects']=int(other['detected']) if other and (name!='Timing Monitor' or r['origin']=='TIMING') else 'N/A'
   result.append(entry)
 write_csv(OUT/'miss_root_cause_summary.csv',result)
 write_csv(OUT/'observability_gap_summary.csv',[r for r in result if r['classification']=='B'])
 summary={v:{'misses':sum(r['version']==v for r in result),'algorithm_limited':sum(r['version']==v and r['classification']=='A' for r in result),'observability_limited':sum(r['version']==v and r['classification']=='B' for r in result),'silent_plant':sum(r['silent_plant'] for r in result if r['version']==v)} for v in ['v7.2','Candidate 2']}
 write_json(OUT/'miss_analysis.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
