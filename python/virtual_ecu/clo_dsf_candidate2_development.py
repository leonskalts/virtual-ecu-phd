"""Second-candidate DEVELOPMENT evaluator; truth stays outside runtime detectors."""
from __future__ import annotations
import csv,gzip,hashlib,itertools,json,math,shutil,subprocess,time
from pathlib import Path
import yaml
from .clo_dsf_development import (ROOT,ORIGINS,write_csv,write_json,sha,ratio,mean,quantile)
from .cross_layer_safety import fault_options,MODEL_TARGETS,summarize_rows,read_rows
OUTPUT=ROOT/'results/cross_layer_safety_v7_1_dev'
STUDY=ROOT/'studies/clo_dsf_candidate2_development_v1.yaml'
METHODS=['Candidate 2','Candidate 1','Simple OR','Weighted Sum','Plain DS','Hybrid','Timing Monitor','B1 Dual-frame','B2 Origin reliability','B3 Propagation','B4 Temporal','Detection reliability 0.9','No origin reliability','Full propagation on','Full propagation off','Single frame positive']
NONLOCAL={'Simple OR','Weighted Sum','Hybrid','Timing Monitor'}
def candidate(i):
 return dict(r_detection=1,r_origin_direct=.9,r_origin_indirect=.6,lambda_temporal=.8 if i&4 else .6,propagation_bonus=.1,
             suspect_threshold=.35,confirmed_threshold=.65 if i&1 else .5,localization_threshold=.55,
             localization_margin_threshold=.15,ignorance_limit=.5,propagation_window_ms=3000,confirmation_persistence=2 if i&2 else 1)
def config_write(path,c):Path(path).write_text(''.join(f'{k}={v}\n' for k,v in c.items()))
def profile(path,load,speed,ambient,duration):
 write_csv(path,[dict(start_ms=a,end_ms=b,vehicle_speed_kph=max(0,speed*f),engine_load=max(.05,min(1,load*f)),ambient_temp_c=ambient,external_airflow_factor=0,road_slope_percent=0) for a,b,f in [(0,18000,.7),(18000,70000,1),(70000,duration,.88)]])
def design(out):
 c=yaml.safe_load(STUDY.read_text());specs=[]
 for p in c['profiles']:profile(out/'profiles'/f"{p['name']}.csv",p['load'],p['speed'],p['ambient'],c['simulation_duration_ms'])
 for origin,models in c['models'].items():
  for model,mags in models.items():
   for behavior in c['behaviors']:
    for severity,magnitude in enumerate(mags):
     for p in c['profiles']:
      for onset in c['injection_times_ms']:
       offset=severity*1300 if (model=='deadline_miss' and behavior in ['transient','permanent']) or (model=='fan_stuck_off' and behavior=='permanent') else 0
       specs.append(dict(origin=origin,model=model,behavior=behavior,magnitude=magnitude,severity=severity,profile=p['name'],start_ms=onset+offset,duration_ms=100 if model=='deadline_miss' and behavior=='transient' else c['durations_ms'][severity],group=f'{origin}/{model}/{behavior}'))
 for p in c['profiles']:
  for i,(lo,so,ao) in enumerate(itertools.product([-.12,-.06,0,.06],[-6,-2,2,6],[-1.5,0,1.5])):
   name=f"benign_{p['name']}_{i:02}";profile(out/'profiles'/f'{name}.csv',p['load']+lo,p['speed']+so,p['ambient']+ao,c['simulation_duration_ms'])
   specs.append(dict(origin='NORMAL',model='baseline',behavior='none',magnitude=0,severity=0,profile=name,start_ms=c['simulation_duration_ms']+100,duration_ms=0,group=f"NORMAL/{p['name']}"))
 val=set()
 for origin in ORIGINS+['NORMAL']:
  groups=sorted({s['group'] for s in specs if s['origin']==origin},key=lambda g:hashlib.sha256(f"{c['split_seed']}:{g}".encode()).hexdigest());val.update(groups[:math.ceil(.3*len(groups))])
 for i,s in enumerate(specs):s.update(run_id=f'c2_{i:04}',partition='development-validation' if s['group'] in val else 'development-train',split_seed=c['split_seed'],simulation_duration_ms=c['simulation_duration_ms'])
 write_csv(out/'development_split_manifest.csv',specs);return specs

