#!/usr/bin/env python3
"""Post-hoc accounting only. No output feeds selection or runtime inference."""
import json,collections,base64,zlib,csv
import run_dynamic_consensus as d
import select_dynamic_consensus as p
import report_comparative_benchmark as common
import numpy as np
B=d.B;O=d.O;METHODS=['A0','A1','A2','A3','A4','SVM-DYN default','SVM-DYN CAL1']
FILTERS={**common.FILTERS,'weak_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step' and abs(x['magnitude'])<.8,'strong_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step' and abs(x['magnitude'])>=.8,'short_pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse' and x['duration_ms']<=250,'long_pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse' and x['duration_ms']>250,'slow_drift':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='ramp',**{domain+'_only':lambda x,domain=domain:x['origin']=='SENSOR_CONTROL' and x['domain']==domain for domain in ['A','B','C','AB','ABC']}}
def stats(rr):
 s=common.stats(rr);s['wrong_confident_fault_runs']=p.wrong_fault(rr);s['wrong_confident_fault_samples']=sum(x['wrong_localized_runtime_samples'] for x in rr if x['injected'])
 if s['benign_runs']:s['benign_ci_low'],s['benign_ci_high']=d.h.wilson(s['benign_false_alarms'],s['benign_runs'])
 if rr and rr[0]['method'].startswith('SVM'):
  for k in list(s):
   if any(t in k for t in ['localiz','unknown','runtime_','wrong_confident']):s[k]=None
 return s

