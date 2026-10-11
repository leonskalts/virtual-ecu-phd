#!/usr/bin/env python3
"""Preregistered origin-aware RF challenger; frozen detector objects reused."""
import os,sys,json,csv,hashlib,pickle,collections,shutil,time,subprocess,tarfile,io
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
import run_ieee_multibaseline as old
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from virtual_ecu import origin_rf as rf
ROOT=old.ROOT;B=Path('/tmp/clo-origin-rf');O=ROOT/'results/ieee_origin_rf'
t=old.t;final=old.final;EXE=B/'instrumentation/compare';METHODS=['CLOVER-ECU','Origin RF','Frozen SVM-INT']
def dump(n,v):t.dump(O/n,v)
def verify(full=False):
 for n in ['scientific_hashes.json','registration_lock.json','evaluation_lock.json']:
  if (O/n).exists():
   for p,v in json.loads((O/n).read_text()).items():assert old.hashfile(p)==v,p
 if full:
  for p,v in json.loads((O/'preservation_hashes.json').read_text()).items():assert old.hashfile(p)==v,p

def design():
 ss=final.design()
 for i,s in enumerate(ss):
  s.update(run_id=f'orf_{i:04}',partition='SECONDARY',group='orf_'+s['group'],profile=f'orf_profile_{i:04}',seed=3310100003+i*421,reference_seed=3410300007+i*431,c_seed=3510700011+i*433)
  pp=json.loads(s['profile_json'])
  for v in pp:v['ambient_temp_c']+=.269+i*.0000033;v['vehicle_speed_kph']+=.457+i*.0000061
  s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=t.h.profile_identity(pp);s.pop('configuration_sha256',None)
  s['configuration_sha256']=hashlib.sha256(json.dumps({k:v for k,v in s.items() if k not in ['run_id','partition','group','profile']},sort_keys=True).encode()).hexdigest()
 return ss