def physical_key(s,out):
 return (s['model'],s['behavior'],sha(out/'profiles'/f"{s['profile']}.csv"),int(s['start_ms']),None if s['behavior']=='permanent' else int(s['duration_ms']),None if s['model'] in ['deadline_miss','fan_stuck_off','baseline'] else float(s['magnitude']))
def audit(specs,out):
 keys=[physical_key(s,out) for s in specs];assert len(keys)==len(set(keys)),'Semantic duplicate configuration'
 old=ROOT/'results/cross_layer_safety_v7_dev';prior=list(csv.DictReader((old/'development_split_manifest.csv').open()))
 oldkeys={physical_key(s,old) for s in prior if s['partition']=='development-validation'}
 assert not set(keys)&oldkeys
 assert not {s['group'] for s in specs if s['partition']=='development-train'}&{s['group'] for s in specs if s['partition']=='development-validation'}
 benign=[k[2] for s,k in zip(specs,keys) if s['origin']=='NORMAL'];assert len(benign)==len(set(benign))
 record=dict(configurations=len(specs),distinct_physical_configurations=len(set(keys)),duplicates=0,candidate1_validation_overlap=0,benign_profile_duplicates=0,group_overlap=0,independent_random_replicates=False)
 write_json(out/'duplicate_audit.json',record);return record

def command(s,out,comparison,config,ws=0):
 raw=out/'raw'/f"{s['run_id']}.csv";m=s['model'];start=s['start_ms'];dur=s['duration_ms'];b=s['behavior'];mag=s['magnitude'];args=['baseline']
 if m in MODEL_TARGETS:
  options=fault_options(m,start_ms=start,duration_ms=dur,behavior=b,bit_index=int(mag) if s['origin']=='MEMORY' else 0,seed=1,intermittent_on_ms=300,intermittent_off_ms=400,task_delay_ms=int(mag) if m=='task_delay' else 200,communication_delay_ms=int(mag) if m=='delayed_update' else 300,drop_count=int(mag) if m=='dropped_update' else 3,drop_every_n_updates=10 if m=='dropped_update' else 0,replay_age_ms=int(mag) if m=='replayed_sample' else 500,stuck_polarity=0)
 else:
  options=['--cross-layer-monitor','on']
  if m!='baseline':args=['custom_multi','2',m,str(start),str(dur),'transient',str(mag),m,str(start+dur+700),str(dur),'transient',str(mag)] if b=='intermittent' else ['custom',m,str(start),str(dur),b,str(mag)]
 return [str(ROOT/'virtual_ecu_v7_1'),str(raw),*args,*options,'--hazard-monitor','on','--timing-monitor','observe_only','--driving-profile',str(out/'profiles'/f"{s['profile']}.csv"),'--simulation-duration-ms',str(s['simulation_duration_ms']),'--detector','builtin_ecu','--detector-action','observe_only','--c2-config',str(config),'--c2-comparison',comparison,'--c2-evaluation-start',str(start),'--c2-evidence',str(out/'traces'/f"{s['run_id']}.candidate2.csv"),'--c2-metrics',str(out/'metrics'/f"{s['run_id']}.csv"),'--c2-weighted-choice',str(ws)]

def derived(r):
 r['localized_correct']=int(r['detected'] and r['origin_at_alarm']==r['origin']);r['unknown_at_alarm']=int(r['detected'] and r['origin_at_alarm']=='UNKNOWN')
 r['localized_wrong']=int(r['detected'] and r['origin_at_alarm'] not in ['UNKNOWN',r['origin']])
 r['localization_before_plant']=int(r['detected'] and r['first_origin']==r['origin'] and r['first_localization_ms']>=0 and r['propagation_plant_ms'] is not None and r['first_localization_ms']<r['propagation_plant_ms'])
 return r

