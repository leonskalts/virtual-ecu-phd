#!/usr/bin/env python3
"""Benign identification, TRAIN-only CP choice and CAL-only fair SVM selection."""
import sys,json,pickle,gzip,subprocess,ctypes,math,collections,struct
from concurrent.futures import ThreadPoolExecutor
import run_change_point as d
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
B=d.B;O=d.O;lib=None

def vector(c):
 def packed(cov):
  l=np.linalg.cholesky(cov);return [l[0,0],l[1,0],l[1,1]]
 v=[*c['mean'],*packed(c['covariance'])]
 for k in range(2):v.extend([*c.get('slope_mean',[[0,0]]*2)[k],*packed(c.get('slope_covariance',[np.eye(2).tolist()]*2)[k])])
 return np.array([*v,c.get('threshold',1e300),c.get('gamma',.25),c.get('combination',0)],float)
SOURCE=r'''
#include "triplex_change_point.h"
void series(unsigned n,const double *a,const double *p,const double *f0,unsigned n0,const double *f1,unsigned n1,const double *f2,unsigned n2,double *out){
 cp_config_t c={0};for(unsigned i=0;i<2;i++)c.mu[i]=p[i];for(unsigned i=0;i<3;i++)c.chol[i]=p[2+i];
 for(unsigned k=0;k<2;k++){for(unsigned i=0;i<2;i++)c.slope_mu[k][i]=p[5+5*k+i];for(unsigned i=0;i<3;i++)c.slope_chol[k][i]=p[7+5*k+i];}
 c.threshold=p[15];c.gamma=p[16];c.combination=(unsigned)p[17];c.cdf[0]=f0;c.cdf[1]=f1;c.cdf[2]=f2;c.cdf_n[0]=n0;c.cdf_n[1]=n1;c.cdf_n[2]=n2;
 cp_state_t s={0};for(unsigned i=0;i<n;i++){cp_input_t u={(unsigned)a[i*4],a[i*4+1],a[i*4+2],a[i*4+3]!=0};triplex_cp_step(&s,&c,&u);double *o=out+i*24;o[0]=u.ms;for(unsigned j=0;j<3;j++){o[1+j]=s.raw[j];o[4+j]=s.p[j];o[9+j]=s.isolated_mass[j];o[20+j]=s.available[j];}o[7]=s.rarity;o[8]=s.mass;o[12]=s.start_step;o[13]=s.start_transient;o[14]=s.end_transient;o[15]=s.drift_window;for(unsigned k=0;k<2;k++)for(unsigned j=0;j<2;j++)o[16+2*k+j]=s.slope[k][j];o[23]=s.stable;}
}
'''
def series(a,c,cdf=None):
 global lib
 if lib is None:
  (B/'series.c').write_text(SOURCE);subprocess.run(['gcc','-std=c11','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror','-Iinclude',str(B/'series.c'),'src/v7_3/triplex_change_point.c','-lm','-o',str(B/'cp.so')],check=True);lib=ctypes.CDLL(str(B/'cp.so'));array=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');lib.series.argtypes=[ctypes.c_uint,array,array,array,ctypes.c_uint,array,ctypes.c_uint,array,ctypes.c_uint,array]
 if cdf is None:cdf=[np.array([],float)]*3
 out=np.empty((len(a),24));args=[]
 for f in cdf:args.extend([np.ascontiguousarray(f),len(f)])
 lib.series(len(a),np.ascontiguousarray(a[:,:4]),vector(c),*args,out);assert np.isfinite(out).all() and out[:,23].all();return out

def covariance(x,robust,floor=.0004):
 mu=x.mean(0);cov=np.cov(x,rowvar=False)+np.eye(2)*floor
 if robust:
  for _ in range(20):
   z=np.linalg.solve(np.linalg.cholesky(cov),(x-mu).T).T;distance=np.sqrt((z*z).sum(1));weights=np.minimum(1,2.5/np.maximum(distance,1e-12));mu=np.average(x,axis=0,weights=weights);delta=x-mu;cov=(delta*weights[:,None]).T@delta/weights.sum()+np.eye(2)*floor
 return dict(mean=mu.tolist(),covariance=cov.tolist(),eigenvalues=np.linalg.eigvalsh(cov).tolist(),condition=float(np.linalg.cond(cov)))
