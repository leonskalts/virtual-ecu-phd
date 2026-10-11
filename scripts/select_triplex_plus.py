#!/usr/bin/env python3
"""TRAIN/CAL-only model fitting and pre-validation architecture selection."""
import sys,json,pickle,collections
from pathlib import Path
import run_triplex_plus as r
sys.path.insert(0,'/tmp/clo-ml-deps')
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
B=r.B;O=r.O

def part_rows(part):return json.loads((B/(part+'_rows.json')).read_text())
def dataset(part,arch):
 rows=[x for x in part_rows(part) if x['method']==r.NAMES[arch]]
 for x in rows:
  with np.load(B/'tapes'/part/(x['run_id']+'.npz')) as a:
   e=r.be.Evidence(a['time'],a['values'][arch],a['available'][arch],a['subsets'][arch])
   yield x,e,a['y'].copy(),a['alarm_origin'][:,arch].copy()

def features(e,extra=None):
 v=e.values;n=len(v);pad=np.pad(v,((9,0),(0,0)));mask=np.pad(e.available.astype(float),((9,0),(0,0)))
 windows=np.lib.stride_tricks.sliding_window_view(pad,10,axis=0)
 counts=np.lib.stride_tricks.sliding_window_view(mask,10,axis=0).sum(axis=-1)
 mean=np.divide(windows.sum(axis=-1),counts,out=np.zeros_like(v),where=counts>0)
 out=np.column_stack((e.features,mean,windows.max(axis=-1)))
 return np.column_stack((out,extra)) if extra is not None else out

def gates(rows,base):
 s=r.bench.summary(rows);b=r.bench.summary(base)
 critical={o:sum(x['detected'] for x in rows if x['origin']==o and (o!='MEMORY' or x['effective_memory_corruption']))>=sum(x['detected'] for x in base if x['origin']==o and (o!='MEMORY' or x['effective_memory_corruption'])) for o in ['MEMORY','TIMING','COMMUNICATION']}
 return s['benign_false_alarm_rate']<=.01 and s['runtime_wrong_runs']==0 and all(critical.values())

def choose():
 r.verify();assert (B/'CALIBRATION_complete').exists() and not (O/'architecture_selection.json').exists()
 rows={p:part_rows(p) for p in ['TRAIN','CALIBRATION']};table=[];eligible={};gains={}
 for arch,m in enumerate(r.NAMES):
  eligible[arch]=True;gains[arch]={}
  for part,rr in rows.items():
   a={x['run_id']:x for x in rr if x['method']=='A0'};b={x['run_id']:x for x in rr if x['method']==m}
   plus=sum(b[k]['detected'] and not a[k]['detected'] for k in a);lost=sum(a[k]['detected'] and not b[k]['detected'] for k in a)
   ok=gates(list(b.values()),list(a.values()));eligible[arch]&=ok;gains[arch][part]=plus
   table.append(dict(partition=part,method=m,additional=plus,lost=lost,gate=ok,**r.bench.summary(list(b.values()))))
 if eligible[1] and (not eligible[2] or all(gains[1][p]>=.95*gains[2][p] for p in rows)):memory=1
 elif eligible[2]:memory=2
 else:memory=0
 stagger=3+memory
 val=lambda arch:next(x['detected'] for x in table if x['partition']=='CALIBRATION' and x['method']==r.NAMES[arch])
 selected=stagger if eligible[stagger] and val(stagger)>val(memory) else memory
 record=dict(selected_arch=selected,selected_name=r.NAMES[selected],memory_arch=memory,memory_interval={0:1000,1:500,2:250}[memory],stagger_eligible=eligible[stagger],stagger_selected=selected>=3,eligible=eligible,predeclared_rate_gain_fraction=.95,utc=r.now())
 r.dump(O/'architecture_selection.json',record);r.h.write(O/'train_calibration_architecture.csv',table);print(record,flush=True)

