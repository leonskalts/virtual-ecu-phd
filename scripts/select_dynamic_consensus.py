#!/usr/bin/env python3
"""Registered benign-only model fit, development selection, locked replay."""
import sys,json,pickle,gzip,subprocess,ctypes,math,collections
import run_dynamic_consensus as d
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
B=d.B;O=d.O;lib=None

def vector(c):return np.array([*c['offset'],*c['variance'],c['process_variance'],c.get('lambda',.8),c.get('threshold',1e300),c.get('alpha',.1),c.get('healthy_margin',math.log(99)),c.get('consistency_bound',0),c.get('common_bound',0),c.get('origin_margin',math.log(1000)),c.get('robust',0),c.get('discount',0),c.get('memory',2)],float)
SOURCE=r'''
#include "dynamic_consensus.h"
void series(unsigned n,const double *a,const double *v,double *out){
 dc_config_t c={0};for(unsigned j=0;j<3;j++){c.offset[j]=v[j];c.variance[j]=v[3+j];}
 c.process_variance=v[6];c.lambda=v[7];c.threshold=v[8];c.alpha=v[9];c.healthy_margin=v[10];c.consistency_bound=v[11];c.common_bound=v[12];c.origin_margin=v[13];c.robust=(unsigned)v[14];
 dc_state_t s={0};for(unsigned i=0;i<n;i++){
  const double *r=a+21*i;dc_input_t u={.ms=(unsigned)r[0],.y={r[13],r[14],r[15]},.context={r[16],r[17],r[18],r[19]},.qualified=r[3]!=0};dynamic_consensus_step(&s,&c,&u);
  double *o=out+16*i;o[0]=u.ms;for(unsigned h=0;h<5;h++)o[h+1]=s.filter[h].ell;
  o[6]=s.D;o[7]=s.margin;o[8]=s.consistency;o[9]=s.common;o[10]=s.q_healthy;o[11]=s.mass;o[12]=s.origin_mass;o[13]=s.best;o[14]=s.qualified;o[15]=s.stable;
 }
}
'''
def series(a,c):
 global lib
 if lib is None:
  (B/'series.c').write_text(SOURCE);subprocess.run(['gcc','-std=c11','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror','-Iinclude',str(B/'series.c'),'src/v7_3/dynamic_consensus.c','-lm','-o',str(B/'dc.so')],check=True);lib=ctypes.CDLL(str(B/'dc.so'));arr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');lib.series.argtypes=[ctypes.c_uint,arr,arr,arr]
 out=np.empty((len(a),16));lib.series(len(a),np.ascontiguousarray(a),vector(c),out);assert np.isfinite(out).all() and out[:,15].all();return out

def evidence(a):return d.r.be.Evidence(a['input'][:,0].astype(int),a['values'],a['available'],a['subset'])
def core(row,c,slot='0'):
 w=B/'work';packet=w/('packet_'+str(slot)+'.bin');params=w/('params_'+str(slot)+'.txt');output=w/('output_'+str(slot)+'.csv');elog=w/('evidence_'+str(slot)+'.csv')
 packet.write_bytes(gzip.decompress((B/'tapes'/(row['run_id']+'.bin.gz')).read_bytes()));params.write_text(' '.join(map(str,vector(c))))
 subprocess.run([str(w/'compare'),'--dc-replay',str(packet),str(params),str(output)],check=True,env=dict(d.os.environ,BENCHMARK_LOG=str(elog)))
 return np.loadtxt(output,delimiter=',')
def score(row,a,v,j):return d.bench.score(row,evidence(a),'A'+str(j) if j<5 else 'M'+str(j-4),(v[:,15+3*j].astype(bool),v[:,16+3*j].astype(int)>>1))
def wrong_fault(rr):return sum(bool(x['wrong_localized_runtime_samples']) for x in rr if x['injected'])
def maxima_level(mm,epsilon):
 n=len(mm);rank=n if not epsilon else math.ceil((n+1)*(1-epsilon));threshold=sorted(mm)[rank-1] if rank<=n else 1e300
 return dict(rank=rank,threshold=threshold,n=n,exceedances=sum(x>threshold for x in mm))
