#!/usr/bin/env python3
"""Grouped development only. Independent analytical predictor; retained core unchanged."""
import sys,os,json,hashlib,subprocess,inspect,gzip,time,pickle,collections,shutil,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_triplex_plus as r
import select_triplex_plus as previous
from scipy.optimize import lsq_linear
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
B=Path('/tmp/clo-heterogeneous');O=ROOT/'results/heterogeneous_observability_development';h=r.h
sha=r.sha

def dump(p,v):p.write_text(json.dumps(v,indent=2))
def verify():
 r.verify()
 if (B/'protected.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'protected.json').read_text()).items())
 if (O/'validation_lock.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((O/'validation_lock.json').read_text()).items())

def design():
 out=[]
 for i,t in enumerate(r.design()):
  s=dict(t);f=i//150;j=i%150
  s.update(run_id=f'hetero_{i:04}',profile=f'hetero_profile_{i:04}',group=f'hetero_family_{f}',seed=2201000011+i*223,reference_seed=2303000017+i*227,c_seed=2407000029+i*229)
  pp=json.loads(s['profile_json'])
  for k,p in enumerate(pp):
   p['ambient_temp_c']+=1.137+((f*7)%11)*.193+j*.000031
   p['engine_load']*=.947+((f*3)%7)*.009
   p['vehicle_speed_kph']+=3.319+i*.000037
   if j%6==0:p['vehicle_speed_kph']=[.7,82.3,34.7,.4,94.1][k]+(f%3)*.1
   if j%6==1:p['engine_load']*= [1.13,.81,1.08,.93,1.04][k]
  # Preserve cold-ambient, weak-load idle-actuator templates unchanged in kind.
  if s['origin']=='MEMORY':
   s['start_ms']=20300+f*300+(j%11)*100
   if s['behavior']!='permanent':s['duration_ms']=[100,200,300,500,1100,2100][(f+j)%6]
  elif s['origin']!='NORMAL':s['start_ms']+=700+(f%7)*100
  if s['origin']=='SENSOR_CONTROL':
   k=j-72;domain=['A','B','AB','C','ABC'][k%5];kind=['step','pulse','ramp'][(k//5+f)%3]
   mag=(2.93+f*.017 if kind=='ramp' else .49 if k%2==0 else -.73)
   s.update(domain=domain,sensor_chain=domain,kind=kind,model={'step':'sensor_bias','pulse':'sensor_interface_intermittent','ramp':'sensor_bias_ramp'}[kind],magnitude=mag,behavior='transient' if kind=='pulse' else 'permanent',duration_ms=[50,150,350,750][(k+f)%4] if kind=='pulse' else 0,sensor_ramp_rise_ms=[23700,43300,67700,89300][(f+k)%4] if kind=='ramp' else 0,start_ms=22931+f*257+k*173)
  s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(pp);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 return out

FRONT=r'''
#include "analytical_thermal.h"
typedef struct {runtime_observation_t o;double extra,c;unsigned checked;bool failed,valid,ambiguous,cvalid;} thermal_packet_t;
static FILE *thermal_packet_log,*thermal_input_log;
'''
REPLAY=r'''
static int thermal_replay(const char *packet_path,const char *output,const char *parameters){
 analytical_config_t p={0};FILE *f=fopen(parameters,"r");if(!f)return 2;
 if(fscanf(f,"%u %lf %lf %lf %lf",&p.model,&p.initial,&p.sigma,&p.bound,&p.coefficient[0])!=5)return 3;
 for(unsigned j=1;j<8;j++)if(fscanf(f,"%lf",&p.coefficient[j])!=1)return 4;fclose(f);
 if(final_config_read("results/cross_layer_safety_v7_3_dev/revised.cfg",&config))return 5;
 FILE *in=fopen(packet_path,"rb"),*out=fopen(output,"w");if(!in||!out)return 6;
 benchmark_log=fopen(getenv("BENCHMARK_LOG"),"w");if(!benchmark_log)return 7;
 clo_revised_t detector[4];for(unsigned j=0;j<4;j++)clo_revised_init(&detector[j]);
 analytical_state_t model={0};thermal_packet_t q;
 while(fread(&q,sizeof q,1,in)==1){
  analytical_input_t u={q.o.time_ms,q.o.engine_load,q.o.ambient_c,q.o.vehicle_speed_kph,q.o.pump_command,q.o.fan_command};
  analytical_thermal_step(&model,&p,&u);
  double values[3]={q.o.source_c,q.o.reference_c,q.c};bool valid[3]={q.o.source_valid,q.o.reference_valid&&!q.o.reference_failed,q.cvalid};bool ambiguous=false;
  double support=analytical_consistency(&model,&p,values,valid,&ambiguous);
  fprintf(out,"%u,%.17g,%.17g,%.17g,%.17g,%u",q.o.time_ms,model.temperature,p.sigma,p.bound,support,ambiguous);
  for(unsigned j=0;j<3;j++)fprintf(out,",%.17g",values[j]-model.temperature);
  for(unsigned j=0;j<4;j++){
   runtime_observation_t x=q.o;if(j&1){x.memory_check_ms=q.checked;x.memory_check_valid=q.valid;x.memory_check_failed=q.failed;}
   triplex_extra_strength=fmax(q.extra,j>=2?support:0);triplex_extra_ambiguous=q.ambiguous||(j>=2&&ambiguous);
   plus_arch=j;clo_triplex_core_step(&detector[j],&config,&x);clo_final_diagnostic(&detector[j].fusion.evidence,x.time_ms,3000);
   fprintf(out,",%u,%u,%.17g",detector[j].fusion.output.alarm,detector[j].fusion.output.estimated_origin,detector[j].fusion.output.anomaly_decision_score);
  }
  fprintf(out,"\n");
 }
 fclose(in);fclose(out);fclose(benchmark_log);return 0;
}
'''

def build(w):
 old=r.adapt
 def adapt(a):
  a=old(a);a=a.replace('static unsigned plus_arch;',FRONT+'\nstatic unsigned plus_arch;')
  needle='  final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);'
  extra=r'''
 if(j==1){
  if(!thermal_packet_log)thermal_packet_log=fopen(getenv("THERMAL_PACKET"),"wb");
  if(!thermal_input_log)thermal_input_log=fopen(getenv("THERMAL_INPUT"),"w");
  thermal_packet_t q={.o=o,.extra=triplex.strength,.c=triplex.aligned_c,.checked=plus_memory[1].checked_ms,.failed=plus_memory[1].failed,.valid=plus_memory[1].valid,.ambiguous=triplex.ambiguous,.cvalid=triplex.qualified};
  fwrite(&q,sizeof q,1,thermal_packet_log);
  fprintf(thermal_input_log,"%u,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%u,%u,%u,%u,%u\n",o.time_ms,(double)o.engine_load,(double)o.ambient_c,(double)o.vehicle_speed_kph,(double)o.pump_command,(double)o.fan_command,(double)o.source_c,(double)o.reference_c,triplex.aligned_c,triplex.qualified,triplex_detector.fusion.output.alarm,triplex_detector.fusion.output.estimated_origin,plus_detector[j].fusion.output.alarm,plus_detector[j].fusion.output.estimated_origin);
 }
'''
  a=a.replace(needle,needle+extra)
  a=a.replace('int main(int argc,char **argv)',REPLAY+'\nint main(int argc,char **argv)')
  a=a.replace(' int write=1;', ' if(argc==5&&!strcmp(argv[1],"--thermal-replay"))return thermal_replay(argv[2],argv[3],argv[4]);\n int write=1;')
  return a
 r.adapt=adapt
 # Link the new pure provider into the temporary experiment harness only.
 oldbuild=r.t.build
 source=inspect.getsource(oldbuild).replace("'src/v7_3/triplex_consistency.c']","'src/v7_3/triplex_consistency.c'] + ['src/v7_3/analytical_thermal.c']")
 # r.build inspects t.build; use its existing build source pipeline with source override.
 oldinspect=r.inspect.getsource
 r.inspect.getsource=lambda fn:source if fn is oldbuild else oldinspect(fn)
 try:return r.build(w)
 finally:r.adapt=old;r.inspect.getsource=oldinspect

def setup():
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='a340ca5cf0473d7dc572f7cd63e44fbc25b175a7'
 verify();assert not (B/'specs.json').exists();B.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
 protected={str(p):sha(p) for parent in ['src','include','scripts','python','tests','presets'] for p in (ROOT/parent).rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'heterogeneous' not in p.name and 'analytical_thermal' not in p.name}
 dump(B/'protected.json',protected);ss=design();r.historical.OUT=O;r.historical.B=B;r.historical.historical_audit(ss)
 dump(B/'specs.json',ss);h.write(O/'campaign_manifest.csv',ss)
 (O/'protocol.md').write_text('''# Heterogeneous observability development: preregistration
3150 new configurations, 21 disjoint profile families. TRAIN1500 (1200fault300benign), CALIBRATION750 (600fault150benign), VALIDATION900 (720fault180benign). Each family24 faults per origin plus30benign. Sensor24 cells rotate A/B/AB/C/ABC and step/pulse/ramp, signed steps/pulses including +0.49 C. Preserve unexcited actuator templates; never rebalance using outcomes. Full historical profile/configuration/seed overlap audit before execution. All cases share unchanged physical simulations.
A0 exact Triplex; A1 only existing 250ms (300/200ms) memory; A2 only analytical; A3 both. No retained sources edited. Fit model parameters on benign TRAIN only. Predefined models P0: constant/load/speed/ambient coupling/combined pump+fan; P1 adds load-speed interaction; P2 separate pump/fan (no interaction). Constrained least squares on successive benign primary acquisitions estimates derivatives. Fixed initialization is mean of benign TRAIN first primary observations, never a runtime sensor read. Choose minimum open-loop TRAIN benign RMSE (tie fewer terms). No fault data in model selection. CAL only computes common model+measurement RMS uncertainty and maximum absolute residual bound across all three members, with a fixed 5% margin and 0.02C quantization floor. Qualification requires1000ms startup and valid all-member readouts. No outcome-tuned operating-region thresholds. One evidence=clamp(max absolute normalized member residual minus1,0,1), provided one member agrees with bound, or coherent all-member residual (UNKNOWN origin unless prior direct non-sensor origin). Mixed all-member disagreement=>ignorance. MAX with correlated sensor evidence, classical DS and global thresholds unchanged. Wide calibrated bounds reduce sensitivity honestly.
Register and freeze source/model/SVM hashes before validation. Evaluate untouched benign validation first and write error/regime/coverage results before fault evaluation. No recalibration after validation. Invalid benign gate rejects provider but complete registered comparisons for transparent reporting. SVM StandardScaler+SVC TRAIN fit, select linearC0.1/linearC1/RBFC1 by CAL balanced run accuracy; zero decision boundary. Features qualified six streams+availability+causal1s means/maxima and exact analytical residuals, normalized residuals, prediction, uncertainty/bound, availability and five non-coolant inputs. No labels/truth fed to inference.
Promotion requires >=93.5% overall,<=1%benign,>=99%plant,zero wrong confident origin runs,no timing/comm/effective-memory/AB regression. Report raw SVM difference. Analytical gain must>=1pp unless material safety gain. Do not reselect after outcomes. Compact summaries and at most8traces (planned0). No unseen/commit/push. CIs/McNemar descriptive for grouped deterministic campaigns.
Cold coverage means cold-ambient startup under the unchanged simulator's fixed warm-engine initialization. There is no cold-soak initialization API; do not pretend these are independent cold-soak tests. RPM changes occur through existing speed-to-RPM scenario mapping; RPM is not an additional predictor input. External airflow and other unmeasured effects remain modeling uncertainty, not hidden inference inputs.
''')
 dump(O/'registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),manifest_sha256=sha(O/'campaign_manifest.csv'),protocol_sha256=sha(O/'protocol.md'),utc=r.now()))
 print('REGISTERED3150',flush=True)

def collect(part,benign_only=False):
 verify();ss=[s for s in json.loads((B/'specs.json').read_text()) if s['partition']==part and (not benign_only or s['origin']=='NORMAL')]
 if part=='VALIDATION' and not benign_only:ss=[s for s in ss if s['origin']!='NORMAL'];assert (O/'benign_model_validation.csv').exists()
 tag=part+('_BENIGN' if benign_only else '');assert not (B/(tag+'_started')).exists();(B/(tag+'_started')).write_text(r.now())
 w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for key,name in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('THERMAL_PACKET','packet.bin'),('THERMAL_INPUT','input.csv')]:os.environ[key]=str(w/name)
 os.environ['PLUS_HOST_MODE']='2';h.c.METHODS=['A0','M250'];h.c.command=lambda s,w:r.t.command(s,w,exe)
 rows=[];tapes=B/'tapes';tapes.mkdir(exist_ok=True)
 read0=h.c.read;cache={}
 def read(p):
  rr=read0(p)
  if Path(p).name=='observations.csv':cache['obs']=rr
  return rr
 h.c.read=read
 for i,s in enumerate(ss):
  rr=h.c.execute(s,w,False);a=np.loadtxt(w/'input.csv',delimiter=',');ev=r.bench.evidence(np.loadtxt(w/'benchmark.csv',delimiter=','),2)
  active=[o for o in cache['obs'] if h.prior.prior.active(s,int(o['time_ms']))];axis='pump_command' if s['model']=='pump_degraded' else 'fan_command';num=lambda v:float.fromhex(v) if '0x' in str(v) else float(v)
  for row in rr:row.update(initially_excited=int(s['origin']=='ACTUATOR' and bool(active) and num(active[0][axis])>0),actuator_excited=int(s['origin']=='ACTUATOR' and any(num(o[axis])>0 for o in active)))
  rows.extend(rr);np.savez_compressed(tapes/(s['run_id']+'.npz'),inputs=a,strength=ev.strength,available=ev.available,subset=ev.origin_subset)
  (tapes/(s['run_id']+'.bin.gz')).write_bytes(gzip.compress((w/'packet.bin').read_bytes(),mtime=0))
  for name in ['packet.bin','input.csv','benchmark.csv','plus_meta.csv','triplex.csv']:(w/name).unlink()
  if (i+1)%100==0:print(tag,i+1,'/',len(ss),flush=True)
 h.c.read=read0;dump(B/(tag+'_rows.json'),rows);verify();print(tag,'COMPLETE',flush=True)

def parameters_text(p):
 (B/'parameters.txt').write_text(' '.join(map(str,[p['model'],p['initial'],p['sigma'],p['bound'],*p['coefficient']])))
def predict(a,beta,initial):
 out=np.empty(len(a));out[0]=initial
 for i in range(1,len(a)):
  _,l,amb,v,_,_=a[i,:6];p,f=a[i-1,4:6];x=np.array([1,l,v,out[i-1]-amb,p+f,l*v,p,f]);out[i]=out[i-1]+(a[i,0]-a[i-1,0])*.001*np.dot(beta,x)
 return out

def identify():
 verify();ss=json.loads((B/'specs.json').read_text());train=[x for x in ss if x['partition']=='TRAIN' and x['origin']=='NORMAL'];cal=[x for x in ss if x['partition']=='CALIBRATION' and x['origin']=='NORMAL']
 arrays=[np.load(B/'tapes'/(s['run_id']+'.npz'))['inputs'] for s in train]
 initial=float(np.mean([a[0,6] for a in arrays]));xx=[];yy=[]
 for a in arrays:
  l,amb,v,_,_=a[1:,1:6].T;p,f=a[:-1,4:6].T;xx.append(np.column_stack((np.ones(len(l)),l,v,a[:-1,6]-amb,p+f,l*v,p,f)));yy.append(np.diff(a[:,6])/.1)
 x=np.concatenate(xx);y=np.concatenate(yy);models=[]
 for model,cols in enumerate([[0,1,2,3,4],[0,1,2,3,4,5],[0,1,2,3,6,7]]):
  lower=np.array([0,0,-np.inf,-10,-np.inf,-np.inf,-np.inf,-np.inf])[cols];upper=np.array([np.inf,np.inf,0,-1e-6,0,np.inf,0,0])[cols]
  beta=np.zeros(8);beta[cols]=lsq_linear(x[:,cols],y,bounds=(lower,upper)).x
  err=np.concatenate([a[:,6]-predict(a,beta,initial) for a in arrays]);models.append(dict(model=model,coefficient=beta.tolist(),initial=initial,train_rmse=float(np.sqrt(np.mean(err**2)))))
 best=dict(min(models,key=lambda v:v['train_rmse']));err=[]
 for spec in cal:
  a=np.load(B/'tapes'/(spec['run_id']+'.npz'))['inputs'];p=predict(a,best['coefficient'],initial);err.extend((a[a[:,9]>0,6:9]-p[a[:,9]>0,None]).ravel())
 err=np.array(err);best.update(sigma=float(np.sqrt(np.mean(err**2))),bound=float(np.max(np.abs(err))*1.05+.02),candidates=models,identification='BENIGN TRAIN only; bound BENIGN CAL only')
 dump(O/'predictor_parameters.json',best);parameters_text(best);print('IDENTIFIED',best,flush=True)

def replay(part):
 verify();tag=part;rows=json.loads((B/(tag+'_rows.json')).read_text());base={x['run_id']:x for x in rows if x['method']=='M250'};out=[]
 w=B/'work';exe=w/'compare';os.environ['BENCHMARK_LOG']=str(w/'replay_evidence.csv')
 for i,(rid,b) in enumerate(base.items()):
  (w/'packet.bin').write_bytes(gzip.decompress((B/'tapes'/(rid+'.bin.gz')).read_bytes()))
  subprocess.run([str(exe),'--thermal-replay',str(w/'packet.bin'),str(w/'replay.csv'),str(B/'parameters.txt')],check=True,cwd=ROOT)
  a=np.loadtxt(w/'replay.csv',delimiter=',');raw=np.loadtxt(w/'replay_evidence.csv',delimiter=',');ev=[r.bench.evidence(raw,k) for k in range(4)]
  original=np.load(B/'tapes'/(rid+'.npz'));inp=original['inputs']
  assert np.array_equal(a[:,9].astype(int),inp[:,10].astype(int));assert np.array_equal(a[:,12].astype(int),inp[:,12].astype(int));assert np.array_equal(a[:,10].astype(int),inp[:,11].astype(int));assert np.array_equal(a[:,13].astype(int),inp[:,13].astype(int))
  for k in range(4):out.append(r.bench.score(b,ev[k],f'A{k}',(a[:,9+k*3].astype(bool),a[:,10+k*3].astype(int)>>1)))
  extra=np.column_stack((a[:,6:9],a[:,6:9]/a[:,3,None],a[:,1:4],inp[:,9],inp[:,1:6]))
  features=np.column_stack((previous.features(ev[3]),extra));np.savez_compressed(B/'tapes'/(rid+'_replay.npz'),features=features,model=a,values=ev[3].strength,available=ev[3].available,subsets=ev[3].origin_subset,time=ev[3].time_ms)
  if (i+1)%150==0:print('REPLAY',tag,i+1,flush=True)
 dump(B/(tag+'_scored.json'),out)
 for name in ['packet.bin','replay.csv','replay_evidence.csv']:(w/name).unlink(missing_ok=True)
 print('REPLAY COMPLETE',tag,flush=True)

def svm():
 from sklearn.metrics import balanced_accuracy_score
 ss={x['run_id']:x for x in json.loads((B/'specs.json').read_text())};train=[x for x in ss.values() if x['partition']=='TRAIN'];xs=[];ys=[]
 for spec in train:
  a=np.load(B/'tapes'/(spec['run_id']+'_replay.npz'));tm=a['time'];y=np.array([spec['origin']!='NORMAL' and (h.prior.prior.active(spec,int(t)) or h.prior.prior.active(spec,max(0,int(t)-99))) for t in tm]);idx=[]
  for c in [0,1]:
   pool=np.flatnonzero(y==c)
   if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
  xs.append(a['features'][idx]);ys.append(y[idx])
 x=np.concatenate(xs);y=np.concatenate(ys);models=[];scores=[]
 base=[z for z in json.loads((B/'CALIBRATION_scored.json').read_text()) if z['method']=='A3']
 for name,kernel,c in [('linear01','linear',.1),('linear1','linear',1.),('rbf1','rbf',1.)]:
  model=make_pipeline(StandardScaler(),SVC(kernel=kernel,C=c,class_weight='balanced',cache_size=512));model.fit(x,y);rr=[]
  for b in base:
   a=np.load(B/'tapes'/(b['run_id']+'_replay.npz'));e=r.be.Evidence(a['time'],a['values'],a['available'],a['subsets']);pred=model.predict(a['features']).astype(bool);rr.append(r.bench.score(b,e,name,(pred,np.zeros(len(pred),int))))
  st=r.bench.summary(rr);models.append(model);scores.append(dict(method=name,**st));print('SVM',name,st['detected'],st['benign_false_alarms'],flush=True)
 best=max(range(3),key=lambda i:(.5*(scores[i]['coverage']+1-scores[i]['benign_false_alarm_rate']),scores[i]['coverage'],-i));(O/'fair_svm.pkl').write_bytes(pickle.dumps(models[best],protocol=4));h.write(O/'svm_calibration.csv',scores)
 paths=[Path(__file__),ROOT/'include/analytical_thermal.h',ROOT/'src/v7_3/analytical_thermal.c',O/'predictor_parameters.json',O/'fair_svm.pkl',O/'protocol.md',O/'campaign_manifest.csv',ROOT/'tests/test_analytical_thermal.py',ROOT/'scripts/report_heterogeneous_observability.py',ROOT/'scripts/benchmark_heterogeneous_observability.py',O/'predictor_definition.md',O/'analytical_independence_test.md']
 dump(O/'validation_lock.json',{str(p):sha(p) for p in paths});print('LOCKED',scores[best]['method'],flush=True)

if __name__=='__main__':
 action=sys.argv[1]
 if action=='setup':setup()
 elif action=='collect':collect(sys.argv[2],len(sys.argv)>3)
 elif action=='identify':identify()
 elif action=='replay':replay(sys.argv[2])
 elif action=='svm':svm()