def benign_sample(part):
 chunks=[]
 for row,a in d.dataset(part):
  if row['origin']!='NORMAL':continue
  x=a['input'];pool=np.flatnonzero(x[:,3]);idx=pool[np.unique(np.linspace(0,len(pool)-1,min(len(pool),24),dtype=int))];chunks.append(x[idx,1:3])
 return np.concatenate(chunks)
def identify():
 d.verify();assert not (O/'whitening_model.json').exists();train=benign_sample('TRAIN');cal=benign_sample('CALIBRATION');records=[]
 for robust in [False,True]:
  tr=covariance(train,robust);ca=covariance(cal,robust);tr.update(estimator='Huber' if robust else 'regularized_standard',regularization=.0004,benign_train_frames=len(train),benign_cal_frames=len(cal),stability=float(np.max(np.abs(np.log(np.array(ca['eigenvalues'])/tr['eigenvalues'])))+.01*np.log(tr['condition'])),cal_eigenvalues=ca['eigenvalues']);records.append(tr)
 selected=min(records,key=lambda x:x['stability']);slopes=[[],[]]
 for row,a in d.dataset('TRAIN'):
  if row['origin']!='NORMAL':continue
  inp=a['input'];v=series(inp,selected)
  for k in range(2):
   counts=[];count=0
   for ii,xx in enumerate(inp):
    count=count+1 if xx[3] and (ii==0 or xx[0]==inp[ii-1,0]+100) else int(bool(xx[3]));counts.append(count)
   pool=np.flatnonzero(np.array(counts)>=[20,50][k]);idx=pool[np.unique(np.linspace(0,len(pool)-1,min(len(pool),24),dtype=int))];slopes[k].append(v[idx,16+2*k:18+2*k])
 fits=[covariance(np.concatenate(x),selected['estimator']=='Huber',1e-6) for x in slopes];selected=dict(selected,slope_mean=[x['mean'] for x in fits],slope_covariance=[x['covariance'] for x in fits],slope_regularization=1e-6)
 d.dump(O/'whitening_model.json',dict(selected=selected,candidates=records,slope_fits=fits,selection='benign TRAIN/CAL stability only; slopes benign TRAIN only',registration=json.loads((B/'registration.json').read_text())))
 cdf=[[],[],[]]
 for part in ['TRAIN','CALIBRATION']:
  for i,(row,a) in enumerate(d.dataset(part)):
   v=series(a['input'],selected);np.savez_compressed(B/'tapes'/(row['run_id']+'_cp.npz'),stats=v)
   if part=='CALIBRATION' and row['origin']=='NORMAL':
    for j in range(3):cdf[j].append(v[v[:,20+j]>0,1+j])
   if (i+1)%300==0:print('RAW',part,i+1,flush=True)
 cdf=[np.sort(np.concatenate(x)) for x in cdf];np.savez_compressed(B/'cdf.npz',**{str(j):x for j,x in enumerate(cdf)})
 with (B/'cdf.bin').open('wb') as f:
  for x in cdf:f.write(struct.pack('I',len(x)));f.write(x.tobytes())
 maxima=[[],[],[]]
 for row,a in d.dataset('CALIBRATION'):
  if row['origin']!='NORMAL':continue
  for method in range(3):maxima[method].append(float(series(a['input'],dict(selected,combination=method),cdf)[:,7].max()))
 levels={}
 for method in range(3):
  mm=maxima[method];ll={}
  for epsilon in [0,.0025,.005,.01,.02]:
   k=len(mm) if not epsilon else math.ceil((len(mm)+1)*(1-epsilon));threshold=sorted(mm)[k-1] if k<=len(mm) else 1e300;ll[str(epsilon)]=dict(rank=k,threshold=threshold,observed_exceedances=sum(x>threshold for x in mm),n=len(mm))
  halves=[np.quantile(mm[offset::2],.995,method='higher') for offset in [0,1]];levels[str(method)]=dict(levels=ll,run_maxima=mm,split_half_instability=float(abs(halves[0]-halves[1])/max(1e-12,*halves)))
 d.dump(B/'cp_config.json',selected);d.dump(B/'tail_calibration.json',levels);print('IDENTIFIED',selected,'CDF',[len(x) for x in cdf],flush=True)

