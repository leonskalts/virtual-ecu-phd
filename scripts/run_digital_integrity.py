#!/usr/bin/env python3
"""Compact protected-driver-boundary development using the existing framework."""
import os,sys,json,hashlib,subprocess,inspect,base64,zlib,pickle,math,collections,csv,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_dynamic_consensus as d
import select_dynamic_consensus as sel
import report_comparative_benchmark as common
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
B=Path('/tmp/clo-digital-integrity');O=ROOT/'results/digital_integrity_development';h=d.h
sha=d.sha;dump=d.dump
BOUNDARY=r'''
#include "digital_sensor_integrity.h"
static FILE *di_log;
typedef struct {ecu_state_t *owner;di_witness_t witness[3];di_record_t envelope[3];unsigned status[3],until[3],bad,available;} di_bank_t;
static di_bank_t di_banks[2],*di_producer;
static di_bank_t *di_bank(ecu_state_t *s){
 for(unsigned i=0;i<2;i++)if(di_banks[i].owner==s)return &di_banks[i];
 for(unsigned i=0;i<2;i++)if(!di_banks[i].owner){di_banks[i].owner=s;return &di_banks[i];}
 abort();
}
static void di_source(ecu_state_t *s){di_producer=di_bank(s);di_publish(&di_producer->witness[0],&di_producer->envelope[0],0,s->sensors.coolant_source_c,s->sensors.coolant_source_ms);}
void __real_redundant_temperature_sample(redundant_temperature_t *,unsigned,float);
void __wrap_redundant_temperature_sample(redundant_temperature_t *s,unsigned ms,float physical){
 __real_redundant_temperature_sample(s,ms,physical);
 if(di_producer&&s->valid)di_publish(&di_producer->witness[1],&di_producer->envelope[1],1,s->value_c,s->sample_ms);
}
bool __real_diagnostic_temperature_sample(diagnostic_temperature_t *,unsigned,float);
bool __wrap_diagnostic_temperature_sample(diagnostic_temperature_t *s,unsigned ms,float physical){
 bool acquired=__real_diagnostic_temperature_sample(s,ms,physical);
 if(di_producer&&acquired&&s->output.valid)di_publish(&di_producer->witness[2],&di_producer->envelope[2],2,s->output.value_c,s->output.sample_ms);
 return acquired;
}
static void di_legal(unsigned ch,float offset){if(di_producer)di_transform(&di_producer->witness[ch],&di_producer->envelope[ch],offset);}
static void di_finish(ecu_state_t *s){
 di_bank_t *b=di_bank(s);float v[3]={s->sensors.coolant_source_c,s->temperature_reference.value_c,diagnostic_c.output.value_c};
 unsigned ms[3]={s->sensors.coolant_source_ms,s->temperature_reference.sample_ms,diagnostic_c.output.sample_ms};b->bad=0;b->available=0;
 for(unsigned j=0;j<3;j++){
  if(!b->witness[j].valid)continue;b->available|=1U<<j;
  b->status[j]=di_verify(&b->witness[j],&b->envelope[j],v[j],ms[j]);
  if(b->status[j]){b->bad|=1U<<j;b->until[j]=s->time.time_ms+300;}
 }
}
static double di_strength(ecu_state_t *s,unsigned now){di_bank_t *b=di_bank(s);for(unsigned j=0;j<3;j++)if(b->until[j]&&now<b->until[j])return 1;return 0;}
'''
def verify():
 if (B/'protected.json').exists():
  for p,v in json.loads((B/'protected.json').read_text()).items():assert sha(Path(p))==v,p
 if (B/'lock.json').exists():
  for p,v in json.loads((B/'lock.json').read_text()).items():assert sha(Path(p))==v,p

