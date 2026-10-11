#!/usr/bin/env python3
"""Preregistered operating-condition study; reuse the exact final executable."""
import os,sys,json,csv,hashlib,subprocess,collections,random,shutil,base64,zlib
from pathlib import Path
import run_integrity_final_unseen as final
import run_benign_alarm as t
import report_benign_alarm as accounting
import regress_digital_integrity as regression
import numpy as np
ROOT=t.ROOT;B=Path('/tmp/clo-frozen-robustness');O=ROOT/'results/frozen_robustness'
EXE=final.B/'work/compare';PHASES=[1,21,41,61,81,99]
def dump(n,v):t.dump(O/n,v)
def verify():
 for n in ['protected_hashes.json','freeze.json']:
  if (O/n).exists():
   for p,v in json.loads((O/n).read_text()).items():assert t.sha(Path(p))==v,p
def sample(rows,n,rng,key):
 groups=collections.defaultdict(list)
 for r in rows:groups[key(r)].append(r)
 keys=sorted(groups);counts={k:len(groups[k])*n//len(rows) for k in keys}
 for k in sorted(keys,key=lambda k:(-(len(groups[k])*n%len(rows)),k))[:n-sum(counts.values())]:counts[k]+=1
 out=[]
 for k in keys:
  rng.shuffle(groups[k]);out+=groups[k][:counts[k]]
 return sorted(out,key=lambda s:s['run_id'])
def design():
 pool=final.design();rng=random.Random(20261007);base=[]
 for o in t.old.d.r.be.ORIGINS:
  base+=sample([s for s in pool if s['origin']==o],60,rng,lambda s:(s['model'],s['behavior'],s['domain'],s['kind']))
 base+=sample([s for s in pool if s['origin']=='NORMAL'],100,rng,lambda s:(s['workload'],))
 out=[]
 for p in range(6):
  for j,src in enumerate(base):
   s=dict(src);i=len(out);s.update(run_id=f'rob_{i:04}',condition=f'P{p}',template_id=src['run_id'],group=f'rob_pair_{j:03}',partition='ROBUSTNESS',profile=f'rob_profile_{i:04}',seed=2410100003+i*337,reference_seed=2510300007+i*347,c_seed=2610700011+i*349)
   pp=json.loads(src['profile_json'])
   for k,v in enumerate(pp):
    v['ambient_temp_c']+=.113+i*.0000037;v['vehicle_speed_kph']+=.217+i*.0000071
    if p==1:v['ambient_temp_c']-=15;v['engine_load']*=.55
    if p==2:v['ambient_temp_c']+=15;v['engine_load']=min(1.,v['engine_load']*1.4)
    if p==5:
     v['ambient_temp_c']+=[-10,8,-4,14,0][k];v['engine_load']=min(1.,v['engine_load']*[.7,1.25,.85,1.4,1.][k])
   if p in [3,5]:s.update(sensor_variation='0.08:0.04:19300',reference_noise=.08,c_noise=.04,c_quantum=.05)
   if p in [4,5]:s['c_phase_ms']=PHASES[j%len(PHASES)]
   if p==5:s.update(target_updates_json='[[35700,103],[72700,92]]',benign_reference_magnitude=(-1 if j%2 else 1)*[.2,.32,.5][j%3],benign_reference_duration=[100,1100,2300,5100][j%4])
   s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=t.h.profile_identity(pp);s.pop('configuration_sha256',None)
   s['configuration_sha256']=hashlib.sha256(json.dumps({k:v for k,v in s.items() if k not in ['run_id','condition','template_id','group','partition','profile']},sort_keys=True).encode()).hexdigest();out.append(s)
 for p in range(6):assert collections.Counter(s['origin'] for s in out if s['condition']==f'P{p}')==dict(MEMORY=60,TIMING=60,COMMUNICATION=60,SENSOR_CONTROL=60,ACTUATOR=60,NORMAL=100)
 # Fault definitions exactly matched across conditions; only runtime context varies.
 fields=['origin','model','behavior','magnitude','stuck_polarity','start_ms','duration_ms','sensor_chain','sensor_ramp_rise_ms','on_ms','off_ms','domain','kind']
 for j in range(400):assert all(all(out[p*400+j][k]==out[j][k] for k in fields) for p in range(6))
 return out
def setup():
 assert not O.exists() and not B.exists();final.verify()
 for n,v in json.loads((final.O/'artifact_hashes.json').read_text()).items():assert t.sha(final.O/n)==v,n
 model,sel,mhash=t.frozen_svm();assert mhash==json.loads((final.O/'registration.json').read_text())['svm_model_sha256']
 O.mkdir();B.mkdir();ss=design()
 paths=[p for root in ['src','include','scripts','python','tests','presets','results'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and O not in p.parents]
 dump('protected_hashes.json',{str(p):t.sha(p) for p in paths})
 h=t.old.d.r.historical;h.OUT=B;h.B=B;h.historical_audit(ss);audit=list(csv.DictReader((B/'historical_overlap_audit.csv').open()))
 profiles={s['profile_semantic_sha256'] for s in ss};ids={s['configuration_sha256'] for s in ss};seeds={str(s[k]) for s in ss for k in ['seed','reference_seed','c_seed']};assert len(profiles)==2400 and len(ids)==2400 and len(seeds)==7200
 for p in [*(ROOT/'results').rglob('*.json'),*Path('/tmp').glob('clo*/specs.json')]:
  if B in p.parents or O in p.parents:continue
  try:obj=json.loads(p.read_text())
  except (OSError,ValueError):continue
  rows=obj if isinstance(obj,list) else obj.get('manifest',[]) if isinstance(obj,dict) else []
  if not isinstance(rows,list) or not rows or not isinstance(rows[0],dict):continue
  op={t.h.profile_identity(json.loads(s['profile_json'])) if s.get('profile_json') else s['profile_semantic_sha256'] for s in rows if s.get('profile_json') or s.get('profile_semantic_sha256')};oi={s['configuration_sha256'] for s in rows if s.get('configuration_sha256')};sd={str(s[k]) for s in rows for k in ['seed','reference_seed','c_seed'] if s.get(k)}
  if not(op or oi):continue
  assert not profiles&op and not ids&oi and not seeds&sd,str(p)
  audit.append(dict(source=str(p),sha256=t.sha(p),rows=len(rows),profile_identities=len(op),configuration_identities=len(oi),seeds=len(sd),profile_overlap=0,configuration_overlap=0,seed_overlap=0))
 t.dump(B/'specs.json',ss);t.h.write(O/'campaign_manifest.csv',ss);t.h.write(O/'overlap_audit.csv',audit);shutil.copy2(ROOT/'scripts/frozen_robustness_protocol.md',O/'protocol.md')
 w=B/'work';w.mkdir();t.h.prepare_work(w,ss)
 dump('registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),utc=t.old.d.r.now(),profiles=6,faults=1800,benign=600,historical_sources=len(audit),overlap=0,executable=str(EXE),executable_sha256=t.sha(EXE),svm_sha256=mhash,svm_threshold=0,phase_offsets_ms=PHASES,scheduler_jitter_evaluated=False,timing_path='unchanged',subgroups=[dict(condition=k[0],origin=k[1],model=k[2],behavior=k[3],kind=k[4],n=v) for k,v in collections.Counter((s['condition'],s['origin'],s['model'],s['behavior'],s['kind']) for s in ss).items()]))
 dump('freeze.json',{str(p):t.sha(p) for p in [*O.iterdir(),B/'specs.json',EXE,*list((w/'profiles').glob('*.csv'))] if p.is_file()});verify();print('LOCKED six profiles /2400 cases; overlap 0',flush=True)
def collect():
 verify();assert not (O/'execution_started.json').exists(),'NO RERUN'
 dump('execution_started.json',dict(utc=t.old.d.r.now(),freeze_sha256=t.sha(O/'freeze.json')))
 ss=json.loads((B/'specs.json').read_text());w=B/'work'
 for k,v in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('DC_INPUT','input.csv'),('DI_LOG','integrity.csv'),('BA_LOG','audit.csv')]:os.environ[k]=str(w/v)
 os.environ['PLUS_HOST_MODE']='2';os.environ['BA_CHOICE']='2';t.h.c.METHODS=['M2'];t.h.c.command=lambda s,w:t.old.d.r.t.command(s,w,EXE)
 model,sel,mhash=t.frozen_svm();assert mhash==json.loads((O/'registration.json').read_text())['svm_sha256'];rr=[]
 for p in range(6):
  dump(f'P{p}_started.json',dict(utc=t.old.d.r.now()))
  for i,s in enumerate([s for s in ss if s['condition']==f'P{p}']):
   base=t.h.c.execute(s,w,False)[0];a=np.loadtxt(w/'input.csv',delimiter=',');it=np.loadtxt(w/'integrity.csv',delimiter=',');q=np.loadtxt(w/'audit.csv',delimiter=',');e=t.old.d.bench.evidence(np.loadtxt(w/'benchmark.csv',delimiter=','),6)
   assert np.array_equal(a[:,0],q[:,0]) and np.array_equal(a[:,0],it[:,0]) and np.array_equal(a[:,0],e.time_ms)
   bypass=(q[:,1]!=7)|(q[:,2]>0)|(q[:,3]>0)|(q[:,4]>0)|(q[:,22]>0);assert np.array_equal(q[bypass,25],q[bypass,20]) and not np.any((q[:,25]>0)&(q[:,20]==0))
   active=np.array([t.h.prior.prior.active(s,int(ms)) for ms in a[:,0]]);post=a[:,0]>=s['start_ms'];axis=18 if s['model']=='fan_stuck_off' else 17
   base.update(integrity_observed=int(np.any(it[:,2])),integrity_active_samples=int(np.count_nonzero(active&(it[:,2]>0))),actuator_excited=int(s['origin']=='ACTUATOR' and np.any(a[active,axis]>0)),active_probe_samples=int(np.count_nonzero(active&(np.r_[0,np.diff(a[:,12])]>0))),positive_active_evidence_samples=int(np.count_nonzero(active&np.any(q[:,6:12]>0,axis=1))),max_active_strength=float(q[active,6:12].max()) if active.any() else 0)
   alarm=q[:,25]>0;origin=np.where(alarm,q[:,21].astype(int)>>1,0);r=t.old.d.bench.score(base,e,'A2',(alarm,origin));r['post_onset_alarm_samples']=int(np.count_nonzero(alarm&post));rr.append(r)
   payload=dict(input=a,integrity=it[:,1:],values=e.strength,available=e.available,subset=e.origin_subset);margin=t.old.d.ml.margin(model,t.old.features(payload));r=t.old.d.bench.score(base,e,'SVM-INT',(margin>0,np.zeros(len(margin),int)));r['post_onset_alarm_samples']=int(np.count_nonzero((margin>0)&post));rr.append(r)
   for n in ['audit.csv','input.csv','integrity.csv','benchmark.csv','triplex.csv','plus_meta.csv']:(w/n).unlink()
   if (i+1)%100==0:print(f'P{p}',i+1,'/400',flush=True)
  dump(f'P{p}_complete.json',dict(utc=t.old.d.r.now(),cases=400))
 t.dump(B/'rows.json',rr);verify();dump('execution_complete.json',dict(utc=t.old.d.r.now(),cases=2400));print('ALL PROFILES COMPLETE',flush=True)
def category(x):
 if x['post_onset_alarm_samples']:return 'alarm-edge-scoring (alarm present but no post-onset rising edge)'
 if x['origin']=='ACTUATOR' and not x['actuator_excited']:return 'structural: unexcited pump'
 if x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse' and not x['integrity_active_samples']:return 'temporal: uncaptured pulse'
 if x['origin']=='MEMORY' and not x['effective_memory_corruption'] and not x['active_probe_samples']:return 'temporal: dormant memory outside probes'
 if x['integrity_active_samples']:return 'classifier/decision: integrity discrepancy without alarm'
 return 'unresolved provider/classifier sensitivity; not proved unobservable'
def report():
 verify();assert (O/'execution_complete.json').exists();rr=json.loads((B/'rows.json').read_text());summary=[];sub=[];pairs=[];loc=[];miss=[];changes=[]
 old={x['method']:x for x in json.loads((final.O/'report.json').read_text())['summary']}
 for p in [*[f'P{i}' for i in range(6)],'POOLED']:
  rows=[x for x in rr if p=='POOLED' or x['condition']==p]
  for m in ['A2','SVM-INT']:
   xs=[x for x in rows if x['method']==m];s=accounting.stats(xs);summary.append(dict(condition=p,method=m,**s))
   for o in [*t.old.d.r.be.ORIGINS,'INTEGRITY_OBSERVABLE']:
    ys=[x for x in xs if x['origin']==o] if o!='INTEGRITY_OBSERVABLE' else [x for x in xs if x['injected'] and x['integrity_observed']]
    sub.append(dict(condition=p,method=m,origin=o,**accounting.stats(ys)))
   baseline=old['A2' if m=='A2' else 'SVM-INT default'];changes.append(dict(condition=p,method=m,detection_delta_pp=100*(s['coverage']-baseline['coverage']),benign_delta_pp=100*(s['benign_false_alarm_rate']-baseline['benign_false_alarm_rate']),plant_detection_delta_pp=100*(s['coverage_given_plant_manifestation']-baseline['coverage_given_plant_manifestation']),latency_median_delta_ms=s['latency_median_ms']-baseline['latency_median_ms'],latency_p95_delta_ms=s['latency_p95_ms']-baseline['latency_p95_ms']))
   if m=='A2':loc.append(dict(condition=p,**accounting.stats([x for x in xs if x['injected']])))
  for endpoint in ['fault','benign']:pairs.append(dict(condition=p,**t.old.common.pair(rows,'A2','SVM-INT',endpoint)))
 for x in rr:
  if x['injected'] and not x['detected']:miss.append({**{k:x.get(k) for k in ['run_id','condition','method','origin','model','behavior','kind','duration_ms','effective_memory_corruption','active_probe_samples','actuator_excited','integrity_active_samples','positive_active_evidence_samples','max_active_strength','post_onset_alarm_samples','plant_manifestation']},'category':category(x)})
 for name,rows in [('summary',summary),('per_origin',sub),('paired',pairs),('localization',loc),('misses',miss),('variation_from_final',changes)]:t.h.write(O/(name+'.csv'),rows)
 a=[s for s in summary if s['method']=='A2' and s['condition']!='POOLED'];worst=dict(detection=[s['condition'] for s in a if s['coverage']==min(x['coverage'] for x in a)],benign=[s['condition'] for s in a if s['benign_false_alarm_rate']==max(x['benign_false_alarm_rate'] for x in a)],plant=[s['condition'] for s in a if s['coverage_given_plant_manifestation']==min(x['coverage_given_plant_manifestation'] for x in a)])
 taxonomy={p:dict(collections.Counter(x['category'] for x in miss if x['method']=='A2' and (p=='POOLED' or x['condition']==p))) for p in [*[f'P{i}' for i in range(6)],'POOLED']}
 dump('report.json',dict(summary=summary,worst=worst,taxonomy=taxonomy,changes=changes,paired=pairs));dump('study_record.json',dict(case_metrics=dict(encoding='zlib+base85 JSON',data=base64.b85encode(zlib.compress(json.dumps(rr,separators=(',',':')).encode())).decode())))
 lines=['# Frozen robustness study','', 'All six profiles locked before execution; one physical run/case, unchanged final executable and frozen SVM default operating point. Scheduler-jitter robustness NOT evaluated: incompatible simulator paths. P4/P5 use fixed Sensor C acquisition phases only.','', '| Profile | Method | Detection | Benign | Plant | Silent | Median/P95 ms |','|---|---|---|---|---|---|---|']
 for s in summary:lines.append(f"| {s['condition']} | {s['method']} | {s['detected']}/{s['faulty_runs']} | {s['benign_false_alarms']}/{s['benign_runs']} | {s['plant_detected']}/{s['plant_manifestation_runs']} | {s['silent_plant']} | {s['latency_median_ms']}/{s['latency_p95_ms']} |")
 lines+=['',f'Worst profiles: {worst}.',f'A2 miss taxonomy: {taxonomy}.','Per-origin, precision, integrity-observable coverage, localization and final-unseen absolute percentage-point differences are in the accompanying CSVs. UNKNOWN is distinct from wrong confident origins. SVM supplies no origin localization.','No retuning or reruns. Same fault definitions across conditions; operating conditions can naturally alter excitation/propagation. New seeds are not paired identical noise realizations. Final-unseen comparison also changes cohort size/composition; profile differences are descriptive, not an isolated causal or field-risk estimate. Unresolved missed evidence is not automatically a proved classifier-only failure.']
 (O/'findings.md').write_text('\n'.join(lines)+'\n');print('REPORT COMPLETE',flush=True)
def finish():
 verify();t.old.B=B;t.old.O=O;t.old.verify=verify;r=json.loads((O/'report.json').read_text());dump('report.json',dict(r,promoted=True))
 try:regression.main()
 finally:dump('report.json',r)
 verify();assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==json.loads((O/'registration.json').read_text())['head']
 (O/'validation_record.md').write_text('# Frozen robustness validation record\n\n2400 cases once; all six profiles registered and frozen before execution. Exact final-unseen executable reused. Scheduler-jitter NOT evaluated; fixed C acquisition phase variation only. Timing-fault path, frozen methods, GUI, Hybrid/HETIA and prior evidence unchanged. No commit/push.\n\n'+(O/'regression.json').read_text()+'\n'+(B/'tests.log').read_text())
 (B/'rows.json').unlink();shutil.rmtree(B/'binary_backup');dump('artifact_hashes.json',{p.name:t.sha(p) for p in O.iterdir() if p.is_file() and p.name!='artifact_hashes.json'});print('FINALIZED',flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
