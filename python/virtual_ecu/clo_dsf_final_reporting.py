"""Post-hoc confirmation analysis; never feeds labels back into runtime."""
from __future__ import annotations
import csv,gzip,hashlib,json,math,statistics
from pathlib import Path
from .clo_dsf_final_confirmation import ROOT,OUTPUT,ORIGINS,METHODS,aggregate,write_csv,write_json,ratio,mean,quantile
NONLOCAL={'Simple OR','Weighted Sum','Hybrid','Timing Monitor'}
def records(path):
 with Path(path).open() as f:rows=list(csv.DictReader(f))
 for r in rows:
  for k,v in r.items():
   if not v:r[k]=None;continue
   try:r[k]=float(v) if any(c in v for c in ['.','e']) else int(v)
   except ValueError:pass
 return rows

def wilson(k,n):
 if not n:return None,None
 z=1.959963984540054;p=k/n;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return max(0,mid-half),min(1,mid+half)
def summarize(rows):
 s=aggregate(rows);f=[r for r in rows if r['injected']];d=[r for r in f if r['detected']];localized=[r for r in d if not r['unknown_at_alarm']]
 s['silent_plant_rate']=ratio(s['silent_plant'],s['plant_manifestation_runs']);s['localization_latency_median_ms']=quantile([r['localization_latency_ms'] for r in f if r['localization_latency_ms'] is not None],.5);s['localization_latency_p95_ms']=quantile([r['localization_latency_ms'] for r in f if r['localization_latency_ms'] is not None],.95)
 for label,k,n in [('coverage',s['detected'],s['faulty_runs']),('benign_false_alarm_rate',s['benign_false_alarms'],s['benign_runs']),('plant_coverage',s['plant_manifestation_runs']-s['silent_plant'],s['plant_manifestation_runs']),('silent_plant_rate',s['silent_plant'],s['plant_manifestation_runs']),('localization_coverage',len(localized),len(d)),('localized_accuracy',s['correct_localizations'],len(localized)),('correct_among_alarms',s['correct_localizations'],len(d)),('unknown_rate',s['unknown'],len(d)),('wrong_origin_rate',s['wrong_localizations'],len(d))]:s[label+'_wilson_low'],s[label+'_wilson_high']=wilson(k,n)
 return s

def paired(rows,other):
 a={r['run_id']:r for r in rows if r['method']=='Final CLO-DSF' and r['injected']};b={r['run_id']:r for r in rows if r['method']==other and r['injected']};n11=n10=n01=n00=0
 for key,x in a.items():
  y=b[key];da=bool(x['detected']);db=bool(y['detected']);n11+=da and db;n10+=da and not db;n01+=not da and db;n00+=not da and not db
 discord=n10+n01;p=min(1.,2*sum(math.comb(discord,k) for k in range(min(n10,n01)+1))/2**discord) if discord else None
 return dict(method_a='Final CLO-DSF',method_b=other,both_detect=n11,only_a=n10,only_b=n01,neither=n00,discordant=discord,exact_mcnemar_p=p,interpretation='No discordance; no test needed' if not discord else 'Low information (<10 discordant); no significance claim' if discord<10 else 'Exploratory exact paired test; designed families are correlated, not population inference')

