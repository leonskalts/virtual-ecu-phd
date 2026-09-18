"""One preregistered runtime-contract revision; no search, no final holdout."""
import csv,gzip,hashlib,itertools,json,shutil,subprocess,tempfile,time
from pathlib import Path
from .clo_dsf_development import ROOT,ORIGINS,write_csv,write_json,sha
from .clo_dsf_candidate2_development import physical_key,derived,aggregate,NONLOCAL
from .clo_dsf_final_confirmation import command as old_command,profile
from .cross_layer_safety import summarize_rows,read_rows
OUT=ROOT/'results/cross_layer_safety_v7_3_dev'
OLD=ROOT/'results/cross_layer_safety_v7_2_confirmation'
METHODS=['Revised CLO-DSF','Candidate 2','v7.2 CLO-DSF','Plain DS','Simple OR','Weighted Sum','Hybrid','Timing Monitor']
PROFILES=[dict(name='r73_cruise',load=.38,speed=75,ambient=18),dict(name='r73_urban',load=.59,speed=35,ambient=27),dict(name='r73_queue',load=.76,speed=8,ambient=36),dict(name='r73_fast',load=.89,speed=115,ambient=25),dict(name='r73_hot_idle',load=.99,speed=5,ambient=42)]
MODELS={'MEMORY':{'bit_flip':[1,2,4],'stuck_bit':[1,2,4]},'TIMING':{'deadline_miss':[100,400,1000],'task_delay':[100,400,1000]},'COMMUNICATION':{'delayed_update':[100,400],'dropped_update':[1,4],'replayed_sample':[200,900]},'SENSOR_CONTROL':{'sensor_bias':[-3,4,9],'sensor_interface_intermittent':[2,6,11]},'ACTUATOR':{'pump_degraded':[.98,.88,.58],'fan_stuck_off':[0,0,0]}}
BEHAVIORS=['transient','intermittent','permanent']
def read(path):
 with path.open(newline='') as f:return list(csv.DictReader(f))
def design():
 specs=[]
 for p in PROFILES:profile(OUT/'profiles'/f"{p['name']}.csv",p,120000)
 for origin,models in MODELS.items():
  for model,magnitudes in models.items():
   for behavior in BEHAVIORS:
    for severity,magnitude in enumerate(magnitudes):
     for pi,p in enumerate(PROFILES):
      for onset in [26300,64300]:
       offset=severity*1200 if (model=='deadline_miss' and behavior in ['transient','permanent']) or (model=='fan_stuck_off' and behavior=='permanent') else 0
       specs.append(dict(origin=origin,model=model,behavior=behavior,magnitude=magnitude,severity=severity,profile=p['name'],start_ms=onset+offset,duration_ms=100 if model=='deadline_miss' and behavior=='transient' else [800,3500,9500][severity],group=f'{origin}/{model}/{behavior}',seed=[19,43,89][(severity+pi)%3],stuck_polarity=pi%2))
 for p in PROFILES:
  for i,(lo,so,ao) in enumerate(itertools.product([-.07,0,.03],[-4,-2,0,2,4],[-1,0,1])):
   name=f"benign_{p['name']}_{i:02}";profile(OUT/'profiles'/f'{name}.csv',dict(load=p['load']+lo,speed=p['speed']+so,ambient=p['ambient']+ao),120000)
   specs.append(dict(origin='NORMAL',model='baseline',behavior='none',magnitude=0,severity=0,profile=name,start_ms=120100,duration_ms=0,group=f"NORMAL/{p['name']}",seed=[19,43,89][i%3],stuck_polarity=0))
 # Hold out a whole behavior group per model; all severity/onset/profile siblings
 # remain together. Benign operating-profile families are grouped separately.
 order=lambda g:hashlib.sha256(('v7.3-runtime-contract:'+g).encode()).hexdigest()
 val=set()
 for origin,models in MODELS.items():
  for model in models:val.add(min([f'{origin}/{model}/{b}' for b in BEHAVIORS],key=order))
 val.update(sorted({s['group'] for s in specs if s['origin']=='NORMAL'},key=order)[:2])
 for i,s in enumerate(specs):s.update(run_id=f'revised_{i:04}',partition='development-validation' if s['group'] in val else 'development-train',simulation_duration_ms=120000)
 write_csv(OUT/'development_split_manifest.csv',specs);return specs

