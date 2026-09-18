"""Fixed-parameter v7.2 DEVELOPMENT CONFIRMATION; no tuning or holdout."""
from __future__ import annotations
import csv,gzip,hashlib,itertools,json,shutil,subprocess,time,tempfile
from pathlib import Path
import yaml
from .clo_dsf_development import ROOT,ORIGINS,write_csv,write_json,sha,ratio,mean,quantile
from .clo_dsf_candidate2_development import physical_key,derived,aggregate,command as c2_command
from .cross_layer_safety import summarize_rows,read_rows
OUTPUT=ROOT/'results/cross_layer_safety_v7_2_confirmation'
STUDY=ROOT/'studies/clo_dsf_final_confirmation_v1.yaml'
C2=ROOT/'results/cross_layer_safety_v7_1_dev'
METHODS=['Final CLO-DSF','Candidate 2','Candidate 2 no origin discount','Final no temporal','Candidate 1','Plain DS','Simple OR','Weighted Sum','Hybrid','Timing Monitor']
FIELDS=['r_detection','lambda_temporal','suspect_threshold','confirmed_threshold','localization_threshold','localization_margin_threshold','ignorance_limit','confirmation_persistence']
def parameters(out):
 selection=json.loads((C2/'selection_record.json').read_text());assert sha(C2/'selected_config.cfg')==selection['selected_config_sha256']
 cfg={k:v for k,v in (line.split('=',1) for line in (C2/'selected_config.cfg').read_text().splitlines() if line and not line.startswith('#'))}
 final={k:cfg[k] for k in FIELDS};(out/'final_reference.cfg').write_text(''.join(f'{k}={v}\n' for k,v in final.items()))
 write_json(out/'parameter_provenance.json',dict(source=str((C2/'selected_config.cfg').relative_to(ROOT)),source_sha256=sha(C2/'selected_config.cfg'),copied_exact_lexical_values=final,removed=['r_origin_direct','r_origin_indirect','propagation_bonus'],diagnostic_only={'propagation_window_ms':cfg['propagation_window_ms']},weighted_choice=selection['weighted_choice'],weighted_parameters=selection['weighted_parameters'],parameter_search=False))
 return selection['weighted_choice']
def profile(path,p,duration):
 write_csv(path,[dict(start_ms=a,end_ms=b,vehicle_speed_kph=max(0,p['speed']*f),engine_load=max(.05,min(1,p['load']*f)),ambient_temp_c=p['ambient'],external_airflow_factor=0,road_slope_percent=0) for a,b,f in [(0,24000,.72),(24000,76000,1),(76000,duration,.90)]])
def design(out):
 cfg=yaml.safe_load(STUDY.read_text());specs=[]
 for p in cfg['profiles']:profile(out/'profiles'/f"{p['name']}.csv",p,cfg['simulation_duration_ms'])
 for origin,models in cfg['models'].items():
  for model,magnitudes in models.items():
   for behavior in cfg['behaviors']:
    for severity,magnitude in enumerate(magnitudes):
     for pi,p in enumerate(cfg['profiles']):
      for onset in cfg['injection_times_ms']:
       offset=cfg['ignored_severity_onset_offsets_ms'][severity] if (model=='deadline_miss' and behavior in ['transient','permanent']) or (model=='fan_stuck_off' and behavior=='permanent') else 0
       specs.append(dict(origin=origin,model=model,behavior=behavior,magnitude=magnitude,severity=severity,profile=p['name'],start_ms=onset+offset,duration_ms=100 if model=='deadline_miss' and behavior=='transient' else cfg['durations_ms'][severity],group=f'{origin}/{model}/{behavior}',seed=cfg['seeds'][(severity+pi)%3],stuck_polarity=pi%2))
 for p in cfg['profiles']:
  for i,(lo,so,ao) in enumerate(itertools.product(*[cfg['benign_offsets'][key] for key in ['load','speed','ambient']])):
   name=f"benign_{p['name']}_{i:02}";profile(out/'profiles'/f'{name}.csv',dict(load=p['load']+lo,speed=p['speed']+so,ambient=p['ambient']+ao),cfg['simulation_duration_ms'])
   specs.append(dict(origin='NORMAL',model='baseline',behavior='none',magnitude=0,severity=0,profile=name,start_ms=cfg['simulation_duration_ms']+100,duration_ms=0,group=f"NORMAL/{p['name']}",seed=cfg['seeds'][i%3],stuck_polarity=0))
 for i,s in enumerate(specs):s.update(run_id=f'final_{i:04}',partition='development-confirmation',simulation_duration_ms=cfg['simulation_duration_ms'])
 write_csv(out/'confirmation_configuration_manifest.csv',specs);return specs

