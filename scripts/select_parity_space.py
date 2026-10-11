#!/usr/bin/env python3
"""Benign covariance/run-tail calibration and fixed comparator selection."""
import sys,json,pickle,gzip,subprocess,ctypes,math,collections
import run_parity_space as d
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
B=d.B;O=d.O;lib=None

def vector(c):
 l=np.linalg.cholesky(np.array(c['covariance']));return [*c['mean'],l[0,0],l[1,0],l[1,1],c.get('tau',1e300),c.get('saturation',2),c.get('beta',.25),2.]
def series(a,c):
 global lib
 if lib is None:
  source='''#include "triplex_parity.h"
void series(unsigned n,const double *a,const double *p,double *out){parity_config_t c={{p[0],p[1]},p[2],p[3],p[4],p[5],p[6],p[7],p[8]};parity_state_t s={0};for(unsigned i=0;i<n;i++){parity_input_t u={(unsigned)a[i*4],a[i*4+1],a[i*4+2],a[i*4+3]!=0};triplex_parity_step(&s,&c,&u);double *o=out+i*11;o[0]=u.ms;o[1]=s.g;o[2]=s.m;o[3]=s.current_m;o[4]=s.window;o[5]=s.direction;o[6]=s.mass;for(unsigned j=0;j<4;j++)o[7+j]=s.directional[j];}}
'''
  (B/'series.c').write_text(source);subprocess.run(['gcc','-std=c11','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror','-Iinclude',str(B/'series.c'),'src/v7_3/triplex_parity.c','-lm','-o',str(B/'parity.so')],check=True);lib=ctypes.CDLL(str(B/'parity.so'));array=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');lib.series.argtypes=[ctypes.c_uint,array,array,array]
 out=np.empty((len(a),11));lib.series(len(a),np.ascontiguousarray(a[:,:4]),np.array(vector(c)),out);assert np.isfinite(out).all();return out

def covariance(x,robust):
 mu=x.mean(0);cov=np.cov(x,rowvar=False)+np.eye(2)*.0004
 if robust:
  for _ in range(20):
   z=np.linalg.solve(np.linalg.cholesky(cov),(x-mu).T).T;distance=np.sqrt((z*z).sum(1));weights=np.minimum(1,2.5/np.maximum(distance,1e-12));mu=np.average(x,axis=0,weights=weights);delta=x-mu;cov=(delta*weights[:,None]).T@delta/weights.sum()+np.eye(2)*.0004
 return dict(mean=mu.tolist(),covariance=cov.tolist(),eigenvalues=np.linalg.eigvalsh(cov).tolist(),condition=float(np.linalg.cond(cov)))
def benign_sample(part):
 chunks=[]
 for row,a in d.dataset(part):
  if row['origin']!='NORMAL':continue
  x=a['input'];pool=np.flatnonzero(x[:,3]);idx=pool[np.unique(np.linspace(0,len(pool)-1,min(len(pool),24),dtype=int))];chunks.append(x[idx,1:3])
 return np.concatenate(chunks)
def identify():
 d.verify();assert not (O/'covariance_model.json').exists();train=benign_sample('TRAIN');cal=benign_sample('CALIBRATION');records=[]
 for robust in [False,True]:
  tr=covariance(train,robust);ca=covariance(cal,robust);tr.update(estimator='Huber' if robust else 'regularized_standard',regularization=.0004,benign_train_frames=len(train),benign_cal_frames=len(cal),stability=float(np.max(np.abs(np.log(np.array(ca['eigenvalues'])/tr['eigenvalues'])))+.01*np.log(tr['condition'])),cal_eigenvalues=ca['eigenvalues']);records.append(tr)
 selected=min(records,key=lambda x:x['stability']);d.dump(O/'covariance_model.json',dict(selected=selected,candidates=records,selection='BENIGN distribution stability only; no fault outcomes',registration=json.loads((B/'registration.json').read_text())))
 maxima=[]
 for part in ['TRAIN','CALIBRATION']:
  for i,(row,a) in enumerate(d.dataset(part)):
   v=series(a['input'],selected);np.savez_compressed(B/'tapes'/(row['run_id']+'_parity.npz'),stats=v)
   if part=='CALIBRATION' and row['origin']=='NORMAL':maxima.append(float(v[:,1].max()))
   if (i+1)%300==0:print('PARITY',part,i+1,flush=True)
 levels={}
 for epsilon in [0,.005,.01,.02,.05]:
  k=len(maxima) if not epsilon else math.ceil((len(maxima)+1)*(1-epsilon));tau=sorted(maxima)[k-1] if k<=len(maxima) else math.inf;levels[str(epsilon)]=dict(rank=k,tau=tau,observed_exceedances=sum(x>tau for x in maxima),n=len(maxima))
 selected=dict(selected,tau=levels['0.01']['tau']);d.dump(B/'parity_config.json',selected);d.dump(B/'tail_calibration.json',dict(levels=levels,run_maxima=maxima));print('COVARIANCE',selected,'TAILS',levels,flush=True)