def execute(s,out,comparison,config,ws=0):
 cmd=command(s,out,comparison,config,ws);start=time.perf_counter();p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(f'{cmd}\n{p.stdout}\n{p.stderr}')
 elapsed=time.perf_counter()-start;raw=Path(cmd[1]);summary=summarize_rows(read_rows(raw));result=[]
 for row in csv.DictReader((out/'metrics'/f"{s['run_id']}.csv").open()):
  r={**s,**row}
  for k in row:
   if k in ['method','origin_at_alarm','leading_at_alarm','first_origin']:continue
   r[k]=float(row[k]) if k.startswith(('mean_','origin_')) else int(row[k])
  r['injected']=int(s['origin']!='NORMAL');r['detected']=int(r['injected'] and r['first_post_alarm_ms']>=0);r['false_alarm']=int(not r['injected'] and r['first_alarm_ms']>=0);r['latency_ms']=r['first_post_alarm_ms']-s['start_ms'] if r['detected'] else None
  for k in ['control_effect','actuator_effect','plant_manifestation','propagation_plant_ms','propagation_control_ms','propagation_actuator_command_ms']:r[k]=summary[k]
  r['silent_plant']=int(r['injected'] and r['plant_manifestation']==1 and not r['detected']);r['host_seconds']=elapsed;result.append(derived(r))
 for path in [raw,raw.with_name(raw.stem+'_summary.csv'),out/'traces'/f"{s['run_id']}.candidate2.csv"]:
  with path.open('rb') as src,path.with_suffix(path.suffix+'.gz').open('wb') as dest:
   with gzip.GzipFile(filename='',mode='wb',fileobj=dest,mtime=0) as gz:shutil.copyfileobj(src,gz)
  path.unlink()
 write_json(out/'commands'/f"{s['run_id']}.json",cmd);return result

def aggregate(rows):
 f=[r for r in rows if r['injected']];b=[r for r in rows if not r['injected']];d=[r for r in f if r['detected']];loc=[r for r in d if r['origin_at_alarm']!='UNKNOWN'];fp=sum(r['false_alarm'] for r in b)
 cov=[ratio(sum(r['detected'] for r in f if r['origin']==o),sum(r['origin']==o for r in f)) for o in ORIGINS]
 macro_loc=[ratio(sum(r['localized_correct'] for r in d if r['origin']==o),sum(r['origin']==o for r in d)) for o in ORIGINS]
 result=dict(runs=len(rows),faulty_runs=len(f),benign_runs=len(b),detected=len(d),coverage=ratio(len(d),len(f)),macro_coverage=mean([v for v in cov if v is not None]),silent_plant=sum(r['silent_plant'] for r in f),benign_false_alarms=fp,benign_false_alarm_rate=ratio(fp,len(b)),precision=ratio(len(d),len(d)+fp),recall=ratio(len(d),len(f)),latency_median_ms=quantile([r['latency_ms'] for r in d],.5),latency_p95_ms=quantile([r['latency_ms'] for r in d],.95),localized=len(loc),localization_coverage=ratio(len(loc),len(d)),correct_localizations=sum(r['localized_correct'] for r in d),wrong_localizations=sum(r['localized_wrong'] for r in d),localization_accuracy=ratio(sum(r['localized_correct'] for r in d),len(d)),macro_localization_accuracy=mean([v for v in macro_loc if v is not None]),accuracy_when_localized=ratio(sum(r['localized_correct'] for r in loc),len(loc)),wrong_localization_rate=ratio(sum(r['localized_wrong'] for r in d),len(d)),unknown=sum(r['unknown_at_alarm'] for r in d),unknown_rate=ratio(sum(r['unknown_at_alarm'] for r in d),len(d)),localized_before_plant=sum(r['localization_before_plant'] for r in f),preinjection_alarm_runs=sum(r['pre_alarm_samples']>0 for r in f),propagation_supported_runs=sum(r['propagation_samples']>0 for r in rows))
 for field in ['control_effect','actuator_effect','plant_manifestation']:
  subset=[r for r in f if r[field]==1];result[field+'_runs']=len(subset);result['coverage_given_'+field]=ratio(sum(r['detected'] for r in subset),len(subset))
 for moment,op in [('pre',lambda a,p:a<p),('same',lambda a,p:a==p),('post',lambda a,p:a>p)]:result[moment+'_plant_alarms']=sum(r['propagation_plant_ms'] is not None and op(r['first_post_alarm_ms'],r['propagation_plant_ms']) for r in d)
 for field in ['mean_anomaly_ignorance','mean_origin_ignorance','mean_detection_conflict','mean_localization_conflict']:result[field]=mean([r[field] for r in rows])
 result['high_detection_conflict_runs']=sum(r['high_detection_conflict_samples']>0 for r in rows);result['high_localization_conflict_runs']=sum(r['high_localization_conflict_samples']>0 for r in rows)
 return result