def fit_svm(stage='initial',oq=None):
 selection=json.loads((O/'architecture_selection.json').read_text());arch=selection['selected_arch']
 xs=[];ys=[]
 for row,e,y,_ in dataset('TRAIN',arch):
  extra=oq_states(e,oq)[0]/oq['boundary'] if oq is not None else None
  x=features(e,extra);idx=[]
  for c in [0,1]:
   pool=np.flatnonzero(y==c)
   if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
  xs.append(x[idx]);ys.append(y[idx])
 x=np.concatenate(xs);y=np.concatenate(ys);train_count=len(y);models={}
 for name,kernel,c in [('linear_0.1','linear',.1),('linear_1','linear',1.),('rbf_1','rbf',1.)]:
  model=make_pipeline(StandardScaler(),SVC(kernel=kernel,C=c,gamma='scale',class_weight='balanced',cache_size=512))
  model.fit(x,y);models[name]=model;print('FIT',stage,name,len(x),x.shape[1],flush=True)
 (B/(stage+'_svm.pkl')).write_bytes(pickle.dumps(models,protocol=4))
 scored=[]
 for row,e,y,_ in dataset('CALIBRATION',arch):
  extra=oq_states(e,oq)[0]/oq['boundary'] if oq else None;x=features(e,extra)
  unique,inverse=np.unique(x,axis=0,return_inverse=True)
  for name,model in models.items():
   pred=model.predict(unique)[inverse].astype(bool)
   scored.append(r.bench.score(row,e,name,(pred,np.zeros(len(pred),int))))
 summaries=[dict(method=name,**r.bench.summary([x for x in scored if x['method']==name])) for name in models]
 best=max(summaries,key=lambda x:(.5*(x['coverage']+1-x['benign_false_alarm_rate']),x['coverage']))
 r.h.write(O/(stage+'_svm_calibration.csv'),summaries)
 record=dict(stage=stage,selected=best['method'],architecture=arch,feature_count=x.shape[1],selection='CAL run balanced accuracy, then recall, then predefined order',training_frames=train_count,models_sha256=r.sha(B/(stage+'_svm.pkl')),utc=r.now())
 r.dump(O/(stage+'_svm_selection.json'),record);r.dump(B/(stage+'_svm_calibration_rows.json'),scored)
 print('SVM SELECTED',stage,best['method'],best['detected'],best['benign_false_alarms'],flush=True)
 return best

def initial():
 assert not (B/'initial_svm.pkl').exists();best=fit_svm()
 selection=json.loads((O/'architecture_selection.json').read_text());arch=selection['selected_arch']
 rows=[x for x in part_rows('CALIBRATION') if x['method']==r.NAMES[arch]];s=r.bench.summary(rows)
 trigger=best['detected']-s['detected']>=3
 r.dump(O/'sequential_decision.json',dict(implemented=False,trigger=trigger,svm_detection=best['detected'],candidate_detection=s['detected'],gap=best['detected']-s['detected'],basis='CAL only; predeclared >=3 cases; no validation read'))
 print('OQ trigger',trigger,'gap',best['detected']-s['detected'],flush=True)

EDGES=np.array([0,1e-6,.01,.025,.05,.1,.2,.35,.5,.75,1.])
_oq_lib=None

def oq_states(e,config):
 global _oq_lib
 import ctypes,subprocess
 if _oq_lib is None:
  lib=B/'oq_runtime.so'
  subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-Iinclude','src/v7_3/triplex_plus_sequential.c','-lm','-o',str(lib)],cwd=r.ROOT,check=True)
  _oq_lib=ctypes.CDLL(str(lib));double=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');byte=np.ctypeslib.ndpointer(dtype=np.uint8,flags='C_CONTIGUOUS')
  _oq_lib.plus_oq_series.argtypes=[ctypes.c_uint,double,byte,double,ctypes.c_double,ctypes.c_double,double,byte]
  _oq_lib.plus_oq_series.restype=None
 values=np.ascontiguousarray(e.strength,dtype=np.float64);available=np.ascontiguousarray(e.available,dtype=np.uint8)
 table=np.ascontiguousarray(config['llr'],dtype=np.float64);state=np.empty_like(values);alarm=np.empty(len(values),dtype=np.uint8)
 _oq_lib.plus_oq_series(len(values),values,available,table,config['decay'],config['boundary'],state,alarm)
 return state,alarm.astype(bool)