def generate():
 d.verify();parts={part:json.loads((B/(part+'_evaluated.json')).read_text()) for part in ['TRAIN','CALIBRATION','VALIDATION','VALIDATION_BENIGN']};parts['VALIDATION']+=parts.pop('VALIDATION_BENIGN');rr=parts['VALIDATION'];by={m:{x['run_id']:x for x in rr if x['method']==m} for m in METHODS+['M1','M2']};config=json.loads((B/'selected.json').read_text())
 allstats=[dict(partition=part,method=m,**stats([x for x in rows if x['method']==m])) for part,rows in parts.items() for m in METHODS];sums={x['method']:x for x in allstats if x['partition']=='VALIDATION'};d.h.write(O/'validation_summary.csv',allstats)
 sub=[dict(partition=part,method=m,subgroup=g,**stats([x for x in rows if x['method']==m and filt(x)])) for part,rows in parts.items() for m in METHODS for g,filt in FILTERS.items()]
 for part,rows in parts.items():
  for m in METHODS:
   groups=collections.defaultdict(list)
   for x in rows:
    if x['method']!=m:continue
    if x['origin']=='SENSOR_CONTROL':
     for key,value in [('amplitude',round(abs(x['magnitude']),3)),('duration_ms',x['duration_ms']),('activation_mod1000',x['start_ms']%1000),('channel',x['domain'])]:groups[f'audit_{key}={value}'].append(x)
    if x['origin']=='NORMAL':groups['audit_benign_regime='+x['workload']].append(x)
   sub.extend(dict(partition=part,method=m,subgroup=g,**stats(v)) for g,v in groups.items())
 d.h.write(O/'subgroup_summary.csv',sub)
 comparisons=[('A1','A0'),('A2','A0'),('A3','A0'),('A3','A1'),('A3','A2'),('A4','A0'),('A4','A3'),('A4','SVM-DYN default'),('A4','SVM-DYN CAL1')]
 pairs=[dict(partition=part,**common.pair(rows,a,b,e)) for part,rows in parts.items() for a,b in comparisons for e in ['fault','benign']];d.h.write(O/'paired_statistics.csv',pairs);d.h.write(O/'svm_comparison.csv',[s for s in allstats if s['method'].startswith('SVM') or s['method']=='A4'])
 loc=[dict(partition=part,method=m,origin=origin,**stats([x for x in rows if x['method']==m and (origin=='ALL' or origin=='FAULT' and x['injected'] or x['origin']==origin)])) for part,rows in parts.items() for m in ['A0','A3','A4'] for origin in ['ALL','FAULT',*d.r.be.ORIGINS,'NORMAL']];d.h.write(O/'localization_summary.csv',loc)
 gains={};lost={};gainrows=[]
 for method,base in comparisons[:7]:
  key=method+'_vs_'+base;gains[key]=[k for k,x in by[method].items() if x['detected'] and not by[base][k]['detected']];lost[key]=[k for k,x in by[base].items() if x['detected'] and not by[method][k]['detected']]
  if method not in ['A3','A4']:continue
  for k in gains[key]:
   x=by[method][k];v=np.load(B/'tapes'/(k+'_evaluated.npz'))['output'];i=int(np.flatnonzero(v[:,0]==x['first_post_alarm_ms'])[0]);hyp=['UNKNOWN','HA','HB','HC','HAB'][int(v[i,13])] if v[i,12]>0 else 'UNKNOWN';gainrows.append(dict(comparison=key,run_id=k,origin=x['origin'],domain=x['domain'],kind=x['kind'],magnitude=x['magnitude'],duration_ms=x['duration_ms'],dominant_hypothesis=hyp,D=v[i,6],margin=v[i,7],mass=v[i,11],origin_support=v[i,12],first_origin=x['origin_at_alarm']))
 d.h.write(O/'hypothesis_gain_summary.csv',gainrows or [dict(note='No additional detections')])
 memory=[]
 for part,rows in parts.items():
  bm={m:{x['run_id']:x for x in rows if x['method']==m} for m in ['A0','M1','M2','A4']}
  for m in ['M1','M2','A4']:
   for group in ['effective_memory','dormant_memory']:
    keys=[k for k,x in bm['A0'].items() if FILTERS[group](x)];memory.append(dict(partition=part,method=m,group=group,cases=len(keys),before=sum(bm['A0'][k]['detected'] for k in keys),after=sum(bm[m][k]['detected'] for k in keys),gained=sum(bm[m][k]['detected'] and not bm['A0'][k]['detected'] for k in keys),lost=sum(bm['A0'][k]['detected'] and not bm[m][k]['detected'] for k in keys),benign_delta=sum(x['false_alarm'] for x in bm[m].values())-sum(x['false_alarm'] for x in bm['A0'].values())))
 d.h.write(O/'memory_summary.csv',memory)
 benign=[]
 for part,rows in parts.items():
  bm={m:{x['run_id']:x for x in rows if x['method']==m} for m in ['A0','A2','A3']}
  for k,x in bm['A0'].items():
   if not x['false_alarm']:continue
   v=np.load(B/'tapes'/(k+'_evaluated.npz'))['output'];a=np.load(B/'tapes'/(k+'.npz'));idx=np.flatnonzero(v[:,15]>0);i=int(idx[0]);e=a['values'];av=a['available'];window=slice(max(0,i-4),i+1);active=np.any((e[window,:5]>0)&(av[window,:5]>0),axis=0);names=['TIMING','COMMUNICATION','MEMORY','SENSOR_CONTROL','ACTUATOR'];categories=[names[j] for j in range(5) if active[j]];category=categories[0] if len(categories)==1 else 'multiple' if categories else 'temporal_or_plant_only';status='strongly_healthy' if v[i,10]>0 else 'fault_like' if v[i,6]>0 else 'ambiguous';benign.append(dict(partition=part,run_id=k,workload=x['workload'],first_alarm_ms=v[i,0],category=category,contributors='|'.join(categories),H0_status=status,D=v[i,6],consistency=v[i,8],common_innovation=v[i,9],q_healthy=v[i,10],A2_suppressed=not bm['A2'][k]['false_alarm'],A3_suppressed=not bm['A3'][k]['false_alarm'],provenance='active evidence in five-frame confirmation window; contributor accounting, not injected labels'))
 d.h.write(O/'benign_root_cause.csv',benign or [dict(note='No baseline benign alarms')])
 a=sums['A4'];base=sums['A0'];critical={o:all(not x['detected'] or by['A4'][k]['detected'] for k,x in by['A0'].items() if x['origin']==o and (o!='MEMORY' or x['effective_memory_corruption'])) for o in ['MEMORY','TIMING','COMMUNICATION']};increment={aa+'_vs_'+bb:sum(x['false_alarm'] and not by[bb][k]['false_alarm'] for k,x in by[aa].items()) for aa,bb in [('A1','A0'),('A3','A2')]}
 gate=dict(gain_ge_2pp=a['coverage']-base['coverage']>=.02-1e-12,total_benign_le_015=a['benign_false_alarm_rate']<=.015,incremental_dynamic_le_005=max(increment.values())<=6,zero_wrong_fault_origins=a['wrong_confident_fault_runs']==0,first_accuracy_ge_999=a['accuracy_when_localized']>=.999,plant_ge_97=a['coverage_given_plant_manifestation']>=.97,**{o+'_preserved':v for o,v in critical.items()})
 promote=all(gate.values()) and config['cal_gate_passed'];faultstats=stats([x for x in by['A4'].values() if x['injected']]);benignval=[x for x in benign if x['partition']=='VALIDATION'];report=dict(overall=sums,promotion_gate=gate,promoted=promote,retained='DYNAMIC-CONSENSUS+MEMORY' if promote else 'TRIPLEX',selected=config,gains=gains,lost=lost,incremental_benign=increment,paired=[x for x in pairs if x['partition']=='VALIDATION'],memory=[x for x in memory if x['partition']=='VALIDATION'],fault_runtime=faultstats,subgroups=[x for x in sub if x['partition']=='VALIDATION' and x['method']=='A4'],benign_categories=dict(collections.Counter(x['category'] for x in benignval)),benign_H0=dict(collections.Counter(x['H0_status'] for x in benignval)),suppressed={m:sum(x[m+'_suppressed'] for x in benignval) for m in ['A2','A3']},both_actual_le_1pct=a['benign_false_alarm_rate']<=.01 and sums['SVM-DYN CAL1']['benign_false_alarm_rate']<=.01,strong_success=a['detected']>=sums['SVM-DYN default']['detected'] and a['benign_false_alarm_rate']<=.015,very_strong_success=a['detected']>sums['SVM-DYN default']['detected'] and a['benign_false_alarm_rate']<=.01 and a['coverage_given_plant_manifestation']>=.99)
 sensor_gains=[by['A3'][k] for k in gains['A3_vs_A0'] if by['A3'][k]['origin']=='SENSOR_CONTROL']
 report['dynamic_gain_concentration']={key:dict(collections.Counter(str(x[key]) for x in sensor_gains)) for key in ['domain','kind','magnitude','duration_ms']}
 report['narrow_sensor_gain_flag']=bool(sensor_gains) and (len({abs(x['magnitude']) for x in sensor_gains})<=1 or len({x['domain'] for x in sensor_gains})<=1)
 d.dump(B/'report.json',report)
 payload=lambda path:dict(encoding='zlib+base85 trusted local pickle',sha256=d.sha(path),data=base64.b85encode(zlib.compress(path.read_bytes())).decode())
 record=dict(primary=config,tail=json.loads((B/'tails.json').read_text()),selection=json.loads((B/'coherence_selection.json').read_text()),svm=json.loads((B/'svm_selection.json').read_text()),registration=json.loads((B/'registration.json').read_text()),validation_lock=json.loads((B/'lock.json').read_text()),manifest=json.loads((B/'specs.json').read_text()),overlap_audit=list(csv.DictReader((B/'historical_overlap_audit.csv').open())),report=report,svm_model=payload(B/'svm.pkl'))
 metric_keys=['run_id','method','detected','false_alarm','plant_manifestation','effective_memory_corruption','first_post_alarm_ms','latency_ms','origin_at_alarm','localized','correct_localization','alarm_samples','localized_runtime_samples','correct_localized_runtime_samples','wrong_localized_runtime_samples','unknown_runtime_samples','localized_correct','localized_wrong','unknown_at_alarm','first_localization_ms','first_origin','propagation_plant_ms','silent_plant','initially_excited','actuator_excited',*['alarm_'+o for o in d.r.be.ORIGINS],'alarm_UNKNOWN']
 compact=[{k:x[k] for k in metric_keys if k in x} for rows in parts.values() for x in rows]
 record['software']={'numpy':np.__version__,'sklearn':__import__('sklearn').__version__,'python':__import__('sys').version}
 record['case_metrics']={'encoding':'zlib+base85 JSON; offline outcomes only, no raw traces','rows':len(compact),'data':base64.b85encode(zlib.compress(json.dumps(compact,separators=(',',':')).encode())).decode()}
 d.dump(O/'calibration.json',record)
 lines=['# Dynamic consensus findings','',f"Promotion: {promote}; calibration eligible: {config['cal_gate_passed']}. Retained: {report['retained']} (existing retained architecture; M1 remains available unchanged; selected M2 is an evaluated schedule, not silently promoted; rejected provider remains switchable study code only).",f'Gate: {json.dumps(gate)}.','', '| Method | Detection | Wilson95% | Benign | Plant | Precision | Median/P95 ms |','|---|---|---|---|---|---|---|']
 for m,s in sums.items():lines.append(f"| {m} | {s['detected']}/{s['faulty_runs']} | {100*s['ci_low']:.2f}–{100*s['ci_high']:.2f}% | {s['benign_false_alarms']}/{s['benign_runs']} | {s['plant_detected']}/{s['plant_manifestation_runs']} | {s['precision']:.5f} | {s['latency_median_ms']}/{s['latency_p95_ms']} |")
 lines+=['',f"Benign root causes: {report['benign_categories']}; H0 status: {report['benign_H0']}; suppressed: {report['suppressed']}; new dynamic alarms: {increment}.",f"Gains: { {k:len(v) for k,v in gains.items()} }; lost: {lost}. Discount losses A2/A0 and A3/A1 must be considered before calling suppression safe.",f"Memory results: {json.dumps(report['memory'])}.",f"FAULT localization: {json.dumps(faultstats)}. Benign assigned origins are counted separately; detector member-hypothesis support is not a proven faulty-member identity.",f"BOTH actual low-FPR<=1%: {report['both_actual_le_1pct']}. Strong: {report['strong_success']}; very strong: {report['very_strong_success']}.",'',f"Dynamic sensor gain concentration: {report['dynamic_gain_concentration']}; narrow amplitude/channel flag: {report['narrow_sensor_gain_flag']}.",'TRAIN/CAL/VALID remain separate in all summary tables. Registered parameter families are disjoint, but generator structure and physical fault semantics are shared; this is nearby-configuration development generalization, not independent field sampling. Amplitude/duration/phase/channel/benign-regime rows expose concentration of gains, not selection feedback. Five-frame root-cause windows describe active evidence contributors; they do not prove physical cause from labels. Dynamic and discount counterfactual replays provide the direct ablation.','Identical global ABC corruption has no independent physical reference. Unexcited-throughout actuator performance faults and memory outside probe/use overlap remain limits. Constant-velocity latent state is sensor consensus, not truth. Relative sensor variance is not uniquely identifiable under correlated acquisition errors; fitted variance includes benign mismatch. Full Gaussian scoring is comparable across hypotheses, while robust state updates make the robust bank a quasi-likelihood model. Run-max calibration is empirical for grouped deterministic simulator cases, not a field false-alarm guarantee. No validation tuning or unseen.','Scientific/protocol/model locks, full manifest, overlap audit, selection records and comparator model are embedded in calibration.json. Temporary traces are removed after final integrity and accounting.']
 (O/'findings.md').write_text('\n'.join(lines)+'\n');print('REPORT',gate,'PROMOTION',promote,flush=True)
if __name__=='__main__':generate()
