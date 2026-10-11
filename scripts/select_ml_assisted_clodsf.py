#!/usr/bin/env python3
"""CAL-only confidence, alpha/gate and standalone operating-point selection."""
import sys,json,pickle,ctypes,subprocess,gzip,collections
from pathlib import Path
import run_ml_assisted_clodsf as d
import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
B=d.B;O=d.O;h=d.h;bench=d.bench
_lib=None

def masses(x,qualified,time,q,alpha,gate):
 global _lib
 if _lib is None:
  code='''#include "ml_sensor_weak.h"
void ml_series(unsigned n,const double *x,const unsigned *time,const unsigned char *qual,const double *q,double alpha,unsigned gate,double *out){ml_sensor_state_t s={0};ml_sensor_config_t c={alpha,gate};for(unsigned i=0;i<n;i++){ml_sensor_input_t v={.time_ms=time[i],.physical=x[i*12],.qualified=qual[i]};for(unsigned k=0;k<12;k++)v.value[k]=x[i*12+k];out[i]=ml_sensor_mass(&s,&c,&v,q[i]);}}
'''
  (B/'series.c').write_text(code);subprocess.run(['gcc','-std=c11','-O2','-shared','-fPIC','-Iinclude',str(B/'series.c'),'src/v7_3/ml_sensor_weak.c','-lm','-o',str(B/'provider.so')],check=True)
  _lib=ctypes.CDLL(str(B/'provider.so'));dbl=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');uint=np.ctypeslib.ndpointer(dtype=np.uint32,flags='C_CONTIGUOUS');byte=np.ctypeslib.ndpointer(dtype=np.uint8,flags='C_CONTIGUOUS');_lib.ml_series.argtypes=[ctypes.c_uint,dbl,uint,byte,dbl,ctypes.c_double,ctypes.c_uint,dbl]
 out=np.empty(len(q));_lib.ml_series(len(q),np.ascontiguousarray(x),np.ascontiguousarray(time,dtype=np.uint32),np.ascontiguousarray(qualified,dtype=np.uint8),np.ascontiguousarray(q),alpha,gate,out);return out

def evidence(a):return d.old.be.Evidence(a['time'],a['values'],a['available'],np.tile([2,4,1,8,16,31],(len(a['time']),1)))
def packet(row):
 (B/'work'/'packet.bin').write_bytes(gzip.decompress((B/'tapes'/(row['run_id']+'.bin.gz')).read_bytes()))
def core(row,a,mass,name):
 w=B/'work';np.savetxt(w/'mass.txt',mass,fmt='%.17g');subprocess.run([str(w/'compare'),'--ml-replay',str(w/'packet.bin'),str(w/'mass.txt'),str(w/'scored.csv')],check=True,cwd=d.ROOT)
 v=np.loadtxt(w/'scored.csv',delimiter=',');result=bench.score(row,evidence(a),name,(v[:,1].astype(bool),v[:,2].astype(int)>>1));return result,v

def standalone(row,a,margin,threshold,name):return bench.score(row,evidence(a),name,(margin>threshold,np.zeros(len(margin),int)))