def evidence(a):return d.r.be.Evidence(a['input'][:,0].astype(int),a['values'],a['available'],a['subset'])
def features(a,v,parity):
 raw=np.column_stack((d.prior.features(evidence(a)),a['input'][:,1:4]));return np.column_stack((raw,v[:,3],v[:,7:11],v[:,1:3])) if parity else raw

def core(row,c,packet=True):
 w=B/'work'
 if packet:(w/'packet.bin').write_bytes(gzip.decompress((B/'tapes'/(row['run_id']+'.bin.gz')).read_bytes()))
 (w/'params.txt').write_text(' '.join(map(str,vector(c))));subprocess.run([str(w/'compare'),'--parity-replay',str(w/'packet.bin'),str(w/'params.txt'),str(w/'output.csv')],check=True,env=dict(d.os.environ,BENCHMARK_LOG=str(w/'replay_evidence.csv')))
 return np.loadtxt(w/'output.csv',delimiter=',')
def score(row,a,v,j):return d.bench.score(row,evidence(a),'A'+str(j),(v[:,11+j*3].astype(bool),v[:,12+j*3].astype(int)>>1))
def wrong_fault(rr):return sum(bool(x['wrong_localized_runtime_samples']) for x in rr if x['injected'])

def select_mapping():
 d.verify();config=json.loads((B/'parity_config.json').read_text());configs=[dict(config,beta=b,saturation=s) for b in [.25,.5] for s in [1.5,2]];results=[[] for _ in configs];paritycheck=0
 for i,(row,a) in enumerate(d.dataset('CALIBRATION')):
  for j,c in enumerate(configs):
   v=core(row,c,packet=j==0);results[j].extend([score(row,a,v,1),score(row,a,v,3)])
   if j==0:
    for k in [0,2]:assert np.array_equal(v[:,11+k*3].astype(bool),a['input'][:,4+k].astype(bool)) and np.array_equal(v[:,12+k*3].astype(int),a['input'][:,5+k].astype(int))
    saved=np.load(B/'tapes'/(row['run_id']+'_parity.npz'))['stats'];assert np.allclose(v[:,1:6],saved[:,1:6],rtol=1e-12,atol=1e-12);paritycheck+=1
  if (i+1)%150==0:print('MAPPING CAL',i+1,flush=True)
 base=json.loads((B/'CALIBRATION_rows.json').read_text());grid=[]
 for c,rr in zip(configs,results):
  stats={m:d.bench.summary([x for x in rr if x['method']==m]) for m in ['A1','A3']};valid=all(s['benign_false_alarm_rate']<=.01 for s in stats.values()) and wrong_fault(rr)==0
  for m,b in [('A1','A0'),('A3','A2')]:
   aa={x['run_id']:x for x in rr if x['method']==m};bb={x['run_id']:x for x in base if x['method']==b}
   valid &= all(not x['detected'] or aa[k]['detected'] for k,x in bb.items())
   valid &= all(not(x['false_alarm'] and 0<=x['first_alarm_ms']<1000) or (bb[x['run_id']]['false_alarm'] and 0<=bb[x['run_id']]['first_alarm_ms']<1000) for x in aa.values())
  sensor=sum(x['detected'] for x in rr if x['method']=='A1' and x['origin']=='SENSOR_CONTROL');grid.append(dict(beta=c['beta'],saturation=c['saturation'],eligible=bool(valid),sensor_detected=sensor,stats=stats,wrong_fault_runs=wrong_fault(rr)))
 eligible=[i for i,g in enumerate(grid) if g['eligible']];choice=max(eligible,key=lambda i:(grid[i]['sensor_detected'],-grid[i]['stats']['A3']['silent_plant'],grid[i]['stats']['A3']['correct_localizations'],-configs[i]['beta'],configs[i]['saturation'])) if eligible else 1
 c=configs[choice];c['cal_gate_passed']=bool(eligible);d.dump(B/'selected_parity.json',c);d.dump(B/'mapping_grid.json',dict(grid=grid,selected=choice,zero_provider_replay_parity_cases=paritycheck));print('SELECTED MAPPING',c,flush=True)