def identify():
 d.verify();assert not (O/'benign_sensor_model.json').exists();residual=[];acceleration=[]
 for row,a in d.dataset('TRAIN'):
  if row['origin']!='NORMAL':continue
  x=a['input'];pool=np.flatnonzero(x[:,3]);idx=pool[np.unique(np.linspace(0,len(pool)-1,min(32,len(pool)),dtype=int))];y=x[:,13:16];residual.append(y[idx]-y[idx].mean(1)[:,None]);common=y.mean(1);valid=(x[2:,3]>0)&(x[1:-1,3]>0)&(x[:-2,3]>0);acceleration.extend((np.diff(common,n=2)[valid]/.01).tolist())
 residual=np.concatenate(residual);offset=residual.mean(0);pair=np.array([np.var(residual[:,i]-residual[:,j],ddof=1) for i,j in [(0,1),(0,2),(1,2)]]);variance=np.maximum(.0004,[(pair[0]+pair[1]-pair[2])/2,(pair[0]+pair[2]-pair[1])/2,(pair[1]+pair[2]-pair[0])/2]);q=max(1,float(np.median(np.square(acceleration))))
 base=dict(offset=offset.tolist(),variance=variance.tolist(),process_variance=q);candidates=[]
 for robust in [0,1]:
  values={}
  for part in ['TRAIN','CALIBRATION']:
   loss=[]
   for row,a in d.dataset(part):
    if row['origin']!='NORMAL':continue
    v=series(a['input'],dict(base,robust=robust));valid=v[:,14]>0;ll=v[:,1]-.8*np.r_[0,v[:-1,1]];loss.append(float(-np.mean(ll[valid])))
   values[part]=float(np.mean(loss))
  candidates.append(dict(robust=robust,loss=values,stability=abs(values['TRAIN']-values['CALIBRATION']),criterion=max(values.values())))
 selected=min(candidates,key=lambda c:(c['criterion'],c['stability'],c['robust']));base['robust']=selected['robust'];tails={}
 for lam in [.8,.9,.95,.98]:
  mm=[];cons=[];common=[];healthy=[]
  for row,a in d.dataset('CALIBRATION'):
   if row['origin']!='NORMAL':continue
   v=series(a['input'],dict(base,**{'lambda':lam}));valid=v[:,14]>0;mm.append(float(v[valid,6].max()));cons.append(float(v[valid,8].max()));common.append(float(v[valid,9].max()));healthy.extend((-v[valid,6]).tolist())
  halves=[float(np.quantile(mm[j::2],.995,method='higher')) for j in [0,1]]
  tails[str(lam)]=dict(levels={str(e):maxima_level(mm,e) for e in [0,.0025,.005,.01,.02]},run_maxima=mm,stability=abs(halves[0]-halves[1])/max(1,abs(halves[0]),abs(halves[1])),healthy_margin=max(math.log(99),float(np.quantile(healthy,.75))),consistency_bound=float(np.quantile(cons,.99,method='higher')),common_bound=float(np.quantile(common,.99,method='higher')))
  print('LAMBDA',lam,tails[str(lam)]['stability'],flush=True)
 lam=min(tails,key=lambda l:(tails[l]['stability'],float(l)));tt=tails[lam];base.update({'lambda':float(lam),'threshold':tt['levels']['0.005']['threshold'],**{k:tt[k] for k in ['healthy_margin','consistency_bound','common_bound']},'alpha':.1,'origin_margin':math.log(1000),'discount':0,'memory':2})
 d.dump(O/'benign_sensor_model.json',dict(selected=base,candidates=candidates,pair_variances=pair.tolist(),benign_train_frames=len(residual),variance_floor=.0004,relative_gauge='sum offsets=0; variance includes acquisition and benign legal mismatch',selection='benign TRAIN fit; benign TRAIN/CAL worst predictive NLL, tie stability and standard',registration=json.loads((B/'registration.json').read_text())))
 d.dump(B/'tails.json',tails);d.dump(B/'model.json',base);print('IDENTIFIED',base,flush=True)