def calibrate():
 d.verify();assert not (O/'calibration.json').exists();training=json.loads((O/'model_training.json').read_text());eligible=[x['type'] for x in training if x['target']=='provider' and x['compact']]
 fitted={};reliability=[]
 for kind in eligible:
  xx=[];yy=[]
  for row,a in d.dataset('CALIBRATION'):
   pool=np.flatnonzero(a['qualified']);idx=pool[np.unique(np.linspace(0,len(pool)-1,min(16,len(pool)),dtype=int))] if len(pool) else []
   if len(idx):xx.extend(np.load(B/'tapes'/(row['run_id']+'_margins.npz'))['provider_'+kind][idx]);yy.extend(a['sensor_target'][idx])
  x=np.array(xx);y=np.array(yy);platt=LogisticRegression(C=1e6,solver='lbfgs').fit(x[:,None],y);slope=float(platt.coef_[0,0]);intercept=float(platt.intercept_[0]);
  if slope<0:slope=0.;intercept=float(np.log(np.clip(y.mean(),1e-12,1-1e-12)/(1-np.clip(y.mean(),1e-12,1-1e-12)))) # Nondecreasing Platt boundary solution.
  q=expit(slope*x+intercept);fitted[kind]=dict(slope=slope,intercept=intercept,calibration_frames=len(y),positive_frames=int(y.sum()),brier=float(brier_score_loss(y,q)))
  for lo in np.linspace(0,.9,10):
   take=(q>=lo)&(q<lo+.1+1e-12);reliability.append(dict(model=kind,low=float(lo),frames=int(take.sum()),mean_q=float(q[take].mean()) if take.any() else None,observed=float(y[take].mean()) if take.any() else None))
 configs=[dict(model=m,alpha=a,gate=g) for m in eligible for a in [.05,.1,.2] for g in [1,2,3]];results=[[] for _ in configs];sv={k:[] for k in ['linear','rbf']};benign_max={k:[] for k in sv};zero_checks=0
 for i,(row,a) in enumerate(d.dataset('CALIBRATION')):
  packet(row);zero,v=core(row,a,np.zeros(len(a['time'])),'A0');assert np.array_equal(v[:,1].astype(bool),a['alarm']) and np.array_equal(v[:,2].astype(int)>>1,a['origin']);zero_checks+=1
  saved=np.load(B/'tapes'/(row['run_id']+'_margins.npz'))
  for k,c in enumerate(configs):
   f=fitted[c['model']];q=expit(f['slope']*saved['provider_'+c['model']]+f['intercept']);mass=masses(a['features'],a['qualified'],a['time'],q,c['alpha'],c['gate']);result,_=core(row,a,mass,'A3');results[k].append(result)
  for kind in sv:
   z=saved['standalone_'+kind];sv[kind].append(standalone(row,a,z,0,'A1-default'))
   if row['origin']=='NORMAL':benign_max[kind].append(float(z.max()))
  if (i+1)%100==0:print('CAL GRID',i+1,flush=True)
 base=json.loads((B/'CALIBRATION_rows.json').read_text());base_stats=bench.summary(base);grid=[]
 for c,rr in zip(configs,results):
  st=bench.summary(rr);critical=all(sum(x['detected'] for x in rr if x['origin']==o and (o!='MEMORY' or x['effective_memory_corruption']))>=sum(x['detected'] for x in base if x['origin']==o and (o!='MEMORY' or x['effective_memory_corruption'])) for o in ['MEMORY','TIMING','COMMUNICATION','ACTUATOR'])
  startup=sum(x['false_alarm'] and 0<=x['first_alarm_ms']<1000 for x in rr)<=sum(x['false_alarm'] and 0<=x['first_alarm_ms']<1000 for x in base)
  grid.append(dict(**c,eligible=st['benign_false_alarm_rate']<=.01 and st['runtime_wrong_runs']==0 and startup and critical,**st))
 best={}
 for kind in eligible:
  ks=[k for k,c in enumerate(grid) if c['model']==kind and c['eligible']]
  if ks:best[kind]=max(ks,key=lambda k:(grid[k]['detected'],-grid[k]['silent_plant'],-grid[k]['alpha'],-grid[k]['gate']))
 selected=best.get('linear');rb=best.get('rbf')
 if rb is not None and (selected is None or grid[rb]['detected']-grid[selected]['detected']>=.01*base_stats['faulty_runs']):selected=rb
 passed=selected is not None
 if selected is None:selected=next(k for k,c in enumerate(configs) if c==dict(model='linear',alpha=.05,gate=2))
 choice=configs[selected];svstats={k:bench.summary(v) for k,v in sv.items()};svkind=max(sv,key=lambda k:(.5*(svstats[k]['coverage']+1-svstats[k]['benign_false_alarm_rate']),svstats[k]['coverage'],k=='linear'))
 maxima=sorted(benign_max[svkind],reverse=True);allowed=int(.01*len(maxima));threshold=maxima[allowed] # Strict > means ties cannot exceed the budget.
 config=dict(provider=choice,platt=fitted[choice['model']],calibration_gate_passed=passed,standalone_model=svkind,standalone_default_threshold=0.,standalone_matched_threshold=threshold,matched_calibration_allowed_alarm_runs=allowed,provider_model_family=training,feature_names=d.FEATURES,zero_mass_parity_cases=zero_checks)
 d.dump(O/'calibration.json',config);h.write(O/'calibration_grid.csv',grid);h.write(O/'calibration_reliability.csv',reliability);d.dump(O/'standalone_calibration.json',svstats)
 for role,kind in [('provider',choice['model']),('standalone',svkind)]:shutil_copy(B/(role+'_'+kind+'.pkl'),O/(role+'_svm.pkl'))
 (O/'svm_model_hash.txt').write_text('\n'.join(f'{d.sha(O/(role+"_svm.pkl"))}  {role}_svm.pkl' for role in ['provider','standalone'])+'\n')
 print('SELECTED',config,flush=True)

