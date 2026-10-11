#!/usr/bin/env python3
"""Frozen observers, causal evidence replay, TRAIN/CAL selection and one unseen."""
import sys, os, json, hashlib, inspect, subprocess, shutil, pickle, collections
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_clo_dsf_triplex as t
import run_clo_dsf_triplex_final_unseen as historical
from virtual_ecu import comparative_backends as be
from virtual_ecu.clo_dsf_candidate2_development import derived, aggregate
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
B=Path('/tmp/clo-comparative');OUT=ROOT/'results/comparative_benchmark';h=t.h
sha=t.sha

def now():return datetime.now(timezone.utc).isoformat()
def dump(p,v):p.write_text(json.dumps(v,indent=2))
def verify():
 lock=json.loads((ROOT/'results/clo_dsf_triplex_final_unseen/hashes.json').read_text())
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==lock['commit']
 assert all(sha(Path(p))==v for p,v in lock['scientific_files'].items())
 art=ROOT/'results/clo_dsf_triplex_final_unseen'
 assert all(sha(art/p)==v for p,v in json.loads((art/'artifact_hashes.json').read_text()).items())
 return lock

# Read-only callback inserted into the temporary existing observer build. The
# arguments are runtime provider qualification, before causal-origin suppression.
CAPTURE=r'''
static FILE *benchmark_log;
void benchmark_capture(unsigned arch,const clo_revised_t *state,const runtime_observation_t *o,double origin_local,double local){
 const clo_evidence_t *e=&state->fusion.evidence;
 unsigned subsets[6]={2,4,1,12,16,31};
 fprintf(benchmark_log,"%u,%u",o->time_ms,arch);
 for(unsigned i=0;i<6;i++){
  double strength=e->strength[i];bool available=e->available[i];
  if(i==3){
   /* Respect the frozen startup qualification. A qualified independent local
    * provider or delivered-sample discrepancy remains available immediately. */
   if(state->slew_qualification_count<5 && origin_local<=0 && strength<=local)available=false;
   if(origin_local>0)subsets[i]=8;
  }
  fprintf(benchmark_log,",%.17g,%u,%u",strength,available,subsets[i]);
 }
 fprintf(benchmark_log,"\n");
}
'''
def build(w):
 source=inspect.getsource(t.build)
 injection='\nvoid benchmark_capture(unsigned,const clo_revised_t *,const runtime_observation_t *,double,double);\n'
 source=source.replace("core=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text();bridge=core+", "core=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text();core=core.replace('#include <math.h>', '#include <math.h>'+"+repr(injection)+");core=core.replace('    unsigned int direct=0, direct_count=0;', '    benchmark_capture(0,state,o,origin_local,local);\\n    unsigned int direct=0, direct_count=0;');bridge=core+")
 source=source.replace('extended=core\n',"extended=core.replace('benchmark_capture(0,','benchmark_capture(1,')\n")
 source=source.replace("adapter=adapter[:where]+FRONT+'\\n'+adapter[where:]", "adapter=adapter[:where]+FRONT+CAPTURE+'\\n'+adapter[where:]")
 source=source.replace('names[0]="A0";', 'benchmark_log=fopen(getenv("BENCHMARK_LOG"),"w");if(!benchmark_log)return 1; names[0]="A0";')
 ns=dict(t.__dict__,CAPTURE=CAPTURE);exec(source,ns)
 exe=ns['build'](w)
 dump(B/'instrumentation.json',dict(builder_sha256=sha(Path(__file__)),adapter_sha256=sha(w/'adapter.c'),bridge_sha256=sha(w/'bridge.c'),extended_sha256=sha(w/'extended.c')))
 return exe

