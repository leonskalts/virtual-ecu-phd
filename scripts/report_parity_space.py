#!/usr/bin/env python3
"""Locked post-hoc study accounting; never feeds outcomes to runtime."""
import json,collections,itertools,base64,zlib
import run_parity_space as d
import select_parity_space as p
import report_comparative_benchmark as common
import numpy as np
B=d.B;O=d.O;METHODS=['A0','A1','A2','A3','SVM-R default','SVM-R matched','SVM-P default','SVM-P matched']
FILTERS={**common.FILTERS,
 'weak_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step' and abs(x['magnitude'])<.8,
 'strong_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step' and abs(x['magnitude'])>=.8,
 'short_pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse' and x['duration_ms']<=250,
 'long_pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse' and x['duration_ms']>250,
 'slow_drift':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='ramp',
 **{domain+'_only':lambda x,domain=domain:x['origin']=='SENSOR_CONTROL' and x['domain']==domain for domain in ['A','B','C']},
 'global_common':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain']=='ABC'}

def stats(rr):
 s=common.stats(rr);s['wrong_confident_fault_runs']=p.wrong_fault(rr);s['wrong_confident_fault_samples']=sum(x['wrong_localized_runtime_samples'] for x in rr if x['injected']);s['first_accuracy_including_unknown']=s['correct_localizations']/s['detected'] if s['detected'] else None
 if rr and rr[0]['method'].startswith('SVM'):
  for k in list(s):
   if any(t in k for t in ['localiz','unknown','runtime_','wrong_confident','first_accuracy']):s[k]=None
  s['localization_provided']=False
 return s

def generate():
 d.verify();parts={part:json.loads((B/(part+'_evaluated.json')).read_text()) for part in ['TRAIN','CALIBRATION','VALIDATION','VALIDATION_BENIGN']};parts['VALIDATION']+=parts.pop('VALIDATION_BENIGN');rr=parts['VALIDATION'];by={m:{x['run_id']:x for x in rr if x['method']==m} for m in METHODS}
 allstats=[dict(partition=part,method=m,**stats([x for x in rows if x['method']==m])) for part,rows in parts.items() for m in METHODS];sums={x['method']:x for x in allstats if x['partition']=='VALIDATION'}
 d.h.write(O/'validation_summary.csv',allstats)
 sub=[dict(partition=part,method=m,subgroup=g,**stats([x for x in rows if x['method']==m and filt(x)])) for part,rows in parts.items() for m in METHODS for g,filt in FILTERS.items()];d.h.write(O/'subgroup_summary.csv',sub)
 pairs=[common.pair(rr,a,b,e) for a,b in [('A1','A0'),('A3','A0'),('A2','A0'),('A3','A1'),('A3','A2'),('A3','SVM-P default'),('A3','SVM-P matched'),('A3','SVM-R default'),('A3','SVM-R matched')] for e in ['fault','benign']];d.h.write(O/'paired_statistics.csv',pairs);d.h.write(O/'svm_comparison.csv',[s for s in allstats if s['method'].startswith('SVM') or s['method']=='A3'])
 loc=[dict(method=m,origin=origin,**stats([x for x in rr if x['method']==m and (origin=='ALL' or x['origin']==origin)])) for m in ['A0','A1','A2','A3'] for origin in ['ALL',*d.r.be.ORIGINS,'NORMAL']];d.h.write(O/'localization_summary.csv',loc)
 gainrows=[];gains={};lost={};windows=collections.Counter();directions=collections.Counter()
 for method,base in [('A1','A0'),('A3','A0'),('A3','A2')]:
  g=[x for k,x in by[method].items() if x['detected'] and not by[base][k]['detected']];gains[method+'_vs_'+base]=[x['run_id'] for x in g];lost[method+'_vs_'+base]=[k for k,x in by[base].items() if x['detected'] and not by[method][k]['detected']]
  for x in g:
   v=np.load(B/'tapes'/(x['run_id']+'_evaluated.npz'))['output'];idx=np.flatnonzero(v[:,0]==x['first_post_alarm_ms']);i=int(idx[0]);direction=int(v[i,5]);top=np.flatnonzero(np.isclose(v[i,7:11],v[i,7:11].max(),rtol=1e-12,atol=1e-12));label='A' if direction==1 else 'B' if direction==2 else 'C/AB ambiguous' if set(top)=={2,3} else 'nondirectional'
   gainrows.append(dict(comparison=method+'_vs_'+base,run_id=x['run_id'],origin=x['origin'],domain=x['domain'],kind=x['kind'],magnitude=x['magnitude'],duration_ms=x['duration_ms'],start_ms=x['start_ms'],winning_window=int(v[i,4]),direction=label,glrt=float(v[i,1]),strength=float(v[i,6]),first_origin=x['origin_at_alarm'],plant=x['plant_manifestation']))
   if method=='A1':windows[int(v[i,4])]+=1;directions[label]+=1
 d.h.write(O/'parity_gain_cases.csv',gainrows or [dict(comparison='A1_vs_A0',run_id='',origin='',domain='',kind='',magnitude='',duration_ms='',start_ms='',winning_window='',direction='',glrt='',strength='',first_origin='',plant='',note='No additional parity detections')])
 memory=[]
 for a,b in [('A2','A0'),('A3','A1')]:
  for group,filt in [('effective',FILTERS['effective_memory']),('dormant',FILTERS['dormant_memory'])]:
   keys=[k for k,x in by[b].items() if filt(x)];memory.append(dict(comparison=a+'_vs_'+b,group=group,cases=len(keys),before=sum(by[b][k]['detected'] for k in keys),after=sum(by[a][k]['detected'] for k in keys),gained=sum(by[a][k]['detected'] and not by[b][k]['detected'] for k in keys),lost=sum(by[b][k]['detected'] and not by[a][k]['detected'] for k in keys),benign_alarm_delta=sums[a]['benign_false_alarms']-sums[b]['benign_false_alarms']))
 d.h.write(O/'memory_gain_summary.csv',memory)
 a=sums['A3'];base=sums['A0'];critical={o:all(not x['detected'] or by['A3'][k]['detected'] for k,x in by['A0'].items() if x['origin']==o and (o!='MEMORY' or x['effective_memory_corruption'])) for o in ['MEMORY','TIMING','COMMUNICATION']}
 faultstats={m:stats([x for x in by[m].values() if x['injected']]) for m in ['A0','A3']}
 startup=all(not(x['false_alarm'] and 0<=x['first_alarm_ms']<1000) or (by['A0'][k]['false_alarm'] and 0<=by['A0'][k]['first_alarm_ms']<1000) for k,x in by['A3'].items())
 gate=dict(gain_ge_1pp=a['coverage']-base['coverage']>=.01,no_parity_losses=not lost['A1_vs_A0'] and not lost['A3_vs_A2'],benign_le_01=a['benign_false_alarm_rate']<=.01,zero_wrong_fault_origins=a['wrong_confident_fault_runs']==0,plant_ge_98=a['coverage_given_plant_manifestation']>=.98,localization_preserved=a['first_accuracy_including_unknown']>=base['first_accuracy_including_unknown'] and faultstats['A3']['runtime_accuracy_among_localized']>=faultstats['A0']['runtime_accuracy_among_localized'],startup_preserved=startup,**{o+'_preserved':v for o,v in critical.items()})
 promote=all(gate.values()) and bool(gains['A1_vs_A0']) and json.loads((B/'selected_parity.json').read_text())['cal_gate_passed']
 memoryclean=any(x['gained'] for x in memory if x['comparison']=='A2_vs_A0' and x['group']=='dormant') and not any(x['lost'] for x in memory if x['comparison']=='A2_vs_A0') and sums['A2']['benign_false_alarms']<=base['benign_false_alarms'] and sums['A2']['wrong_confident_fault_runs']==0 and all(not x['detected'] or by['A2'][k]['detected'] for k,x in by['A0'].items())
 retained='PARITY+MEMORY' if promote else 'MEMORY' if memoryclean else 'TRIPLEX'
 # Window attribution for all sensor detections, not only incremental gains.
 attribution=[]
 for method in ['A1','A3']:
  for group in ['weak_steps','strong_steps','short_pulses','long_pulses','slow_drift']:
   counts=collections.Counter()
   for x in by[method].values():
    if x['detected'] and FILTERS[group](x):
     v=np.load(B/'tapes'/(x['run_id']+'_evaluated.npz'))['output'];i=int(np.flatnonzero(v[:,0]==x['first_post_alarm_ms'])[0]);counts[(int(v[i,4]),bool(v[i,6]>0))]+=1
   attribution.append(dict(method=method,subgroup=group,window_and_parity_active={str(k):v for k,v in counts.items()}))
 robustness=[]
 for part,rows in parts.items():
  for m in ['A0','A1','A2','A3']:
   for field in ['magnitude','duration_ms','domain']:
    values=sorted({str(x[field]) for x in rows if x['origin']=='SENSOR_CONTROL'})
    for val in values:
     ss=[x for x in rows if x['method']==m and x['origin']=='SENSOR_CONTROL' and str(x[field])==val];robustness.append(dict(partition=part,method=m,field=field,value=val,cases=len(ss),detected=sum(x['detected'] for x in ss)))
   for phase in sorted({x['start_ms']%100 for x in rows if x['origin']=='SENSOR_CONTROL'}):
    ss=[x for x in rows if x['method']==m and x['origin']=='SENSOR_CONTROL' and x['start_ms']%100==phase];robustness.append(dict(partition=part,method=m,field='activation_phase_ms',value=phase,cases=len(ss),detected=sum(x['detected'] for x in ss)))
   for workload in sorted({x['workload'] for x in rows if x['origin']=='NORMAL'}):
    ss=[x for x in rows if x['method']==m and x['origin']=='NORMAL' and x['workload']==workload];robustness.append(dict(partition=part,method=m,field='benign_workload',value=workload,cases=len(ss),alarms=sum(x['false_alarm'] for x in ss)))
 report=dict(overall=sums,promotion_gate=gate,parity_promoted=promote,memory_clean_gain=bool(memoryclean),retained=retained,gains=gains,lost=lost,paired=pairs,memory=memory,winning_windows=dict(windows),winning_directions=dict(directions),window_attribution=attribution,robustness=robustness)
 d.dump(B/'report.json',report)
 threshold_record=dict(primary=json.loads((B/'selected_parity.json').read_text()),tail=json.loads((B/'tail_calibration.json').read_text()),mapping=json.loads((B/'mapping_grid.json').read_text()),svm=json.loads((B/'svm_selection.json').read_text()),registration=json.loads((B/'registration.json').read_text()),validation_lock=json.loads((B/'lock.json').read_text()),manifest=json.loads((B/'specs.json').read_text()),report=report,models={space:dict(encoding='zlib+base85 pickle; trusted local study artifact only',sha256=d.sha(B/('svm_'+space+'.pkl')),data=base64.b85encode(zlib.compress((B/('svm_'+space+'.pkl')).read_bytes())).decode()) for space in ['R','P']})
 d.dump(O/'thresholds.json',threshold_record)
 lines=['# Multiscale parity-space findings','',f'Retained architecture: {retained}. Parity promotion: {promote}.',f'Gate: {json.dumps(gate)}.','', '| Method | Detection | Wilson95% | Benign | Plant | Precision | Median/P95 ms |','|---|---|---|---|---|---|---|']
 for m,s in sums.items():lines.append(f"| {m} | {s['detected']}/{s['faulty_runs']} | {100*s['ci_low']:.2f}–{100*s['ci_high']:.2f}% | {s['benign_false_alarms']}/{s['benign_runs']} | {s['plant_detected']}/{s['plant_manifestation_runs']} | {s['precision']:.5f} | {s['latency_median_ms']}/{s['latency_p95_ms']} |")
 lines+=['',f"Parity incremental A1 vsA0: {len(gains['A1_vs_A0'])}; A3 vsA2: {len(gains['A3_vs_A2'])}. Parity losses: {lost}. Memory: {json.dumps(memory)}.",'',f"Winning windows: {dict(windows)}; directions: {dict(directions)}. C/AB squared scores are identical; no faulty-member claims. Global equal common mode is unobservable to parity; any detected global case requires separate physical runtime evidence or a timing/alignment transient and is not proof of absolute common-mode observability.",'','All eight methods share physical cases. SVM receives cross-layer observations including250ms memory and raw parity; SVM-P also receives every parity statistic. Statistical and fault-origin uncertainty are preserved. UNKNOWN is not correct first-detection localization; wrong-origin promotion gate counts FAULT runs, while all-runtime and benign origin samples are also reported.','',f'Window attribution (active means nonzero new parity strength): {json.dumps(attribution)}.','', 'TRAIN/CAL/VALID performance is in validation_summary.csv; subgroup_summary.csv separates nearby amplitudes and fault families through subgroup definitions. Detailed amplitude/phase/duration/channel/benign-regime audits are embedded in thresholds.json. No tuning after validation. CIs/McNemar are descriptive for grouped deterministic campaigns; no statistical-method novelty claim. Regression and integrity results are recorded in calibration_record.md.']
 (O/'findings.md').write_text('\n'.join(lines)+'\n');print('REPORT',retained,gate,'GAINS', {k:len(v) for k,v in gains.items()},flush=True)
if __name__=='__main__':generate()
