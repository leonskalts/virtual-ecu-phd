#!/usr/bin/env python3
"""Locked post-hoc accounting, no validation selection."""
import json,base64,zlib,collections
import run_benign_alarm as t
B=t.B;O=t.O

def stats(rows):
 s=t.old.common.stats(rows);s['wrong_fault_runs']=sum(bool(x['wrong_localized_runtime_samples']) for x in rows if x['injected']);s['wrong_fault_samples']=sum(x['wrong_localized_runtime_samples'] for x in rows if x['injected'])
 if rows and rows[0]['method'].startswith('SVM'):
  for k in list(s):
   if any(v in k for v in ['localiz','unknown','runtime_','wrong_fault']):s[k]=None
  s['localization_provided']=False
 return s

def main():
 t.verify();sel=json.loads((O/'selection.json').read_text());parts={p:json.loads((B/(p+'_rows.json')).read_text()) for p in ['TRAIN','CALIBRATION','VALIDATION']};summary=[];sub=[];loc=[];pairs=[]
 for part,rr in parts.items():
  methods=['A2 original','Refined','SVM-INT default','SVM-INT CAL1'] if part=='VALIDATION' else ['A2 original','G1','G2','G3','G4','SVM-INT default','SVM-INT CAL1']
  for m in methods:
   rows=[x for x in rr if x['method']==m];summary.append(dict(partition=part,method=m,**stats(rows)))
   for origin in [*t.old.d.r.be.ORIGINS,'NORMAL']:
    chosen=[x for x in rows if x['origin']==origin];sub.append(dict(partition=part,method=m,origin=origin,**stats(chosen)))
   sub.append(dict(partition=part,method=m,origin='INTEGRITY_OBSERVED',**stats([x for x in rows if x['injected'] and x['integrity_observed']])))
   if not m.startswith('SVM'):
    for group,f in [('FAULT',lambda x:x['injected']),('BENIGN',lambda x:not x['injected'])]:loc.append(dict(partition=part,method=m,group=group,**stats([x for x in rows if f(x)])))
  chosen='Refined' if part=='VALIDATION' else 'G'+str(sel['selected']) if sel['selected'] else 'A2 original'
  for base in ['A2 original','SVM-INT default','SVM-INT CAL1']:
   for endpoint in ['fault','benign']:pairs.append(dict(partition=part,**t.old.common.pair(rr,chosen,base,endpoint)))
 t.h.write(O/'summary.csv',summary);t.h.write(O/'per_origin.csv',sub);t.h.write(O/'localization.csv',loc);t.h.write(O/'paired.csv',pairs)
 rr=parts['VALIDATION'];b={x['run_id']:x for x in rr if x['method']=='A2 original'};a={x['run_id']:x for x in rr if x['method']=='Refined'};lost=[k for k,x in b.items() if x['detected'] and not a[k]['detected']];gained=[k for k,x in a.items() if x['detected'] and not b[k]['detected']];plant_lost=[k for k in lost if b[k]['plant_manifestation']];integrity_lost=[k for k in lost if b[k]['integrity_observed']];s={x['method']:x for x in summary if x['partition']=='VALIDATION'};remaining=[dict(run_id=k,workload=x['workload'],first_alarm_ms=x['first_alarm_ms'],alarm_samples=x['alarm_samples'],integrity_observed=x['integrity_observed']) for k,x in a.items() if x['false_alarm']];t.h.write(O/'remaining_benign.csv',remaining or [dict(note='Zero remaining benign alarm runs')])
 gates=dict(benign_le_005=s['Refined']['benign_false_alarm_rate']<=.005,no_plant_losses=not plant_lost,no_wrong_fault_origins=s['Refined']['wrong_fault_runs']==0,no_integrity_losses=not integrity_lost,loss_le_0025=len(lost)<=3)
 report=dict(selected=sel['selected'],summary=s,lost=lost,gained=gained,plant_lost=plant_lost,integrity_lost=integrity_lost,benign_removed=sum(x['false_alarm'] and not a[k]['false_alarm'] for k,x in b.items()),benign_added=sum(x['false_alarm'] and not b[k]['false_alarm'] for k,x in a.items()),remaining_benign=remaining,gates=gates,retained=sel['eligible'] and all(gates.values()) and s['Refined']['benign_false_alarms']<s['A2 original']['benign_false_alarms'],paired=[x for x in pairs if x['partition']=='VALIDATION']);t.dump(O/'report.json',report)
 keys=['run_id','method','detected','false_alarm','plant_manifestation','effective_memory_corruption','first_alarm_ms','first_post_alarm_ms','latency_ms','origin_at_alarm','alarm_samples','wrong_localized_runtime_samples','alarm_UNKNOWN','localized_correct','localized_wrong','unknown_at_alarm','first_localization_ms','first_origin','propagation_plant_ms','silent_plant','integrity_observed','integrity_samples',*['alarm_'+o for o in t.old.d.r.be.ORIGINS]]
 compact=[{k:x[k] for k in keys if k in x} for rows in parts.values() for x in rows];t.dump(O/'study_record.json',dict(validation_lock=json.loads((B/'lock.json').read_text()),case_metrics=dict(encoding='zlib+base85 JSON',data=base64.b85encode(zlib.compress(json.dumps(compact,separators=(',',':')).encode())).decode()),svm_frozen_source=str(t.old.O/'study_record.json'),svm_selection=sel['svm_unchanged'],scientific_hashes={p:v for p,v in json.loads((B/'protected.json').read_text()).items() if t.Path(p).suffix in ['.c','.h','.py','.cfg','.mk'] or p.endswith('gui_session_state.json')}))
 lines=['# Benign-alarm elimination findings','',f"Retained development refinement: {report['retained']}; selected G{sel['selected']} using NEW TRAIN/CAL only. Gates: {gates}.",'', '| Method | Fault detection | Benign | Plant detection | Precision | Median/P95 ms |','|---|---|---|---|---|---|']
 for m,x in s.items():lines.append(f"| {m} | {x['detected']}/{x['faulty_runs']} | {x['benign_false_alarms']}/{x['benign_runs']} | {x['plant_detected']}/{x['plant_manifestation_runs']} | {x['precision']} | {x['latency_median_ms']}/{x['latency_p95_ms']} |")
 lines += ['',f"Detections lost: {lost}; gained: {gained}; benign removed: {report['benign_removed']}; new benign: {report['benign_added']}; remaining: {remaining}.",'Historical55: all witnessPASS and no other-layer evidence.42 had AB_FAST,20Triplex,7overlap. Strength1 bursts lasted1–2consecutive qualified samples; DS carry-over produced4–9alarm samples.53legal_offset cases plus2authorized_update cases. Weak slew<=.100434 accompanied5; no trajectory-response or slow-redundant contribution at alarms. No correctly detected historical fault depended exclusively on PASS-only legacy evidence;52sensor fault runs had eligible recovery-tail samples.1255historical reconstructions matched original A2 detection/alarm/localization metrics exactly. These old cases did NOT select the refinement.','The gate verifies complete PASS and absence of any other evidence/current retained direct-origin provenance. IntegrityFAIL or unavailable witness bypasses; all non-sensor layers bypass. DS mass, combination, thresholds, Triplex, M2, integrity provider and causal origins are unchanged. Final confirmation is a runtime provenance rule, not an injected-label classifier. Frozen SVM41features/scaler/model and both previous thresholds are untouched.','Per-origin changes, first/runtime localization, UNKNOWN and benign origins are separate tables. This is development validation; no unseen. No claim of preserved sensitivity to unmodeled pre-protection physical faults: a genuine PASS-only sensor anomaly can incur extra confirmation delay or be missed if too brief. Current post-conversion faults with witnessFAIL are never suppressed.','Benign diversity includes legal offsets/calibrations, independent noise/quantization and thermal/load/speed changes. Groups/configurations/profiles/seeds are disjoint, but this remains shared simulator-family development evidence, not a field false-alarm guarantee.']
 (O/'findings.md').write_text('\n'.join(lines)+'\n');print('REPORT',gates,'RETAINED',report['retained'],flush=True)
if __name__=='__main__':main()