def readout(rows,threshold,margin):
 result=[]
 for source in rows:
  r=source.copy();r['origin_at_alarm']=r['leading_at_alarm'] if r['detected'] and r['origin_score_at_alarm']>=threshold and r['origin_margin_at_alarm']>=margin and r['origin_ignorance_at_alarm']<=.5 else 'UNKNOWN'
  # Later timestamps cannot be recovered from first-alarm sufficient statistics.
  r['first_localization_ms']=-1;r['first_origin']='UNKNOWN';derived(r);result.append(r)
 return result

def key(s,i,local=True):
 return (s['benign_false_alarms'],s['silent_plant'],-(s['macro_coverage'] or 0),*((s['wrong_localizations'],-s['correct_localizations']) if local else ()),s['latency_median_ms'] if s['latency_median_ms'] is not None else math.inf,i)

def summarize(rows,out):
 summaries=[];layers=[]
 for part in ['development-train','development-validation']:
  for method in METHODS:
   subset=[r for r in rows if r['partition']==part and r['method']==method and (method!='Timing Monitor' or r['origin'] in ['NORMAL','TIMING'])]
   s=dict(partition=part,method=method,**aggregate(subset))
   if method in NONLOCAL:
    for k in list(s):
     if 'localiz' in k or 'ignorance' in k or 'conflict' in k or k.startswith('unknown'):s[k]=None
   summaries.append(s)
   for origin in ORIGINS:
    if method=='Timing Monitor' and origin!='TIMING':continue
    layers.append(dict(partition=part,method=method,origin=origin,**aggregate([r for r in subset if r['origin']==origin])))
 write_csv(out/'candidate2_baseline_comparison.csv',summaries);write_csv(out/'candidate2_layer_summary.csv',layers)
 for part,name in [('development-train','train'),('development-validation','validation')]:write_csv(out/f'candidate2_{name}_summary.csv',[s for s in summaries if s['partition']==part])
 write_csv(out/'candidate2_localization_summary.csv',[s for s in summaries if s['method'] not in NONLOCAL])
 write_csv(out/'candidate2_ablation.csv',[s for s in summaries if s['partition']=='development-validation' and s['method'] in ['Plain DS','B1 Dual-frame','B2 Origin reliability','B3 Propagation','B4 Temporal','Detection reliability 0.9','No origin reliability','Full propagation on','Full propagation off','Single frame positive','Candidate 2']])
 confusion=[]
 for method in ['Candidate 2','Candidate 1']:
  for origin in ORIGINS:
   subset=[r for r in rows if r['partition']=='development-validation' and r['method']==method and r['origin']==origin]
   confusion.append(dict(method=method,true_origin_evaluation_only=origin,**{o:sum(r['detected'] and r['origin_at_alarm']==o for r in subset) for o in ORIGINS+['UNKNOWN']},misses=sum(not r['detected'] for r in subset)))
 write_csv(out/'candidate2_origin_confusion.csv',confusion)
 uncertainty=[]
 for part in ['development-train','development-validation']:
  for origin in ORIGINS+['NORMAL']:
   subset=[r for r in rows if r['partition']==part and r['origin']==origin and r['method']=='Candidate 2']
   for field in ['mean_anomaly_ignorance','mean_origin_ignorance','mean_detection_conflict','mean_localization_conflict','origin_score_at_alarm','origin_margin_at_alarm']:
    values=[r[field] for r in subset if not field.endswith('_at_alarm') or r['detected']]
    uncertainty.append(dict(partition=part,origin=origin,quantity=field,n=len(values),mean=mean(values),p05=quantile(values,.05),median=quantile(values,.5),p95=quantile(values,.95)))
 write_csv(out/'candidate2_uncertainty_summary.csv',uncertainty);return summaries,layers,confusion