def evidence(a):return d.r.be.Evidence(a['input'][:,0].astype(int),a['values'],a['available'],a['subset'])
def comparator_parity(a,c):
 """Previous SVM-P descriptive transforms only; no evidence provider/mass."""
 inp=a['input'];z=np.linalg.solve(np.linalg.cholesky(c['covariance']),(inp[:,1:3]-c['mean']).T).T;directions=np.linalg.solve(np.linalg.cholesky(c['covariance']),np.array([[1,0],[0,1],[-1,-1],[1,1]]).T).T;directions/=np.linalg.norm(directions,axis=1)[:,None]
 out=np.zeros((len(inp),7));valid=inp[:,3]>0;indices=np.arange(len(inp));gaps=np.r_[False,np.diff(inp[:,0])!=100];resets=np.where(~valid,indices,np.where(gaps,indices-1,-1));count=indices-np.maximum.accumulate(resets);cs=np.vstack((np.zeros(2),np.cumsum(z,axis=0)))
 out[valid,0]=(z[valid]*z[valid]).sum(axis=1)
 for w in [1,2,4,8]:
  if len(inp)<w:continue
  v=(cs[w:]-cs[:-w])/np.sqrt(w);scores=(v@directions.T)**2;take=np.flatnonzero(count[w-1:]>=w);rows=take+w-1;out[rows,1:5]=np.maximum(out[rows,1:5],scores[take]);out[rows,5]=np.maximum(out[rows,5],scores[take].max(axis=1));out[rows,6]=np.maximum(out[rows,6],(v[take]*v[take]).sum(axis=1))
 return out

def features(a,v,cp):
 raw=np.column_stack((d.prior.features(evidence(a)),a['input'][:,1:4],a['svm_parity']));return np.column_stack((raw,v[:,1:4],v[:,7])) if cp else raw

def core(row,c,packet=True,slot=None):
 w=B/'work';suffix='' if slot is None else '_'+str(slot);packet_path=w/('packet'+suffix+'.bin');params=w/('params'+suffix+'.txt');output=w/('output'+suffix+'.csv');elog=w/('replay_evidence'+suffix+'.csv')
 if packet:packet_path.write_bytes(gzip.decompress((B/'tapes'/(row['run_id']+'.bin.gz')).read_bytes()))
 params.write_text(' '.join(map(str,vector(c))));subprocess.run([str(w/'compare'),'--cp-replay',str(packet_path),str(params),str(output)],check=True,env=dict(d.os.environ,BENCHMARK_LOG=str(elog),CP_CDF=str(B/'cdf.bin'),CP_LIGHT=str(int(slot is not None)),CP_SKIP_BASE=str(int(slot is not None and slot!=0))))
 return np.loadtxt(output,delimiter=',')
def score(row,a,v,j):return d.bench.score(row,evidence(a),'A'+str(j) if j<4 else 'H'+str(j-3),(v[:,23+j*3].astype(bool),v[:,24+j*3].astype(int)>>1))
def wrong_fault(rr):return sum(bool(x['wrong_localized_runtime_samples']) for x in rr if x['injected'])

