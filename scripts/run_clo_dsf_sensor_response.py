#!/usr/bin/env python3
"""One groupwise CURRENT sensor-response development campaign (not a holdout)."""
import csv,difflib,hashlib,json,subprocess,sys,tempfile,shutil
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_development import write_csv,sha,ORIGINS
from virtual_ecu.clo_dsf_holdout import profile_identity,prepare_work
from virtual_ecu.clo_dsf_final_reporting import records
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
from virtual_ecu.clo_dsf_candidate2_development import aggregate
OUT=ROOT/'results/clo_dsf_current';BASE_COMMAND=c.command

def design():
 specs=[]
 for f,load in enumerate([.42,.61,.79,.96,.56,.92]):
  cells=[]
  for bit in [(f+i)%5 for i in range(3)]:
   for polarity in [0,1]:
    for b in ['transient','intermittent','permanent']:cells.append(('MEMORY','stuck_bit',b,bit,polarity,0))
  for bit in [f%5,(f+2)%5]:
   for b in ['transient','intermittent','permanent']:cells.append(('MEMORY','bit_flip',b,bit,0,0))
  for origin,models in [('COMMUNICATION',{'delayed_update':[100,800],'dropped_update':[1,4],'replayed_sample':[100,1100]}),('ACTUATOR',{'pump_degraded':[.989,.973,.861,.621],'fan_stuck_off':[0,0]}),('TIMING',{'deadline_miss':[0,0],'task_delay':[200,900]}),('SENSOR_CONTROL',{'sensor_bias':[-.9,.9,-1.1,1.1,-2.2,2.2],'sensor_interface_intermittent':[.3,.45,.7,2.1]})]:
   for model,mags in models.items():
    for mag in mags:
     for b in ['transient','intermittent','permanent']:cells.append((origin,model,b,mag,0,0))
  for mag in [-.9,.9,-2.2,2.2,-4.4,4.4]:
   for rise in [2000,10000,30000]:cells.append(('SENSOR_CONTROL','sensor_bias_ramp','permanent',mag,0,rise))
  cells += [('NORMAL','baseline','none',0,0,0)]*30
  assert len(cells)==150
  for j,(origin,model,b,mag,polarity,rise) in enumerate(cells):
   profile=[dict(start_ms=a,end_ms=z,vehicle_speed_kph=(23+13*f)*fac,engine_load=(load+j*.000023)*fac,ambient_temp_c=23+f*2.7+j*.0013,external_airflow_factor=0,road_slope_percent=0) for a,z,fac in [(0,14900,.63),(14900,26300,1),(26300,26400,.4),(26400,48300,.97),(48300,75900,.62),(75900,120000,.87)]]
   updates=[[30500,99],[61300,92]] if (j+f)%2 else []
   s=dict(run_id=f'response_{len(specs):04}',origin=origin,model=model,behavior=b,magnitude=mag,stuck_polarity=polarity,start_ms=120100 if origin=='NORMAL' else 22500+(j%9)*500+f*100,duration_ms=0 if b in ['none','permanent'] else 100 if model=='deadline_miss' and b=='transient' else [300,900,6100][(j+f)%3] if origin=='SENSOR_CONTROL' else [8900,14300,19700][(j+f)%3],group=f'response_family_{f}',partition='development-train' if f<4 else 'development-validation',profile=f'response_profile_{len(specs):04}',profile_json=json.dumps(profile,sort_keys=True),target_updates_json=json.dumps(updates),workload='authorized_updates' if updates else 'static_target',seed=81001+f*307+j*11,simulation_duration_ms=120000,sensor_ramp_rise_ms=rise,sensor_variation=['0:0:8600','0.025:0:8600','0.065:0:8600','0.095:0:8600','0.04:1.4:14600','0.08:2.4:8200'][(j-120)//5] if origin=='NORMAL' else '0:0:8600',initially_latent_stuck=int(model=='stuck_bit' and ((92>>int(mag))&1)==polarity))
   s['profile_semantic_sha256']=profile_identity(profile);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();specs.append(s)
 assert len(specs)==900
 return specs

def command(s,work):
 physical=dict(s)
 if s['model']=='sensor_bias_ramp':physical.update(model='sensor_bias',magnitude=0)
 cmd=BASE_COMMAND(physical,work)
 if s['model']=='sensor_bias_ramp':cmd+=['--revised-sensor-ramp',f"{s['start_ms']}:{s['sensor_ramp_rise_ms']}:{s['magnitude']}"]
 return cmd

def report(rows):
 c.summarize(rows)
 localization=[];ablation=[];sub=[];confusion=[]
 for part in ['development-train','development-validation']:
  a={r['run_id']:r for r in rows if r['partition']==part and r['method']=='Revised CLO-DSF'}
  for method in c.METHODS:
   rs=[r for r in rows if r['partition']==part and r['method']==method]
   groups={'weak_bias':[r for r in rs if r['model']=='sensor_bias' and abs(r['magnitude'])<=1.1], 'positive_bias':[r for r in rs if r['model']=='sensor_bias' and r['magnitude']>0], 'negative_bias':[r for r in rs if r['model']=='sensor_bias' and r['magnitude']<0], 'low_magnitude':[r for r in rs if r['origin']=='SENSOR_CONTROL' and abs(r['magnitude'])<=1.1], 'medium_high_magnitude':[r for r in rs if r['origin']=='SENSOR_CONTROL' and abs(r['magnitude'])>1.1], 'sensor_short':[r for r in rs if r['origin']=='SENSOR_CONTROL' and 0<r['duration_ms']<=900], 'sensor_persistent':[r for r in rs if r['origin']=='SENSOR_CONTROL' and r['duration_ms']==0], 'slow_bias':[r for r in rs if r['model']=='sensor_bias_ramp'],'sensor_pulses':[r for r in rs if r['model']=='sensor_interface_intermittent'], 'effective_memory':[r for r in rs if r['origin']=='MEMORY' and r['effective_memory_corruption']], 'dormant_memory':[r for r in rs if r['model']=='stuck_bit' and not r['effective_memory_corruption']]}
   for group,subset in groups.items():sub.append(dict(partition=part,method=method,group=group,**aggregate(subset)))
   if method!='Weighted Sum':
    for origin in ['ALL',*ORIGINS]:
     subset=[r for r in rs if origin=='ALL' or r['origin']==origin]
     localization.append(dict(partition=part,method=method,origin=origin,**runtime_stats(subset)))
     confusion.append(dict(partition=part,method=method,origin=origin,**{o:sum(r['alarm_'+o] for r in subset) for o in ['UNKNOWN',*ORIGINS]}))
   if method=='Revised CLO-DSF':continue
   b={r['run_id']:r for r in rs};cnt=[0]*4
   for k,r in a.items():
    if not r['injected']:continue
    d=b[k];cnt[0 if r['detected'] and d['detected'] else 1 if r['detected'] else 2 if d['detected'] else 3]+=1
   ablation.append(dict(partition=part,comparator=method,both=cnt[0],only_improved=cnt[1],only_comparator=cnt[2],neither=cnt[3],current_silent=sum(r['silent_plant'] for r in a.values()),comparator_silent=sum(r['silent_plant'] for r in rs)))
 write_csv(OUT/'subgroup_summary.csv',sub);write_csv(OUT/'runtime_localization_summary.csv',localization);write_csv(OUT/'runtime_confusion_summary.csv',confusion);write_csv(OUT/'ablation_comparison.csv',ablation)

def run():
 baseline=Path('/tmp/clo-sensor-response/prechange.c');specs=design();c.command=command
 with tempfile.TemporaryDirectory(prefix='clo-sensor-development-') as tmp:
  work=Path(tmp);c.build_prechange(work,baseline);c.prepare(specs,work)
  prior={r['profile_semantic_sha256'] for r in records(OUT/'configuration_manifest.csv')};assert not prior&{s['profile_semantic_sha256'] for s in specs}
  for p in OUT.iterdir():
   if not p.is_file():raise ValueError('Unexpected CURRENT subdirectory')
  for p in OUT.iterdir():p.unlink()
  for s in specs:s['command_json']=json.dumps([v.replace(str(work),'$WORK').replace(str(ROOT),'$ROOT') for v in command(s,work)])
  write_csv(OUT/'development_manifest.csv',specs)
  shutil.copy2('/tmp/clo-sensor-response/sensor_miss_classification.csv',OUT/'sensor_miss_classification.csv')
  frozen={p:sha(ROOT/p) for p in ['src/v7_3/clo_dsf_revised.c','include/clo_dsf_revised.h','src/v7_3/revised_runtime.c','scripts/run_clo_dsf_sensor_response.py','docs/clo_dsf_current.md','results/cross_layer_safety_v7_3_dev/revised.cfg','results/clo_dsf_current/development_manifest.csv']}
  reverse=''.join(difflib.unified_diff((ROOT/'src/v7_3/clo_dsf_revised.c').read_text().splitlines(True),baseline.read_text().splitlines(True),fromfile='current.c',tofile='prechange.c'))
  (OUT/'validation_record.md').write_text('# Sensor-response development record\n\nRegistered '+datetime.now(timezone.utc).isoformat()+' before TRAIN outcomes. 900 new configurations;600 TRAIN/300 VALIDATION. Parameters fixed initially; no search. Previous final-unseen dataset is now development evidence, preserved unchanged.\n\nProtocol: docs/clo_dsf_current.md. A0 actual pre-change source SHA256 '+sha(baseline)+'\n\nSource/design SHA256:\n```json\n'+json.dumps(frozen,indent=2)+'\n```\n\nA0 reconstruction from A1 (temporary only):\n```diff\n'+reverse+'```\n')
  retained={next(s['run_id'] for s in specs if s['origin']==o) for o in [*ORIGINS,'NORMAL']};retained.add(next(s['run_id'] for s in specs if s['model']=='sensor_bias_ramp'));retained.add(next(s['run_id'] for s in specs if s['model']=='sensor_interface_intermittent'))
  rows=[]
  for part in ['development-train','development-validation']:
   assert all(sha(ROOT/p)==h for p,h in frozen.items())
   selected=[s for s in specs if s['partition']==part]
   for i,s in enumerate(selected):
    r=c.execute(s,work,s['run_id'] in retained)
    for x in r:x.pop('command_json',None)
    rows+=r
    if (i+1)%50==0:print(part,i+1,'/',len(selected),flush=True)
   report(rows)
   a=[r for r in rows if r['partition']==part and r['method']=='Revised CLO-DSF'];b={r['run_id']:r for r in rows if r['partition']==part and r['method']=='Pre-change CLO-DSF'}
   failures=dict(benign=sum(r['false_alarm'] for r in a),wrong=sum(r['wrong_localized_runtime_samples'] for r in a),lost=sum(b[r['run_id']]['detected'] and not r['detected'] for r in a),effective_missed=sum(r['origin']=='MEMORY' and r['effective_memory_corruption'] and not r['detected'] for r in a),dormant_alarm=sum(r['model']=='stuck_bit' and not r['effective_memory_corruption'] and r['detected'] for r in a))
   with (OUT/'validation_record.md').open('a') as f:f.write('\n'+part+' complete; checks '+json.dumps(failures)+'\n')
   print(part,failures,flush=True)
   if part=='development-train' and any(failures.values()):raise RuntimeError('TRAIN rejects candidate; no validation outcomes run')
  assert all(sha(ROOT/p)==h for p,h in frozen.items())
  print('900-case development complete',flush=True)
if __name__=='__main__':run()