def run(out=OUTPUT):
 out=Path(out).resolve()
 if out!=OUTPUT.resolve():raise ValueError('Dedicated Candidate 2 output directory only')
 if (out/'preregistered_protocol.json').exists():raise ValueError('Refuse to overwrite an executed or preregistered campaign')
 for folder in ['raw','metrics','profiles','traces','commands','figures']:(out/folder).mkdir(parents=True,exist_ok=True)
 specs=design(out);audit_record=audit(specs,out)
 write_json(out/'preregistered_protocol.json',dict(study_sha256=sha(STUDY),protocol_sha256=sha(out/'selection_protocol.md'),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src/v7_1').glob('*.c'))},audit=audit_record,partitions={part:sum(s['partition']==part for s in specs) for part in ['development-train','development-validation']}))
 config_write(out/'initial_config.cfg',candidate(7));allrows=[];train=[s for s in specs if s['partition']=='development-train']
 for i,s in enumerate(train):
  allrows+=execute(s,out,'train',out/'initial_config.cfg')
  if i%25==0:print(f'TRAIN {i+1}/{len(train)}',flush=True)
 search=[]
 for index in range(8):
  for bonus in [0,.1]:
   method=f'candidate_{index}'+('_no_prop' if bonus==0 else '')
   subset=[r for r in allrows if r['method']==method]
   for threshold,margin in itertools.product([.55,.70,.85],[.15,.30]):search.append(dict(candidate=index,propagation_bonus=bonus,localization_threshold=threshold,localization_margin_threshold=margin,**aggregate(readout(subset,threshold,margin))))
 off=min([s for s in search if s['propagation_bonus']==0],key=lambda s:(key(s,s['candidate']),s['localization_threshold'],s['localization_margin_threshold']))
 on=next(s for s in search if s['candidate']==off['candidate'] and s['localization_threshold']==off['localization_threshold'] and s['localization_margin_threshold']==off['localization_margin_threshold'] and s['propagation_bonus']==.1)
 chosen=on if on['correct_localizations']>off['correct_localizations'] and on['wrong_localizations']<=off['wrong_localizations'] else off
 for s in search:s['selected']=int(s is chosen)
 write_csv(out/'candidate2_parameter_search.csv',search);write_csv(out/'candidate2_selective_localization_train.csv',search)
 cfg=candidate(chosen['candidate']);cfg.update({k:chosen[k] for k in ['propagation_bonus','localization_threshold','localization_margin_threshold']})
 weighted=[dict(candidate=i,weights='uniform' if i<6 else '.2/.2/.2/.1/.2/.1',threshold=[.04,.06,.08,.10,.14,.18][i%6],**aggregate([r for r in allrows if r['method']==f'weighted_{i}'])) for i in range(12)]
 ws=min(range(12),key=lambda i:key(weighted[i],i,False))
 for s in weighted:s['selected']=int(s['candidate']==ws)
 write_csv(out/'weighted_sum_parameter_search.csv',weighted);config_write(out/'selected_config.cfg',cfg)
 write_json(out/'selection_record.json',dict(selected_candidate=chosen['candidate'],parameters=cfg,weighted_choice=ws,weighted_parameters=weighted[ws],propagation_comparison=dict(off=off,on=on,retained=chosen is on),validation_seen=False,selected_config_sha256=sha(out/'selected_config.cfg')))
 print(f'SELECTED {cfg}; WS {ws}. Validation still unseen.',flush=True)
 method=f"candidate_{chosen['candidate']}"+('_no_prop' if cfg['propagation_bonus']==0 else '')
 selected=readout([r for r in allrows if r['method']==method],cfg['localization_threshold'],cfg['localization_margin_threshold'])
 # TRAIN ablations are at the preregistered starting configuration, validation ablations at the selected point.
 allrows=[r for r in allrows if r['method'] not in ['Candidate 2','Weighted Sum']]+[{**r,'method':'Candidate 2','later_localization_available':False} for r in selected]+[{**r,'method':'Weighted Sum'} for r in allrows if r['method']==f'weighted_{ws}']
 write_csv(out/'candidate2_train_checkpoint.csv',allrows)
 val=[s for s in specs if s['partition']=='development-validation']
 for i,s in enumerate(val):
  allrows+=execute(s,out,'validation',out/'selected_config.cfg',ws)
  if i%25==0:print(f'VALIDATION {i+1}/{len(val)}',flush=True)
 write_csv(out/'candidate2_dev_runs.csv',allrows);summarize(allrows,out)
 print('Development complete; no final holdout.',flush=True)