def select_mapping():
 from concurrent.futures import ThreadPoolExecutor
 d.verify();base=json.loads((B/'model.json').read_text());configs=[dict(base,discount=x) for x in [0,.15,.25,.35]];results=[[] for c in configs];parity=0
 pool=ThreadPoolExecutor(max_workers=4)
 for part in ['TRAIN','CALIBRATION']:
  for i,(row,a) in enumerate(d.dataset(part)):
   if part=='CALIBRATION' and row['origin']!='NORMAL':continue
   pending=[pool.submit(core,row,c,j) for j,c in enumerate(configs)]
   for j,f in enumerate(pending):
    v=f.result();results[j].extend(dict(score(row,a,v,k),partition=part) for k in range(7))
    if j==0:
     for k,col in [(0,4),(5,6),(6,8)]:
      assert np.array_equal(v[:,15+3*k].astype(int),a['input'][:,col].astype(int)),(row['run_id'],k,'alarm')
      assert np.array_equal(v[:,16+3*k].astype(int),a['input'][:,col+1].astype(int)),(row['run_id'],k,'origin')
     parity+=1
   if (i+1)%200==0:print('DISCOUNT',part,i+1,flush=True)
 pool.shutdown();grid=[]
 for c,rr in zip(configs,results):
  by={m:{x['run_id']:x for x in rr if x['method']==m} for m in ['A0','A1','A2','A3']}
  lost=[k for k,x in by['A0'].items() if x['partition']=='TRAIN' and x['detected'] and not by['A2'][k]['detected']]
  alarms={m:sum(x['false_alarm'] for x in by[m].values() if x['partition']=='CALIBRATION') for m in by};eligible=not lost and not wrong_fault([x for x in rr if x['partition']=='TRAIN' and x['method']=='A2'])
  grid.append(dict(discount=c['discount'],eligible=eligible,train_lost=lost,cal_alarms=alarms))
 eligible=[j for j,x in enumerate(grid) if x['eligible']];chosen=min(eligible,key=lambda j:(grid[j]['cal_alarms']['A2'],configs[j]['discount'])) if eligible else 0;selected=configs[chosen]
 rr=sum([json.loads((B/(part+'_rows.json')).read_text()) for part in ['TRAIN','CALIBRATION']],[]);by={m:{x['run_id']:x for x in rr if x['method']==m} for m in ['A0','M1','M2']};mem=[]
 for m in ['M1','M2']:
  losses=[k for k,x in by['A0'].items() if x['origin']=='MEMORY' and x['detected'] and not by[m][k]['detected']];mem.append(dict(method=m,losses=losses,detected=sum(x['detected'] for x in by[m].values() if x['origin']=='MEMORY')))
 choice=min(mem,key=lambda x:(bool(x['losses']),-x['detected'],x['method']!='M2'));selected['memory']=int(choice['method'][1:])
 margin=grid[chosen]['cal_alarms']['A2']<grid[chosen]['cal_alarms']['A0'] and grid[chosen]['cal_alarms']['A2']<=12
 d.dump(B/'coherence_selection.json',dict(grid=grid,selected=chosen,memory=mem,selected_memory=choice,margin_created=margin,replay_parity_cases=parity))
 # Conditional sensitivity search is intentionally not executed without budget.
 if margin:
  selected=conditional_sensitivity(selected)
 else:
  selected['cal_gate_passed']=False;selected['selection_reason']='No legitimate total CAL<=1% budget created; fixed conservative diagnostic reference, no sensitivity search'
 d.dump(B/'selected.json',selected);print('SELECTED',selected,flush=True)
 # Dynamic features and comparator-only transforms, no rejected provider.
 for part in ['TRAIN','CALIBRATION']:
  for row,a in d.dataset(part):
   np.savez_compressed(B/'tapes'/(row['run_id']+'_dyn.npz'),stats=series(a['input'],selected))
   if selected['memory']==1:
    core(row,selected,'selected');e=d.bench.evidence(np.loadtxt(B/'work/evidence_selected.csv',delimiter=','),4)
    data=dict(a);data.update(values=e.strength,available=e.available,subset=e.origin_subset);np.savez_compressed(B/'tapes'/(row['run_id']+'.npz'),**data)

