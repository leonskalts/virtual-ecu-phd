#!/usr/bin/env python3
"""One group-separated FAST+SLOW development, with temporary ablation objects."""
import csv,hashlib,json,subprocess,sys,tempfile,difflib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
import run_clo_dsf_redundant_sensor as prior
import run_clo_dsf_integrity_event as reporting
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_development import write_csv,sha
from virtual_ecu.clo_dsf_candidate2_development import aggregate
OUT=c.OUT;BASE=Path('/tmp/clo-fast-redundancy');METHODS=['Pre-change CLO-DSF','FAST only','SLOW only','Revised CLO-DSF']
def design():
 old=prior.design();specs=[]
 for f in range(10):
  block=old[f*140:(f+1)*140];cells=[dict(s) for s in block if s['origin']!='SENSOR_CONTROL'];template=next(s for s in block if s['origin']=='SENSOR_CONTROL');sensor=[]
  for chain in ['primary','reference']:
   for mag in [-1.45,1.45,-2.35,2.35]:
    for rise in [9500,28500,47500]:sensor.append((chain,'sensor_bias_ramp','permanent',mag,0,rise))
   for mag in [-.72,.72,-.96,.96]:
    mag+= (.005*f if mag>0 else -.005*f)
    for dur in [300,0]:sensor.append((chain,'sensor_bias','transient' if dur else 'permanent',mag,dur,0))
   for mag in [.48+.005*f,.68+.005*f,1.6+.01*f]:
    for dur in [900,0]:sensor.append((chain,'sensor_interface_intermittent','transient' if dur else 'permanent',mag,dur,0))
  sensor += [('reference','sensor_dropout','transient',0,700,0),('reference','sensor_dropout','permanent',0,0,0)]
  sensor += [('common_mode','sensor_bias_ramp','permanent',mag,0,36500) for mag in [-2.35,2.35]]
  for chain,model,behavior,mag,dur,rise in sensor:
   s=dict(template);s.update(sensor_chain=chain,model=model,behavior=behavior,magnitude=mag,duration_ms=dur,sensor_ramp_rise_ms=rise,initially_latent_stuck=0);cells.append(s)
  assert len(cells)==156
  for j,s in enumerate(cells):
   i=len(specs);s['run_id']=f'fast_redundant_{i:04}';s['profile']=f'fast_redundant_profile_{i:04}';s['group']=f'fast_redundant_family_{f}';s['partition']='development-train' if f<6 else 'development-validation'
   profile=json.loads(s['profile_json'])
   for z in profile:z['vehicle_speed_kph']+=.71+j*.0019;z['engine_load']*=.991;z['ambient_temp_c']+=.37+j*.0011
   s['profile_json']=json.dumps(profile,sort_keys=True);s['profile_semantic_sha256']=profile_identity(profile)
   s['seed']=3900017+f*2017+j*43;s['reference_seed']=710011+f*1297+j*79
   s['reference_offset']=round((j%5-2)*.047,3);s['reference_noise']=[.035,.065,.095][(j+f)%3]
   if s['origin']!='NORMAL':s['start_ms']=24700+f*100+(j%9)*300
   s['benign_reference_transient']='none'
   if s['origin']=='NORMAL':
    k=j-80
    # Challenge bounded noise, legal triangles, isolated spikes, and small
    # multi-sample disagreement. These are workload labels, never observations.
    s['benign_reference_transient']=['none','isolated_positive','isolated_negative','small_short','small_long'][k%5]
   s.pop('configuration_sha256');s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();specs.append(s)
 assert len(specs)==1560 and len({s['profile_semantic_sha256'] for s in specs})==1560
 return specs

def command(s,work):
 cmd=prior.command(s,work)
 benign=s['benign_reference_transient']
 if benign!='none':
  mag,duration={'isolated_positive':(.9,100),'isolated_negative':(-.9,100),'small_short':(.35,300),'small_long':(-.35,900)}[benign]
  cmd+=['--revised-reference-fault',f'2:28300:0:{duration}:0:{mag}']
 return cmd

