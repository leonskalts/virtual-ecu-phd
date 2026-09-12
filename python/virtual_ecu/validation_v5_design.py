"""Predeclared holdout design and source-frozen runtime contracts."""
import hashlib,itertools,json,subprocess
from pathlib import Path
import yaml
from .cross_layer_safety import PROJECT_ROOT,read_rows

OUTPUT=PROJECT_ROOT/'results/cross_layer_safety_v5'
STUDY=PROJECT_ROOT/'studies/cross_layer_v5_holdout.yaml'
FROZEN_SOURCES=('src/timing_safety_monitor.c','include/timing_safety_monitor.h','include/runtime_timing_observation.h',
 'src/runtime_timing_observation.c','src/runtime_safety_policy.c','src/safety_policy_v5.c','include/safety_policy_v5.h',
 'src/scheduler_stress.c','include/scheduler_stress.h','src/validation_v5_config.c','src/scheduler.c')

def source_hashes():return {p:hashlib.sha256((PROJECT_ROOT/p).read_bytes()).hexdigest() for p in FROZEN_SOURCES}

def freeze(output=OUTPUT):
 output.mkdir(parents=True,exist_ok=True);(output/'contracts').mkdir(exist_ok=True)
 manifest={'baseline':'da126cb','version':5,'primary_monitor':'combined','monitor_mode':'observe_only',
  'period_ms':100,'relative_deadline_ms':100,'observation_period_ms':100,
  'deadline_rule':'unfinished at D after completion opportunity or completion after D',
  'missed_execution_rule':'actual rejected/cancelled release; queue backlog alone is not rejection',
  'age_rule':'execution_age_ms > P+D','repeated_rule':'at least 3 violating observation periods in half-open trailing 10P',
  'critical_absence_rule':'execution_age_ms >= 3P; age/combined only',
  'policies':{'observe_only':'No new policy action',
   'immediate':'Exact v4: repeated timing -> cooling; critical absence -> limp; qualified communication -> limp',
   'graded':'Repeated timing or qualified communication -> cooling; timing execution age >=5P or continuous qualified communication >=5P -> limp'},
  'qualification':'existing detector alarm AND existing failed freshness; no new detector threshold',
  'release_envelope':'release jitter + start jitter + execution duration <= P=D for legal workload',
  'queue_capacity':4,'simulation_event_resolution_ms':1,'thermal_step_ms':100,
  'source_sha256':source_hashes(),'study_sha256':hashlib.sha256(STUDY.read_bytes()).hexdigest(),
  'profile_sha256':{str(p.relative_to(PROJECT_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((PROJECT_ROOT/'profiles/driving/v5').glob('*.csv'))},
  'freeze_status':'Before final holdout; synthetic implementation checks only; no v4 monitor corrections or retuning.'}
 path=output/'timing_monitor_contract.json'
 if path.exists():
  assert json.loads(path.read_text())==manifest,'Frozen configuration changed: explicitly revise protocol before evaluation'
 else:path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 (output/'contracts/timing_monitor_contract.json').write_bytes(path.read_bytes())
 return manifest

def expand(config):
 runs=[]
 def add(study,profile,model,params=None,**extras):
  spec={'study_kind':study,'profile':profile,'detector':config['detector'],'model':model,
        'parameters':{'seed':42,**(params or {})},'policy':'observe_only',**extras}
  spec['case_id']=f'{study}_{len(runs):04d}_{model}';spec['pair_id']=spec['case_id'];spec['run_id']=spec['case_id']+'_observe_only'
  runs.append(spec);return spec
 times=config['injection_times_ms'];t=config['timing']
 for p in config['profiles']:
  for pattern in t['legal_patterns']:
   seeds=t['legal_seeds'] if pattern['release_jitter_ms'] or pattern['start_jitter_ms'] else [1]
   for seed in seeds:
    stress={k:v for k,v in pattern.items() if k!='id'};stress['seed']=seed
    add('timing',p,'baseline',stress=stress,stress_kind='legal',behavior='legal',timing_magnitude=stress['execution_ms'],timing_pattern=pattern['id'])
  for start,model,behavior in itertools.product(times,['deadline_miss','task_delay'],['transient','intermittent','permanent']):
   durations=t['durations_ms'] if behavior=='transient' else [3700,13700] if behavior=='intermittent' else [100]
   patterns=t['intermittent_patterns'] if behavior=='intermittent' else [None]
   magnitudes=t['delays_ms'] if model=='task_delay' else [0]
   for duration,pattern,magnitude in itertools.product(durations,patterns,magnitudes):
    params={'start_ms':start,'duration_ms':duration,'behavior':behavior}
    if model=='deadline_miss' and behavior=='transient':
     params.update(start_ms=start+t['deadline_transient_offsets_ms'][t['durations_ms'].index(duration)],duration_ms=100)
    if pattern:params.update(intermittent_on_ms=pattern[0],intermittent_off_ms=pattern[1])
    if model=='task_delay':params['task_delay_ms']=magnitude
    add('timing',p,model,params,behavior=behavior,timing_magnitude=magnitude or duration,timing_pattern='direct_injection')
  for start,duration,magnitude in itertools.product(times,t['overload_durations_ms'],t['overload_execution_ms']):
   stress={'seed':47,'release_jitter_ms':0,'start_jitter_ms':0,'execution_ms':20,'stress_start_ms':start,'stress_duration_ms':duration,'overload_execution_ms':magnitude}
   add('timing',p,'baseline',stress=stress,stress_kind='overload',behavior='temporary_overload',timing_magnitude=magnitude,timing_pattern='backlog')
 # Deliberately balanced fixed action subset: first case of every profile/model/behavior/start stratum.
 selected={}
 for r in runs:
  if r['model']!='baseline':selected.setdefault((r['profile']['id'],r['model'],r['behavior'],min(times,key=lambda t:abs(t-r['parameters']['start_ms']))),r)
 for r in list(selected.values()):
  for policy in ['immediate','graded']:runs.append({**r,'policy':policy,'run_id':r['pair_id']+'_'+policy})
 c=config['communication']
 for pi,p in enumerate(config['profiles']):
  benign=add('communication',p,'baseline',behavior='benign')
  for policy in ['immediate','graded']:runs.append({**benign,'policy':policy,'run_id':benign['pair_id']+'_'+policy})
  for mi,(model,magnitudes) in enumerate(c['magnitudes'].items()):
   for vi,magnitude in enumerate(magnitudes):
    for bi,behavior in enumerate(c['behaviors']):
     start=times[(pi+mi+vi+bi)%len(times)]
     params={'start_ms':start,'duration_ms':c['intermittent_duration_ms'] if behavior=='intermittent' else c['transient_duration_ms'],'behavior':behavior}
     params[{'delayed_update':'communication_delay_ms','replayed_sample':'replay_age_ms','dropped_update':'drop_count'}[model]]=magnitude
     if model=='dropped_update' and behavior!='transient':params['drop_every_n_updates']=magnitude+1
     if behavior=='intermittent':params.update(intermittent_on_ms=c['on_ms'],intermittent_off_ms=c['off_ms'])
     r=add('communication',p,model,params,behavior=behavior,timing_magnitude=magnitude)
     for policy in ['immediate','graded']:runs.append({**r,'policy':policy,'run_id':r['pair_id']+'_'+policy})
 for p in config['profiles']:
  add('cross_layer',p,'baseline',behavior='benign')
  for model,behavior,variant,start in itertools.product(config['cross_layer']['models'],config['cross_layer']['behaviors'],config['cross_layer']['variants'],times):
   if model in ['sensor_bias','pump_degraded','fan_stuck_off'] and behavior=='intermittent':behavior='permanent'
   params={'start_ms':start,'duration_ms':[1900,7300,19300][variant],'behavior':behavior}
   if model=='fan_stuck_off' and behavior=='permanent':params['start_ms']=start+[0,400,1800][variant]
   if model=='deadline_miss' and behavior=='transient':params.update(start_ms=start+[0,400,1800][variant],duration_ms=100)
   if model in ('bit_flip','stuck_bit'):params.update(bit_index=[1,3,5][variant]);params.update({'stuck_polarity':variant%2} if model=='stuck_bit' else {})
   elif model=='task_delay':params['task_delay_ms']=[100,300,1500][variant]
   elif model=='delayed_update':params['communication_delay_ms']=[100,500,1700][variant]
   elif model=='replayed_sample':params['replay_age_ms']=[200,700,1900][variant]
   elif model=='dropped_update':params.update(drop_count=[1,4,9][variant],drop_every_n_updates=[3,7,11][variant])
   elif model=='sensor_bias':params['parameter']=[-4,3,8][variant]
   elif model=='pump_degraded':params['parameter']=[.25,.5,.75][variant]
   elif model=='fan_stuck_off':params['parameter']=0
   if behavior=='intermittent' and model not in ['sensor_bias','pump_degraded','fan_stuck_off']:params.update(intermittent_on_ms=700,intermittent_off_ms=900)
   add('cross_layer',p,model,params,behavior=behavior)
 m=config['matched']
 for p,start,bit in itertools.product(config['profiles'],times,m['bits']):
  match=f"{p['id']}_{start}_{bit}"
  add('matched',p,'bit_flip',{'start_ms':start,'duration_ms':100,'behavior':'transient','bit_index':bit},behavior='transient_bit_flip',match_id=match,polarity=None)
  for polarity,behavior in itertools.product(m['polarities'],['permanent','intermittent']):
   params={'start_ms':start,'duration_ms':m['duration_ms'],'behavior':behavior,'bit_index':bit,'stuck_polarity':polarity}
   if behavior=='intermittent':params.update(intermittent_on_ms=m['on_ms'],intermittent_off_ms=m['off_ms'])
   add('matched',p,'stuck_bit',params,behavior=behavior+'_stuck_bit',match_id=match,polarity=polarity)
 return runs

def load_config():return yaml.safe_load(STUDY.read_text())