def conditional_sensitivity(base):
 from concurrent.futures import ThreadPoolExecutor
 tails=json.loads((B/'tails.json').read_text())[str(base['lambda'])]['levels']
 configs=[dict(base,alpha=alpha,threshold=tails[str(epsilon)]['threshold'],epsilon=epsilon) for alpha in [.1,.2,.3,.4] for epsilon in [0,.0025,.005]]
 records=[];pool=ThreadPoolExecutor(max_workers=4)
 # Search only inside a CAL budget already created by coherence qualification.
 for offset in range(0,len(configs),4):
  batch=configs[offset:offset+4];out=[[] for _ in batch]
  for part in ['TRAIN','CALIBRATION']:
   for row,a in d.dataset(part):
    if part=='CALIBRATION' and row['origin']!='NORMAL':continue
    futures=[pool.submit(core,row,c,j) for j,c in enumerate(batch)]
    for j,f in enumerate(futures):
     v=f.result();out[j].extend(dict(score(row,a,v,k),partition=part) for k in [0,2,3,4])
  for c,rows in zip(batch,out):
   by={m:{x['run_id']:x for x in rows if x['method']==m} for m in ['A0','A2','A3','A4']}
   cal=[x for x in by['A4'].values() if x['partition']=='CALIBRATION'];train=[x for x in by['A4'].values() if x['partition']=='TRAIN'];alarms=sum(x['false_alarm'] for x in cal);inc=sum(x['false_alarm'] and not by['A2'][x['run_id']]['false_alarm'] for x in cal);losses=[x['run_id'] for x in train if by['A0'][x['run_id']]['detected'] and not x['detected'] and (x['origin'] in ['TIMING','COMMUNICATION'] or x['origin']=='MEMORY' and x['effective_memory_corruption'])]
   records.append(dict(config=c,eligible=alarms<=12 and inc<=6 and not losses and not wrong_fault(train),cal_alarms=alarms,cal_increment=inc,train_detected=sum(x['detected'] for x in train),train_plant=sum(x['detected'] and x['plant_manifestation'] for x in train),critical_losses=losses))
 pool.shutdown();eligible=[x for x in records if x['eligible']]
 chosen=max(eligible,key=lambda x:(x['train_detected'],x['train_plant'],-x['config']['alpha'],-x['config']['epsilon'])) if eligible else None
 selected=dict(chosen['config'] if chosen else base,cal_gate_passed=bool(chosen),selection_reason='Registered conditional TRAIN sensitivity selection within CAL budget' if chosen else 'No conditional sensitivity candidate met CAL budget')
 d.dump(B/'sensitivity_grid.json',records);return selected

def comparator_features(a,c):
 # Descriptive multiscale residual features only; no parity evidence provider.
 inp=a['input'];R=np.array(c['variance']);cov=np.array([[R[0]+R[2],R[2]],[R[2],R[1]+R[2]]]);mu=np.array(c['offset'][:2])-c['offset'][2];chol=np.linalg.cholesky(cov);z=np.linalg.solve(chol,(inp[:,1:3]-mu).T).T;directions=np.linalg.solve(chol,np.array([[1,0],[0,1],[-1,-1],[1,1]]).T).T;directions/=np.linalg.norm(directions,axis=1)[:,None]
 out=np.zeros((len(inp),7));valid=inp[:,3]>0;indices=np.arange(len(inp));gaps=np.r_[False,np.diff(inp[:,0])!=100];resets=np.where(~valid,indices,np.where(gaps,indices-1,-1));count=indices-np.maximum.accumulate(resets);cs=np.vstack((np.zeros(2),np.cumsum(z,axis=0)));out[valid,0]=(z[valid]*z[valid]).sum(1)
 for w in [1,2,4,8]:
  v=(cs[w:]-cs[:-w])/np.sqrt(w);scores=(v@directions.T)**2;take=np.flatnonzero(count[w-1:]>=w);rows=take+w-1;out[rows,1:5]=np.maximum(out[rows,1:5],scores[take]);out[rows,5]=np.maximum(out[rows,5],scores[take].max(1));out[rows,6]=np.maximum(out[rows,6],(v[take]*v[take]).sum(1))
 return out

def features(a,v,c):
 # All dynamic outputs, cross-layer streams and legitimate raw sensing/context.
 return np.column_stack((d.prior.features(evidence(a)),a['input'][:,1:4],a['input'][:,13:21],comparator_features(a,c),v[:,1:15]))