def instrument():
 w=B/'instrumentation';w.mkdir();source=final.B/'work/adapter.c';s=source.read_text()
 expressions=['o->'+x for x in rf.OBS]+['o->timing.'+x for x in rf.TIMING]+['diagnostic_c.output.'+x for x in rf.C]
 expressions+=['triplex_extra_strength','triplex_extra_ambiguous','triplex.qualified','triplex.aligned_c','qualified','local','ba_current->available','ba_current->bad','ba_current->status[0]','ba_current->status[1]','ba_current->status[2]','di_strength(ba_current->owner,o->time_ms)']
 assert len(expressions)==len(rf.FIELDS)
 function='\nstatic void orf_capture(const runtime_observation_t *o,double qualified,double local){\n static FILE *out; if(!out){out=fopen(getenv("ORF_INPUT"),"w");if(!out)abort();}\n double values[]={'+','.join('(double)('+x+')' for x in expressions)+'};\n for(unsigned i=0;i<sizeof(values)/sizeof(values[0]);i++)fprintf(out,i?",%.17g":"%.17g",values[i]);fputc(\'\\n\',out);\n}\n'
 needle='static FILE *benchmark_log;';assert s.count(needle)==1;s=s.replace(needle,'static void orf_capture(const runtime_observation_t *,double,double);\n'+needle)
 needle=' if(arch==0)return;arch=plus_arch;';assert s.count(needle)==1;s=s.replace(needle,needle+'\n if(arch==6)orf_capture(o,origin_local,local);')
 needle='static di_bank_t *ba_current;';assert s.count(needle)==1;s=s.replace(needle,needle+function)
 p=w/'adapter.c';p.write_text(s)
 subprocess.run(['gcc','-O2','-Iinclude','-c',str(p),'-o',str(w/'adapter.o')],check=True)
 objs=[str(p) for p in (final.B/'work').glob('*.o') if p.name not in ['adapter.o','dynamic_consensus.o']]+[str(w/'adapter.o')]+[str(p) for p in (ROOT/'src').glob('*.o') if p.name not in ['main.o','diagnostic_temperature.o']]+[str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o']]
 cmd=['gcc',*objs,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-Wl,--wrap=redundant_temperature_sample','-Wl,--wrap=diagnostic_temperature_sample','-lm','-o',str(EXE)];subprocess.run(cmd,check=True)
 dump('instrumentation.json',dict(source=str(source),source_hash=old.hashfile(source),logging_adapter=str(p),logging_adapter_hash=old.hashfile(p),executable_hash=old.hashfile(EXE),link_command=cmd,object_hashes={v:old.hashfile(v) for v in objs},change='Three logging-only insertions in temporary adapter. All frozen detector/provider objects linked unchanged; no candidate algorithm copy.'))

def setup():
 assert not B.exists() and not O.exists();old.verify(full=True);B.mkdir();O.mkdir()
 paths=[p for root in ['src','include','scripts','python','tests','presets','docs','rtl','results'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and O not in p.parents]
 dump('preservation_hashes.json',{str(p):old.hashfile(p) for p in paths})
 dump('scientific_hashes.json',{str(p):old.hashfile(p) for p in paths if p.relative_to(ROOT).parts[0] in ['src','include','scripts','python','tests','presets']})
 ss=design();hist=t.old.d.r.historical;hist.OUT=B;hist.B=B;hist.historical_audit(ss);audit=list(csv.DictReader((B/'historical_overlap_audit.csv').open()))
 profiles={s['profile_semantic_sha256'] for s in ss};ids={s['configuration_sha256'] for s in ss};seeds={str(s[k]) for s in ss for k in ['seed','reference_seed','c_seed']};assert len(ids)==1800 and len(profiles)==1800 and len(seeds)==5400
 for p in [*(ROOT/'results').rglob('*.json'),*Path('/tmp').glob('clo*/specs.json')]:
  if B in p.parents or O in p.parents:continue
  try:obj=json.loads(p.read_text())
  except (ValueError,OSError):continue
  rows=obj if isinstance(obj,list) else obj.get('manifest',[]) if isinstance(obj,dict) else []
  if not isinstance(rows,list) or not rows or not isinstance(rows[0],dict):continue
  op={t.h.profile_identity(json.loads(x['profile_json'])) if x.get('profile_json') else x['profile_semantic_sha256'] for x in rows if x.get('profile_json') or x.get('profile_semantic_sha256')};oi={x['configuration_sha256'] for x in rows if x.get('configuration_sha256')};sd={str(x[k]) for x in rows for k in ['seed','reference_seed','c_seed'] if x.get(k)}
  if not(op or oi):continue
  assert not profiles&op and not ids&oi and not seeds&sd,str(p)
  audit.append(dict(source=str(p),sha256=old.hashfile(p),rows=len(rows),profile_identities=len(op),configuration_identities=len(oi),seeds=len(sd),profile_overlap=0,configuration_overlap=0,seed_overlap=0))
 train=[s for s in json.loads((t.B/'specs.json').read_text()) if s['partition'] in ['TRAIN','CALIBRATION']]
 assert collections.Counter(s['partition'] for s in train)=={'TRAIN':2400,'CALIBRATION':2400}
 t.dump(B/'specs.json',ss);t.dump(B/'authorized_specs.json',train);t.h.write(O/'campaign_manifest.csv',ss);t.h.write(O/'overlap_audit.csv',audit)
 shutil.copy2(ROOT/'scripts/origin_rf_protocol.md',O/'protocol.md');dump('input_schema.json',rf.schema());instrument()
 _,_,mhash=t.frozen_svm();dump('registration.json',dict(utc=old.stamp(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),git_status=subprocess.check_output(['git','status','--porcelain'],text=True),cases=1800,faults=1200,benign=600,historical_sources=len(audit),overlap=0,training_manifest=str(t.O/'campaign_manifest.csv'),training_manifest_hash=old.hashfile(t.O/'campaign_manifest.csv'),frozen_svm_hash=mhash,original_executable_hash=old.hashfile(final.B/'work/compare')))
 locked=[O/n for n in ['protocol.md','input_schema.json','campaign_manifest.csv','overlap_audit.csv','registration.json','instrumentation.json']]+[B/'specs.json',B/'authorized_specs.json',EXE,B/'instrumentation/adapter.c',B/'instrumentation/adapter.o']
 dump('registration_lock.json',{str(p):old.hashfile(p) for p in locked});verify();print('REGISTERED 1800 cases; historical sources',len(audit),'overlap ZERO',flush=True)

def work(part,ss,exe=EXE):
 old.B=B;old.EXE=exe;w=old.work(part,ss);os.environ['ORF_INPUT']=str(w/'upstream.csv');return w

def run(s,w,packet=True):
 native,a,it,q,e,xold=old.run_case(s,w)
 p=np.loadtxt(w/'upstream.csv',delimiter=',') if packet else None
 if packet:assert np.array_equal(p[:,0],e.time_ms);(w/'upstream.csv').unlink()
 return native,a,it,q,e,xold,p

def parity():
 verify();assert not (O/'parity_started.json').exists();dump('parity_started.json',dict(utc=old.stamp()))
 train=[s for s in json.loads((B/'authorized_specs.json').read_text()) if s['partition']=='TRAIN'];ss=[]
 for origin in rf.CLASSES:
  # Spread across the authorized TRAIN partition, fixed before outcomes.
  z=[s for s in train if s['origin']==origin];ss.extend(z[j] for j in np.linspace(0,len(z)-1,4,dtype=int))
 w0=work('PARITY_ORIGINAL',ss,final.B/'work/compare');w1=work('PARITY_INSTRUMENTED',ss,EXE);out=[]
 for s in ss:
  def activate(w,exe):
   for k,v in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('DC_INPUT','input.csv'),('DI_LOG','integrity.csv'),('BA_LOG','audit.csv'),('ORF_INPUT','upstream.csv')]:os.environ[k]=str(w/v)
   t.h.c.command=lambda s,w:t.old.d.r.t.command(s,w,exe)
  activate(w0,final.B/'work/compare');n0,a0,i0,q0,e0,x0,_=run(s,w0,False)
  activate(w1,EXE);n1,a1,i1,q1,e1,x1,p=run(s,w1)
  assert n0==n1,s['run_id']
  for v0,v1 in [(a0,a1),(i0,i1),(q0,q1),(e0.strength,e1.strength),(e0.available,e1.available),(e0.origin_subset,e1.origin_subset),(x0,x1)]:assert np.array_equal(v0,v1,equal_nan=True),s['run_id']
  assert np.isfinite(rf.features(p,e1)).all();out.append(dict(run_id=s['run_id'],origin=s['origin'],exact_native_metric_and_all_original_stream_parity=True,raw_sha256=n0[0]['raw_sha256'],runtime_trace_sha256=n0[0]['runtime_trace_sha256']))
 t.h.write(O/'instrumentation_parity.csv',out);shutil.rmtree(w0);shutil.rmtree(w1);dump('parity_complete.json',dict(utc=old.stamp(),cases=len(ss)));print('PARITY PASSED',len(ss),flush=True)

def fit():
 verify();assert (O/'parity_complete.json').exists() and not (O/'training_started.json').exists();dump('training_started.json',dict(utc=old.stamp()))
 ss=[s for s in json.loads((B/'authorized_specs.json').read_text()) if s['partition']=='TRAIN'];w=work('TRAIN',ss);xx=[];yy=[]
 for i,s in enumerate(ss):
  native,a,it,q,e,xold,p=run(s,w);x=rf.features(p,e)
  active=np.array([s['origin']!='NORMAL' and (t.h.prior.prior.active(s,int(ms)) or t.h.prior.prior.active(s,max(0,int(ms)-99))) for ms in e.time_ms])
  y=np.where(active,rf.CLASSES.index(s['origin']),0);idx=[]
  for label in np.unique(y):
   pool=np.flatnonzero(y==label);idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,16,dtype=int))])
  xx.append(x[idx]);yy.append(y[idx])
  if (i+1)%150==0:print('TRAIN',i+1,'/2400',flush=True)
 x=np.concatenate(xx);y=np.concatenate(yy);models={}
 for depth in [12,None]:
  for leaf in [4,16]:
   model=RandomForestClassifier(n_estimators=200,max_depth=depth,min_samples_leaf=leaf,max_features='sqrt',class_weight='balanced',n_jobs=1,random_state=20261009);model.fit(x,y);assert np.array_equal(model.classes_,np.arange(6));models[f'RF_{depth}_{leaf}']=model
   print('FIT',depth,leaf,flush=True)
 (B/'models.pkl').write_bytes(pickle.dumps(models,protocol=4));dump('training_record.json',dict(utc=old.stamp(),runs=len(ss),frames=len(y),features=x.shape[1],classes=dict(collections.Counter(map(int,y))),models=list(models),feature_matrix_hash=hashlib.sha256(x.tobytes()).hexdigest(),label_hash=hashlib.sha256(y.tobytes()).hexdigest()))
 shutil.rmtree(w)

