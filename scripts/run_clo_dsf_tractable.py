#!/usr/bin/env python3
"""One in-place development with independently observable memory/FAST ablations."""
import sys,csv,json,hashlib,subprocess,tempfile,shutil
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
import run_clo_dsf_fast_redundancy as prior
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_development import write_csv,sha,ORIGINS
from virtual_ecu.clo_dsf_candidate2_development import aggregate
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
OUT=c.OUT;BASE=Path('/tmp/clo-tractable');METHODS=['A0','A1','A2','A3','A4']
def design():
 specs=prior.design()
 for i,s in enumerate(specs):
  f=i//156;j=i%156;s['run_id']=f'tractable_{i:04}';s['profile']=f'tractable_profile_{i:04}';s['group']=f'tractable_family_{f}'
  p=json.loads(s['profile_json'])
  for z in p:z['vehicle_speed_kph']+=.53+j*.0013;z['engine_load']*=.971;z['ambient_temp_c']+=.79+j*.0017
  s['profile_json']=json.dumps(p,sort_keys=True);s['profile_semantic_sha256']=profile_identity(p)
  s['seed']+=1700003;s['reference_seed']+=230003;s['on_ms']=[600,700,800][f%3];s['off_ms']=2000-s['on_ms']
  if s['origin']=='MEMORY':
   s['start_ms']=20100+(j%7)*2000+(100 if (j+f)%2 else 0)
   if s['behavior']=='transient':s['duration_ms']=[1800,4600,9200][(j+f)%3]
   if s['behavior']=='intermittent':s['duration_ms']=[4100,7300,11300][(j+f)%3]
  elif s['origin']!='NORMAL':s['start_ms']+=1100
  if s['model']=='sensor_bias':s['magnitude']=(1 if s['magnitude']>0 else -1)*(.64+.005*f if abs(s['magnitude'])<.9 else .82+.005*f);s['duration_ms']=200 if s['duration_ms'] else 0
  if s['model']=='sensor_interface_intermittent':s['magnitude']=.41+.004*f if s['magnitude']<.6 else .61+.004*f if s['magnitude']<1 else 1.41+.01*f;s['duration_ms']=500 if s['duration_ms'] else 0
  if s['model']=='sensor_bias_ramp' and s['sensor_chain']!='common_mode':s['magnitude']=(1 if s['magnitude']>0 else -1)*(1.55 if abs(s['magnitude'])<2 else 2.45)
  s.pop('configuration_sha256');s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
 return specs

def command(s,w):
 cmd=prior.command(s,w)
 for k,v in {'--intermittent-on-ms':s['on_ms'],'--intermittent-off-ms':s['off_ms']}.items():
  if k in cmd:cmd[cmd.index(k)+1]=str(v)
 return cmd