def fit_svm():
 d.verify();c=json.loads((B/'selected.json').read_text());xx=[];yy=[]
 for row,a in d.dataset('TRAIN'):
  v=np.load(B/'tapes'/(row['run_id']+'_dyn.npz'))['stats'];x=features(a,v,c);y=a['target'];idx=[]
  for label in [0,1]:
   pool=np.flatnonzero(y==label)
   if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
  xx.append(x[idx]);yy.append(y[idx])
 x=np.concatenate(xx);y=np.concatenate(yy);models={};records=[]
 for kernel,C in [('linear',.1),('linear',1.),('rbf',1.)]:
  name=f'{kernel}_{C}';model=make_pipeline(StandardScaler(),SVC(kernel=kernel,C=C,gamma='scale',class_weight='balanced',cache_size=512));model.fit(x,y);assert np.allclose(model.decision_function(x[:64]),d.ml.margin(model,x[:64]),rtol=1e-8,atol=1e-8);models[name]=model;records.append(dict(name=name,frames=len(y),features=x.shape[1],support_vectors=len(model[1].support_)));print('FIT',records[-1],flush=True)
 results={k:[] for k in models};maxima={k:[] for k in models}
 for i,(row,a) in enumerate(d.dataset('CALIBRATION')):
  v=np.load(B/'tapes'/(row['run_id']+'_dyn.npz'))['stats'];x=features(a,v,c);saved={}
  for k,model in models.items():
   margin=d.ml.margin(model,x);saved[k]=margin;results[k].append(d.bench.score(row,evidence(a),k,(margin>0,np.zeros(len(margin),int))))
   if row['origin']=='NORMAL':maxima[k].append(float(margin.max()))
  np.savez_compressed(B/'tapes'/(row['run_id']+'_svm.npz'),**saved)
  if (i+1)%150==0:print('SVM CAL',i+1,flush=True)
 summaries={k:d.bench.summary(rr) for k,rr in results.items()};ks=list(models);chosen=max(ks,key=lambda k:(.5*(summaries[k]['coverage']+1-summaries[k]['benign_false_alarm_rate']),summaries[k]['coverage'],-ks.index(k)));selection=dict(model=chosen,**maxima_level(maxima[chosen],.01),cal_default=summaries[chosen]);(B/'svm.pkl').write_bytes(pickle.dumps(models[chosen],protocol=4));d.dump(B/'svm_selection.json',dict(selection=selection,candidates=summaries,training=records));print('SVM SELECTED',selection,flush=True)

def freeze():
 d.verify();assert not (B/'VALIDATION_BENIGN_started').exists();assert not (B/'lock.json').exists()
 paths=[d.ROOT/p for p in ['include/dynamic_consensus.h','src/v7_3/dynamic_consensus.c','scripts/run_dynamic_consensus.py','scripts/select_dynamic_consensus.py','scripts/report_dynamic_consensus.py','scripts/benchmark_dynamic_consensus.py','scripts/regress_dynamic_consensus.py','scripts/finalize_dynamic_consensus.py','scripts/dynamic_consensus_protocol.md','tests/test_dynamic_consensus.py']]+[B/p for p in ['specs.json','selected.json','svm_selection.json','svm.pkl','model.json','tails.json','coherence_selection.json','build_cleanup.json']]+[O/'model_definition.md',O/'benign_sensor_model.json',O/'hypothesis_definition.md']
 d.dump(B/'lock.json',{str(p.resolve()):d.sha(p) for p in paths});print('VALIDATION LOCKED',flush=True)

def evaluate(part):
 d.verify();c=json.loads((B/'selected.json').read_text());selection=json.loads((B/'svm_selection.json').read_text())['selection'];model=pickle.loads((B/'svm.pkl').read_bytes());out=[]
 for i,(row,a) in enumerate(d.dataset(part)):
  a=dict(a);v=core(row,c)
  for k,col in [(0,4),(5,6),(6,8)]:
   assert np.array_equal(v[:,15+3*k].astype(int),a['input'][:,col].astype(int)) and np.array_equal(v[:,16+3*k].astype(int),a['input'][:,col+1].astype(int)),(row['run_id'],k,'native endpoint parity')
  out.extend(score(row,a,v,j) for j in range(7));np.savez_compressed(B/'tapes'/(row['run_id']+'_evaluated.npz'),output=v)
  path=B/'tapes'/(row['run_id']+'_svm.npz');margin=np.load(path)[selection['model']] if path.exists() else d.ml.margin(model,features(a,v,c))
  for threshold,name in [(0,'default'),(selection['threshold'],'CAL1')]:out.append(d.bench.score(row,evidence(a),'SVM-DYN '+name,(margin>threshold,np.zeros(len(margin),int))))
  if (i+1)%150==0:print('EVALUATE',part,i+1,flush=True)
 d.dump(B/(part+'_evaluated.json'),out)
 if part=='VALIDATION_BENIGN':d.dump(B/'benign_gate.json',{m:d.bench.summary([x for x in out if x['method']==m]) for m in ['A0','A1','A2','A3','A4']});print('BENIGN',[(m,sum(x['false_alarm'] for x in out if x['method']==m)) for m in ['A0','A1','A2','A3','A4']],flush=True)
 print('COMPLETE EVALUATE',part,flush=True)
if __name__=='__main__':
 {'identify':identify,'mapping':select_mapping,'svm':fit_svm,'freeze':freeze}.get(sys.argv[1],lambda:evaluate(sys.argv[2]))()