def shutil_copy(a,b):b.write_bytes(a.read_bytes())

def evaluate(part):
 d.verify();config=json.loads((O/'calibration.json').read_text());provider=pickle.loads((O/'provider_svm.pkl').read_bytes());svm=pickle.loads((O/'standalone_svm.pkl').read_bytes());out=[];summaries=[]
 for i,(row,a) in enumerate(d.dataset(part)):
  oldmargin=B/'tapes'/(row['run_id']+'_margins.npz')
  if oldmargin.exists():z=np.load(oldmargin);pm=z['provider_'+config['provider']['model']];sm=z['standalone_'+config['standalone_model']]
  else:pm=d.margin(provider,a['features']);sm=d.margin(svm,a['features'])
  p=config['platt'];q=expit(p['slope']*pm+p['intercept']);packet(row);out.append(row)
  outputs=[]
  for gate,name in [(0,'A2'),(config['provider']['gate'],'A3')]:
   mass=masses(a['features'],a['qualified'],a['time'],q,config['provider']['alpha'],gate);rr,v=core(row,a,mass,name);out.append(rr);outputs.append(v)
  for threshold,name in [(0,'A1-default'),(config['standalone_matched_threshold'],'A1-matched')]:out.append(standalone(row,a,sm,threshold,name))
  np.savez_compressed(B/'tapes'/(row['run_id']+'_evaluated.npz'),q=q,provider_margin=pm,svm_margin=sm,output=np.stack(outputs))
  summaries.append(dict(run_id=row['run_id'],origin=row['origin'],max_q=float(q.max()),max_qualified_q=float(q[a['qualified']].max()) if a['qualified'].any() else 0,qualified_samples=int(a['qualified'].sum())))
  if (i+1)%150==0:print('EVALUATE',part,i+1,flush=True)
 d.dump(B/(part+'_evaluated.json'),out);h.write(O/(part.lower()+'_ml_scores.csv'),summaries)
 if part=='VALIDATION_BENIGN':
  gate={m:bench.summary([x for x in out if x['method']==m]) for m in ['A0','A2','A3']};d.dump(O/'benign_gate.json',gate);print('BENIGN FIRST',[(m,v['benign_false_alarms'],v['runtime_wrong_runs']) for m,v in gate.items()],flush=True)
 print('COMPLETE EVALUATE',part,flush=True)

def freeze():
 d.verify();assert not (B/'VALIDATION_BENIGN_started').exists();assert not (O/'validation_lock.json').exists()
 paths=[d.ROOT/'scripts/run_ml_assisted_clodsf.py',Path(__file__),d.ROOT/'scripts/report_ml_assisted_clodsf.py',d.ROOT/'scripts/export_ml_sensor_runtime.py',d.ROOT/'include/ml_sensor_weak.h',d.ROOT/'src/v7_3/ml_sensor_weak.c',d.ROOT/'tests/test_ml_sensor_weak.py',*[O/name for name in ['protocol.md','feature_definition.md','model_definition.md','campaign_manifest.csv','calibration.json','provider_svm.pkl','standalone_svm.pkl','runtime_model.json']]]
 d.dump(O/'validation_lock.json',{str(p.resolve()):d.sha(p) for p in paths});print('VALIDATION LOCKED',flush=True)

if __name__=='__main__':
 if sys.argv[1]=='calibrate':calibrate()
 elif sys.argv[1]=='evaluate':evaluate(sys.argv[2])
 elif sys.argv[1]=='freeze':freeze()