def calibrate():
 verify();assert not (O/'calibration_started.json').exists();dump('calibration_started.json',dict(utc=old.stamp()))
 ss=[s for s in json.loads((B/'authorized_specs.json').read_text()) if s['partition']=='CALIBRATION'];w=work('CAL',ss);models=pickle.loads((B/'models.pkl').read_bytes());cache=B/'cal_scores';cache.mkdir();maxima=collections.defaultdict(list)
 for i,s in enumerate(ss):
  native,a,it,q,e,xold,p=run(s,w);x=rf.features(p,e);probs={k:m.predict_proba(x) for k,m in models.items()}
  if s['origin']=='NORMAL':
   for k,pr in probs.items():maxima[k].append(float((1-pr[:,0]).max()))
  np.savez_compressed(cache/(s['run_id']+'.npz'),time=e.time_ms,**probs)
  if (i+1)%150==0:print('CAL',i+1,'/2400',flush=True)
 thresholds={k:max(v) for k,v in maxima.items()};records={}
 for k in models:
  for conf in [.5,.7,.85,.95,.99,1.,1.000001]:
   for margin in [0.,.1,.2]:records[k,conf,margin]=dict(candidate=k,alarm_threshold=thresholds[k],confidence=conf,margin=margin,detected=0,benign=0,first_localized=0,first_correct=0,first_wrong=0,runtime_localized=0,runtime_wrong=0)
 for s in ss:
  truth=rf.CLASSES.index(s['origin']);bit=1<<(truth-1) if truth else 0
  with np.load(cache/(s['run_id']+'.npz')) as a:
   for (k,conf,margin),r in records.items():
    alarm,orig=rf.decisions(a[k],r['alarm_threshold'],conf,margin);edges=alarm&~np.r_[False,alarm[:-1]];post=np.flatnonzero(edges&(a['time']>=s['start_ms']))
    if truth:
     r['detected']+=int(len(post)>0)
     if len(post) and orig[post[0]]:
      r['first_localized']+=1;r['first_correct']+=int(orig[post[0]]==bit);r['first_wrong']+=int(orig[post[0]]!=bit)
     r['runtime_localized']+=int(np.count_nonzero(orig));r['runtime_wrong']+=int(np.count_nonzero((orig!=0)&(orig!=bit)))
    else:r['benign']+=int(alarm.any())
 eligible=[r for r in records.values() if r['benign']==0 and r['first_wrong']==0 and r['runtime_wrong']==0]
 assert eligible # confidence>1 provides explicitly documented abstain-all fallback
 winner=min(eligible,key=lambda r:(-r['detected'],-r['first_correct'],-r['runtime_localized'],list(models).index(r['candidate']),r['confidence'],r['margin']))
 dump('selection.json',dict(utc=old.stamp(),selected=winner,rule='Zero CAL benign and zero confident CAL first/runtime origin errors; maximize detected faults then correct first-localized cases then localized samples, then predefined candidate order and confidence/margin.',faults=1200,benign=1200))
 t.h.write(O/'calibration_candidates.csv',list(records.values()));(O/'rf_model.pkl').write_bytes(pickle.dumps(models[winner['candidate']],protocol=4))
 shutil.rmtree(cache);shutil.rmtree(w);(B/'models.pkl').unlink()
 dump('evaluation_lock.json',{str(p):old.hashfile(p) for p in [O/'selection.json',O/'rf_model.pkl',O/'training_record.json',O/'calibration_candidates.csv',O/'instrumentation_parity.csv',O/'parity_complete.json']});verify();print('LOCKED',winner,flush=True)