def audit(specs):
 keys={physical_key(s,OUT) for s in specs};assert len(keys)==len(specs)==1125
 assert not {s['group'] for s in specs if s['partition']=='development-train'}&{s['group'] for s in specs if s['partition']=='development-validation'}
 checks=[]
 for folder,manifest in [('cross_layer_safety_v7_dev','development_split_manifest.csv'),('cross_layer_safety_v7_1_dev','development_split_manifest.csv'),('cross_layer_safety_v7_2_confirmation','confirmation_configuration_manifest.csv'),('cross_layer_safety_v7_2_confirmation/validation/invalid_attempt_01','confirmation_configuration_manifest.csv')]:
  old=ROOT/'results'/folder;prior={physical_key(s,old) for s in read(old/manifest)};overlap=len(keys&prior);assert overlap==0
  checks.append(dict(historical=folder,prior_configurations=len(prior),exact_overlap=overlap))
 write_json(OUT/'overlap_audit.json',dict(status='PASS',unique_configurations=len(keys),group_overlap=0,historical=checks,independent_random_replicates=False))

def command(s):
 cmd=old_command(s,OUT,OUT/'revised.cfg',6)
 cmd[0]=str(ROOT/'virtual_ecu_v7_3')
 cmd=[v.replace('--final-','--revised-') for v in cmd]
 # Existing command constructor and validators preserve accepted injector semantics.
 cmd[cmd.index('--revised-evidence')+1]=str(OUT/'scratch'/f"{s['run_id']}.csv")
 cmd[cmd.index('--revised-observations')+1]=str(OUT/'observations'/f"{s['run_id']}.csv")
 return cmd

def validate(specs):
 with tempfile.TemporaryDirectory(prefix='revised-validate-') as t:
  exe=Path(t)/'check';objects=[str(p) for p in sorted((ROOT/'src').glob('*.o')) if p.name!='main.o']
  subprocess.run(['gcc','-std=c11','-Iinclude','tests/final_configuration_check.c',*objects,'-o',str(exe)],cwd=ROOT,check=True)
  for s in specs:
   cmd=command(s);p=subprocess.run([str(exe),*cmd[2:]],capture_output=True,text=True)
   if p.returncode:raise ValueError(s['run_id']+': '+p.stderr)
 write_json(OUT/'configuration_validation.json',dict(status='PASS',cases=len(specs),validator='Unchanged C parser and injector validator, before any simulation'))

def execute(s):
 cmd=command(s);p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(str(cmd)+'\n'+p.stderr)
 raw=Path(cmd[1]);summary=summarize_rows(read_rows(raw));result=[]
 for row in read(OUT/'metrics'/f"{s['run_id']}.csv"):
  if None in row:raise ValueError('Malformed metrics row')
  r={**s,**row}
  for k in row:
   if k not in ['method','origin_at_alarm','leading_at_alarm','first_origin']:r[k]=float(row[k]) if k.startswith(('mean_','origin_')) else int(row[k])
  r['injected']=int(s['origin']!='NORMAL');r['detected']=int(r['injected'] and r['first_post_alarm_ms']>=0);r['false_alarm']=int(not r['injected'] and r['first_alarm_ms']>=0);r['latency_ms']=r['first_post_alarm_ms']-s['start_ms'] if r['detected'] else None
  for k in ['control_effect','actuator_effect','plant_manifestation','propagation_plant_ms','propagation_control_ms','propagation_actuator_command_ms']:r[k]=summary[k]
  r['silent_plant']=int(r['injected'] and r['plant_manifestation']==1 and not r['detected']);derived(r)
  r['wrong_localized_runtime_samples']=sum(r['alarm_'+origin] for origin in ORIGINS if origin!=s['origin']);result.append(r)
 # Retain exact allowlisted input streams and small online metrics; raw scientific
 # outputs are reproducible from commands, with hashes retained instead of duplicates.
 obs=OUT/'observations'/f"{s['run_id']}.csv"
 with obs.open('rb') as src,obs.with_suffix('.csv.gz').open('wb') as dest:
  with gzip.GzipFile(filename='',mode='wb',fileobj=dest,mtime=0) as gz:shutil.copyfileobj(src,gz)
 record=dict(run_id=s['run_id'],command=cmd,raw_sha256=sha(raw),summary_sha256=sha(raw.with_name(raw.stem+'_summary.csv')),trace_sha256=sha(OUT/'scratch'/f"{s['run_id']}.csv"),observation_sha256=sha(obs))
 with (OUT/'commands.jsonl').open('a') as f:f.write(json.dumps(record,sort_keys=True)+'\n')
 for path in [obs,raw,raw.with_name(raw.stem+'_summary.csv'),OUT/'scratch'/f"{s['run_id']}.csv"]:path.unlink()
 return result