def identities(rows,out):
 final=[r for r in rows if r['method']=='Final CLO-DSF'];groups={};trace_stats=[]
 for ix,r in enumerate(final):
  name=r['run_id'];observation_digest=hashlib.sha256();evidence_digest=hashlib.sha256();snapshot=None
  with gzip.open(out/'observations'/f'{name}.csv.gz','rt') as f:
   for obs in csv.DictReader(f):
    payload=','.join(obs.values()).encode();observation_digest.update(payload+b'\n')
    if int(obs['time_ms'])==r['first_post_alarm_ms']:snapshot=hashlib.sha256(payload).hexdigest()
  unknown_steps=wrong_steps=path_steps=0;first_unknown=-1
  with gzip.open(out/'traces'/f'{name}.final.csv.gz','rt') as f:
   for t in csv.DictReader(f):
    # Available strength sequence is exactly what the inherited feature map supplies.
    fields=[t[k] for k in t if k.endswith('_evidence') or k.endswith('_detection_reliability')]
    evidence_digest.update((','.join(fields)+'\n').encode())
    if t['alarm']=='1' and t['estimated_origin']=='UNKNOWN':unknown_steps+=1;first_unknown=int(t['time_ms']) if first_unknown<0 else first_unknown
    if r['injected'] and t['alarm']=='1' and t['estimated_origin'] not in ['UNKNOWN',r['origin']]:wrong_steps+=1
    path_steps+=int(t['observed_evidence_path'])!=0
  trace_stats.append(dict(run_id=name,true_origin_evaluation_only=r['origin'],injected=r['injected'],detected=r['detected'],unknown_at_first_alarm=r['unknown_at_alarm'],any_confirmed_unknown=int(unknown_steps>0),confirmed_unknown_steps=unknown_steps,first_unknown_ms=first_unknown,wrong_localized_runtime_steps=wrong_steps,diagnostic_path_steps=path_steps,control_effect=r['control_effect'],actuator_effect=r['actuator_effect'],plant_manifestation=r['plant_manifestation'],observation_sha256=observation_digest.hexdigest(),evidence_sha256=evidence_digest.hexdigest(),first_alarm_observation_sha256=snapshot))
  for level,digest in [('full_runtime_observation_history',observation_digest.hexdigest()),('full_evidence_history',evidence_digest.hexdigest()),('first_alarm_snapshot_only',snapshot)]:
   if digest and r['injected']:groups.setdefault((level,digest),[]).append(r)
  if ix%100==0:print(f'Identity audit {ix+1}/{len(final)}',flush=True)
 result=[];membership={}
 for (level,digest),group in groups.items():
  if len({r['origin'] for r in group})<2:continue
  origins=sorted({r['origin'] for r in group});entry=dict(level=level,sha256=digest,runs=len(group),true_origins_evaluation_only='|'.join(origins),run_ids='|'.join(r['run_id'] for r in group),detected=sum(r['detected'] for r in group),unknown_at_first_alarm=sum(r['unknown_at_alarm'] for r in group),interpretation='Snapshot coincidence only; histories may differ' if level=='first_alarm_snapshot_only' else 'Indistinguishable to this complete evidence map' if level=='full_evidence_history' else 'Identical whole allowed observations: origin underdetermined for these cases')
  result.append(entry)
  for r in group:membership.setdefault(r['run_id'],set()).add(level)
 write_csv(out/'final_candidate_identifiability_analysis.csv',result or [dict(level='none',runs=0,true_origins_evaluation_only='',interpretation='No mixed-origin exact-equivalence groups observed')])
 for r in trace_stats:r['mixed_origin_equivalence_levels']='|'.join(sorted(membership.get(r['run_id'],set())))
 write_csv(out/'runtime_identifiability_signatures.csv',trace_stats)
 breakdown=[]
 for origin in ORIGINS:
  subset=[r for r in trace_stats if r['true_origin_evaluation_only']==origin];unknown=[r for r in subset if r['unknown_at_first_alarm']];any_unknown=[r for r in subset if r['any_confirmed_unknown']]
  breakdown.append(dict(origin_evaluation_only=origin,runs=len(subset),unknown_at_first_alarm=len(unknown),any_confirmed_unknown=len(any_unknown),confirmed_unknown_runtime_steps=sum(r['confirmed_unknown_steps'] for r in subset),unknown_control=sum(r['control_effect']==1 for r in unknown),unknown_actuator=sum(r['actuator_effect']==1 for r in unknown),unknown_plant=sum(r['plant_manifestation']==1 for r in unknown),unknown_with_full_observation_equivalence=sum('full_runtime_observation_history' in r['mixed_origin_equivalence_levels'] for r in unknown),runtime_wrong_localization_runs=sum(r['wrong_localized_runtime_steps']>0 for r in subset)))
 write_csv(out/'confirmed_unknown_breakdown.csv',breakdown)
 write_json(out/'identifiability_summary.json',dict(mixed_origin_groups={level:sum(r['level']==level for r in result) for level in ['full_runtime_observation_history','full_evidence_history','first_alarm_snapshot_only']},mixed_origin_sensor_groups=sum('SENSOR_CONTROL' in r['true_origins_evaluation_only'] and r['level']=='full_runtime_observation_history' for r in result),confirmed_unknown_first_alarm=sum(r['unknown_at_first_alarm'] for r in trace_stats),confirmed_unknown_anytime=sum(r['any_confirmed_unknown'] for r in trace_stats),wrong_localized_runtime_runs=sum(r['wrong_localized_runtime_steps']>0 for r in trace_stats),runtime_rows=len(final)*1201,exact_grouping=True))
 return result,breakdown

