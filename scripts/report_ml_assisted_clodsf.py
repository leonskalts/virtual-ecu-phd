#!/usr/bin/env python3
"""Locked post-hoc accounting; never imported by runtime or model selection."""
import json,collections,math,itertools
import run_ml_assisted_clodsf as d
import report_comparative_benchmark as common
import numpy as np
B=d.B;O=d.O;METHODS=['A0','A1-default','A1-matched','A2','A3']

def stats(rr):
 s=common.stats(rr)
 s['first_detection_accuracy']=s['correct_localizations']/s['detected'] if s['detected'] else None
 if rr and rr[0]['method'].startswith('A1'):
  for k in list(s):
   if any(x in k for x in ['localiz','unknown','runtime_','first_detection_accuracy']):s[k]=None
  s['localization_provided']=False
 return s

FILTERS={**common.FILTERS,
 'weak_plus_049_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step' and abs(x['magnitude']-.49)<1e-9,
 'strong_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step' and abs(x['magnitude'])>.5,
 'short_pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse' and x['duration_ms']<=250,
 'long_pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse' and x['duration_ms']>250,
 'slow_drift':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='ramp',
 **{domain+'_only':lambda x,domain=domain:x['origin']=='SENSOR_CONTROL' and x['domain']==domain for domain in ['A','B','C']}}

def gain_group(x):
 if x['origin']!='SENSOR_CONTROL':return x['origin']
 if FILTERS['weak_plus_049_steps'](x):return 'weak_steps'
 if x['kind']=='pulse':return 'pulses'
 return 'other_sensor'

