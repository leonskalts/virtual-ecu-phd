#!/usr/bin/env python3
"""Pre-registered, group-disjoint redundant-sensor development (never holdout)."""
import csv,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
import run_clo_dsf_active_diagnostic as active
import run_clo_dsf_integrity_event as reporting
import run_clo_dsf_sensor_response as response
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_development import write_csv,sha
from virtual_ecu.clo_dsf_candidate2_development import aggregate
OUT=c.OUT;BASE=Path('/tmp/clo-redundancy');METHODS=['Pre-change CLO-DSF','Revised CLO-DSF','Weighted Sum']
def design():
 specs=[];old=active.design()
 for f in range(10):
  block=old[f*120:(f+1)*120];cells=[dict(s) for s in block if s['origin']!='SENSOR_CONTROL']
  template=next(s for s in block if s['origin']=='SENSOR_CONTROL')
  sensor=[]
  for chain in ['primary','reference']:
   for mag in [-1.4,1.4,-2.4,2.4]:
    for rise in [9000,27000,49000]:sensor.append((chain,'sensor_bias_ramp','permanent',mag,0,rise))
   for mag in [-.9,.9]:
    for dur in [500,0]:sensor.append((chain,'sensor_bias','transient' if dur else 'permanent',mag,dur,0))
   for mag in [.5,1.8]:sensor.append((chain,'sensor_interface_intermittent','permanent',mag,0,0))
  sensor += [('reference','sensor_dropout','transient',0,900,0),('reference','sensor_dropout','permanent',0,0,0)]
  sensor += [('common_mode','sensor_bias_ramp','permanent',mag,0,35000) for mag in [-2.4,2.4]]
  for chain,model,behavior,mag,dur,rise in sensor:
   s=dict(template);s.update(sensor_chain=chain,model=model,behavior=behavior,magnitude=mag,duration_ms=dur,sensor_ramp_rise_ms=rise,initially_latent_stuck=0);cells.append(s)
  assert len(cells)==140
  for j,s in enumerate(cells):
   idx=len(specs);s['run_id']=f'redundant_{idx:04}';s['profile']=f'redundant_profile_{idx:04}';s['group']=f'redundant_family_{f}'
   s['partition']='development-train' if f<6 else 'development-validation'
   profile=json.loads(s['profile_json'])
   for z in profile:
    z['vehicle_speed_kph']+=1.31+j*.0031;z['engine_load']*=.979;z['ambient_temp_c']+=.61+j*.0017
   s['profile_json']=json.dumps(profile,sort_keys=True);s['profile_semantic_sha256']=profile_identity(profile)
   s['seed']=2300041+f*1999+j*41;s['reference_seed']=510007+f*1237+j*73
   s['reference_offset']=round((j%5-2)*.05,3);s['reference_noise']=[.03,.06,.09][(j+f)%3]
   if s['origin']!='NORMAL':s['start_ms']=23900+f*100+(j%9)*300
   s['sensor_chain']=s.get('sensor_chain','none')
   s['anchor_status']='not_applicable'
   s.pop('configuration_sha256');s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();specs.append(s)
 assert len(specs)==1400 and len({s['profile_semantic_sha256'] for s in specs})==1400
 return specs

def command(s,work):
 physical=dict(s);chain=s['sensor_chain']
 if chain=='reference':physical.update(model='sensor_bias',magnitude=0,sensor_ramp_rise_ms=0)
 cmd=response.command(physical,work)
 cmd+=['--revised-reference',f"{s['reference_seed']}:{s['reference_offset']}:{s['reference_noise']}"]
 if chain in ['reference','common_mode']:
  kind={'sensor_bias_ramp':1,'sensor_bias':2,'sensor_dropout':3,'sensor_interface_intermittent':4}[s['model']]
  cmd+=['--revised-reference-fault',f"{kind}:{s['start_ms']}:{s['sensor_ramp_rise_ms']}:{s['duration_ms']}:0:{s['magnitude']}"]
 return cmd

def report(rows):
 reporting.OUT=OUT;reporting.METHODS=METHODS;reporting.report(rows)
 groups=[]
 for part in ['development-train','development-validation']:
  for method in METHODS:
   rr=[r for r in rows if r['partition']==part and r['method']==method]
   for chain in ['primary','reference','common_mode']:
    for model in ['ALL','sensor_bias_ramp','sensor_bias','sensor_interface_intermittent','sensor_dropout']:
     ss=[r for r in rr if r['sensor_chain']==chain and (model=='ALL' or r['model']==model)]
     if ss:groups.append(dict(partition=part,method=method,chain=chain,model=model,**aggregate(ss)))
 write_csv(OUT/'redundancy_summary.csv',groups)
 for p in OUT.glob('*.csv'):p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))

