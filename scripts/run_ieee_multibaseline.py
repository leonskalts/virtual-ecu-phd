#!/usr/bin/env python3
"""Single secondary benchmark; exact frozen native architecture and SVM reused."""
import os,sys,json,csv,hashlib,pickle,collections,shutil,time,base64,zlib,subprocess
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import run_integrity_final_unseen as final
import run_benign_alarm as t
import report_benign_alarm as accounting
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from virtual_ecu import comparative_backends as be
from virtual_ecu import ieee_baselines as ib
ROOT=t.ROOT;O=ROOT/'results/ieee_multibaseline';B=Path('/tmp/clo-ieee-multibaseline')
EXE=final.B/'work/compare';METHODS=['Threshold OR','Weighted Sum','Plain DS','EWMA','CUSUM','Logistic Regression','Random Forest','Frozen SVM-INT','Original Triplex A0','CLOVER-ECU']
BINARY={'EWMA','CUSUM','Logistic Regression','Random Forest','Frozen SVM-INT'}
def dump(n,v):t.dump(O/n,v)
def stamp():return t.old.d.r.now()
def hashfile(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify(full=False):
 for n in ['scientific_hashes.json','registration_lock.json','evaluation_lock.json']:
  if (O/n).exists():
   for p,v in json.loads((O/n).read_text()).items():assert hashfile(p)==v,p
 if full:
  for p,v in json.loads((O/'preservation_hashes.json').read_text()).items():assert hashfile(p)==v,p

def design():
 ss=final.design()
 for i,s in enumerate(ss):
  s.update(run_id=f'ieee_{i:04}',partition='SECONDARY',group='ieee_'+s['group'],profile=f'ieee_profile_{i:04}',seed=3010100003+i*401,reference_seed=3110300007+i*409,c_seed=3210700011+i*419)
  pp=json.loads(s['profile_json'])
  for v in pp:v['ambient_temp_c']+=.157+i*.0000029;v['vehicle_speed_kph']+=.379+i*.0000059
  # Preserve fault durations/magnitudes/activation semantics and subtype allocation.
  # New profiles and independent seeds define new configurations; no outcome selection.
  s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=t.h.profile_identity(pp)
  s.pop('configuration_sha256',None)
  s['configuration_sha256']=hashlib.sha256(json.dumps({k:v for k,v in s.items() if k not in ['run_id','partition','group','profile']},sort_keys=True).encode()).hexdigest()
 return ss

def setup():
 assert not O.exists() and not B.exists(),'Never overwrite this study'
 # Final manifests themselves are authoritative, including the generated executable.
 final.verify()
 O.mkdir();B.mkdir()
 paths=[p for root in ['src','include','scripts','python','tests','presets','docs','rtl','results'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and O not in p.parents]
 dump('preservation_hashes.json',{str(p):hashfile(p) for p in paths})
 scientific=[p for p in paths if any(root in p.relative_to(ROOT).parts[:1] for root in ['src','include','scripts','python','tests','presets'])]+[EXE,ROOT/'Makefile',ROOT/'clo_dsf_revised.mk']
 dump('scientific_hashes.json',{str(p):hashfile(p) for p in scientific})
 ss=design();h=t.old.d.r.historical;h.OUT=B;h.B=B;h.historical_audit(ss)
 audit=list(csv.DictReader((B/'historical_overlap_audit.csv').open()));profiles={s['profile_semantic_sha256'] for s in ss};ids={s['configuration_sha256'] for s in ss};seeds={str(s[k]) for s in ss for k in ['seed','reference_seed','c_seed']}
 assert len(profiles)==1800 and len(ids)==1800 and len(seeds)==5400
 for p in [*(ROOT/'results').rglob('*.json'),*Path('/tmp').glob('clo*/specs.json')]:
  if O in p.parents or B in p.parents:continue
  try:obj=json.loads(p.read_text())
  except (ValueError,OSError):continue
  rows=obj if isinstance(obj,list) else obj.get('manifest',[]) if isinstance(obj,dict) else []
  if not isinstance(rows,list) or not rows or not isinstance(rows[0],dict):continue
  op={t.h.profile_identity(json.loads(s['profile_json'])) if s.get('profile_json') else s['profile_semantic_sha256'] for s in rows if s.get('profile_json') or s.get('profile_semantic_sha256')};oi={s['configuration_sha256'] for s in rows if s.get('configuration_sha256')};sd={str(s[k]) for s in rows for k in ['seed','reference_seed','c_seed'] if s.get(k)}
  if not(op or oi):continue
  assert not profiles&op and not ids&oi and not seeds&sd,str(p)
  audit.append(dict(source=str(p),sha256=hashfile(p),rows=len(rows),profile_identities=len(op),configuration_identities=len(oi),seeds=len(sd),profile_overlap=0,configuration_overlap=0,seed_overlap=0))
 train=[s for s in json.loads((t.old.B/'specs.json').read_text()) if s['partition'] in ['TRAIN','CALIBRATION']]
 # Exact original supervised split, labels and frame sampling, never seen validation.
 assert collections.Counter(s['partition'] for s in train)=={'TRAIN':3600,'CALIBRATION':2400}
 t.dump(B/'specs.json',ss);t.dump(B/'authorized_specs.json',train)
 t.h.write(O/'campaign_manifest.csv',ss);t.h.write(O/'overlap_audit.csv',audit)
 shutil.copy2(ROOT/'scripts/ieee_multibaseline_protocol.md',O/'protocol.md')
 model,sel,mhash=t.frozen_svm()
 dump('registration.json',dict(utc=stamp(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),git_status_before=subprocess.check_output(['git','status','--porcelain'],text=True),historical_sources=len(audit),overlap=0,cohort=1800,faults=1200,benign=600,executable=str(EXE),executable_sha256=hashfile(EXE),frozen_svm_sha256=mhash,primary_replay_feasible=False,reason='Final case sufficient statistics omit framewise evidence and features. Primary outcomes are not replayed or replaced.',training_manifest=str(t.old.O/'campaign_manifest.csv'),training_manifest_sha256=hashfile(t.old.O/'campaign_manifest.csv'),authorized_counts=dict(collections.Counter(s['partition'] for s in train))))
 locked=[O/'protocol.md',O/'campaign_manifest.csv',O/'overlap_audit.csv',O/'registration.json',B/'specs.json',B/'authorized_specs.json']
 dump('registration_lock.json',{str(p):hashfile(p) for p in locked})
 verify();print('PREREGISTERED: 1800 secondary cases, zero overlap;',len(audit),'historical sources',flush=True)

def work(part,specs):
 w=B/('work_'+part);w.mkdir();t.h.prepare_work(w,specs)
 for k,v in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('DC_INPUT','input.csv'),('DI_LOG','integrity.csv'),('BA_LOG','audit.csv')]:os.environ[k]=str(w/v)
 os.environ['PLUS_HOST_MODE']='2';os.environ['BA_CHOICE']='2';t.h.c.METHODS=['A0','M2'];t.h.c.command=lambda s,w:t.old.d.r.t.command(s,w,EXE)
 return w

def run_case(s,w):
 native=t.h.c.execute(s,w,False);a=np.loadtxt(w/'input.csv',delimiter=',');it=np.loadtxt(w/'integrity.csv',delimiter=',');q=np.loadtxt(w/'audit.csv',delimiter=',');e=t.old.d.bench.evidence(np.loadtxt(w/'benchmark.csv',delimiter=','),6)
 assert np.array_equal(a[:,0],it[:,0]) and np.array_equal(a[:,0],q[:,0]) and np.array_equal(a[:,0],e.time_ms)
 payload=dict(input=a,integrity=it[:,1:],values=e.strength,available=e.available,subset=e.origin_subset)
 x=t.old.features(payload);assert x.shape[1]==41
 for n in ['input.csv','integrity.csv','audit.csv','benchmark.csv','triplex.csv','plus_meta.csv']:(w/n).unlink()
 return native,a,it,q,e,x

def fit():
 verify();assert not (O/'training_started.json').exists();dump('training_started.json',dict(utc=stamp()))
 ss=[s for s in json.loads((B/'authorized_specs.json').read_text()) if s['partition']=='TRAIN'];w=work('TRAIN',ss);xx=[];yy=[]
 for i,s in enumerate(ss):
  native,a,it,q,e,x=run_case(s,w)
  y=np.array([s['origin']!='NORMAL' and (t.h.prior.prior.active(s,int(ms)) or t.h.prior.prior.active(s,max(0,int(ms)-99))) for ms in a[:,0]])
  idx=[]
  for label in [0,1]:
   pool=np.flatnonzero(y==label)
   if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
  xx.append(x[idx]);yy.append(y[idx])
  if (i+1)%150==0:print('AUTHORIZED TRAIN',i+1,'/3600',flush=True)
 x=np.concatenate(xx);y=np.concatenate(yy);models={}
 for C in [.1,1.,10.]:
  model=make_pipeline(StandardScaler(),LogisticRegression(C=C,class_weight='balanced',max_iter=2000,random_state=20261008));model.fit(x,y);models['LR_'+str(C)]=model
 for depth in [8,None]:
  for leaf in [2,8]:
   model=RandomForestClassifier(n_estimators=100,max_depth=depth,min_samples_leaf=leaf,max_features='sqrt',class_weight='balanced',n_jobs=1,random_state=20261008);model.fit(x,y);models[f'RF_{depth}_{leaf}']=model
 (B/'models.pkl').write_bytes(pickle.dumps(models,protocol=4));dump('training_record.json',dict(utc=stamp(),runs=len(ss),frames=len(y),features=x.shape[1],positives=int(y.sum()),models=list(models),source='Exact original SVM-INT TRAIN configurations and identical at-most-eight frames/class/run sampling; labels used for fitting only.'))
 shutil.rmtree(w);print('FITTED',list(models),flush=True)

def scores(e,x,models):
 out={f'WS_{j}':ib.weighted_score(e,w) for j,w in enumerate(be.WEIGHTS)}
 for alpha in [.1,.3,.6]:out['EWMA_'+str(alpha)]=ib.ewma(e.values,alpha)
 for k in [.05,.15]:out['CUSUM_'+str(k)]=ib.cusum(e.values,k)
 for name,m in models.items():out[name]=m.decision_function(x) if name.startswith('LR') else m.predict_proba(x)[:,1]
 return out

def family(name):return 'Logistic Regression' if name.startswith('LR') else 'Random Forest' if name.startswith('RF') else 'Weighted Sum' if name.startswith('WS') else name.split('_')[0]

def calibrate():
 verify();assert not (O/'calibration_started.json').exists();dump('calibration_started.json',dict(utc=stamp()))
 ss=[s for s in json.loads((B/'authorized_specs.json').read_text()) if s['partition']=='CALIBRATION'];w=work('CAL',ss);cache=B/'cal_scores';cache.mkdir();models=pickle.loads((B/'models.pkl').read_bytes());maxima=collections.defaultdict(list)
 for i,s in enumerate(ss):
  native,a,it,q,e,x=run_case(s,w);sscores=scores(e,x,models)
  if s['origin']=='NORMAL':
   for n,v in sscores.items():maxima[n].append(float(v.max()))
  np.savez_compressed(cache/(s['run_id']+'.npz'),time=e.time_ms,**sscores)
  if (i+1)%150==0:print('AUTHORIZED CAL',i+1,'/2400',flush=True)
 grid={}
 for name in sscores:
  if name.startswith('WS'):thresholds=list(be.THRESHOLDS)
  elif name.startswith('EWMA'):thresholds=[.1,.25,.5]
  elif name.startswith('CUSUM'):thresholds=[.25,.5,1.,2.]
  else:
   z=sorted(maxima[name]);thresholds=[0. if name.startswith('LR') else .5,z[-1],z[-1-int(.005*len(z))],z[-1-int(.01*len(z))]]
  grid[name]=sorted(set(thresholds))
 records={(n,v):dict(candidate=n,method=family(n),threshold=v,detected=0,benign=0) for n,vs in grid.items() for v in vs}
 # Calibration operating point uses run-level false alarms and edge-based recall.
 for s in ss:
  with np.load(cache/(s['run_id']+'.npz')) as a:
   for (n,v),r in records.items():
    det,alarm=ib.detect_edges(a[n],v,a['time'],s['start_ms'])
    r['detected']+=int(s['origin']!='NORMAL' and det);r['benign']+=int(s['origin']=='NORMAL' and alarm)
 selected={}
 for m in ['Weighted Sum','EWMA','CUSUM','Logistic Regression','Random Forest']:
  rs=[r for r in records.values() if r['method']==m];eligible=[r for r in rs if r['benign']<=12]
  winner=min(eligible,key=lambda r:(-r['detected'],r['benign'],r['candidate'],r['threshold'])) if eligible else min(rs,key=lambda r:(r['benign'],-r['detected'],r['candidate'],r['threshold']))
  selected[m]=dict(winner,benign_gate_met=bool(eligible))
 t.h.write(O/'calibration_candidates.csv',list(records.values()));dump('selection.json',dict(selected=selected,rule='<=1% CAL benign, then maximum CAL fault edge detection, then fewer benign, then lexical candidate and threshold; if infeasible minimum benign then maximum detection',utc=stamp(),faults=1200,benign=1200))
 chosen={v['candidate']:models[v['candidate']] for k,v in selected.items() if k in ['Logistic Regression','Random Forest']}
 (O/'baseline_models.pkl').write_bytes(pickle.dumps(chosen,protocol=4))
 shutil.rmtree(cache);shutil.rmtree(w);(B/'models.pkl').unlink()
 dump('evaluation_lock.json',{str(p):hashfile(p) for p in [O/'selection.json',O/'baseline_models.pkl',O/'training_record.json',O/'calibration_candidates.csv']});verify();print('LOCKED BASELINES',selected,flush=True)

def predictions(e,x,models,selection,svm):
 yield 'Threshold OR',lambda:be.simple_or(e)
 def weighted():
  s=selection['Weighted Sum'];j=int(s['candidate'].split('_')[1]);alarm,origin=be.weighted_sum(e,be.WEIGHTS[j],s['threshold']);return ib.weighted_score(e,be.WEIGHTS[j])>s['threshold'],origin
 yield 'Weighted Sum',weighted
 yield 'Plain DS',lambda:be.plain_ds(e)
 for m in ['EWMA','CUSUM','Logistic Regression','Random Forest']:
  def infer(m=m):
   s=selection[m];n=s['candidate']
   if m=='EWMA':v=ib.ewma(e.values,float(n.split('_')[1]))
   elif m=='CUSUM':v=ib.cusum(e.values,float(n.split('_')[1]))
   elif m=='Logistic Regression':v=models[n].decision_function(x)
   else:v=models[n].predict_proba(x)[:,1]
   return v>s['threshold'],np.zeros(len(v),int)
  yield m,infer
 yield 'Frozen SVM-INT',lambda:(t.old.d.ml.margin(svm,x)>0,np.zeros(len(x),int))

def evaluate():
 verify(full=True);assert not (O/'execution_started.json').exists(),'NO RERUN'
 assert (O/'evaluation_lock.json').exists();dump('execution_started.json',dict(utc=stamp()))
 ss=json.loads((B/'specs.json').read_text());w=work('SECONDARY',ss);models=pickle.loads((O/'baseline_models.pkl').read_bytes());selection=json.loads((O/'selection.json').read_text())['selected'];svm,_,mhash=t.frozen_svm();assert mhash==json.loads((O/'registration.json').read_text())['frozen_svm_sha256']
 rr=[];overhead=collections.defaultdict(lambda:dict(cpu_seconds=0.,frames=0,runs=0))
 for i,s in enumerate(ss):
  native,a,it,q,e,x=run_case(s,w);base=next(r for r in native if r['method']=='M2');a0=next(r for r in native if r['method']=='A0');a0['method']='Original Triplex A0'
  active=np.array([t.h.prior.prior.active(s,int(ms)) for ms in a[:,0]]);axis=18 if s['model']=='fan_stuck_off' else 17
  meta=dict(integrity_observed=int(np.any(it[:,2])),actuator_excited=int(s['origin']=='ACTUATOR' and np.any(a[active,axis]>0)),active_probe_samples=int(np.count_nonzero(active&(np.r_[0,np.diff(a[:,12])]>0))))
  base.update(meta);a0.update(meta);rr.append(a0)
  bypass=(q[:,1]!=7)|(q[:,2]>0)|(q[:,3]>0)|(q[:,4]>0)|(q[:,22]>0)
  assert np.array_equal(q[bypass,25],q[bypass,20]) and not np.any((q[:,25]>0)&(q[:,20]==0))
  alarm=q[:,25]>0;origin=np.where(alarm,q[:,21].astype(int)>>1,0);rr.append(t.old.d.bench.score(base,e,'CLOVER-ECU',(alarm,origin)))
  for method,infer in predictions(e,x,models,selection,svm):
   begin=time.process_time();pred=infer();elapsed=time.process_time()-begin
   overhead[method]['cpu_seconds']+=elapsed;overhead[method]['frames']+=len(x);overhead[method]['runs']+=1
   rr.append(t.old.d.bench.score(base,e,method,pred))
  if (i+1)%100==0:print('SECONDARY',i+1,'/1800',flush=True)
 t.dump(B/'rows.json',rr);dump('overhead.json',dict(scope='Single-pass Python batch inference CPU only, includes model dispatch/allocation and DS localization; excludes feature/provider production, simulator, logging and scoring. Native A0/A2 lack isolated final-core timing in unchanged executable: not measured, no cross-language speed ranking.',measurements=dict(overhead),host=subprocess.check_output(['uname','-a'],text=True).strip()))
 shutil.rmtree(w);verify();dump('execution_complete.json',dict(utc=stamp(),cases=1800));print('SECONDARY COMPLETE',flush=True)

def stats(rows):
 s=accounting.stats(rows)
 if rows and rows[0]['method'] in BINARY:
  for k in list(s):
   if any(x in k for x in ['localiz','unknown','runtime_','wrong_fault']):s[k]=None
  s['localization_provided']=False
 return s

def report():
 assert (O/'execution_complete.json').exists();verify();rr=json.loads((B/'rows.json').read_text())
 sums=[dict(method=m,**stats([r for r in rr if r['method']==m])) for m in METHODS]
 t.h.write(O/'summary.csv',sums)
 sub=[dict(method=m,origin=o,**stats([r for r in rr if r['method']==m and r['origin']==o])) for m in METHODS for o in be.ORIGINS];t.h.write(O/'per_origin.csv',sub)
 loc=[dict(method=m,**stats([r for r in rr if r['method']==m and r['injected']])) for m in METHODS];t.h.write(O/'localization.csv',loc)
 pairs=[t.old.common.pair(rr,'CLOVER-ECU',m,endpoint) for m in METHODS if m!='CLOVER-ECU' for endpoint in ['fault','benign']]
 for p in pairs:
  if not p['discordant']:p['mcnemar_exact_p']=1.
 # Holm controls the eight primary algorithm comparisons, separately by endpoint.
 for endpoint in ['fault','benign']:
  ordered=sorted([p for p in pairs if p['endpoint']==endpoint and p['method_b']!='Original Triplex A0'],key=lambda p:p['mcnemar_exact_p']);running=0
  for i,p in enumerate(ordered):
   running=max(running,min(1.,(len(ordered)-i)*p['mcnemar_exact_p']));p['holm_p']=running;p['mcnemar_scope']='Exact paired, Holm over eight primary algorithm comparisons per endpoint; grouped simulator inference remains descriptive'
 for p in pairs:
  if p['method_b']=='Original Triplex A0':p['holm_p']=None;p['mcnemar_scope']='Separate architecture ablation, exact paired descriptive test'
 t.h.write(O/'paired.csv',pairs)
 fields=['run_id','method','origin','model','behavior','domain','kind','duration_ms','injected','detected','false_alarm','latency_ms','plant_manifestation','silent_plant','integrity_observed','actuator_excited','effective_memory_corruption','active_probe_samples','first_origin','origin_at_alarm','alarm_samples','wrong_localized_runtime_samples','alarm_UNKNOWN']
 t.h.write(O/'case_metrics.csv',[{k:r.get(k) for k in fields} for r in rr])
 filters={'integrity_observable':lambda r:r['injected'] and r['integrity_observed'],'unexcited_actuator':lambda r:r['origin']=='ACTUATOR' and not r['actuator_excited'],'dormant_memory':lambda r:r['origin']=='MEMORY' and not r['effective_memory_corruption'],'weak_steps':lambda r:r['origin']=='SENSOR_CONTROL' and r['kind']=='step','pulses':lambda r:r['origin']=='SENSOR_CONTROL' and r['kind']=='pulse','common_mode':lambda r:r['origin']=='SENSOR_CONTROL' and r['domain'] in ['AB','ABC']}
 t.h.write(O/'subgroups.csv',[dict(method=m,subgroup=g,**stats([r for r in rr if r['method']==m and f(r)])) for m in METHODS for g,f in filters.items()])
 table=['# IEEE secondary multi-baseline benchmark','', 'CLOVER-ECU is the publication name of frozen refined A2; source/result identifiers remain unchanged. This is a new secondary cohort, not a replacement or extension of the primary final unseen.','', '| Method | Detection (95% Wilson CI) | Benign /600 | Precision | Plant | Silent | Median/P95 ms |','|---|---|---|---|---|---|---|']
 for s in sums:table.append(f"| {s['method']} | {s['detected']}/1200; {100*s['coverage']:.2f}% ({100*s['ci_low']:.2f}–{100*s['ci_high']:.2f}) | {s['benign_false_alarms']} | {100*s['precision']:.2f}% | {s['plant_detected']}/{s['plant_manifestation_runs']} | {s['silent_plant']} | {s['latency_median_ms']}/{s['latency_p95_ms']} |")
 table+=['','All decision backends share frozen provider preprocessing including integrity and M2. OR/WS/DS/EWMA/CUSUM intentionally reduce the shared runtime input to six bounded provider streams; supervised methods receive the original 41 runtime features. This equal provider availability is not an identical feature representation or a raw-signal algorithm benchmark. No A2 alarm/origin or metadata is an inference input. Original A0 is an architecture ablation lacking the additions.','', 'OR and Plain DS use original fixed .5 criteria; WS and sequential baselines have CAL-selected thresholds. LR/RF use exactly the original SVM TRAIN configurations/frame sampling, and original CAL configurations; SVM parameters/threshold are untouched. Selection and evaluation cohort were locked before secondary outcomes.','', 'EWMA and CUSUM monitor anomaly-strength streams (not Gaussian physical residuals); no theoretical average-run-length claim. LR/RF/EWMA/CUSUM/SVM have no localization head. OR/WS/DS retain existing limited origin rules; detailed conditional localization and errors are reported separately.','', 'Detection uses the established first post-onset rising edge. Sustained pre-onset alarms can mask later detection; benign alarms and precision must be read with recall. Latency is conditional on detected runs; paired jointly detected faster/equal/slower counts are in paired.csv.','', 'Exact McNemar p-values and Holm corrections are descriptive for correlated simulator families. A greater raw count alone is not a superiority claim. Host Python batch overhead is not embedded WCET and cannot be ranked against unmeasured native A2. Common-mode corruption of both data and trusted witness, physical pre-protection faults, field reliability and independent simulator validation remain outside coverage.','', 'Historical comparative results, primary integrity_final_unseen, frozen_robustness and this secondary benchmark remain separate evidence; no cross-cohort subtraction as paired improvement.']
 (O/'comparison_table.md').write_text('\n'.join(table)+'\n');dump('report.json',dict(summary=sums,paired=pairs,excluded=[],promoted=True))
 print('\n'.join(table[:16]),flush=True)

def finish():
 verify(full=True)
 import regress_digital_integrity as regression
 t.old.B=B;t.old.O=O;t.old.verify=verify
 regression.main();verify(full=True)
 reg=json.loads((O/'regression.json').read_text());(O/'validation_record.md').write_text('# Validation record\n\nFrozen architecture, SVM, previous results, Hybrid/HETIA and GUI verified unchanged before/after. One locked secondary execution, no tuning or reruns after outcomes. Authorized TRAIN/CAL reconstruction is selection data only.\n\n'+json.dumps(reg,indent=2)+'\n\n'+(B/'tests.log').read_text())
 (B/'rows.json').unlink();shutil.rmtree(B/'binary_backup')
 dump('artifact_hashes.json',{p.name:hashfile(p) for p in O.iterdir() if p.is_file() and p.name!='artifact_hashes.json'})
 print('REGRESSION AND PRESERVATION COMPLETE',flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