def evaluate():
 verify(full=True);assert (O/'evaluation_lock.json').exists() and not (O/'execution_started.json').exists();dump('execution_started.json',dict(utc=old.stamp()))
 ss=json.loads((B/'specs.json').read_text());w=work('SECONDARY',ss);model=pickle.loads((O/'rf_model.pkl').read_bytes());sel=json.loads((O/'selection.json').read_text())['selected'];svm,_,mhash=t.frozen_svm();assert mhash==json.loads((O/'registration.json').read_text())['frozen_svm_hash'];rr=[];cpu=0;frames=0
 archive=tarfile.open(O/'runtime_evidence.tar.gz','w:gz')
 try:
  for i,s in enumerate(ss):
   native,a,it,q,e,xold,p=run(s,w);base=next(r for r in native if r['method']=='M2');base.update(integrity_observed=int(np.any(it[:,2])))
   alarm=q[:,25]>0;orig=np.where(alarm,q[:,21].astype(int)>>1,0);preds={'CLOVER-ECU':(alarm,orig)}
   x=rf.features(p,e);begin=time.process_time();pr=model.predict_proba(x);preds['Origin RF']=rf.decisions(pr,sel['alarm_threshold'],sel['confidence'],sel['margin']);cpu+=time.process_time()-begin;frames+=len(x)
   svm_margin=t.old.d.ml.margin(svm,xold);preds['Frozen SVM-INT']=(svm_margin>0,np.zeros(len(x),int))
   for m,pred in preds.items():
    row=t.old.d.bench.score(base,e,m,pred)
    first=np.flatnonzero(pred[0]);value=int(pred[1][first[0]]) if len(first) else 0
    row['global_first_origin']=rf.CLASSES[value.bit_length()] if value and not(value&(value-1)) else 'UNKNOWN'
    rr.append(row)
   # Lossless upstream numeric packet and provider outputs, separate from predictions.
   # One compact member/case, transposed for compressibility; no physical truth trace.
   stream=io.BytesIO();np.savez(stream,upstream=p.T.copy(),strength=e.strength.T.copy(),available=e.available.T.copy(),origin_support=e.origin_subset.T.copy(),svm_features=xold.T.copy(),rf_probability=pr.T.copy(),clover_alarm=alarm,clover_origin=orig,svm_margin=svm_margin)
   content=stream.getvalue();member=tarfile.TarInfo(s['run_id']+'.npz');member.size=len(content);member.mtime=0;archive.addfile(member,io.BytesIO(content))
   if (i+1)%100==0:print('SECONDARY',i+1,'/1800',flush=True)
 finally:archive.close()
 t.dump(B/'rows.json',rr);dump('runtime_record.json',dict(cpu_seconds=cpu,frames=frames,microseconds_per_frame=cpu*1e6/frames,scope='One-pass RF batch inference and alarm/UNKNOWN logic; excludes shared providers/features; not native CLOVER WCET.',packet_fields=rf.FIELDS,feature_count=x.shape[1],archive_sha256=old.hashfile(O/'runtime_evidence.tar.gz')))
 shutil.rmtree(w);verify();dump('execution_complete.json',dict(utc=old.stamp(),cases=1800))