def report(out=OUTPUT):
 rows=records(out/'final_candidate_runs.csv');summaries=[];layers=[]
 for method in METHODS:
  subset=[r for r in rows if r['method']==method and (method!='Timing Monitor' or r['origin'] in ['NORMAL','TIMING'])];s=dict(method=method,**summarize(subset))
  if method in NONLOCAL:
   for k in list(s):
    if 'localiz' in k or 'ignorance' in k or 'conflict' in k or 'origin_rate' in k or 'correct_among' in k or k.startswith('unknown'):s[k]=None
  summaries.append(s)
  for origin in ORIGINS:
   if method=='Timing Monitor' and origin!='TIMING':continue
   layers.append(dict(method=method,origin=origin,**summarize([r for r in subset if r['origin']==origin])))
 write_csv(out/'final_candidate_summary.csv',[r for r in summaries if r['method']=='Final CLO-DSF']);write_csv(out/'final_candidate_baseline_comparison.csv',summaries);write_csv(out/'final_candidate_layer_summary.csv',layers);write_csv(out/'final_candidate_localization_summary.csv',[r for r in summaries if r['method'] not in NONLOCAL]);write_csv(out/'final_candidate_simplification_ablation.csv',[r for r in summaries if r['method'] in ['Final CLO-DSF','Candidate 2','Candidate 2 no origin discount','Final no temporal']])
 write_csv(out/'final_candidate_paired_comparison.csv',[paired(rows,m) for m in ['Weighted Sum','Simple OR','Candidate 2']])
 confusion=[]
 for origin in ORIGINS:
  subset=[r for r in rows if r['method']=='Final CLO-DSF' and r['origin']==origin]
  confusion.append(dict(true_origin_evaluation_only=origin,**{o:sum(r['detected'] and r['origin_at_alarm']==o for r in subset) for o in ORIGINS+['UNKNOWN']},misses=sum(not r['detected'] for r in subset)))
 write_csv(out/'final_candidate_origin_confusion.csv',confusion)
 uncertainty=[];final=[r for r in rows if r['method']=='Final CLO-DSF']
 cohorts={o:[r for r in final if r['origin']==o] for o in ORIGINS+['NORMAL']};cohorts.update(benign=[r for r in final if not r['injected']],faulty=[r for r in final if r['injected']],localized=[r for r in final if r['detected'] and not r['unknown_at_alarm']],unknown=[r for r in final if r['unknown_at_alarm']],correct=[r for r in final if r['localized_correct']],incorrect=[r for r in final if r['localized_wrong']])
 for cohort,subset in cohorts.items():
  for field in ['mean_anomaly_ignorance','mean_origin_ignorance','mean_detection_conflict','mean_localization_conflict','origin_score_at_alarm','origin_margin_at_alarm','origin_ignorance_at_alarm']:
   values=[r[field] for r in subset if not field.endswith('_at_alarm') or r['detected']];uncertainty.append(dict(cohort=cohort,quantity=field,n=len(values),mean=mean(values),p05=quantile(values,.05),median=quantile(values,.5),p95=quantile(values,.95)))
 write_csv(out/'final_candidate_uncertainty_summary.csv',uncertainty)
 identities(rows,out)
 print('Confirmation summaries, paired comparisons and identifiability complete.',flush=True)