def summarize(rows,part):
 summaries=[]
 for method in METHODS:
  subset=[r for r in rows if r['method']==method and (method!='Timing Monitor' or r['origin'] in ['NORMAL','TIMING'])]
  s=dict(partition=part,method=method,**aggregate(subset));s['wrong_localized_runtime_samples']=sum(r['wrong_localized_runtime_samples'] for r in subset)
  if method in NONLOCAL:
   for k in s:
    if any(x in k for x in ['localiz','ignorance','conflict','unknown']):s[k]=None
  summaries.append(s)
 return summaries

def register(specs):
 paths=[ROOT/'clo_dsf_revised.mk',ROOT/'include/clo_dsf_revised.h',*sorted((ROOT/'src/v7_3').glob('*.c')),Path(__file__),ROOT/'docs/clo_dsf_revised_development.md',ROOT/'scripts/run_clo_dsf_revised_development.py',OUT/'revised.cfg',OUT/'development_split_manifest.csv',OUT/'miss_root_cause_summary.csv',OUT/'observability_gap_summary.csv',OLD/'clo_dsf_final_scientific_hashes.json']
 old=json.loads((OLD/'clo_dsf_final_scientific_hashes.json').read_text())['sha256'];sources={str(p.relative_to(ROOT)):sha(p) for p in paths};sources.update(old)
 write_json(OUT/'preregistered_development.json',dict(purpose='DEVELOPMENT ONLY; no final holdout',source_sha256=sources,parameter_search=False,selection_objective='Single contract-derived revision; all v7.2 parameters unchanged. Reject contradictory TRAIN. Freeze only after validation improves material safety/localization endpoints without detection loss, new benign alarms or wrong confident origins.',configurations=len(specs),train=sum(s['partition']=='development-train' for s in specs),validation=sum(s['partition']=='development-validation' for s in specs)))

def run():
 if (OUT/'preregistered_development.json').exists():raise ValueError('Refuse to overwrite a registered campaign')
 for folder in ['profiles','raw','metrics','scratch','observations','validation']:(OUT/folder).mkdir(parents=True,exist_ok=True)
 shutil.copyfile(OLD/'final_reference.cfg',OUT/'revised.cfg');specs=design();audit(specs);validate(specs);register(specs)
 allrows=[]
 for part in ['development-train','development-validation']:
  if part=='development-validation':
   frozen=json.loads((OUT/'preregistered_development.json').read_text())['source_sha256']
   assert all(sha(ROOT/k)==v for k,v in frozen.items())
   train=summarize(allrows,'development-train');new=next(r for r in train if r['method']=='Revised CLO-DSF');old=next(r for r in train if r['method']=='v7.2 CLO-DSF')
   if new['benign_false_alarms']>old['benign_false_alarms'] or new['wrong_localized_runtime_samples']>old['wrong_localized_runtime_samples']:raise ValueError('TRAIN contradicts contract; stop without validation')
   write_json(OUT/'selection_record.json',dict(selected='Single preregistered revision, no search',validation_seen=False,parameters_changed=False,config_sha256=sha(OUT/'revised.cfg'),source_sha256=frozen,train_summary=new))
  selected=[s for s in specs if s['partition']==part];rows=[]
  for i,s in enumerate(selected):
   rows+=execute(s)
   if i%25==0:print(f'{part} {i+1}/{len(selected)}',flush=True)
  write_csv(OUT/('train_runs.csv' if part=='development-train' else 'validation_runs.csv'),rows)
  write_csv(OUT/('revised_train_summary.csv' if part=='development-train' else 'revised_validation_summary.csv'),summarize(rows,part));allrows+=rows
 print('Development execution complete; no holdout and no parameter changes.',flush=True)