def design(part):
 # Historical template definitions only; no previous unseen result is read.
 templates=t.prior.design();n=750 if part=='VALIDATION' else 1500;out=[]
 salt=0 if part=='VALIDATION' else 10000
 for i in range(n):
  f=i//150;j=i%150;u=i+salt;s=dict(templates[(f%16)*150+j])
  s.update(run_id=f'benchmark_{part.lower()}_{i:04}',profile=f'benchmark_profile_{part.lower()}_{i:04}',group=f'benchmark_{part}_family_{f}',partition=part,
   seed=1733000011+u*173,reference_seed=1793000021+u*179,c_seed=1831000033+u*181,domain='NONE',kind='none',subgroup='base',
   c_offset=(f%5-2)*.0431,c_gain=(f%3-1)*.00043,c_noise=.0177+f*.00073,c_quantum=[.021,.025,.029][f%3],c_adc_gain=(f%4-1.5)*.000173,c_phase_ms=19+f*7,c_lag_ms=0)
  load=[.41,.51,.61,.71,.81,.91,.46,.56,.76,.86][f]
  pp=[dict(start_ms=a,end_ms=b,engine_load=(load+u*.00000013)*fac,ambient_temp_c=12.731+f*1.771+u*.000031+(1.21 if a>=71900 else 0),vehicle_speed_kph=(26.913+f*6.131+u*.000027)*fac,external_airflow_factor=.063 if a>=47100 else 0,road_slope_percent=0) for a,b,fac in [(0,18300,.73),(18300,47100,.97),(47100,71900,.82),(71900,97900,1),(97900,120000,.87)]]
  if (s['origin']=='ACTUATOR' and (j-96)%4==0) or (s['origin']=='NORMAL' and j>=144):
   for p in pp:p.update(engine_load=.0797+f*.00029+u*.00000011,ambient_temp_c=8.931+f*.179+u*.000013,vehicle_speed_kph=73.731+f*.193+u*.000017)
  if s['origin']!='NORMAL':s['start_ms']=24100+(j%13)*500+f*100+(0 if part=='VALIDATION' else 200)
  s['on_ms']=[600,1100,1400][f%3];s['off_ms']=[1200,1600,2100][f%3]
  if s['behavior'] not in ['permanent','none'] and s['model']!='deadline_miss':s['duration_ms']=[900,3100,7900,14900][(j+f)%4]
  if s['origin']=='MEMORY':
   s['start_ms']=22700+(j%10)*100+f*1300
   if s['behavior']!='permanent':s['duration_ms']=[200,600,1400,2800][(j+f)%4]
  if s['origin']=='ACTUATOR' and s['model']=='pump_degraded':s['magnitude']=[.993,.969,.929,.857,.747,.601][(j-96)//3]
  if s['origin']=='SENSOR_CONTROL':
   k=j-72;domain=['A','B','AB'][k//8];cell=k%8;kind=['ramp','step','pulse'][(cell+f+k//8)%3]
   mag=(-1 if (cell+f)%2 else 1)*(2.59+f*.023 if kind=='ramp' else [.51,.69,.91,1.09][(cell+f)%4])
   duration=[100,300,700,1300][(cell+f)%4] if kind=='pulse' else 0
   s.update(domain=domain,kind=kind,subgroup=domain+'_'+kind,sensor_chain=domain,model={'ramp':'sensor_bias_ramp','step':'sensor_bias','pulse':'sensor_interface_intermittent'}[kind],behavior='transient' if duration else 'permanent',magnitude=mag,duration_ms=duration,sensor_ramp_rise_ms=[21100,40900,64700,85300][(cell+f)%4] if kind=='ramp' else 0,start_ms=23700+f*300+cell*400,initially_latent_stuck=0,target_updates_json='[]',workload='triplex_fault')
  s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(pp)
  s.pop('configuration_sha256',None);s.pop('command_json',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 assert len({s['profile_semantic_sha256'] for s in out})==n
 return out

def setup():
 verify();assert not (B/'registered.json').exists()
 ss=json.loads(Path('/tmp/clo-multirate/specs.json').read_text())
 ss=[s for s in ss if s['partition'] in ['TRAIN','CALIBRATION']]
 assert len(ss)==1950
 validation=design('VALIDATION')
 historical.OUT=OUT;historical.B=B;count=historical.historical_audit(validation)
 h.write(OUT/'train_calibration_manifest.csv',ss);h.write(OUT/'validation_manifest.csv',validation)
 dump(B/'specs.json',ss+validation)
 frozen=verify()
 dump(B/'registered.json',dict(utc=now(),historical_sources=count,files=frozen['scientific_files'],train_calibration_manifest_sha256=sha(OUT/'train_calibration_manifest.csv'),validation_manifest_sha256=sha(OUT/'validation_manifest.csv'),protocol_sha256=sha(OUT/'protocol.md')))
 print('REGISTERED TRAIN1200 CAL750 VALID750; zero historical validation overlap',flush=True)

def evidence(a,arch):
 x=a[a[:,1]==arch];v=x[:,2:].reshape(-1,6,3)
 return be.Evidence(x[:,0].astype(int),v[:,:,0],v[:,:,1].astype(bool),v[:,:,2].astype(int))

def summary(rows):
 st=aggregate(rows);st.update({'runtime_'+k:v for k,v in runtime_stats(rows).items()});st['ci_low'],st['ci_high']=h.wilson(st['detected'],st['faulty_runs']);return st

def score(base,e,method,pred):
 alarm,orig=pred;alarm=np.asarray(alarm,bool);orig=np.asarray(orig,int)
 r=dict(base,method=method);time=e.time_ms;start=int(base['start_ms']);edge=alarm & ~np.r_[False,alarm[:-1]]
 first=np.flatnonzero(edge);post=np.flatnonzero(edge & (time>=start))
 ai=int(first[0]) if len(first) else -1;pi=int(post[0]) if len(post) else -1
 name=lambda v: be.ORIGINS[int(v).bit_length()-1] if v and not(v&(v-1)) else 'UNKNOWN'
 r.update(first_alarm_ms=int(time[ai]) if ai>=0 else -1,first_post_alarm_ms=int(time[pi]) if pi>=0 else -1,origin_at_alarm=name(orig[pi]) if pi>=0 else 'UNKNOWN',leading_at_alarm=name(orig[pi]) if pi>=0 else 'UNKNOWN',samples=len(time),alarm_samples=int(alarm.sum()),pre_alarm_samples=int(np.sum(alarm&(time<start))),propagation_samples=0,high_detection_conflict_samples=0,high_localization_conflict_samples=0)
 for field in ['mean_anomaly_ignorance','mean_origin_ignorance','mean_detection_conflict','mean_localization_conflict']:r[field]=0
 r['detected']=int(r['injected'] and pi>=0);r['false_alarm']=int(not r['injected'] and ai>=0);r['latency_ms']=int(time[pi])-start if r['detected'] else None
 loc=np.flatnonzero(alarm & (orig!=0) & (time>= (time[pi] if pi>=0 else np.inf)))
 r['first_localization_ms']=int(time[loc[0]]) if len(loc) else -1;r['first_origin']=name(orig[loc[0]]) if len(loc) else 'UNKNOWN'
 for i,o in enumerate(be.ORIGINS):r['alarm_'+o]=int(np.sum(alarm&(orig==(1<<i))))
 r['alarm_UNKNOWN']=int(np.sum(alarm&(orig==0)));r['wrong_localized_runtime_samples']=sum(r['alarm_'+o] for o in be.ORIGINS if o!=r['origin'])
 r['silent_plant']=int(r['injected'] and r['plant_manifestation']==1 and not r['detected'])
 return derived(r)

def candidates():
 return [('OR',None),('Plain DS',None)]+[(f'WS{w}_{k}',(weights,threshold)) for w,weights in enumerate(be.WEIGHTS) for k,threshold in enumerate(be.THRESHOLDS)]

def replay(e,models,selection=None):
 yield 'OR',be.simple_or(e);yield 'Plain DS',be.plain_ds(e)
 if selection is None:
  for name,param in candidates()[2:]:yield name,be.weighted_sum(e,*param)
  for name,model in models.items():yield name,be.svm_predict(e,model)
 else:
  yield 'Weighted Sum',be.weighted_sum(e,selection['weights'],selection['threshold'])
  yield 'SVM',be.svm_predict(e,models[selection['svm']])

def run(part):
 verify();assert not (B/(part+'_started')).exists()
 if part in ['VALIDATION','UNSEEN']:check_lock()
 specs=json.loads((B/'specs.json').read_text());ss=[s for s in specs if s['partition']==part]
 w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 os.environ['TRIPLEX_LOG']=str(w/'triplex.csv');os.environ['BENCHMARK_LOG']=str(w/'benchmark.csv')
 h.c.METHODS=['A0','A1'];h.c.command=lambda s,w:t.command(s,w,exe)
 read0=h.c.read;cache={}
 def read(p):
  rr=read0(p)
  if Path(p).name=='observations.csv':cache['obs']=rr
  return rr
 h.c.read=read
 models=pickle.loads((B/'models.pkl').read_bytes()) if part!='TRAIN' else None
 selection=json.loads((OUT/'selected_parameters.json').read_text()) if part in ['VALIDATION','UNSEEN'] else None
 training=[[],[]];labels=[];rows=[]
 (B/(part+'_started')).write_text(now())
 with (B/(part+'_checkpoint.jsonl')).open('w') as ck:
  for i,s in enumerate(ss):
   rr=h.c.execute(s,w,False);a=np.loadtxt(w/'benchmark.csv',delimiter=',');(w/'benchmark.csv').unlink();(w/'triplex.csv').unlink()
   obs=[o for o in cache['obs'] if h.prior.prior.active(s,int(o['time_ms']))];axis='pump_command' if s['model']=='pump_degraded' else 'fan_command'
   num=lambda x:float.fromhex(x) if '0x' in x.lower() else float(x)
   for r in rr:r.update(initially_excited=int(s['origin']=='ACTUATOR' and bool(obs) and num(obs[0][axis])>0),actuator_excited=int(s['origin']=='ACTUATOR' and any(num(o[axis])>0 for o in obs)))
   rr[0]['method']='C1 CURRENT';rr[1]['method']='C2 TRIPLEX'
   ev=[evidence(a,k) for k in [0,1]];assert np.array_equal(ev[0].time_ms,ev[1].time_ms)
   if part=='TRAIN':
    y=np.array([int(s['origin']!='NORMAL' and h.prior.prior.active(s,int(ms))) for ms in ev[0].time_ms])
    idx=[]
    for label in [0,1]:
     pool=np.flatnonzero(y==label)
     if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
    for arch in [0,1]:training[arch].append(ev[arch].features[idx])
    labels.append(y[idx])
   else:
    for arch,e in enumerate(ev):
     for name,pred in replay(e,models[arch],selection[str(arch)] if selection else None):rr.append(score(rr[arch],e,f'C{arch+1} '+name,pred))
   ck.write(json.dumps(rr)+'\n');ck.flush();rows.extend(rr)
   if (i+1)%50==0:print(part,i+1,'/',len(ss),flush=True)
 if part=='TRAIN':np.savez_compressed(B/'train_samples.npz',x0=np.concatenate(training[0]),x1=np.concatenate(training[1]),y=np.concatenate(labels))
 dump(B/(part+'_rows.json'),rows);(B/(part+'_complete')).write_text(now());verify();shutil.rmtree(w)
 if part!='TRAIN':h.write(OUT/(part.lower()+'_summary.csv'),[dict(method=m,**summary([r for r in rows if r['method']==m])) for m in sorted({r['method'] for r in rows})])

def fit():
 assert (B/'TRAIN_complete').exists() and not (B/'models.pkl').exists()
 # Local installed package API/version, isolated from production requirements.
 sys.path.insert(0,'/tmp/clo-ml-deps')
 import sklearn
 from sklearn.pipeline import make_pipeline
 from sklearn.preprocessing import StandardScaler
 from sklearn.svm import SVC
 a=np.load(B/'train_samples.npz');models=[]
 for arch in [0,1]:
  mm={}
  for name,kernel,c in [('SVM_linear_0.1','linear',.1),('SVM_linear_1','linear',1.),('SVM_rbf_1','rbf',1.)]:
   model=make_pipeline(StandardScaler(),SVC(kernel=kernel,C=c,gamma='scale',class_weight='balanced',cache_size=512))
   model.fit(a['x'+str(arch)],a['y']);mm[name]=model
   print('FIT',arch,name,len(a['y']),flush=True)
  models.append(mm)
 (B/'models.pkl').write_bytes(pickle.dumps(models,protocol=4))
 dump(OUT/'svm_fit_record.json',dict(sklearn=sklearn.__version__,numpy=np.__version__,samples=len(a['y']),class_counts=dict(zip(*[x.tolist() for x in np.unique(a['y'],return_counts=True)])),models_sha256=sha(B/'models.pkl')))

def select():
 assert (B/'CALIBRATION_complete').exists() and not (B/'VALIDATION_started').exists()
 rows=json.loads((B/'CALIBRATION_rows.json').read_text());selected={};records=[]
 for arch in [0,1]:
  prefix=f'C{arch+1} '
  def rank(name):
   st=summary([r for r in rows if r['method']==prefix+name]);records.append(dict(architecture=prefix.strip(),candidate=name,**st))
   return (st['benign_false_alarms'],-st['macro_coverage'],st['latency_p95_ms'] or 0)
  ws=min([x[0] for x in candidates()[2:]],key=rank)
  svm=min(['SVM_linear_0.1','SVM_linear_1','SVM_rbf_1'],key=rank)
  wi,ti=map(int,ws[2:].split('_'));selected[str(arch)]=dict(weights=be.WEIGHTS[wi],threshold=be.THRESHOLDS[ti],svm=svm)
 dump(OUT/'selected_parameters.json',selected);h.write(OUT/'calibration_selection.csv',records)
 paths=[Path(__file__),ROOT/'python/virtual_ecu/comparative_backends.py',OUT/'protocol.md',OUT/'selected_parameters.json',B/'models.pkl',OUT/'train_calibration_manifest.csv',OUT/'validation_manifest.csv']
 dump(B/'selection_lock.json',dict(utc=now(),files={str(p):sha(p) for p in paths}))
 print('SELECTED',selected,flush=True)

def check_lock():
 lock=json.loads((B/'selection_lock.json').read_text());assert all(sha(Path(p))==v for p,v in lock['files'].items())
 if (OUT/'method_freeze.json').exists():
  f=json.loads((OUT/'method_freeze.json').read_text());assert all(sha(Path(p))==v for p,v in f['files'].items())
 if (B/'unseen_lock.json').exists():
  f=json.loads((B/'unseen_lock.json').read_text());assert all(sha(Path(p))==v for p,v in f['files'].items())

def freeze_unseen():
 verify();check_lock();assert (B/'VALIDATION_complete').exists() and not (OUT/'method_freeze.json').exists()
 shutil.copy2(B/'models.pkl',OUT/'svm_models.pkl')
 f=json.loads((B/'selection_lock.json').read_text());f.update(frozen_utc=now(),frozen_commit=verify()['commit'],selection=json.loads((OUT/'selected_parameters.json').read_text()),training_case_count=1200,calibration_case_count=750,validation_case_count=750,
  methods={'OR':dict(version='1',threshold=.5,features='qualified provider evidence'), 'Weighted Sum':dict(version='1',parameters='selection per C1/C2',features='qualified provider evidence'),'Plain DS':dict(version='1',detection_threshold=.5,localization_threshold=.55,margin=.15,ignorance_limit=.5,temporal_fusion=False),'SVM':dict(version='1',parameters='selection per C1/C2',features=[*be.CHANNELS,*[c+'_available' for c in be.CHANNELS]],model_sha256=sha(OUT/'svm_models.pkl'),localization='NOT PROVIDED'),'CURRENT':dict(version='frozen pre-Triplex',core_sha256=sha(ROOT/'src/v7_3/clo_dsf_revised.c')),'TRIPLEX':dict(version=verify()['commit'],scientific_files=verify()['scientific_files'])})
 f['files'][str(OUT/'svm_models.pkl')]=sha(OUT/'svm_models.pkl');dump(OUT/'method_freeze.json',f)
 ss=design('UNSEEN');old=json.loads((B/'specs.json').read_text())
 for key in ['configuration_sha256','profile_semantic_sha256','seed']:assert not {s[key] for s in ss}&{s[key] for s in old}
 historical.OUT=OUT;historical.B=B;count=historical.historical_audit(ss)
 h.write(OUT/'unseen_manifest.csv',ss);(OUT/'unseen_manifest_hash.txt').write_text(sha(OUT/'unseen_manifest.csv')+'  unseen_manifest.csv\n')
 dump(B/'specs.json',old+ss)
 lock=dict(utc=now(),historical_sources=count,historical_overlap=0,benchmark_train_cal_validation_overlap=0,files={str(p):sha(p) for p in [OUT/'unseen_manifest.csv',OUT/'method_freeze.json',B/'specs.json']},seed_formula='u=10000+i;scenario1733000011+173u;B1793000021+179u;C1831000033+181u')
 dump(B/'unseen_lock.json',lock);dump(OUT/'unseen_lock.json',lock);print('UNSEEN LOCKED',sha(OUT/'unseen_manifest.csv'),flush=True)

if __name__=='__main__':
 action=sys.argv[1]
 if action=='setup':setup()
 elif action=='run':
  if sys.argv[2]!='TRAIN':sys.path.insert(0,'/tmp/clo-ml-deps')
  run(sys.argv[2])
 elif action=='fit':fit()
 elif action=='select':select()
 elif action=='freeze':freeze_unseen()