def select_mapping():
 d.verify();config=json.loads((B/'cp_config.json').read_text());tail=json.loads((B/'tail_calibration.json').read_text());configs=[dict(config,combination=m,gamma=g,threshold=tail[str(m)]['levels']['0.005']['threshold']) for m in range(3) for g in [.25,.5]];results=[[] for _ in configs];benign=[[] for _ in configs];paritycheck=0;pool=ThreadPoolExecutor(max_workers=4)
 for part in ['TRAIN','CALIBRATION']:
  for i,(row,a) in enumerate(d.dataset(part)):
   if part=='CALIBRATION' and row['origin']!='NORMAL':continue
   pending=[pool.submit(core,row,c,True,j) for j,c in enumerate(configs)]
   for j,future in enumerate(pending):
    v=future.result();(results[j] if part=='TRAIN' else benign[j]).extend([score(row,a,v,1),score(row,a,v,3)])
    if j==0:
     for k in [0,2]:assert np.array_equal(v[:,23+k*3].astype(bool),a['input'][:,4+k].astype(bool)) and np.array_equal(v[:,24+k*3].astype(int),a['input'][:,5+k].astype(int))
     saved=np.load(B/'tapes'/(row['run_id']+'_cp.npz'))['stats'];assert np.allclose(v[:,1:4],saved[:,1:4],rtol=1e-12,atol=1e-12);paritycheck+=1
   if (i+1)%150==0:print('MAPPING',part,i+1,flush=True)
 pool.shutdown()
 base={part:json.loads((B/(part+'_rows.json')).read_text()) for part in ['TRAIN','CALIBRATION']};grid=[]
 for c,rr,bb in zip(configs,results,benign):
  stats={m:d.bench.summary([x for x in rr if x['method']==m]) for m in ['A1','A3']};valid=wrong_fault(rr)==0;increment={}
  for m,b in [('A1','A0'),('A3','A2')]:
   aa={x['run_id']:x for x in rr if x['method']==m};old={x['run_id']:x for x in base['TRAIN'] if x['method']==b};valid &= all(not x['detected'] or aa[k]['detected'] for k,x in old.items())
   old={x['run_id']:x for x in base['CALIBRATION'] if x['method']==b and x['origin']=='NORMAL'};increment[m]=sum(x['false_alarm'] and not old[x['run_id']]['false_alarm'] for x in bb if x['method']==m)/len(old);valid &= increment[m]<=.005
  sensor=sum(x['detected'] for x in rr if x['method']=='A1' and x['origin']=='SENSOR_CONTROL');grid.append(dict(gamma=c['gamma'],combination=c['combination'],eligible=bool(valid),sensor_detected=sensor,stats=stats,cal_increment=increment,wrong_fault_runs=wrong_fault(rr)))
 eligible=[i for i,g in enumerate(grid) if g['eligible']];choice=max(eligible,key=lambda i:(grid[i]['sensor_detected'],-grid[i]['stats']['A3']['silent_plant'],-tail[str(configs[i]['combination'])]['split_half_instability'],-configs[i]['gamma'],-configs[i]['combination'])) if eligible else 0
 c=configs[choice];c['cal_gate_passed']=bool(eligible);d.dump(B/'selected_cp.json',c);d.dump(B/'mapping_grid.json',dict(grid=grid,selected=choice,zero_provider_replay_parity_cases=paritycheck));print('SELECTED',c,flush=True)
 # Cache selected statistics and comparator transforms without altering data.
 cdf=[np.load(B/'cdf.npz')[str(j)] for j in range(3)]
 for part in ['TRAIN','CALIBRATION']:
  for row,a in d.dataset(part):
   v=series(a['input'],c,cdf);np.savez_compressed(B/'tapes'/(row['run_id']+'_cp.npz'),stats=v)
   np.savez_compressed(B/'tapes'/(row['run_id']+'_features.npz'),svm_parity=comparator_parity(a,c))