def build(w):
 oldrun=subprocess.run
 def run(cmd,*args,**kw):
  if isinstance(cmd,list) and cmd[0]=='gcc':
   if '-c' in cmd:
    path=Path(cmd[cmd.index('-c')+1])
    if path.name=='adapter.c':
     s=path.read_text();start=s.index('static int dc_replay(');end=s.index('int main(',start);s=s[:start]+s[end:]
     s=s.replace(' if(argc==5&&!strcmp(argv[1],"--dc-replay"))return dc_replay(argv[2],argv[3],argv[4]);','')
     s=s.replace('static const char *names',BOUNDARY+'\nstatic const char *names',1)
     s=s.replace(' __real_sensors_step(state);',' di_producer=di_bank(state);\n __real_sensors_step(state);\n di_source(state);')
     s=s.replace(' r->value_c+=amount;',' r->value_c+=amount;di_legal(1,amount);')
     s=s.replace(' if(sensor_jitter==0 && sensor_drift==0)return;',' if(sensor_jitter==0 && sensor_drift==0){di_finish(state);return;}')
     s=s.replace(' state->sensors.coolant_source_c+=sensor_variation(state->sensors.coolant_source_ms);',' state->sensors.coolant_source_c+=sensor_variation(state->sensors.coolant_source_ms);\n di_legal(0,sensor_variation(state->sensors.coolant_source_ms));')
     s=s.replace(' state->sensors.coolant_temp_meas_c+=sensor_variation(state->sensors.coolant_sensor_last_update_ms);',' state->sensors.coolant_temp_meas_c+=sensor_variation(state->sensors.coolant_sensor_last_update_ms);\n di_finish(state);')
     s=s.replace('  plus_arch=0;double begin=cpu();','  dc_mass=dc_origin=dc_discount=0;plus_arch=0;double begin=cpu();')
     s=s.replace('  if(memory_index[j]){','  if(j==99&&memory_index[j]){')
     s=s.replace('  plus_arch=j+1;double begin=cpu();','  dc_mass=dc_origin=di_strength(state,o.time_ms);plus_arch=j+1;double begin=cpu();')
     needle='  dc_packet_t q={';pos=s.index(needle); # preserve existing input/evidence accounting, but do not retain packet traces
     s=s.replace('fwrite(&q,sizeof q,1,dc_packet_log);','')
     s=s.replace('  if(!dc_packet_log)dc_packet_log=fopen(getenv("DC_PACKET"),"wb");','')
     pos=s.index('  fprintf(dc_input_log,');end=s.index('\n }',pos)
     s=s[:end]+r'''
  if(!di_log)di_log=fopen(getenv("DI_LOG"),"w");di_bank_t *ib=di_bank(state);
  fprintf(di_log,"%u,%u,%u,%u,%u,%u,%.0f\n",o.time_ms,ib->available,ib->bad,ib->status[0],ib->status[1],ib->status[2],di_strength(state,o.time_ms));
'''+s[end:]
     path.write_text(s)
    elif path.name=='extended.c':
     s=path.read_text();start=s.index('    bool dc_clean=');end=s.index('    s->evidence.strength[3] = fmax',start)
     s=s[:start]+'    local=fmax(local,dc_mass);origin_local=fmax(origin_local,dc_origin);\n'+s[end:];path.write_text(s)
   elif '-o' in cmd and str(w/'compare') in cmd:
    obj=w/'digital_sensor_integrity.o';oldrun(['gcc','-std=c11','-O2','-Iinclude','-c','src/v7_3/digital_sensor_integrity.c','-o',str(obj)],check=True)
    cmd=[v for v in cmd if not v.endswith('/dynamic_consensus.o')]+[str(obj),'-Wl,--wrap=redundant_temperature_sample','-Wl,--wrap=diagnostic_temperature_sample']
  return oldrun(cmd,*args,**kw)
 subprocess.run=run
 try:return d.build(w)
 finally:subprocess.run=oldrun

