#!/usr/bin/env python3
"""One registered execution of the unchanged retained digital-integrity methods."""
import os,sys,json,csv,hashlib,subprocess,collections,shutil,base64,zlib
from pathlib import Path
import run_benign_alarm as t
import report_benign_alarm as accounting
import regress_digital_integrity as regression
import numpy as np
ROOT=t.ROOT; B=Path('/tmp/clo-integrity-final-unseen'); O=ROOT/'results/integrity_final_unseen'
METHODS=['A0','A2','SVM-INT default','SVM-INT CAL1']
def write(name,value):t.dump(O/name,value)
def verify():
 for name in ['protected_hashes.json','freeze.json']:
  if (O/name).exists():
   for p,v in json.loads((O/name).read_text()).items():assert t.sha(Path(p))==v,p

def design():
 out=[];benign=collections.Counter()
 for src in t.old.design():
  if src['partition']!='VALIDATION':continue
  f=int(src['group'].split('_')[-1])-48
  if src['origin']=='NORMAL':
   benign[f]+=1
   if benign[f]>60:continue
  s=dict(src);i=len(out)
  s.update(run_id=f'ifu_{i:04}',partition='UNSEEN',group=f'ifu_family_{f}',profile=f'ifu_profile_{i:04}',seed=1801100003+i*313,reference_seed=1903300007+i*317,c_seed=2007700011+i*331)
  pp=json.loads(s['profile_json'])
  for j,p in enumerate(pp):
   p['ambient_temp_c']+=.217+i*.0000053
   p['engine_load']*=.989+(f%5)*.005
   p['vehicle_speed_kph']+=.683+i*.000013
  if s['origin']!='NORMAL':s['start_ms']+=211 if s['origin']=='SENSOR_CONTROL' else 300+(f%3)*100
  if s['origin']=='SENSOR_CONTROL':
   s['magnitude']*=1.013
   if s['kind']=='ramp':s['sensor_ramp_rise_ms']+=521
  if s['origin']=='NORMAL':
   s['reference_noise']=[.021,.033,.049,.061][i%4]
   s['c_noise']=[.011,.019,.027,.039][(i//3)%4]
   s['sensor_variation']=['0.019:0:13900','0.027:.012:19300','0.035:.019:23900'][i%3]
  s['c_phase_ms']=(int(s['c_phase_ms'])+8)%100
  s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=t.h.profile_identity(pp)
  s.pop('configuration_sha256',None)
  # Exclude administrative identities: hash physical/runtime configuration only.
  physical={k:v for k,v in s.items() if k not in ['run_id','partition','group','profile']}
  s['configuration_sha256']=hashlib.sha256(json.dumps(physical,sort_keys=True).encode()).hexdigest();out.append(s)
 assert collections.Counter(s['origin'] for s in out)==dict(NORMAL=600,MEMORY=240,TIMING=240,COMMUNICATION=240,SENSOR_CONTROL=240,ACTUATOR=240)
 return out

def setup():
 assert not O.exists() and not B.exists(),'Never overwrite or regenerate this campaign'
 t.verify()
 for n,v in json.loads((t.O/'artifact_hashes.json').read_text()).items():assert t.sha(t.O/n)==v,n
 prior=json.loads((t.O/'report.json').read_text());assert prior['retained'] and prior['selected']==2
 model,svm,mhash=t.frozen_svm();assert mhash==json.loads((t.O/'selection.json').read_text())['svm_unchanged']['sha256']
 O.mkdir();B.mkdir()
 paths=[p for root in ['src','include','scripts','python','tests','presets','results'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and O not in p.parents]
 paths += [p for p in ROOT.iterdir() if p.is_file() and (p.suffix in ['.mk','.cfg'] or p.name.startswith('virtual_ecu') or p.name=='Makefile')]
 write('protected_hashes.json',{str(p):t.sha(p) for p in paths})
 ss=design();hist=t.old.d.r.historical;hist.OUT=B;hist.B=B;hist.historical_audit(ss)
 audit=list(csv.DictReader((B/'historical_overlap_audit.csv').open()))
 profiles={s['profile_semantic_sha256'] for s in ss};ids={s['configuration_sha256'] for s in ss};seeds={str(s[k]) for s in ss for k in ['seed','reference_seed','c_seed']}
 assert len(profiles)==len(ss) and len(ids)==len(ss) and len(seeds)==3*len(ss)
 def embedded(path):
  try:p=json.loads(path.read_text())
  except (ValueError,OSError):return
  rows=p if isinstance(p,list) else p.get('manifest',[]) if isinstance(p,dict) else []
  if not isinstance(rows,list) or not rows or not isinstance(rows[0],dict):return
  op=set();oi=set();sd=set()
  for x in rows:
   if x.get('profile_json'):op.add(t.h.profile_identity(json.loads(x['profile_json'])))
   elif x.get('profile_semantic_sha256'):op.add(x['profile_semantic_sha256'])
   if x.get('configuration_sha256'):oi.add(x['configuration_sha256'])
   for k in ['seed','reference_seed','c_seed']:
    if x.get(k):sd.add(str(x[k]))
  if not(op or oi):return
  assert not profiles&op and not ids&oi and not seeds&sd,str(path)
  audit.append(dict(source=str(path),sha256=t.sha(path),rows=len(rows),profile_identities=len(op),configuration_identities=len(oi),seeds=len(sd),profile_overlap=0,configuration_overlap=0,seed_overlap=0))
 for p in [*(ROOT/'results').rglob('*.json'),*Path('/tmp').glob('clo*/specs.json')]:
  if O not in p.parents and B not in p.parents:embedded(p)
 t.dump(B/'specs.json',ss);t.h.write(O/'campaign_manifest.csv',ss);t.h.write(O/'overlap_audit.csv',audit)
 shutil.copy2(ROOT/'scripts/integrity_final_unseen_protocol.md',O/'protocol.md')
 exe=t.execute_setup(B/'work',ss)
 # Build once before outcomes; retain exact generated adapter/build hashes.
 write('registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),git_status_before=subprocess.check_output(['git','status','--porcelain'],text=True),utc=t.old.d.r.now(),cases=len(ss),fault=1200,benign=600,historical_sources=len(audit),overlap=0,selected_gate=2,svm_model_sha256=mhash,svm_default_threshold=0,svm_CAL1_threshold=svm['threshold'],subtypes=[dict(origin=k[0],model=k[1],behavior=k[2],kind=k[3],n=v) for k,v in collections.Counter((s['origin'],s['model'],s['behavior'],s['kind']) for s in ss).items()]))
 paths=[p for p in O.iterdir() if p.is_file()]+[B/'specs.json',exe,*list((B/'work').glob('*.c')),*list((B/'work').glob('*.o')),*list((B/'work'/'profiles').glob('*'))]
 write('freeze.json',{str(p):t.sha(p) for p in paths if p.is_file()});verify();print('FROZEN 1800 cases; historical sources',len(audit),'overlap 0',flush=True)

def collect():
 verify();assert not (O/'execution_started.json').exists(),'NO RERUNS'
 write('execution_started.json',dict(utc=t.old.d.r.now(),freeze_sha256=t.sha(O/'freeze.json')))
 ss=json.loads((B/'specs.json').read_text());w=B/'work'
 for k,v in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('DC_INPUT','input.csv'),('DI_LOG','integrity.csv'),('BA_LOG','audit.csv')]:os.environ[k]=str(w/v)
 os.environ['PLUS_HOST_MODE']='2';os.environ['BA_CHOICE']='2';t.h.c.METHODS=['A0','M2'];t.h.c.command=lambda s,w:t.old.d.r.t.command(s,w,w/'compare')
 model,svm,mhash=t.frozen_svm();assert mhash==json.loads((O/'registration.json').read_text())['svm_model_sha256'];rows=[]
 for i,s in enumerate(ss):
  native=t.h.c.execute(s,w,False);assert {r['method'] for r in native}=={'A0','M2'}
  base=next(r for r in native if r['method']=='M2');a0=next(r for r in native if r['method']=='A0')
  a=np.loadtxt(w/'input.csv',delimiter=',');it=np.loadtxt(w/'integrity.csv',delimiter=',');q=np.loadtxt(w/'audit.csv',delimiter=',');e=t.old.d.bench.evidence(np.loadtxt(w/'benchmark.csv',delimiter=','),6)
  assert np.array_equal(a[:,0],q[:,0]) and np.array_equal(a[:,0],it[:,0]) and np.array_equal(a[:,0],e.time_ms)
  assert np.array_equal(q[:,20],q[:,23])
  bypass=(q[:,1]!=7)|(q[:,2]>0)|(q[:,3]>0)|(q[:,4]>0)|(q[:,22]>0)
  assert np.array_equal(q[bypass,25],q[bypass,20]) and not np.any((q[:,25]>0)&(q[:,20]==0))
  # Ground truth below is used for post-hoc categorization only, never inference.
  active=np.array([t.h.prior.prior.active(s,int(ms)) for ms in a[:,0]])
  axis=18 if s['model']=='fan_stuck_off' else 17
  meta=dict(integrity_observed=int(np.any(it[:,2])),integrity_samples=int(np.count_nonzero(it[:,2])),actuator_excited=int(s['origin']=='ACTUATOR' and np.any(a[active,axis]>0)),active_probe_samples=int(np.count_nonzero(active & (np.r_[0,np.diff(a[:,12])]>0))))
  base.update(meta);a0.update(meta);rows.append(a0)
  alarm=q[:,25]>0;origin=np.where(alarm,q[:,21].astype(int)>>1,0);rows.append(t.old.d.bench.score(base,e,'A2',(alarm,origin)))
  payload=dict(input=a,integrity=it[:,1:],values=e.strength,available=e.available,subset=e.origin_subset);margin=t.old.d.ml.margin(model,t.old.features(payload))
  for threshold,name in [(0,'SVM-INT default'),(svm['threshold'],'SVM-INT CAL1')]:rows.append(t.old.d.bench.score(base,e,name,(margin>threshold,np.zeros(len(margin),int))))
  for name in ['audit.csv','input.csv','integrity.csv','benchmark.csv','triplex.csv','plus_meta.csv']:(w/name).unlink()
  if (i+1)%150==0:print('UNSEEN',i+1,'/1800',flush=True)
 t.dump(B/'rows.json',rows);verify();write('execution_complete.json',dict(cases=len(ss),utc=t.old.d.r.now()));print('EXECUTION COMPLETE',flush=True)

def report():
 verify();assert (O/'execution_complete.json').exists();rr=json.loads((B/'rows.json').read_text())
 summary=[dict(method=m,**accounting.stats([x for x in rr if x['method']==m])) for m in METHODS]
 filters={**{o:lambda x,o=o:x['origin']==o for o in t.old.d.r.be.ORIGINS},'integrity_observable':lambda x:x['injected'] and x['integrity_observed'],'effective_memory':lambda x:x['origin']=='MEMORY' and x['effective_memory_corruption'],'dormant_memory':lambda x:x['origin']=='MEMORY' and x['initially_latent_stuck'] and not x['effective_memory_corruption'],'weak_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step' and abs(x['magnitude'])<1,'pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse','common_mode_AB_ABC':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain'] in ['AB','ABC'],'unexcited_actuator':lambda x:x['origin']=='ACTUATOR' and not x['actuator_excited']}
 sub=[dict(method=m,subgroup=g,**accounting.stats([x for x in rr if x['method']==m and f(x)])) for m in METHODS for g,f in filters.items()]
 pairs=[t.old.common.pair(rr,'A2',m,end) for m in ['A0','SVM-INT default','SVM-INT CAL1'] for end in ['fault','benign']]
 for x in pairs:
  if not x['discordant']:x['mcnemar_exact_p']=1.;x['mcnemar_scope']='No discordant pairs; exact p=1, no evidence of difference'
 misses=[]
 for x in rr:
  if not x['injected'] or x['detected']:continue
  if x['origin']=='ACTUATOR' and not x['actuator_excited']:reason='No positive actuator command during active fault; no modeled idle-health observable'
  elif x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse' and not x['integrity_observed']:reason='Short pulse with no captured integrity violation; acquisition-window limit'
  elif x['origin']=='MEMORY' and not x['effective_memory_corruption']:reason='Dormant stored value; no detected inconsistency during finite probe window'
  else:reason='Available evidence did not cross frozen method decision; see sufficient statistics'
  misses.append({**{k:x.get(k) for k in ['run_id','method','origin','model','behavior','kind','domain','magnitude','duration_ms','effective_memory_corruption','active_probe_samples','actuator_excited','integrity_observed','plant_manifestation']},'reason':reason})
 t.h.write(O/'summary.csv',summary);t.h.write(O/'subgroups.csv',sub);t.h.write(O/'paired.csv',pairs);t.h.write(O/'misses.csv',misses)
 loc=[dict(method=m,origin=o,**accounting.stats([x for x in rr if x['method']==m and (x['injected'] if o=='ALL_FAULT' else x['origin']==o)])) for m in ['A0','A2'] for o in ['ALL_FAULT',*t.old.d.r.be.ORIGINS,'NORMAL']];t.h.write(O/'localization.csv',loc)
 t.h.write(O/'confusion.csv',[dict(method=m,origin=o,**{p:sum(x['alarm_'+p] for x in rr if x['method']==m and x['origin']==o) for p in [*t.old.d.r.be.ORIGINS,'UNKNOWN']}) for m in ['A0','A2'] for o in [*t.old.d.r.be.ORIGINS,'NORMAL']])
 # Compact per-case sufficient statistics, no bulk traces or duplicate manifests.
 exclude={'profile','profile_semantic_sha256','configuration_sha256','target_updates_json'}
 compact=[{k:v for k,v in x.items() if k not in exclude} for x in rr]
 write('study_record.json',dict(case_metrics=dict(encoding='zlib+base85 JSON',data=base64.b85encode(zlib.compress(json.dumps(compact,separators=(',',':')).encode())).decode())))
 write('report.json',dict(summary=summary,paired=pairs,remaining_A2=dict(collections.Counter(x['origin']+'/'+x['model']+'/'+x['reason'] for x in misses if x['method']=='A2'))))
 lines=['# Final frozen unseen evaluation','', 'One physical simulation per case. Frozen retained A2 G2, integrity, M2, Triplex and SVM unchanged; no outcome-based selection. SVM default is primary; CAL1 is the previously frozen secondary point. Wilson CIs and exact paired tests are descriptive for grouped deterministic simulations, not field-risk guarantees.','', '| Method | Detection | Wilson 95% | Benign | Precision | Plant | Silent | Median/P95 ms |','|---|---|---|---|---|---|---|---|']
 for x in summary:lines.append(f"| {x['method']} | {x['detected']}/1200 | {x['ci_low']:.6f}–{x['ci_high']:.6f} | {x['benign_false_alarms']}/600 | {x['precision']} | {x['plant_detected']}/{x['plant_manifestation_runs']} | {x['silent_plant']} | {x['latency_median_ms']}/{x['latency_p95_ms']} |")
 lines+=['','Common-mode cases here corrupt post-conversion data with an intact protected witness. They do not establish physical/pre-protection or shared data+witness failure coverage. Brief integrity-PASS physical anomalies remain outside modeled coverage. No detector/model change, rerun, commit or push. Detailed per-origin, localization, paired and miss tables accompany this report.']
 (O/'findings.md').write_text('\n'.join(lines)+'\n');print('REPORT COMPLETE',flush=True)

def finish():
 verify();assert not (B/'regression_started').exists()
 # Reuse the existing isolated regression runner without changing its source.
 t.old.B=B;t.old.O=O;t.old.verify=verify
 p=O/'report.json';r=json.loads(p.read_text());write('report.json',dict(r,promoted=True))
 try:regression.main()
 finally:write('report.json',r)
 verify();reg=json.loads((O/'regression.json').read_text());head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head==json.loads((O/'registration.json').read_text())['head']
 (O/'validation_record.md').write_text('# Execution and regression record\n\nOne frozen unseen cohort:1800 unique configurations,1200 faults/600 benign. No reruns or tuning. All source/config/model/generated-executable hashes verified before and after outcomes and regression. Historical files, Hybrid/HETIA and GUI unchanged.\n\nHEAD: '+head+'\n\n'+json.dumps(reg,indent=2)+'\n\n'+(B/'tests.log').read_text())
 # Preserve generated build lock targets; remove only temporary physical run data.
 for p in (B/'work').glob('*.csv'):p.unlink()
 (B/'rows.json').unlink();shutil.rmtree(B/'binary_backup')
 write('artifact_hashes.json',{p.name:t.sha(p) for p in O.iterdir() if p.is_file() and p.name!='artifact_hashes.json'})
 print('FINALIZED',sum(p.stat().st_size for p in O.iterdir() if p.is_file()),'bytes',flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