def fit_svm():
 d.verify();models={};record=[]
 for space in ['X','CP']:
  xx=[];yy=[]
  for row,a in d.dataset('TRAIN'):
   a=dict(a);a.update(np.load(B/'tapes'/(row['run_id']+'_features.npz')));v=np.load(B/'tapes'/(row['run_id']+'_cp.npz'))['stats'];x=features(a,v,space=='CP');y=a['target'];idx=[]
   for c in [0,1]:
    pool=np.flatnonzero(y==c)
    if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
   if idx:xx.append(x[idx]);yy.append(y[idx])
  x=np.concatenate(xx);y=np.concatenate(yy)
  for kernel,C in [('linear',.1),('linear',1.),('rbf',1.)]:
   name=f'{space}_{kernel}_{C}';model=make_pipeline(StandardScaler(),SVC(kernel=kernel,C=C,gamma='scale',class_weight='balanced',cache_size=512));model.fit(x,y);models[name]=model;reference=model.decision_function(x[:64]);fast=d.ml.margin(model,x[:64]);assert np.allclose(reference,fast,rtol=1e-8,atol=1e-8);record.append(dict(name=name,frames=len(y),features=x.shape[1],support_vectors=len(model[1].support_),linear_weights=x.shape[1] if kernel=='linear' else None,margin_max_abs_error=float(np.max(np.abs(reference-fast)))));print('FIT',record[-1],flush=True)
 (B/'svms.pkl').write_bytes(pickle.dumps(models,protocol=4));d.dump(B/'svm_training.json',record)
 results={k:[] for k in models};maxima={k:[] for k in models}
 for i,(row,a) in enumerate(d.dataset('CALIBRATION')):
  a=dict(a);a.update(np.load(B/'tapes'/(row['run_id']+'_features.npz')));v=np.load(B/'tapes'/(row['run_id']+'_cp.npz'))['stats'];saved={}
  for k,model in models.items():
   margin=d.ml.margin(model,features(a,v,k.startswith('CP_')));saved[k]=margin;results[k].append(d.bench.score(row,evidence(a),k,(margin>0,np.zeros(len(margin),int))))
   if row['origin']=='NORMAL':maxima[k].append(float(margin.max()))
  np.savez_compressed(B/'tapes'/(row['run_id']+'_svm.npz'),**saved)
  if (i+1)%150==0:print('SVM CAL',i+1,flush=True)
 summaries={k:d.bench.summary(rr) for k,rr in results.items()};selection={}
 for space in ['X','CP']:
  ks=[k for k in models if k.startswith(space+'_')];chosen=max(ks,key=lambda k:(.5*(summaries[k]['coverage']+1-summaries[k]['benign_false_alarm_rate']),summaries[k]['coverage'],-ks.index(k)));n=len(maxima[chosen]);rank=math.ceil((n+1)*.99);threshold=sorted(maxima[chosen])[rank-1];selection[space]=dict(model=chosen,threshold=threshold,rank=rank,benign_cal_runs=n,cal_alarm_runs=sum(x>threshold for x in maxima[chosen]),cal_default=summaries[chosen]);(B/('svm_'+space+'.pkl')).write_bytes(pickle.dumps(models[chosen],protocol=4))
 d.dump(B/'svm_selection.json',dict(selection=selection,candidates=summaries,training=record));print('SVM SELECTED',selection,flush=True)

def freeze():
 d.verify();assert not (B/'VALIDATION_BENIGN_started').exists();assert not (B/'lock.json').exists()
 paths=[d.ROOT/p for p in ['scripts/run_change_point.py','scripts/select_change_point.py','scripts/report_change_point.py','scripts/benchmark_change_point.py','scripts/regress_change_point.py','scripts/finalize_change_point.py','scripts/change_point_protocol.md','include/triplex_change_point.h','src/v7_3/triplex_change_point.c','tests/test_triplex_change_point.py']]+[B/p for p in ['specs.json','selected_cp.json','svm_selection.json','svm_X.pkl','svm_CP.pkl','cdf.npz','cdf.bin']]+[O/'detector_definition.md',O/'whitening_model.json']
 d.dump(B/'lock.json',{str(p.resolve()):d.sha(p) for p in paths});print('VALIDATION LOCKED',flush=True)

def evaluate(part):
 d.verify();config=json.loads((B/'selected_cp.json').read_text());selection=json.loads((B/'svm_selection.json').read_text())['selection'];models={s:pickle.loads((B/('svm_'+s+'.pkl')).read_bytes()) for s in ['X','CP']};out=[]
 for i,(row,a) in enumerate(d.dataset(part)):
  a=dict(a);a['svm_parity']=comparator_parity(a,config);v=core(row,config);out.extend(score(row,a,v,j) for j in range(7));np.savez_compressed(B/'tapes'/(row['run_id']+'_evaluated.npz'),output=v)
  if not (B/'tapes'/(row['run_id']+'_cp.npz')).exists():np.savez_compressed(B/'tapes'/(row['run_id']+'_cp.npz'),stats=v[:,:23])
  for space,model in models.items():
   path=B/'tapes'/(row['run_id']+'_svm.npz');margin=np.load(path)[selection[space]['model']] if path.exists() else d.ml.margin(model,features(a,v,space=='CP'))
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
