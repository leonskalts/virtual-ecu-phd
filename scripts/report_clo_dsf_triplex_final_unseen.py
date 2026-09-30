#!/usr/bin/env python3
"""Post-completion report for the frozen primary and expanded cohorts."""
import json,math
from pathlib import Path
import run_clo_dsf_triplex_final_unseen as u
import report_clo_dsf_triplex as q
h=q.h;O=u.OUT;B=u.B

def main():
 lock=u.verify();assert all((B/(p+'_complete')).exists() for p in ['PRIMARY','SECONDARY'])
 primary=h.records(B/'PRIMARY_rows.csv');secondary=h.records(B/'SECONDARY_rows.csv');assert len(primary)==3000 and len(secondary)==600
 summary=[];subgroups=[];localization=[];expanded=[]
 for part,rows in [('PRIMARY',primary),('SECONDARY',secondary)]:
  for method in ['A0','A1']:
   rr=[r for r in rows if r['method']==method];name={'A0':'CURRENT','A1':'TRIPLEX'}[method]
   for origin in ['ALL',*h.prior.ORIGINS]:summary.append(dict(cohort=part,method=name,origin=origin,**q.stats([r for r in rr if origin=='ALL' or r['origin']==origin])))
   for group,fn in q.FILTERS.items():subgroups.append(dict(cohort=part,method=name,group=group,**q.stats([r for r in rr if fn(r)])))
   for origin in ['ALL',*h.prior.ORIGINS]:
    ss=[r for r in rr if origin=='ALL' or r['origin']==origin];localization.append(dict(cohort=part,method=name,origin=origin,**h.runtime_stats(ss),**{o:sum(r['alarm_'+o] for r in ss) for o in [*h.prior.ORIGINS,'UNKNOWN']}))
   if part=='SECONDARY':
    for group in ['ALL','C','C_bias','C_ramp','C_step','C_pulse','C_freeze','ABC','AC','BC']:
     ss=[r for r in rr if group=='ALL' or (r['domain']=='C' if group=='C' else r['subgroup']==group)];expanded.append(dict(method=name,group=group,**q.stats(ss)))
 a={r['run_id']:r for r in primary if r['method']=='A0'};p=dict(both=0,current_only=0,triplex_only=0,neither=0,common_mode_gain=0,plant_gain=0,plant_loss=0)
 for r in primary:
  if r['method']!='A1' or not r['injected']:continue
  x=a[r['run_id']];key='both' if x['detected'] and r['detected'] else 'current_only' if x['detected'] else 'triplex_only' if r['detected'] else 'neither';p[key]+=1
  if key=='triplex_only':p['common_mode_gain']+=r['domain']=='AB';p['plant_gain']+=r['plant_manifestation']==1
  if key=='current_only':p['plant_loss']+=r['plant_manifestation']==1
 n=p['current_only']+p['triplex_only'];p['mcnemar_exact_p']=min(1,2*sum(math.comb(n,j) for j in range(min(p['current_only'],p['triplex_only'])+1))/2**n) if n else 1
 def overall(part,method):return next(s for s in summary if s['cohort']==part and s['method']==method and s['origin']=='ALL')
 current=overall('PRIMARY','CURRENT');triplex=overall('PRIMARY','TRIPLEX');sec=overall('SECONDARY','TRIPLEX')
 p['benign_alarm_difference']=triplex['benign_false_alarms']-current['benign_false_alarms']
 for filename,rows in [('final_summary.csv',summary),('subgroup_summary.csv',subgroups),('paired_comparison.csv',[p]),('expanded_architecture_summary.csv',expanded),('localization_summary.csv',localization)]:h.write(O/filename,rows)
 h.write(O/'case_summary.csv',[{k:r[k] for k in ['run_id','partition','method','origin','domain','kind','subgroup','detected','false_alarm','effective_memory_corruption','plant_manifestation','silent_plant','latency_ms','origin_at_alarm','wrong_localized_runtime_samples','initially_excited','actuator_excited']} for r in primary+secondary])
 (O/'actuator_observability_limitation.md').write_text('Idle pump-performance degradation is unobservable in the modeled architecture until actuator excitation occurs.\n\nThe existing model is pump_actual=command*scale. No electrical failure, health bit or active excitation was added. See results/clo_dsf_current/actuator_health_feasibility.md and its33-case audit.\n')
 def fraction(s):return f"{s['detected']}/{s['faulty_runs']} = {100*s['coverage']:.4f}%"
 (O/'findings.md').write_text(f'''# Final frozen Triplex unseen results

Frozen commit {lock['commit']}. Primary and secondary completed once, no source/threshold/model changes after lock; hashes verified. No algorithm selection from results. Both CURRENT and TRIPLEX observe identical physical cases. Historical overlap0 across {lock['historical_sources']} unique recorded sources. Protocol and explicit seeds are frozen in the manifests.

Primary original space: CURRENT {fraction(current)}; TRIPLEX {fraction(triplex)}. Triplex Wilson95 {100*triplex['wilson95_low']:.4f}–{100*triplex['wilson95_high']:.4f}%. Triplex plant {triplex['plant_manifestation_runs']-triplex['silent_plant']}/{triplex['plant_manifestation_runs']}; silent {triplex['silent_plant']}; benign {triplex['benign_false_alarms']}/300; runtime wrong origins {triplex['runtime_wrong_runs']}/{triplex['runtime_wrong_samples']} runs/samples.

Paired: both{p['both']},CURRENT-only{p['current_only']},TRIPLEX-only{p['triplex_only']},neither{p['neither']}; exact two-sided McNemar p={p['mcnemar_exact_p']}. Common-mode additional{p['common_mode_gain']}; plant additional{p['plant_gain']},lost{p['plant_loss']}; benign difference{p['benign_alarm_difference']}. These paired counts support only claims consistent with the observed gains/losses; do not infer superiority on every subgroup or external deployment population.

Secondary architecture faults: {fraction(sec)}, plant {sec['plant_manifestation_runs']-sec['silent_plant']}/{sec['plant_manifestation_runs']}, wrong runs/samples{sec['runtime_wrong_runs']}/{sec['runtime_wrong_samples']}. This percentage is NOT included in the primary headline. C-biased-from-startup is reported separately from later steps. ABC common-mode remains a redundancy limitation wherever no independent reference disagrees.

All subgroup denominators, safety timing, precision/recall, latency and localization are in the CSVs. UNKNOWN is reported separately from errors. Latency is conditional on detection; differing detected sets prevent interpreting marginal P95 alone as paired speed superiority. Wilson/McNemar are descriptive for deterministic grouped simulation, not a population-randomized trial. Initially-unexcited faults were retained. Idle pump-performance degradation remains unobservable until excitation. Dormant-memory detection through active writes is not passive stored-value corruption.

The prior development91.04% and90.25% findings remain historical evidence; this is the final unseen result. No reruns/tuning permitted. Freeze regression passed before commit:330 tests, forced build,compile,diff,48legacy,64RTL,Triplex symmetry/C independence,Hybrid/HETIA integrity;150 seen-case cleanup equivalence runs produced identical results. No post-result detector edits.
''')
 (O/'validation_record.md').write_text(f'''# Execution record

Commit: {lock['commit']}
Locked UTC: {lock['locked_utc']}
Primary manifest SHA256: {lock['primary_manifest_sha256']}
Secondary manifest SHA256: {lock['secondary_manifest_sha256']}
Seeds: {lock['seed_formula']}
Historical overlap:0; audit CSV includes archived/Git and working-tree provenance.

PRIMARY1500 and SECONDARY300 executed once; methodsA0=CURRENT,A1=TRIPLEX. No outcomes inspected before each cohort completed. Scientific hashes,protocol,manifests and GUI verified unchanged after both. No parameters fitted. Raw per-run data deleted by collector; final temporary build directories deleted after each cohort. Compact per-case statistics retained, zero new raw traces. Historical result directories preserved. Freeze regression is recorded in results/clo_dsf_current/triplex_freeze_record.md. No post-result source modification, commit or push.
''')
 print(json.dumps(dict(primary_current=current,primary_triplex=triplex,secondary_triplex=sec,paired=p),indent=2))
if __name__=='__main__':main()