def audit(specs,out):
 # Conservative audit ignores seed/polarity differences: a match here would be rejected
 # even when those settings could distinguish physical effects.
 keys=[physical_key(s,out) for s in specs];assert len(set(keys))==len(keys)
 audit=[dict(compared_to='within confirmation',configurations=len(keys),exact_overlap=len(keys)-len(set(keys)))]
 for directory,label in [('cross_layer_safety_v7_dev','Candidate 1'),('cross_layer_safety_v7_1_dev','Candidate 2')]:
  old=ROOT/'results'/directory
  with (old/'development_split_manifest.csv').open() as f:prior=list(csv.DictReader(f))
  for part in ['development-train','development-validation']:
   previous={physical_key(s,old) for s in prior if s['partition']==part};overlap=len(set(keys)&previous);assert overlap==0
   audit.append(dict(compared_to=label+' '+part,configurations=len(previous),exact_overlap=overlap))
 invalid=out/'validation/invalid_attempt_01'
 if invalid.exists():
  with (invalid/'confirmation_configuration_manifest.csv').open() as f:past=list(csv.DictReader(f))
  done={p.stem for p in (invalid/'commands').glob('*.json')};pastkeys={physical_key(s,invalid) for s in past if s['run_id'] in done};overlap=len(set(keys)&pastkeys);assert overlap==0
  audit.append(dict(compared_to='Invalid attempt completed configurations (excluded)',configurations=len(pastkeys),exact_overlap=overlap))
 write_csv(out/'configuration_overlap_audit.csv',audit)
 assert len({s['run_id'] for s in specs})==900

def command(s,out,config,ws):
 # Existing command constructor supplies unchanged physics/injector semantics.
 cmd=c2_command(s,out,'validation',config,ws);cmd=cmd[:cmd.index('--c2-config')];cmd[0]=str(ROOT/'virtual_ecu_v7_2_reference')
 replacements={'--fault-seed':s['seed'],'--seed':s['seed'],'--intermittent-on-ms':400,'--intermittent-off-ms':500,'--drop-every-n-updates':9,'--stuck-polarity':s['stuck_polarity']}
 for key,value in replacements.items():
  if key in cmd:cmd[cmd.index(key)+1]=str(value)
 # Existing constructor's second legacy transient begins duration+700 after onset.
 if 'custom_multi' in cmd:
  index=cmd.index('custom_multi');cmd[index+8]=str(s['start_ms']+s['duration_ms']+900)
 return cmd+['--final-config',str(config),'--final-c2-config',str(C2/'selected_config.cfg'),'--final-comparison','--final-evaluation-start',str(s['start_ms']),'--final-weighted-choice',str(ws),'--final-evidence',str(out/'traces'/f"{s['run_id']}.final.csv"),'--final-observations',str(out/'observations'/f"{s['run_id']}.csv"),'--final-metrics',str(out/'metrics'/f"{s['run_id']}.csv")]
def validate_configurations(specs,out,ws):
 with tempfile.TemporaryDirectory(prefix='final-config-check-') as t:
  exe=Path(t)/'check';objects=[str(p) for p in sorted((ROOT/'src').glob('*.o')) if p.name!='main.o']
  subprocess.run(['gcc','-std=c11','-Iinclude','tests/final_configuration_check.c',*objects,'-o',str(exe)],cwd=ROOT,check=True)
  for spec in specs:
   cmd=command(spec,out,out/'final_reference.cfg',ws)
   result=subprocess.run([str(exe),*cmd[2:]],capture_output=True,text=True)
   if result.returncode:raise ValueError(f"Invalid {spec['run_id']}: {result.stderr}")
   assert spec['start_ms']%100==0 and spec['duration_ms']%100==0
   if spec['behavior']=='intermittent' and spec['model'] not in ['bit_flip','stuck_bit','deadline_miss','task_delay','delayed_update','dropped_update','replayed_sample']:assert spec['start_ms']+2*spec['duration_ms']+900<=120000
 write_json(out/'configuration_validation.json',dict(status='PASS',configurations=len(specs),validator='Unchanged cross_layer_parse_options + cross_layer_validate; no simulation or detector execution',legacy_tick_and_duration_checks=True))

