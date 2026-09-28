#!/usr/bin/env python3
"""One group-separated development campaign, no unseen holdout."""
import sys,json,subprocess,tempfile,hashlib,shutil,time,csv
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
import run_clo_dsf_unseen_retained as prior
import run_clo_dsf_tractable as report_prior
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_development import sha,write_csv,ORIGINS
from virtual_ecu.clo_dsf_candidate2_development import aggregate
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
OUT=ROOT/'results/clo_dsf_current';B=Path('/tmp/clo-qualified');METHODS=['A0','A1','A2','A3','A4']
def write(p,rows):write_csv(p,rows);p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
def design():
 old=prior.design();specs=[]
 for f in range(10):
  block=old[f*150:(f+1)*150];template=next(s for s in block if s['origin']=='SENSOR_CONTROL');extra=[]
  for chain in ['primary','reference']:
   for k in range(6):
    s=dict(template);s.update(sensor_chain=chain,model=['sensor_bias','sensor_bias','sensor_interface_intermittent','sensor_interface_intermittent','sensor_bias_ramp','sensor_bias_ramp'][k],magnitude=(-1 if k%2==0 else 1)*([.77,.77,.83,.83,1.73,1.73][k]+f*.002),duration_ms=300 if k<2 else 700 if k<4 else 0,sensor_ramp_rise_ms=15300 if k>=4 else 0,behavior='transient' if k<4 else 'permanent',start_ms=200 if k%2==0 else 400,workload='early_sensor',target_updates_json='[]');extra.append(s)
  for k in range(6):
   s=dict(block[120+k]);s.update(workload='benign_cold',target_updates_json='[]');extra.append(s)
  for j,s in enumerate(block+extra):
   i=len(specs);s.update(run_id=f'qualified_{i:04}',profile=f'qualified_profile_{i:04}',group=f'qualified_family_{f}',partition='development-train' if f<6 else 'development-validation',seed=s['seed']+730003,reference_seed=s['reference_seed']+970003)
   pp=json.loads(s['profile_json']);cold=j>=150 or s['origin']=='ACTUATOR' and (j-96)%4==0
   for p in pp:
    p['vehicle_speed_kph']+=.417+j*.0011;p['ambient_temp_c']+=.193+f*.011;p['engine_load']*=.987
    if cold:p.update(engine_load=.091+j*.000001,ambient_temp_c=9.137+f*.117,vehicle_speed_kph=71.731+j*.011)
   if s['origin']=='MEMORY':
    s['start_ms']=21300+(j%10)*100+f*1000
    if s['behavior']!='permanent':s['duration_ms']=[400,700,1300,2100][(f+j)%4]
   elif s['origin']!='NORMAL' and j<150:s['start_ms']+=1300
   if s['model']=='sensor_bias' and j<150:s['magnitude']+=.011 if s['magnitude']>0 else -.011
   if s['model']=='sensor_interface_intermittent' and j<150:s['magnitude']+=.017 if s['magnitude']>0 else -.017
   s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=profile_identity(pp);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();specs.append(s)
 assert len(specs)==1680
 return specs

def variants():
 current=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text();old=(B/'baseline.c').read_text()
 a2=current.replace('    s->evidence.strength[3] =','    origin_local=local; /* A2: original unqualified origin behavior. */\n    s->evidence.strength[3] =')
 start=current.index('} else {\n            /* Pointwise expiry');end=current.index('\n    }\n    if(s->fast_edges',start)
 a3=current[:start]+'} else {s->fast_active=false;s->fast_count=0;}'+current[end:]
 return {'prechange':old,'fast_only':a2,'qualification_only':a3}