def build(work):
 a0=c.build_prechange(work,BASE/'baseline.c')
 core=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text()
 # FAST only removes ONLY averaging, preserving direct conversion status.
 fast=core.replace('local=fmax(local,redundant_sensor(state,o));','local=fmax(local,o->reference_enabled && o->reference_failed && o->reference_ms==o->time_ms ? 1.0 : 0.0);')
 for sym in ['clo_revised_init','clo_revised_extract','clo_revised_step']:fast=fast.replace(sym,sym.replace('clo_revised','clo_fast_only'))
 p=work/'fast_only.c';p.write_text(fast);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(obj)],cwd=ROOT,check=True)
 adapter=(ROOT/'src/v7_3/revised_runtime.c').read_text().replace('static clo_revised_t prechange;','static clo_revised_t prechange,fast_only;\nvoid clo_fast_only_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);')
 adapter=adapter.replace('clo_final_step(&previous,&config,&o);final_score(2,o.time_ms,&previous.output);','clo_final_step(&previous,&config,&o);clo_fast_only_step(&fast_only,&config,&o);final_score(2,o.time_ms,&fast_only.fusion.output);')
 adapter=adapter.replace('clo_dsf_step(&plain,&plain_config,CLO_PLAIN,&o);old_score(3,o.time_ms,&plain);','final_score(3,o.time_ms,&prechange.fusion.output);')
 adapter=adapter.replace('clo_revised_init(&prechange);','names[2]="FAST only";names[3]="SLOW only";clo_revised_init(&fast_only);clo_revised_init(&prechange);')
 p=work/'adapter.c';p.write_text(adapter);ad=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(ad)],cwd=ROOT,check=True)
 objects=[str(a0),str(obj),str(ad)]+[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
 objects += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o','src/v7_3/clo_dsf_revised.o']]
 exe=work/'ablation';subprocess.run(['gcc',*objects,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-lm','-o',str(exe)],check=True);return exe

def report(rows):
 reporting.OUT=OUT;reporting.METHODS=METHODS;reporting.report(rows)
 sub=[]
 for part in ['development-train','development-validation']:
  for method in METHODS:
   rr=[r for r in rows if r['partition']==part and r['method']==method]
   for chain in ['primary','reference','common_mode']:
    for model in ['ALL','sensor_bias_ramp','sensor_bias','sensor_interface_intermittent','sensor_dropout']:
     ss=[r for r in rr if r['sensor_chain']==chain and (model=='ALL' or r['model']==model)]
     if ss:sub.append(dict(partition=part,method=method,chain=chain,model=model,**aggregate(ss)))
 write_csv(OUT/'redundancy_summary.csv',sub)
 for p in OUT.glob('*.csv'):p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))

def main():
 if (OUT/'campaign_manifest.csv').exists() and 'fast_redundant_0000' in (OUT/'campaign_manifest.csv').read_text():raise SystemExit('Refuse accidental campaign repeat')
 specs=design();new={s['profile_semantic_sha256'] for s in specs};audit=[]
 for p in (ROOT/'results').rglob('*manifest.csv'):
  with p.open() as f:old={r['profile_semantic_sha256'] for r in csv.DictReader(f) if r.get('profile_semantic_sha256')}
  if old:audit.append(dict(manifest=str(p.relative_to(ROOT)),sha256=sha(p),profiles=len(old),overlap=len(old&new)));assert not old&new
 assert not {s['group'] for s in specs if s['partition']=='development-train'}&{s['group'] for s in specs if s['partition']=='development-validation'}
 with tempfile.TemporaryDirectory(prefix='clo-fast-development-') as tmp:
  work=Path(tmp);prepare_work(work,specs);exe=build(work);c.METHODS=METHODS
  c.command=lambda s,w:[str(exe),*command(s,w)[1:]]
  for s in specs:s['command_json']=json.dumps([x.replace(str(work),'$WORK').replace(str(ROOT),'$ROOT') for x in c.command(s,work)])
  assert all(p.is_file() for p in OUT.iterdir())
  for p in OUT.iterdir():p.unlink()
  write_csv(OUT/'campaign_manifest.csv',specs);write_csv(OUT/'overlap_audit.csv',audit)
  for p in OUT.glob('*.csv'):p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
  scientific=[p for folder in ['src','include'] for p in (ROOT/folder).rglob('*') if p.suffix in ['.c','.h']]+[Path(__file__),c.CONFIG,OUT/'campaign_manifest.csv']
  frozen={str(p.relative_to(ROOT)):sha(p) for p in scientific};(BASE/'frozen.json').write_text(json.dumps(frozen,indent=2))
  reverse=''.join(difflib.unified_diff((ROOT/'src/v7_3/clo_dsf_revised.c').read_text().splitlines(True),(BASE/'baseline.c').read_text().splitlines(True),fromfile='current.c',tofile='baseline.c'))
  (OUT/'validation_record.md').write_text('# Multi-timescale redundant sensor development\n\nRegistered before outcomes '+datetime.now(timezone.utc).isoformat()+'. Git baseline '+(BASE/'head').read_text().strip()+' plus retained uncommitted redundant-sensor implementation (A0 core SHA256 '+sha(BASE/'baseline.c')+').\n\n1560 simulations: TRAIN936(816 faults/120 benign), VALIDATION624(544 faults/80 benign); six versus four disjoint operating families. Per family:20 each MEMORY/TIMING/COMMUNICATION/ACTUATOR,56 SENSOR_CONTROL,20 benign. Sensors:12 slow drifts/8 steps/6 pulses per chain;2 reference conversion failures;2 common-mode limitation controls. Positive/negative weak offsets;300ms or permanent steps;900ms or permanent pulse trains; new magnitudes, seeds, onsets and profiles. Same physics stream for all observers. Prior inline manifests audited before replacing CURRENT.\n\nA0=SLOW only, an explicit identical alias. FAST only removes only the slow averaging feature, retaining all inherited local sensor evidence and direct conversion-failure status. FAST+SLOW is the proposed current detector. Temporary ablation objects only, no maintained candidate tree.\n\nFAST contract fixed before TRAIN: two-sample noise difference<=0.40C and legal differential slew<=1.2C/s. Edge violation abs(delta[k]-delta[k-1])>0.52C at100ms cadence. Freeze pre-event disagreement for<=300ms; require two consecutive same-sign residuals beyond0.40+1.2*h, OR three excessive edges in a ten-acquisition(1s) rolling window. One isolated spike plus recovery supplies at most two edges. Confirmation supplies direct SENSOR_CONTROL contract evidence1, max-merged with existing sensor evidence; no extra DS source. No global threshold, slow window, causal precedence, memory, timing, communication, actuator or sensor model change. Sensor-member attribution remains UNKNOWN. No hidden truth/labels in inference.\n\nBenign tests retain independent noise/calibration and legal triangular disagreement; additionally reference-only isolated +/-0.9C100ms spikes and +/-0.35C300/900ms transients. Repeated large out-of-contract impulsive noise is not promised distinguishable from fault pulse trains. Common-mode not targeted.\n\nNo parameter search planned. TRAIN may reject; settings lock before VALIDATION. Retain only substantial new weak abrupt-fault validation detections, preserved slow-drift and other-origin detections, no lost A0 cases, near-zero benign alarms and wrong origins. Desired percentages never select cohorts/parameters. Latency comparison reports full detected populations and paired common detections, recognizing changed denominators. Eight compressed representative traces preselected; raw run artifacts discarded immediately after scoring. No unseen holdout/commit/push.\n\nA0 reconstruction from current core (temporary only):\n```diff\n'+reverse+'```\n\nScientific identities:\n```json\n'+json.dumps(frozen,indent=2)+'\n```\n')
  retain={next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['sensor_chain']==ch and s['model']==mo) for ch in ['primary','reference'] for mo in ['sensor_bias','sensor_interface_intermittent','sensor_bias_ramp']}
  retain.add(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['sensor_chain']=='common_mode'))
  retain.add(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['benign_reference_transient']=='isolated_positive'))
  rows=[]
  for part in ['development-train','development-validation']:
   assert all(sha(ROOT/p)==h for p,h in frozen.items())
   for i,s in enumerate([s for s in specs if s['partition']==part]):
    rr=c.execute(s,work,s['run_id'] in retain)
    for r in rr:r.pop('command_json',None)
    a0=next(r for r in rr if r['method']=='Pre-change CLO-DSF');slow=next(r for r in rr if r['method']=='SLOW only');assert {k:v for k,v in a0.items() if k!='method'}=={k:v for k,v in slow.items() if k!='method'}
    rows+=rr
    if (i+1)%40==0:print(part,i+1,flush=True)
   report(rows)
   with (OUT/'validation_record.md').open('a') as f:f.write('\n'+part+' complete; all scientific hashes unchanged.\n')
   if part=='development-train':
    (BASE/'train_ready').write_text('ready');print('TRAIN READY; waiting for locked gate',flush=True)
    import time
    while not (BASE/'validation_go').exists():time.sleep(1)
  assert all(sha(ROOT/p)==h for p,h in frozen.items());print('1560-case FAST campaign COMPLETE',flush=True)
if __name__=='__main__':main()