def summarize(rows):
 s=old.stats(rows);det=[r for r in rows if r['injected'] and r['detected']]
 if rows and rows[0]['method']!='Frozen SVM-INT':
  localized=[r for r in det if r['origin_at_alarm']!='UNKNOWN'];correct=sum(r['origin_at_alarm']==r['origin'] for r in localized)
  s.update(first_alarm_localized=len(localized),first_alarm_correct=correct,first_alarm_wrong=len(localized)-correct,first_alarm_unknown=len(det)-len(localized),first_alarm_coverage=len(localized)/len(det) if det else None,first_alarm_accuracy=correct/len(localized) if localized else None)
 else:s.update(first_alarm_localized=None,first_alarm_correct=None,first_alarm_wrong=None,first_alarm_unknown=None,first_alarm_coverage=None,first_alarm_accuracy=None)
 return s

def report():
 verify();assert (O/'execution_complete.json').exists();rr=json.loads((B/'rows.json').read_text());summary=[dict(method=m,**summarize([r for r in rr if r['method']==m])) for m in METHODS];t.h.write(O/'summary.csv',summary)
 t.h.write(O/'per_origin.csv',[dict(method=m,origin=o,**summarize([r for r in rr if r['method']==m and r['origin']==o])) for m in METHODS for o in rf.CLASSES])
 common=set.intersection(*[{r['run_id'] for r in rr if r['method']==m and r['detected']} for m in ['CLOVER-ECU','Origin RF']])
 loc=[dict(method=m,cohort=group,**summarize([r for r in rr if r['method']==m and r['injected'] and (group=='OWN' or r['run_id'] in common)])) for m in ['CLOVER-ECU','Origin RF'] for group in ['OWN','COMMON_DETECTED']];t.h.write(O/'localization.csv',loc)
 paired=[t.old.common.pair(rr,'CLOVER-ECU',m,endpoint) for m in ['Origin RF','Frozen SVM-INT'] for endpoint in ['fault','benign']]
 for p in paired:
  if not p['discordant']:p['mcnemar_exact_p']=1.
 t.h.write(O/'paired.csv',paired)
 labels=rf.CLASSES+['UNKNOWN'];conf=[]
 for method in ['Origin RF','CLOVER-ECU']:
  for truth in rf.CLASSES:
   rows=[r for r in rr if r['method']==method and r['origin']==truth];counts=collections.Counter()
   for r in rows:
    pred=r['origin_at_alarm'] if r['detected'] else 'NORMAL'
    if not r['injected'] and r['false_alarm']:pred=r['global_first_origin']
    counts[pred]+=1
   conf.append(dict(method=method,cohort='ALL_CASES_FIRST',truth=truth,**{p:counts[p] for p in labels}))
  for truth in rf.CLASSES[1:]:
   rows=[r for r in rr if r['method']==method and r['run_id'] in common and r['origin']==truth];counts=collections.Counter(r['origin_at_alarm'] for r in rows);conf.append(dict(method=method,cohort='COMMON_DETECTED_FIRST',truth=truth,**{p:counts[p] for p in labels}))
 t.h.write(O/'first_confusion.csv',conf)
 t.h.write(O/'runtime_confusion.csv',[dict(method=m,truth=o,**{p:sum(r['alarm_'+p] for r in rr if r['method']==m and r['origin']==o) for p in [*rf.CLASSES[1:],'UNKNOWN']}) for m in ['Origin RF','CLOVER-ECU'] for o in rf.CLASSES])
 fields=['run_id','method','origin','model','behavior','domain','kind','injected','detected','false_alarm','first_alarm_ms','first_post_alarm_ms','latency_ms','plant_manifestation','silent_plant','integrity_observed','origin_at_alarm','first_origin','global_first_origin','alarm_samples','wrong_localized_runtime_samples',*['alarm_'+o for o in [*rf.CLASSES[1:],'UNKNOWN']]]
 t.h.write(O/'case_metrics.csv',[{k:r.get(k) for k in fields} for r in rr]);dump('report.json',dict(summary=summary,paired=paired,common_detected=len(common),localization=loc,promoted=True))
 print(json.dumps(dict(summary=[{k:s[k] for k in ['method','detected','benign_false_alarms','plant_detected','silent_plant','latency_median_ms','latency_p95_ms','first_alarm_coverage','first_alarm_accuracy','runtime_accuracy_among_localized','runtime_unknown_rate','wrong_fault_runs','wrong_fault_samples']} for s in summary],common_detected=len(common)),indent=2),flush=True)

def finish():
 verify(full=True)
 import regress_digital_integrity as regression
 t.old.B=B;t.old.O=O;t.old.verify=verify;regression.main();verify(full=True)
 (O/'validation_record.md').write_text('# Origin-aware RF secondary evaluation\n\nOne locked 1800-case cohort. No post-outcome tuning or reruns. All prior source/results, frozen objects/model and GUI hashes preserved. Logging-only adapter parity on24 authorized TRAIN cases.\n\n'+(O/'regression.json').read_text()+'\n\n'+(B/'tests.log').read_text())
 (B/'rows.json').unlink();shutil.rmtree(B/'binary_backup');dump('artifact_hashes.json',{p.name:old.hashfile(p) for p in O.iterdir() if p.is_file() and p.name!='artifact_hashes.json'});print('REGRESSION COMPLETE',flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