def generate():
 d.verify();parts={p:json.loads((B/(p+'_evaluated.json')).read_text()) for p in ['TRAIN','CALIBRATION','VALIDATION','VALIDATION_BENIGN']};parts['VALIDATION']+=parts.pop('VALIDATION_BENIGN')
 allstats=[dict(partition=p,method=m,**stats([x for x in rr if x['method']==m])) for p,rr in parts.items() for m in METHODS]
 sums={x['method']:x for x in allstats if x['partition']=='VALIDATION'};rr=parts['VALIDATION'];by={m:{x['run_id']:x for x in rr if x['method']==m} for m in METHODS}
 sub=[dict(method=m,subgroup=g,**stats([x for x in rr if x['method']==m and filt(x)])) for m in METHODS for g,filt in FILTERS.items()]
 d.h.write(O/'validation_summary.csv',list(sums.values()));d.h.write(O/'partition_summary.csv',allstats);d.h.write(O/'subgroup_summary.csv',sub)
 paired=[common.pair(rr,'A3',m,e) for m in ['A0','A1-default','A1-matched'] for e in ['fault','benign']];d.h.write(O/'paired_statistics.csv',paired)
 d.h.write(O/'matched_fpr_comparison.csv',[dict(**sums[m],observed_validation_fpr_le_01=sums[m]['benign_false_alarm_rate']<=.01) for m in ['A0','A1-matched','A3']])
 loc=[]
 for m in ['A0','A2','A3']:
  for origin in ['ALL',*d.old.be.ORIGINS,'NORMAL']:
   s=stats([x for x in rr if x['method']==m and (origin=='ALL' or x['origin']==origin)])
   loc.append(dict(method=m,origin=origin,**{k:v for k,v in s.items() if any(t in k for t in ['localiz','unknown','runtime_','first_detection'])}))
 d.h.write(O/'localization_summary.csv',loc)
 d.h.write(O/'confusion_summary.csv',[dict(method=m,origin=o,**{p:sum(x['alarm_'+p] for x in by[m].values() if x['origin']==o) for p in [*d.old.be.ORIGINS,'UNKNOWN']}) for m in ['A0','A2','A3'] for o in [*d.old.be.ORIGINS,'NORMAL']])
 gains=[x for k,x in by['A3'].items() if x['detected'] and not by['A0'][k]['detected']];losses=[k for k,x in by['A0'].items() if x['detected'] and not by['A3'][k]['detected']];groups=collections.Counter(gain_group(x) for x in gains)
 d.h.write(O/'incremental_detections.csv',[dict(run_id=x['run_id'],origin=x['origin'],subgroup=gain_group(x),first_alarm_ms=x['first_post_alarm_ms'],physical_origin=x['origin_at_alarm'],plant=x['plant_manifestation'],interpretation='sensor-origin gain' if x['origin']=='SENSOR_CONTROL' else 'cross-origin binary effect; sensor ML cannot establish this fault origin') for x in gains])
 a=sums['A3'];base=sums['A0'];critical={o:all(not x['detected'] or by['A3'][k]['detected'] for k,x in by['A0'].items() if x['origin']==o and (o!='MEMORY' or x['effective_memory_corruption'])) for o in ['MEMORY','TIMING','COMMUNICATION','ACTUATOR']}
 startup=all(not(x['false_alarm'] and 0<=x['first_alarm_ms']<1000) or (by['A0'][k]['false_alarm'] and 0<=by['A0'][k]['first_alarm_ms']<1000) for k,x in by['A3'].items())
 gate=dict(gain_at_least_1pp=a['coverage']-base['coverage']>=.01,benign_le_01=a['benign_false_alarm_rate']<=.01,plant_ge_98=a['coverage_given_plant_manifestation']>=.98,zero_wrong_origins=a['runtime_wrong_runs']==0,first_detection_100=a['correct_localizations']==a['detected'],startup_preserved=startup,**{o+'_preserved':v for o,v in critical.items()})
 config=json.loads((O/'calibration.json').read_text());gate['calibration_gate']=config['calibration_gate_passed'];promote=all(gate.values())
 # Distribution tails and boundary/phase checks: TRAIN defines the tail boundary.
 import pickle
 model=pickle.loads((O/'provider_svm.pkl').read_bytes());scaler=model[0]
 trainmax=[]
 for row,v in d.dataset('TRAIN'):
  if row['origin']=='NORMAL':trainmax.append(float(np.abs(scaler.transform(v['features'])).max()))
 tail=float(np.quantile(trainmax,.95));tails=[];reliability=[];brier={};phase=[]
 for part in ['TRAIN','CALIBRATION','VALIDATION']:
  dataset=itertools.chain(d.dataset(part),d.dataset('VALIDATION_BENIGN')) if part=='VALIDATION' else d.dataset(part)
  qq=[];yy=[]
  for row,v in dataset:
   saved=np.load(B/'tapes'/(row['run_id']+'_evaluated.npz'));pool=np.flatnonzero(v['qualified']);idx=pool[np.unique(np.linspace(0,len(pool)-1,min(16,len(pool)),dtype=int))] if len(pool) else []
   if len(idx):qq.extend(saved['q'][idx]);yy.extend(v['sensor_target'][idx])
   if part=='VALIDATION' and row['origin']=='NORMAL':
    z=float(np.abs(scaler.transform(v['features'])).max());tails.append(dict(run_id=row['run_id'],max_abs_train_z=z,train_benign_run_max_p95=tail,in_tail=z>tail,max_q=float(saved['q'].max()),A0_alarm=by['A0'][row['run_id']]['false_alarm'],A3_alarm=by['A3'][row['run_id']]['false_alarm']))
  q=np.array(qq);y=np.array(yy);brier[part]=float(np.mean((q-y)**2))
  for lo in np.linspace(0,.9,10):
   take=(q>=lo)&(q<lo+.1+1e-12);reliability.append(dict(partition=part,low=float(lo),frames=int(take.sum()),mean_q=float(q[take].mean()) if take.any() else None,observed=float(y[take].mean()) if take.any() else None))
 for m in METHODS:
  for ph in [17,47,79]:phase.append(dict(method=m,phase_ms=ph,**stats([x for x in rr if x['method']==m and x['origin']=='SENSOR_CONTROL' and x['start_ms']%100==ph])))
 d.h.write(O/'benign_tail_analysis.csv',tails);d.h.write(O/'phase_generalization.csv',phase);d.h.write(O/'probability_reliability.csv',reliability)
 # Five honest representatives, using misses if hybrid-only cases do not exist.
 chosen=[('hybrid_only',x['run_id']) for x in gains[:2]]
 if len(chosen)<2:
  misses=[x['run_id'] for x in by['A3'].values() if x['origin']=='SENSOR_CONTROL' and not x['detected']]
  chosen += [('substitute_sensor_miss_no_hybrid_only_available',k) for k in misses[:2-len(chosen)]]
 both=[k for k,x in by['A3'].items() if x['injected'] and x['detected'] and by['A0'][k]['detected']];chosen += [('both_detect',both[0])] if both else []
 benign=[]
 for k,x in by['A3'].items():
  if not x['injected'] and not x['false_alarm']:
   v=np.load(B/'tapes'/(k+'.npz'));q=np.load(B/'tapes'/(k+'_evaluated.npz'))['q'];benign.append((float(q[v['qualified']].max()) if v['qualified'].any() else 0,k))
 chosen += [('benign_high_score_suppressed',k) for _,k in sorted(benign,reverse=True)[:2]]
 reps=['# Representative cases','',f'Actual hybrid-only detections: {len(gains)}. Substitutions are identified explicitly. No extra traces retained.','']
 for role,k in chosen:
  x=by['A3'][k];v=np.load(B/'tapes'/(k+'.npz'));q=np.load(B/'tapes'/(k+'_evaluated.npz'))['q'];ix=int(q.argmax());reps += [f'## {k}: {role}',f"Origin {x['origin']}; {x['domain']}/{x['kind']}; magnitude {x['magnitude']}. A0/A3 detection {by['A0'][k]['detected']}/{x['detected']}; A3 benign alarm {x['false_alarm']}. Peak q={q[ix]:.6g} at {int(v['time'][ix])} ms, qualified={bool(v['qualified'][ix])}, physical sensor strength={v['features'][ix,0]:.6g}. First A3 origin {x['origin_at_alarm']}. Final DS threshold, temporal requirements and gate still apply; high q alone is not an alarm.",'']
 (O/'representative_cases.md').write_text('\n'.join(reps))
 fields=['run_id','partition','method','origin','domain','kind','magnitude','start_ms','duration_ms','injected','detected','false_alarm','latency_ms','plant_manifestation','silent_plant','effective_memory_corruption','initially_latent_stuck','initially_excited','actuator_excited','origin_at_alarm','localized_correct','localized_wrong','unknown_at_alarm','wrong_localized_runtime_samples','alarm_samples','alarm_UNKNOWN','raw_sha256','runtime_trace_sha256']
 d.h.write(O/'case_sufficient_statistics.csv',[{k:x.get(k) for k in fields} for x in rr])
 gap={m:{p:next(s['coverage'] for s in allstats if s['partition']==p and s['method']==m)-sums[m]['coverage'] for p in ['TRAIN','CALIBRATION']} for m in METHODS}
 report=dict(overall=sums,subgroups=sub,paired=paired,gains=dict(groups),gain_cases=len(gains),lost_cases=losses,promotion_gate=gate,promoted=promote,retained='ML-ASSISTED-CLODSF' if promote else 'TRIPLEX',gap=gap,brier=brier,tail_cases=sum(x['in_tail'] for x in tails),tail_alarms=sum(x['in_tail'] and x['A3_alarm'] for x in tails))
 d.dump(O/'report.json',report)
 lines=['# ML-assisted development findings','',f"Retention: {report['retained']}. Promotion gate: {json.dumps(gate,sort_keys=True)}.",'','| Method | Detection | Wilson 95% | Benign | Plant | Precision | Median/P95 ms |','|---|---|---|---|---|---|---|']
 for m,s in sums.items():lines.append(f"| {m} | {s['detected']}/{s['faulty_runs']} | {100*s['ci_low']:.2f}–{100*s['ci_high']:.2f}% | {s['benign_false_alarms']}/{s['benign_runs']} | {s['plant_detected']}/{s['plant_manifestation_runs']} | {s['precision']:.4f} | {s['latency_median_ms']}/{s['latency_p95_ms']} |")
 lines += ['',f"Incremental groups: {dict(groups)}; lost detections: {len(losses)}. Paired tests: {json.dumps(paired)}.",'',f"TRAIN/CAL minus VALIDATION detection gaps: {json.dumps(gap)}. Qualified-frame Brier scores: {brier}. CAL reliability is apparent (also used for calibration and selection); VALIDATION reliability is post-hoc only. Benign TRAIN-defined tail: {report['tail_cases']} cases, {report['tail_alarms']} A3 alarms. See boundary subgroups and unseen-phase table; no parameters changed after validation.",'','Linear standardized weights describe associations, not causes. SVM and physical evidence share inputs; discounting does not establish statistical independence. Standalone uses the same twelve sensor features and all-fault labels; it is not the historical cross-layer SVM. UNKNOWN is not counted as correct first-detection localization. Wilson intervals and exact McNemar are descriptive for deterministic grouped cases, without multiplicity adjustment.','',f"Additional non-sensor detections: {sum(v for k,v in groups.items() if k in d.old.be.ORIGINS)}. Such gains, if any, are binary fusion effects of sensor evidence; ML supplies no physical origin diagnosis. No unseen execution, commit or push. Retained source and prior evidence hashes are checked separately in validation_record.md."]
 (O/'findings.md').write_text('\n'.join(lines)+'\n');print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':generate()