def execute(s,out,config,ws):
 cmd=command(s,out,config,ws);start=time.perf_counter();p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(f'{cmd}\n{p.stdout}\n{p.stderr}')
 elapsed=time.perf_counter()-start;raw=Path(cmd[1]);summary=summarize_rows(read_rows(raw));results=[]
 with (out/'metrics'/f"{s['run_id']}.csv").open() as f:metrics=list(csv.DictReader(f))
 for row in metrics:
  r={**s,**row}
  for k in row:
   if k not in ['method','origin_at_alarm','leading_at_alarm','first_origin']:r[k]=float(row[k]) if k.startswith(('mean_','origin_')) else int(row[k])
  r.update(injected=int(s['origin']!='NORMAL'));r['detected']=int(r['injected'] and r['first_post_alarm_ms']>=0);r['false_alarm']=int(not r['injected'] and r['first_alarm_ms']>=0);r['latency_ms']=r['first_post_alarm_ms']-s['start_ms'] if r['detected'] else None
  for k in ['control_effect','actuator_effect','plant_manifestation','propagation_plant_ms','propagation_control_ms','propagation_actuator_command_ms']:r[k]=summary[k]
  r['silent_plant']=int(r['injected'] and r['plant_manifestation']==1 and not r['detected']);r['host_seconds']=elapsed;derived(r)
  r['localization_latency_ms']=r['first_localization_ms']-s['start_ms'] if r['first_localization_ms']>=0 else None;results.append(r)
 for path in [raw,raw.with_name(raw.stem+'_summary.csv'),out/'traces'/f"{s['run_id']}.final.csv",out/'observations'/f"{s['run_id']}.csv"]:
  with path.open('rb') as src,path.with_suffix(path.suffix+'.gz').open('wb') as dest:
   with gzip.GzipFile(filename='',mode='wb',fileobj=dest,mtime=0) as gz:shutil.copyfileobj(src,gz)
  path.unlink()
 write_json(out/'commands'/f"{s['run_id']}.json",cmd);return results

def run(out=OUTPUT):
 if out.resolve()!=OUTPUT.resolve():raise ValueError('Dedicated confirmation directory required')
 if (out/'preregistered_confirmation.json').exists():raise ValueError('Refuse to rerun or overwrite confirmation')
 gate=json.loads((out/'validation/ablation_reproduction/reproduction.json').read_text());assert gate['status']=='PASS'
 for folder in ['profiles','raw','metrics','traces','observations','commands','figures','benchmark']:(out/folder).mkdir(parents=True,exist_ok=True)
 ws=parameters(out);specs=design(out);audit(specs,out);validate_configurations(specs,out,ws)
 # Scientific, adapter and evaluation definitions all precede confirmation.
 sources=[*sorted((ROOT/'src/v7_2').glob('*.c')),*sorted((ROOT/'include').glob('clo_final*.h')),ROOT/'include/clo_dsf_final.h',Path(__file__),ROOT/'clo_dsf_final.mk',STUDY,out/'confirmation_protocol.md',out/'final_reference.cfg',out/'confirmation_configuration_manifest.csv',out/'parameter_provenance.json',out/'campaign_correction.md',ROOT/'tests/final_configuration_check.c']
 write_json(out/'preregistered_confirmation.json',dict(purpose='DEVELOPMENT CONFIRMATION — NOT FINAL HOLDOUT',parameters_may_change=False,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},configurations=len(specs),parameter_search=False))
 rows=[]
 for i,s in enumerate(specs):
  rows+=execute(s,out,out/'final_reference.cfg',ws)
  if i%25==0:print(f'CONFIRMATION {i+1}/{len(specs)}',flush=True)
 write_csv(out/'final_candidate_runs.csv',rows)
 print('Confirmation complete; no parameter changes or holdout.',flush=True)