def main():
 if (OUT/'campaign_manifest.csv').exists() and 'redundant_0000' in (OUT/'campaign_manifest.csv').read_text():raise SystemExit('Refuse accidental repeat of registered campaign')
 specs=design();old=set();audit=[]
 for p in (ROOT/'results').rglob('*manifest.csv'):
  with p.open() as f:identities={r['profile_semantic_sha256'] for r in csv.DictReader(f) if r.get('profile_semantic_sha256')}
  if identities:audit.append(dict(manifest=str(p.relative_to(ROOT)),sha256=sha(p),profiles=len(identities),overlap=len(identities&{s['profile_semantic_sha256'] for s in specs})));old|=identities
 assert not old&{s['profile_semantic_sha256'] for s in specs}
 assert not {s['group'] for s in specs if s['partition']=='development-train'}&{s['group'] for s in specs if s['partition']=='development-validation'}
 with tempfile.TemporaryDirectory(prefix='clo-redundancy-development-') as tmp:
  work=Path(tmp);c.build_prechange(work,BASE/'baseline.c');prepare_work(work,specs);c.METHODS=METHODS;c.command=command
  for s in specs:s['command_json']=json.dumps([x.replace(str(work),'$WORK').replace(str(ROOT),'$ROOT') for x in command(s,work)])
  assert all(p.is_file() for p in OUT.iterdir())
  for p in OUT.iterdir():p.unlink()
  write_csv(OUT/'campaign_manifest.csv',specs);write_csv(OUT/'overlap_audit.csv',audit)
  for p in OUT.glob('*.csv'):p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
  scientific=[p for folder in ['src','include'] for p in (ROOT/folder).rglob('*') if p.suffix in ['.c','.h']]
  scientific += [Path(__file__),c.CONFIG,OUT/'campaign_manifest.csv']
  frozen={str(p.relative_to(ROOT)):sha(p) for p in scientific};(BASE/'frozen.json').write_text(json.dumps(frozen,indent=2))
  (OUT/'validation_record.md').write_text('# Redundant sensor development\n\nRegistered before outcomes '+datetime.now(timezone.utc).isoformat()+'. A0 baseline '+(BASE/'head').read_text().strip()+'.\n\n1400 cases: TRAIN840 (720 faults/120 benign), VALIDATION560 (480 faults/80 benign). Six versus four disjoint operating families. Each family:20 MEMORY,20 TIMING,20 COMMUNICATION,20 ACTUATOR,40 SENSOR_CONTROL,20 benign. Sensor cases/family:12 primary and12 reference slow drifts,4 steps and2 pulses per chain,2 reference conversion dropouts,2 common-mode drifts. New profiles/seeds/onsets; all previous inline profile manifests audited before replacing CURRENT. No unseen holdout. All settings fixed before TRAIN; no search.\n\nHardware assumption: two co-located independent temperature transducers, separate ADC/calibration/noise/update state, synchronous100ms acquisition. Sensor2 samples plant only inside the sensor model, quantizes0.01C, has independent seeded bounded uniform noise0.03/0.06/0.09C and offsets -0.10 through+0.10C. Its measurement is not supplied to control, only runtime diagnostics. A separate counterfactual ECU remains the propagation reference. Primary faults never enter sensor2 unless the explicitly registered common-mode experiment separately injects both chains. Reference-only faults leave primary/control unperturbed. No perfect equality or inference from fault labels.\n\nEvidence: full32s signed mean of primary acquisition minus reference, reset on gaps/missing values; e=min(1,max(0,(abs(mean)-0.90)/2)). Window bound0.90C covers historical legal primary triangular measurement variation A<=2.3C,P<=24.2s (mean bound0.435C), aggregate calibration0.20C, bounded noise0.20C,quantization0.005C. Alternation cancels; genuine shared thermal ramps cancel. Explicit current conversion-failure status produces sensor evidence; disabled hardware/stale timestamps alone do not. Merge by max into existing SENSOR_CONTROL evidence; DS/global thresholds and causal precedence unchanged. Sensor chain sub-origin always UNKNOWN for disagreement: two readings cannot identify the faulty member. Broad SENSOR_CONTROL localization is assessed. No claim to detect identical common-mode drift or short small reference pulses.\n\nRetention: substantial slow-drift gain in BOTH primary-only and reference-only validation; reduced silent plant misses; zero new benign alarms or wrong origins; no lost A0 detections, no memory/timing/communication/actuator regression. Desired percentages do not select parameters/cohorts. Sources/config locked before TRAIN and verified before VALIDATION and after completion. Max8 compressed traces selected before outcomes; all raw data deleted after scoring.\n\nScientific identities:\n```json\n'+json.dumps(frozen,indent=2)+'\n```\n')
  retain={next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['origin']==o) for o in ['MEMORY','TIMING','COMMUNICATION','ACTUATOR','NORMAL']}
  retain.update(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['sensor_chain']==chain and s['model']=='sensor_bias_ramp') for chain in ['primary','reference','common_mode'])
  rows=[]
  for part in ['development-train','development-validation']:
   assert all(sha(ROOT/p)==h for p,h in frozen.items())
   for i,s in enumerate([s for s in specs if s['partition']==part]):
    rr=c.execute(s,work,s['run_id'] in retain)
    for r in rr:r.pop('command_json',None)
    rows+=rr
    if (i+1)%40==0:print(part,i+1,flush=True)
   report(rows)
   with (OUT/'validation_record.md').open('a') as f:f.write('\n'+part+' completed; scientific hashes verified unchanged.\n')
   if part=='development-train':
    (BASE/'train_ready').write_text('ready');print('TRAIN READY; waiting for unchanged-settings gate',flush=True)
    import time
    while not (BASE/'validation_go').exists():time.sleep(1)
  assert all(sha(ROOT/p)==h for p,h in frozen.items());print('1400-case redundancy development COMPLETE',flush=True)
if __name__=='__main__':main()