def design():
 ss=d.design()
 for i,s in enumerate(ss):
  s.update(run_id=f'di_{i:04}',profile=f'di_profile_{i:04}',group=s['group'].replace('dc_','di_'),seed=120100003+i*269,reference_seed=220300007+i*271,c_seed=320700011+i*277)
  pp=json.loads(s['profile_json'])
  for p in pp:p['ambient_temp_c']+=.493+i*.0000031;p['engine_load']*=1.007+(i//150%3)*.003;p['vehicle_speed_kph']+=.937+i*.000007
  s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(pp)
  if s['origin']!='NORMAL':s['start_ms']+=103 if s['origin']=='SENSOR_CONTROL' else 100
  if s['origin']=='SENSOR_CONTROL':s['magnitude']*=1.017;s['sensor_ramp_rise_ms']+=311 if s['kind']=='ramp' else 0
  s['c_phase_ms']=(s['c_phase_ms']+4)%100
  s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
 return ss

def setup():
 B.mkdir(exist_ok=True);O.mkdir(exist_ok=True);assert not (B/'specs.json').exists()
 paths=[p for root in ['src','include','scripts','python','tests','presets','results'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'digital_integrity' not in str(p) and 'digital_sensor' not in str(p)]
 dump(B/'protected.json',{str(p):sha(p) for p in paths});ss=design()
 d.r.historical.OUT=B;d.r.historical.B=B;count=d.r.historical.historical_audit(ss)
 # Explicitly include prior dynamic embedded manifest, independent of legacy discovery.
 hist=json.loads((ROOT/'results/dynamic_consensus_development/calibration.json').read_text())['manifest'];assert not ({s['configuration_sha256'] for s in ss}&{s['configuration_sha256'] for s in hist});assert not ({s['profile_semantic_sha256'] for s in ss}&{s['profile_semantic_sha256'] for s in hist})
 dump(B/'specs.json',ss);h.write(O/'campaign_manifest.csv',ss);shutil.copy2(B/'historical_overlap_audit.csv',O/'overlap_audit.csv');shutil.copy2(ROOT/'scripts/digital_integrity_protocol.md',O/'protocol.md')
 dump(O/'registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),utc=d.r.now(),manifest_sha256=sha(O/'campaign_manifest.csv'),protocol_sha256=sha(O/'protocol.md'),historical_sources=count,explicit_dynamic_cases=len(hist),overlap=0));verify();print('REGISTERED',len(ss),flush=True)

def collect(part):
 verify();assert not (B/(part+'_started')).exists()
 if part=='VALIDATION':assert (B/'lock.json').exists()
 (B/(part+'_started')).write_text(d.r.now());ss=[s for s in json.loads((B/'specs.json').read_text()) if s['partition']==part]
 if part=='SEEN90':
  p=json.loads((ROOT/'results/dynamic_consensus_development/calibration.json').read_text());mm={s['run_id']:s for s in p['manifest']};rr=json.loads(zlib.decompress(base64.b85decode(p['case_metrics']['data'])));ss=[mm[x['run_id']] for x in rr if x['method']=='A0' and not x['detected'] and mm[x['run_id']]['partition']=='VALIDATION' and mm[x['run_id']]['origin']=='SENSOR_CONTROL' and mm[x['run_id']]['kind'] in ['step','pulse']];assert len(ss)==90
 w=B/('work_'+part);w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for k,v in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('DC_INPUT','input.csv'),('DI_LOG','integrity.csv')]:os.environ[k]=str(w/v)
 os.environ['PLUS_HOST_MODE']='2';h.c.METHODS=['A0','M250','M2'];h.c.command=lambda s,w:d.r.t.command(s,w,exe)
 rows=[];(B/'tapes').mkdir(exist_ok=True)
 for i,s in enumerate(ss):
  rr=h.c.execute(s,w,False);a=np.loadtxt(w/'input.csv',delimiter=',');it=np.loadtxt(w/'integrity.csv',delimiter=',');assert np.array_equal(a[:,0],it[:,0]);e=d.bench.evidence(np.loadtxt(w/'benchmark.csv',delimiter=','),6)
  for row in rr:row['method']={'A0':'A0','M250':'A1','M2':'A2'}[row['method']];row['integrity_observed']=int(np.any(it[:,2]));row['integrity_samples']=int(np.count_nonzero(it[:,2]))
  rows.extend(rr);target=np.array([s['origin']!='NORMAL' and (h.prior.prior.active(s,int(ms)) or h.prior.prior.active(s,max(0,int(ms)-99))) for ms in a[:,0]])
  np.savez_compressed(B/'tapes'/(s['run_id']+'.npz'),input=a,integrity=it[:,1:],values=e.strength,available=e.available,subset=e.origin_subset,target=target)
  for name in ['input.csv','integrity.csv','benchmark.csv','triplex.csv','plus_meta.csv']:(w/name).unlink()
  if (i+1)%150==0:print(part,i+1,'/',len(ss),flush=True)
 dump(B/(part+'_rows.json'),rows);verify();print('COMPLETE',part,flush=True)

def dataset(part):
 for row in json.loads((B/(part+'_rows.json')).read_text()):
  if row['method']=='A0':yield row,np.load(B/'tapes'/(row['run_id']+'.npz'))
def evidence(a):return d.r.be.Evidence(a['input'][:,0].astype(int),a['values'],a['available'],a['subset'])
def features(a):return np.column_stack((d.prior.features(evidence(a)),a['input'][:,1:4],a['input'][:,13:21],a['integrity']))
def svm():
 verify();xx=[];yy=[]
 for row,a in dataset('TRAIN'):
  x=features(a);y=a['target'];idx=[]
  for label in [0,1]:
   pool=np.flatnonzero(y==label)
   if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
  xx.append(x[idx]);yy.append(y[idx])
 x=np.concatenate(xx);y=np.concatenate(yy);models={};records=[]
 for kernel,C in [('linear',.1),('linear',1.),('rbf',1.)]:
  name=f'{kernel}_{C}';model=make_pipeline(StandardScaler(),SVC(kernel=kernel,C=C,gamma='scale',class_weight='balanced',cache_size=512));model.fit(x,y);models[name]=model;records.append(dict(name=name,frames=len(y),features=x.shape[1],support_vectors=len(model[1].support_)));print('FIT',records[-1],flush=True)
 results={k:[] for k in models};maxima={k:[] for k in models}
 for i,(row,a) in enumerate(dataset('CALIBRATION')):
  x=features(a)
  for k,model in models.items():
   margin=d.ml.margin(model,x);results[k].append(d.bench.score(row,evidence(a),k,(margin>0,np.zeros(len(margin),int))))
   if row['origin']=='NORMAL':maxima[k].append(float(margin.max()))
  if (i+1)%150==0:print('SVM CAL',i+1,flush=True)
 summaries={k:d.bench.summary(rr) for k,rr in results.items()};ks=list(models);chosen=max(ks,key=lambda k:(.5*(summaries[k]['coverage']+1-summaries[k]['benign_false_alarm_rate']),summaries[k]['coverage'],-ks.index(k)))
 selection=dict(model=chosen,**sel.maxima_level(maxima[chosen],.01));(B/'svm.pkl').write_bytes(pickle.dumps(models[chosen],protocol=4));dump(O/'svm_selection.json',dict(selection=selection,candidates=summaries,training=records));print(selection,flush=True)
 paths=[ROOT/'include/digital_sensor_integrity.h',ROOT/'src/v7_3/digital_sensor_integrity.c',ROOT/'scripts/run_digital_integrity.py',ROOT/'scripts/digital_integrity_protocol.md',ROOT/'tests/test_digital_sensor_integrity.py',B/'specs.json',B/'svm.pkl',O/'svm_selection.json',O/'protocol.md',O/'registration.json',O/'overlap_audit.csv',O/'campaign_manifest.csv',ROOT/'scripts/report_digital_integrity.py',ROOT/'scripts/regress_digital_integrity.py',ROOT/'scripts/finalize_digital_integrity.py',B/'failure_matrix.c'];dump(B/'lock.json',{str(p):sha(p) for p in paths});print('LOCKED BEFORE VALIDATION',flush=True)

def evaluate(part):
 verify();rr=json.loads((B/(part+'_rows.json')).read_text());model=pickle.loads((B/'svm.pkl').read_bytes());selection=json.loads((O/'svm_selection.json').read_text())['selection'];out=list(rr)
 for i,(row,a) in enumerate(dataset(part)):
  margin=d.ml.margin(model,features(a))
  for t,name in [(0,'default'),(selection['threshold'],'CAL1')]:out.append(d.bench.score(row,evidence(a),'SVM-INT '+name,(margin>t,np.zeros(len(margin),int))))
  if (i+1)%300==0:print('EVALUATE',part,i+1,flush=True)
 dump(B/(part+'_evaluated.json'),out)
if __name__=='__main__':
 {'setup':setup,'svm':svm}.get(sys.argv[1],lambda:globals()[sys.argv[1]](sys.argv[2]))()