def build(w):
 objects=[]
 for name,source in variants().items():
  for fn in ['clo_revised_init','clo_revised_extract','clo_revised_step']:source=source.replace(fn,fn.replace('clo_revised','clo_'+name))
  p=w/(name+'.c');p.write_text(source);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
 adapter=(ROOT/'src/v7_3/revised_runtime.c').read_text().replace('static clo_revised_t prechange;','static clo_revised_t prechange,fast_only,qualification_only;\nvoid clo_fast_only_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);\nvoid clo_qualification_only_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);')
 adapter=adapter.replace('clo_final_step(&previous,&config,&o);final_score(2,o.time_ms,&previous.output);','final_score(2,o.time_ms,&prechange.fusion.output);')
 adapter=adapter.replace('clo_dsf_step(&plain,&plain_config,CLO_PLAIN,&o);old_score(3,o.time_ms,&plain);','clo_fast_only_step(&fast_only,&config,&o);final_score(3,o.time_ms,&fast_only.fusion.output);')
 adapter=adapter.replace('simple_score(4,o.time_ms,peak>=.5);','clo_qualification_only_step(&qualification_only,&config,&o);final_score(4,o.time_ms,&qualification_only.fusion.output);')
 adapter=adapter.replace('clo_revised_init(&prechange);','names[0]="A4";names[1]="A0";names[2]="A1";names[3]="A2";names[4]="A3";clo_revised_init(&fast_only);clo_revised_init(&qualification_only);clo_revised_init(&prechange);')
 p=w/'adapter.c';p.write_text(adapter);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
 objects += [str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
 objects += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o','src/v7_3/clo_dsf_revised.o']]
 exe=w/'compare';subprocess.run(['gcc',*objects,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-lm','-o',str(exe)],check=True);return exe

def report(rows):
 sums=[];subs=[]
 for part in ['development-train','development-validation']:
  for method in METHODS:
   rr=[r for r in rows if r['partition']==part and r['method']==method]
   if not rr:continue
   groups={'ALL':rr,**{o:[r for r in rr if r['origin']==o] for o in ORIGINS}}
   for g,rs in groups.items():sums.append(dict(partition=part,method=method,group=g,**aggregate(rs),**{'runtime_'+k:v for k,v in runtime_stats(rs).items()}))
   filters={'effective_memory':lambda r:r['origin']=='MEMORY' and r['effective_memory_corruption'],'dormant_memory':lambda r:r['model']=='stuck_bit' and not r['effective_memory_corruption'],'transient_dormant':lambda r:r['model']=='stuck_bit' and not r['effective_memory_corruption'] and r['behavior']=='transient','weak_steps':lambda r:r['model']=='sensor_bias','pulses':lambda r:r['model']=='sensor_interface_intermittent','primary':lambda r:r['sensor_chain']=='primary','reference':lambda r:r['sensor_chain']=='reference','slow_drift':lambda r:r['model']=='sensor_bias_ramp' and r['sensor_chain']!='common_mode','common_mode':lambda r:r['sensor_chain']=='common_mode','early_sensor':lambda r:r['workload']=='early_sensor','cold_benign':lambda r:r['workload']=='benign_cold','legal_updates':lambda r:not r['injected'] and r['workload']=='authorized_updates','cold_actuator':lambda r:r['origin']=='ACTUATOR' and r['cold_profile']}
   for g,fn in filters.items():
    ss=[r for r in rr if fn(r)];subs.append(dict(partition=part,method=method,group=g,**aggregate(ss),**{'runtime_'+k:v for k,v in runtime_stats(ss).items()},probe_phase_misses=sum(not r['detected'] and r['model']=='stuck_bit' and not r['effective_memory_corruption'] and r['active_probe_checks']==0 for r in ss)))
 write(OUT/'ablation_summary.csv',sums);write(OUT/'subgroup_summary.csv',subs);write(OUT/'case_summary.csv',rows)

def main():
 assert (B/'classification_complete').exists() and not (B/'started').exists()
 specs=design();keys={s['profile_semantic_sha256'] for s in specs};assert len(keys)==1680
 audit=[]
 for p in (ROOT/'results').rglob('*manifest.csv'):
  with p.open() as f:old={r['profile_semantic_sha256'] for r in csv.DictReader(f) if r.get('profile_semantic_sha256')}
  if old:assert not keys&old; audit.append(dict(manifest=str(p.relative_to(ROOT)),sha256=sha(p),prior_profiles=len(old),overlap=0))
 frozen={str(p.relative_to(ROOT)):sha(p) for d in ['src','include'] for p in (ROOT/d).rglob('*') if p.suffix in ['.c','.h']};frozen[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));frozen[str(c.CONFIG.relative_to(ROOT))]=sha(c.CONFIG)
 with tempfile.TemporaryDirectory(prefix='clo-qualified-development-') as temp:
  w=Path(temp);prepare_work(w,specs);exe=build(w)
  check=w/'check';objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o'];subprocess.run(['gcc','-std=c11','-Iinclude','tests/holdout_configuration_check.c',*objects,'-o',str(check)],check=True)
  for s in specs:
   cmd=prior.command(s,w);p=subprocess.run([str(check),*cmd[2:]],capture_output=True,text=True);assert p.returncode==0,(s['run_id'],p.stderr)
   s['command_json']=json.dumps([x.replace(str(w),'$WORK').replace(str(ROOT),'$ROOT') for x in [str(exe),*cmd[1:]]])
  shutil.copyfile(OUT/'campaign_manifest.csv',B/'prior_manifest.csv')
  shutil.rmtree(OUT);OUT.mkdir();shutil.copyfile(B/'root_cause_summary.csv',OUT/'root_cause_summary.csv');write(OUT/'campaign_manifest.csv',specs);write(OUT/'overlap_audit.csv',audit)
  protocol='''# Qualification and tractable-miss DEVELOPMENT protocol
Registered before outcomes.1680 simulations:TRAIN1008 across six operating families;VALIDATION672 across four disjoint families. Each family132 faults/36 benign:24 each MEMORY/TIMING/COMMUNICATION/ACTUATOR;36 sensor including early primary/reference faults;30 varied benign plus6 matched cold-start benign. Short dormant400/700/1300/2100ms finite memory faults; weak steps/pulses of both signs, slow drifts and common-mode controls; cold unexcited actuators unchanged. New profiles/seeds/onsets; no unseen holdout.

All116 previously seen targeted runs individually replayed before modification. Memory A/B/C/D/E=0/7/0/0/0: finite active windows500-700ms between legitimate probes. Same average probe rate cannot guarantee every shorter transient; no scheduling change selected. Existing maximum1100ms, average1Hz,7 accesses/check,16-byte diagnostic state on this platform. Atomic save/write/read/restore unchanged.

FAST: keep coherent same-sign residual area when an individual sample fails the widening envelope, but only within original300ms anchor, with original0.40C floor and1.2C/s bound. No threshold, onset, SLOW, or common-mode change. Localization: absolute-slew provider qualifies after five contiguous in-envelope acquisitions under its own2.5C/s contract. Qualification gates only origin; anomaly stays unchanged. Independent redundancy, forecast and implausibility providers retain their own qualifications, allowing early genuine faults. No ground truth or profile IDs in inference.

A0=current baseline48315a66;A1=A0 (no justified memory modification);A2=FAST only;A3=qualification only;A4=both proposals. Temporary comparison objects only. Parameters fixed before TRAIN. TRAIN may reject; no tuning to VALIDATION. Retain FAST only for incremental validation detection with no lost prior detections, added benign alarms, wrong-origin regression or protected-origin losses. Retain qualification only for fewer wrong origins, identical detection and no loss of legitimate early direct localization. Any failed mechanism is independently removed; keep rejected ablation evidence. >=96% never selects cases/settings.

Report all alarm samples including pre-onset and benign: qualified origins on NORMAL count wrong. Qualification cannot remove existing anomaly alarms from benign cold starts; report those honestly, without suppressing them. No promise of zero benign alarms if baseline physics violates its absolute-slew envelope. Eight traces selected before outcomes; checkpoint all summaries before enrichment; raw traces deleted after scoring. Full regression once on retained combination. No commit/push; preserve GUI and all historical evidence.
'''
  (OUT/'validation_record.md').write_text(protocol+'\nRegistered UTC '+datetime.now(timezone.utc).isoformat()+'\n')
  for name in ['campaign_manifest.csv','validation_record.md']:frozen[str((OUT/name).relative_to(ROOT))]=sha(OUT/name)
  (B/'frozen.json').write_text(json.dumps(frozen));(B/'started').write_text('started')
  def verify():assert all(sha(ROOT/p)==v for p,v in frozen.items())
  c.OUT=OUT;c.METHODS=METHODS;c.command=lambda s,w:[str(exe),*prior.command(s,w)[1:]]
  original=c.read;cache={}
  def read(p):
   rr=original(p)
   if Path(p).name=='trace.csv':cache['trace']=rr
   return rr
  c.read=read
  retain={next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['origin']==o) for o in [*ORIGINS,'NORMAL']}
  retain.add(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['workload']=='early_sensor'))
  retain.add(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['workload']=='benign_cold'));assert len(retain)==8
  rows=[];checkpoint=(B/'checkpoint.jsonl').open('w')
  for part in ['development-train','development-validation']:
   verify()
   for i,s in enumerate([s for s in specs if s['partition']==part]):
    rr=c.execute(s,w,s['run_id'] in retain);checkpoint.write(json.dumps(rr)+'\n');checkpoint.flush()
    checks=sum(int(t['memory_check_valid']) and t['memory_check_ms']==t['time_ms'] and prior.active(s,int(t['time_ms'])) for t in cache['trace'])
    cold=json.loads(s['profile_json'])[0]['engine_load']<.10
    for r in rr:r.pop('command_json',None);r.update(active_probe_checks=checks,cold_profile=int(cold))
    rows+=rr
    if (i+1)%50==0:print(part,i+1,flush=True)
   report(rows);verify()
   if part=='development-train':
    (B/'train_ready').write_text('ready');print('TRAIN READY; waiting for lock',flush=True)
    while not (B/'validation_go').exists():time.sleep(1)
  (B/'complete').write_text('1680 complete');print('DEVELOPMENT COMPLETE',flush=True)
if __name__=='__main__':main()