def fit_svm():
 d.verify();models={};record=[]
 for space in ['R','P']:
  xx=[];yy=[]
  for row,a in d.dataset('TRAIN'):
   v=np.load(B/'tapes'/(row['run_id']+'_parity.npz'))['stats'];x=features(a,v,space=='P');y=a['target'];idx=[]
   for c in [0,1]:
    pool=np.flatnonzero(y==c)
    if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
   if idx:xx.append(x[idx]);yy.append(y[idx])
  x=np.concatenate(xx);y=np.concatenate(yy)
  for kernel,C in [('linear',.1),('linear',1.),('rbf',1.)]:
   name=f'{space}_{kernel}_{C}';model=make_pipeline(StandardScaler(),SVC(kernel=kernel,C=C,gamma='scale',class_weight='balanced',cache_size=512));model.fit(x,y);models[name]=model;record.append(dict(name=name,frames=len(y),features=x.shape[1],support_vectors=len(model[1].support_)));print('FIT',record[-1],flush=True)
 (B/'svms.pkl').write_bytes(pickle.dumps(models,protocol=4));d.dump(B/'svm_training.json',record)
 results={k:[] for k in models};maxima={k:[] for k in models}
 for i,(row,a) in enumerate(d.dataset('CALIBRATION')):
  v=np.load(B/'tapes'/(row['run_id']+'_parity.npz'))['stats'];saved={}
  for k,model in models.items():
   margin=d.ml.margin(model,features(a,v,k.startswith('P')));saved[k]=margin;results[k].append(d.bench.score(row,evidence(a),k,(margin>0,np.zeros(len(margin),int))))
   if row['origin']=='NORMAL':maxima[k].append(float(margin.max()))
  np.savez_compressed(B/'tapes'/(row['run_id']+'_svm.npz'),**saved)
  if (i+1)%150==0:print('SVM CAL',i+1,flush=True)
 summaries={k:d.bench.summary(rr) for k,rr in results.items()};selection={}
 for space in ['R','P']:
  ks=[k for k in models if k.startswith(space)];chosen=max(ks,key=lambda k:(.5*(summaries[k]['coverage']+1-summaries[k]['benign_false_alarm_rate']),summaries[k]['coverage'],-ks.index(k)));n=len(maxima[chosen]);rank=math.ceil((n+1)*.99);threshold=sorted(maxima[chosen])[rank-1];selection[space]=dict(model=chosen,threshold=threshold,rank=rank,benign_cal_runs=n,cal_alarm_runs=sum(x>threshold for x in maxima[chosen]),cal_default=summaries[chosen]);(B/('svm_'+space+'.pkl')).write_bytes(pickle.dumps(models[chosen],protocol=4))
 d.dump(B/'svm_selection.json',dict(selection=selection,candidates=summaries,training=record));print('SVM SELECTED',selection,flush=True)

def freeze():
 d.verify();assert not (B/'VALIDATION_BENIGN_started').exists();assert not (B/'lock.json').exists()
 paths=[d.ROOT/p for p in ['scripts/run_parity_space.py','scripts/select_parity_space.py','scripts/report_parity_space.py','scripts/benchmark_parity_space.py','include/triplex_parity.h','src/v7_3/triplex_parity.c','tests/test_triplex_parity.py']]+[B/p for p in ['specs.json','selected_parity.json','svm_selection.json','svm_R.pkl','svm_P.pkl']]+[O/'parity_definition.md',O/'covariance_model.json']
 d.dump(B/'lock.json',{str(p.resolve()):d.sha(p) for p in paths});print('VALIDATION LOCKED',flush=True)

def evaluate(part):
 d.verify();config=json.loads((B/'selected_parity.json').read_text());selection=json.loads((B/'svm_selection.json').read_text())['selection'];models={s:pickle.loads((B/('svm_'+s+'.pkl')).read_bytes()) for s in ['R','P']};out=[]
 for i,(row,a) in enumerate(d.dataset(part)):
  v=core(row,config);out.extend(score(row,a,v,j) for j in range(4));np.savez_compressed(B/'tapes'/(row['run_id']+'_evaluated.npz'),output=v)
  if not (B/'tapes'/(row['run_id']+'_parity.npz')).exists():np.savez_compressed(B/'tapes'/(row['run_id']+'_parity.npz'),stats=v[:,:11])
  for space,model in models.items():
   path=B/'tapes'/(row['run_id']+'_svm.npz');margin=np.load(path)[selection[space]['model']] if path.exists() else d.ml.margin(model,features(a,v,space=='P'))
   for th,name in [(0,'default'),(selection[space]['threshold'],'matched')]:out.append(d.bench.score(row,evidence(a),'SVM-'+space+' '+name,(margin>th,np.zeros(len(margin),int))))
  if (i+1)%150==0:print('EVALUATE',part,i+1,flush=True)
 d.dump(B/(part+'_evaluated.json'),out)
 if part=='VALIDATION_BENIGN':d.dump(B/'benign_gate.json',{m:d.bench.summary([x for x in out if x['method']==m]) for m in ['A0','A1','A2','A3']});print('BENIGN',[(m,sum(x['false_alarm'] for x in out if x['method']==m)) for m in ['A0','A1','A2','A3']],flush=True)
 print('COMPLETE EVALUATE',part,flush=True)
if __name__=='__main__':
 if sys.argv[1]=='identify':identify()
 elif sys.argv[1]=='mapping':select_mapping()
 elif sys.argv[1]=='svm':fit_svm()
 elif sys.argv[1]=='freeze':freeze()
 elif sys.argv[1]=='evaluate':evaluate(sys.argv[2])