def sequential():
 r.verify();decision=json.loads((O/'sequential_decision.json').read_text())
 assert decision['trigger'] and not decision['implemented'] and not (B/'VALIDATION_started').exists()
 selection=json.loads((O/'architecture_selection.json').read_text());arch=selection['selected_arch'];hist=np.zeros((2,6,10))
 for row,e,y,base in dataset('TRAIN',arch):
  bins=np.searchsorted(EDGES[1:-1],e.strength,side='right')
  for label in [0,1]:
   for channel in range(6):
    take=(y==label)&e.available[:,channel]
    hist[label,channel]+=np.bincount(bins[take,channel],minlength=10)
 prob=(hist+1)/(hist.sum(axis=2,keepdims=True)+10)
 llr=np.clip(np.log(prob[1]/prob[0]),-4,4)
 r.dump(O/'oq_train_model.json',dict(bin_edges=EDGES.tolist(),histogram=hist.tolist(),probability=prob.tolist(),llr=llr.tolist(),smoothing=1,source='TRAIN only'))
 configs=[dict(decay=d,boundary=b,llr=llr.tolist(),bin_edges=EDGES.tolist(),cap=32.,increment_clip=[-4,4],training_histogram=hist.tolist()) for d in [.8,.95,.99] for b in [4.,8.,12.]]
 outputs={part:[[] for _ in configs] for part in ['TRAIN','CALIBRATION']}
 for part in outputs:
  for i,(row,e,y,base) in enumerate(dataset(part,arch)):
   basealarm=base[:,0].astype(bool);origin=np.where(basealarm,base[:,1]>>1,0)
   for k,cfg in enumerate(configs):
    state,alarm=oq_states(e,cfg)
    outputs[part][k].append(r.bench.score(row,e,f'OQ{k}',(basealarm|alarm,origin)))
   if (i+1)%250==0:print('OQ',part,i+1,flush=True)
 summaries=[];eligible=[]
 for k,cfg in enumerate(configs):
  good=True
  for part in outputs:
   base=[x for x in part_rows(part) if x['method']=='A0'];rr=outputs[part][k];st=r.bench.summary(rr);ok=gates(rr,base);good&=ok
   summaries.append(dict(partition=part,index=k,decay=cfg['decay'],boundary=cfg['boundary'],eligible=ok,**st))
  if good:eligible.append(k)
 baseline=r.bench.summary([x for x in part_rows('CALIBRATION') if x['method']==r.NAMES[arch]])['detected']
 def key(k):
  st=next(x for x in summaries if x['partition']=='CALIBRATION' and x['index']==k)
  return (st['detected'],-st['benign_false_alarms'],-k)
 selected=max(eligible,key=key) if eligible else None
 retained=selected is not None and key(selected)[0]>baseline
 r.h.write(O/'sequential_calibration_grid.csv',summaries)
 decision.update(implemented=True,selected=retained,eligible_configurations=eligible,selected_index=selected,selection_utc=r.now())
 if retained:
  r.dump(O/'oq_set.json',configs[selected]);decision.update(decay=configs[selected]['decay'],boundary=configs[selected]['boundary'],calibration_detected=key(selected)[0])
 r.dump(O/'sequential_decision.json',decision);print('OQ DECISION',decision,flush=True)
 if retained:fit_svm('final',configs[selected])

# OQ-SET is implemented only following the preregistered CAL gap decision.

def freeze():
 r.verify();assert not (B/'VALIDATION_started').exists() and not (O/'validation_lock.json').exists()
 decision=json.loads((O/'sequential_decision.json').read_text());use=decision.get('selected',False);stage='final' if use else 'initial'
 svm=json.loads((O/(stage+'_svm_selection.json')).read_text());models=pickle.loads((B/(stage+'_svm.pkl')).read_bytes());model=models[svm['selected']]
 (O/'fair_svm.pkl').write_bytes(pickle.dumps(model,protocol=4))
 record=dict(utc=r.now(),architecture=json.loads((O/'architecture_selection.json').read_text()),svm=svm,oq_set=decision,
  features=[*r.be.CHANNELS,*[x+'_available' for x in r.be.CHANNELS],*[x+'_mean1s' for x in r.be.CHANNELS],*[x+'_max1s' for x in r.be.CHANNELS]]+([x+'_sequential' for x in r.be.CHANNELS] if use else []))
 files=[Path(__file__),ROOT/'scripts/run_triplex_plus.py',ROOT/'src/v7_3/triplex_plus.c',ROOT/'include/triplex_plus.h',ROOT/'tests/test_triplex_plus.py',O/'fair_svm.pkl',O/'architecture_selection.json',O/'sequential_decision.json',O/'protocol.md',O/'campaign_manifest.csv',B/'specs.json']
 if use:files += [O/'oq_set.json',ROOT/'src/v7_3/triplex_plus_sequential.c',ROOT/'include/triplex_plus_sequential.h']
 files += [ROOT/'scripts/report_triplex_plus.py',ROOT/'tests/test_triplex_plus_sequential.py']
 if decision.get('implemented'):files += [O/'oq_train_model.json',O/'sequential_calibration_grid.csv',ROOT/'src/v7_3/triplex_plus_sequential.c',ROOT/'include/triplex_plus_sequential.h']
 record['files']={str(p):r.sha(p) for p in files};r.dump(O/'validation_lock.json',record);print('VALIDATION LOCKED',flush=True)

ROOT=r.ROOT
if __name__=='__main__':
 if sys.argv[1]=='choose':choose()
 elif sys.argv[1]=='initial':initial()
 elif sys.argv[1]=='freeze':freeze()
 elif sys.argv[1]=='sequential':sequential()