def build(w):
 sources={'prechange':(BASE/'baseline.c').read_text(),'a1':(BASE/'baseline.c').read_text().replace('o->time_ms - o->memory_check_ms < MEMORY_DIAGNOSTIC_PERIOD_MS','o->time_ms - o->memory_check_ms < MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS'),'a3':(ROOT/'src/v7_3/clo_dsf_revised.c').read_text().replace('o->time_ms - o->memory_check_ms < MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS','o->time_ms - o->memory_check_ms < MEMORY_DIAGNOSTIC_PERIOD_MS'),'old_probe':(BASE/'memory.c').read_text().replace('memory_diagnostic_step','memory_diagnostic_old_step')}
 objects=[]
 for name,source in sources.items():
  if name!='old_probe':
   for fn in ['clo_revised_init','clo_revised_extract','clo_revised_step']:source=source.replace(fn,fn.replace('clo_revised','clo_'+name))
  p=w/(name+'.c');p.write_text(source);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(obj)],cwd=ROOT,check=True);objects.append(str(obj))
 adapter=(ROOT/'src/v7_3/revised_runtime.c').read_text().replace('static clo_revised_t prechange;', '''static clo_revised_t prechange,memory_only,fast_only;
static memory_diagnostic_t old_probe;
void memory_diagnostic_old_step(memory_diagnostic_t *,unsigned int,memory_read_fn,memory_write_fn,void *);
void clo_a1_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);
void clo_a3_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);''')
 adapter=adapter.replace(' if(enabled && state->log_file)\n  memory_diagnostic_step', ' if(enabled && state->log_file)\n  memory_diagnostic_old_step(&old_probe,state->time.time_ms,cross_layer_memory_read,cross_layer_memory_write,state);\n if(enabled && state->log_file)\n  memory_diagnostic_step')
 adapter=adapter.replace(' if(comparison) {',' if(comparison) {\n  runtime_observation_t legacy_o=o;legacy_o.memory_check_ms=old_probe.checked_ms;legacy_o.memory_check_valid=old_probe.valid;legacy_o.memory_check_failed=old_probe.failed;')
 adapter=adapter.replace('clo_prechange_step(&prechange,&config,&o)','clo_prechange_step(&prechange,&config,&legacy_o)')
 adapter=adapter.replace('clo_final_step(&previous,&config,&o);final_score(2,o.time_ms,&previous.output);','clo_final_step(&previous,&config,&o);clo_a1_step(&memory_only,&config,&o);final_score(2,o.time_ms,&memory_only.fusion.output);')
 adapter=adapter.replace('clo_dsf_step(&plain,&plain_config,CLO_PLAIN,&o);old_score(3,o.time_ms,&plain);','final_score(3,o.time_ms,&prechange.fusion.output);')
 adapter=adapter.replace('simple_score(4,o.time_ms,peak>=.5);','clo_a3_step(&fast_only,&config,&legacy_o);final_score(4,o.time_ms,&fast_only.fusion.output);')
 adapter=adapter.replace('clo_revised_init(&prechange);','names[0]="A4";names[1]="A0";names[2]="A1";names[3]="A2";names[4]="A3";clo_revised_init(&memory_only);clo_revised_init(&fast_only);clo_revised_init(&prechange);')
 p=w/'adapter.c';p.write_text(adapter);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(obj)],cwd=ROOT,check=True);objects.append(str(obj))
 objects += [str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
 objects += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o','src/v7_3/clo_dsf_revised.o']]
 exe=w/'comparison';subprocess.run(['gcc',*objects,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-lm','-o',str(exe)],check=True);return exe

def report(rows):
 summary=[];memory=[];actuator=[];sensor=[]
 for part in ['development-train','development-validation']:
  for m in METHODS:
   rr=[r for r in rows if r['partition']==part and r['method']==m]
   if not rr:continue
   for g in ['ALL',*ORIGINS]:
    ss=[r for r in rr if g=='ALL' or r['origin']==g];summary.append(dict(partition=part,method=m,group=g,**aggregate(ss),**{'runtime_'+k:v for k,v in runtime_stats(ss).items()}))
   groups={'effective':[r for r in rr if r['origin']=='MEMORY' and r['effective_memory_corruption']],'dormant':[r for r in rr if r['model']=='stuck_bit' and not r['effective_memory_corruption']],'legal_updates':[r for r in rr if not r['injected'] and r['workload']=='authorized_updates']}
   for g,ss in groups.items():memory.append(dict(partition=part,method=m,group=g,maximum_probe_gap_ms=1100 if m in ['A1','A4'] else 1000,**aggregate(ss)))
   for g in ['ALL','transient','intermittent','permanent','weak']:
    ss=[r for r in rr if r['origin']=='ACTUATOR' and (g=='ALL' or r['behavior']==g or g=='weak' and r['model']=='pump_degraded' and r['magnitude']>=.94)];actuator.append(dict(partition=part,method=m,group=g,**aggregate(ss)))
   for ch in ['ALL','primary','reference','common_mode']:
    for model in ['ALL','sensor_bias','sensor_interface_intermittent','sensor_bias_ramp']:
     for sign in ['ALL','positive','negative']:
      ss=[r for r in rr if r['origin']=='SENSOR_CONTROL' and (ch=='ALL' or r['sensor_chain']==ch) and (model=='ALL' or r['model']==model) and (sign=='ALL' or (r['magnitude']>0)==(sign=='positive'))]
      if ss:sensor.append(dict(partition=part,method=m,chain=ch,model=model,sign=sign,**aggregate(ss)))
 for name,rs in [('ablation_summary.csv',summary),('memory_probe_summary.csv',memory),('actuator_summary.csv',actuator),('sensor_fast_summary.csv',sensor),('case_summary.csv',rows)]:write_csv(OUT/name,rs)
 for p in OUT.glob('*.csv'):p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))

def main():
 assert (BASE/'classification_complete').exists()
 if (OUT/'campaign_manifest.csv').exists() and 'tractable_0000' in (OUT/'campaign_manifest.csv').read_text():raise SystemExit('Refuse accidental rerun')
 specs=design();new={s['profile_semantic_sha256'] for s in specs};assert len(new)==1560
 for p in (ROOT/'results').rglob('*manifest.csv'):
  with p.open() as f:old={r.get('profile_semantic_sha256') for r in csv.DictReader(f)}
  assert not old&new
 with tempfile.TemporaryDirectory(prefix='clo-tractable-development-') as tmp:
  w=Path(tmp);prepare_work(w,specs);exe=build(w);c.OUT=OUT;c.METHODS=METHODS;c.command=lambda s,w:[str(exe),*command(s,w)[1:]]
  for s in specs:s['command_json']=json.dumps([v.replace(str(w),'$WORK').replace(str(ROOT),'$ROOT') for v in c.command(s,w)])
  assert all(p.is_file() for p in OUT.iterdir())
  for p in OUT.iterdir():p.unlink()
  shutil.copyfile(BASE/'root_cause_summary.csv',OUT/'root_cause_summary.csv');write_csv(OUT/'campaign_manifest.csv',specs)
  for p in OUT.glob('*.csv'):p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
  files=[p for d in ['src','include'] for p in (ROOT/d).rglob('*') if p.suffix in ['.c','.h']]+[Path(__file__),c.CONFIG,OUT/'campaign_manifest.csv'];frozen={str(p.relative_to(ROOT)):sha(p) for p in files};(BASE/'frozen.json').write_text(json.dumps(frozen))
  (OUT/'validation_record.md').write_text('# Tractable-miss development protocol\n\nRegistered '+datetime.now(timezone.utc).isoformat()+' before outcomes. Existing final unseen results are now explicitly seen DEVELOPMENT evidence; they are preserved unchanged. All60 targeted misses individually replayed before implementation changes, with exact original runtime trace hashes: memory5 scheduling gaps(A), actuator13 passive observability gaps(D), steps22(amplitude3,duration17,persistence2), pulses20(amplitude7,duration13). root_cause_summary.csv gives every case.\n\n1560 new simulations:TRAIN936(816 faults/120 benign), VALIDATION624(544 faults/80 benign), six/four disjoint operating families and unique new full profiles. Same cases for A0=current final, A1=phase-swept memory only, A2=unchanged actuator alias ofA0, A3=FAST integral only, A4=both proposed changes. No actuator mechanism invented when command=actual=0; no excitation authorized. No common-mode or SLOW changes.\n\nMemory:probe intervals nine1100ms then100ms, mean1000ms, max1100ms at100ms invocation cadence. Ten phase positions, no injector knowledge; same seven-access atomic save/write0/read/writeFFFF/read/restore/read sequence. No promise to detect every isolated transient shorter than a gap. Fresh-result lifetime1100ms matches maximum cadence. Comparison adapter performs both old/new restored transactions independently, but each observer sees only its own timestamps/status. Diagnostic probes do not modify control/plant; parity checked separately.\n\nFAST: unchanged edge/three-edge criteria and300ms anchor. Added bounded signed integral uses original0.40C noise floor and1.2C/s envelope: require two same-sign residuals individually>0.40C and sum(abs(residual))>sum(0.40+1.2*h). Reset on recovery/sign reversal/gap/anchor expiry. Max-merge into original sensor evidence; no new independent DS mass or threshold change. An isolated weak100ms impulse remains fundamentally confounded with allowed benign excursions; no alarm forced for it.\n\nAll settings fixed before TRAIN. VALIDATION proceeds only after unchanged-setting gate; no case-specific selection. Retain each mechanism only for incremental validation benefit without lost existing detections, timing/communication or slow/common-mode changes and unacceptable benign/wrong-origin regression. >=95% is a goal, not a selection rule. No new unseen holdout. Eight traces preselected, raw runs deleted; no commit/push.\n\nFrozen hashes:\n```json\n'+json.dumps(frozen,indent=2)+'\n```\n')
  retain={next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['origin']==o) for o in ['MEMORY','TIMING','COMMUNICATION','ACTUATOR','NORMAL']};retain.update(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['sensor_chain']==ch and s['model']=='sensor_bias') for ch in ['primary','reference']);retain.add(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['origin']=='MEMORY' and s['behavior']=='intermittent'))
  rows=[]
  for part in ['development-train','development-validation']:
   assert all(sha(ROOT/p)==h for p,h in frozen.items())
   for i,s in enumerate([s for s in specs if s['partition']==part]):
    rr=c.execute(s,w,s['run_id'] in retain)
    for r in rr:r.pop('command_json',None)
    rows+=rr
    if (i+1)%40==0:print(part,i+1,flush=True)
   report(rows)
   if part=='development-train':
    (BASE/'train_ready').write_text('ready');print('TRAIN READY',flush=True)
    import time
    while not (BASE/'validation_go').exists():time.sleep(1)
  assert all(sha(ROOT/p)==h for p,h in frozen.items());print('TRACTABLE CAMPAIGN COMPLETE',flush=True)
if __name__=='__main__':main()
