"""Paper-candidate v5 tables and figures with explicit scope and denominators."""
import json,statistics
from collections import Counter
from pathlib import Path
from .cross_layer_analysis import write_table
from .validation_v5_metrics import rate,timing_metrics,policy_metrics,percentile


def records(path):
 import csv
 def convert(v):
  if v in ('','N/A'):return None
  try:return int(v)
  except ValueError:
   try:return float(v)
   except ValueError:return v
 with Path(path).open() as f:return [{k:convert(v) for k,v in r.items()} for r in csv.DictReader(f)]


def cross_metrics(rows,**group):
 faults=[r for r in rows if r['is_perturbed']]
 return [rate(name,[int(test(r)) for r in faults if select(r)],**group) for name,select,test in [
  ('combined_detection',lambda r:True,lambda r:r['combined_detected']==1),
  ('existing_detection',lambda r:True,lambda r:r['detected']==1),
  ('detection_given_internal',lambda r:r['internal_corruption']==1,lambda r:r['combined_detected']==1),
  ('detection_given_control',lambda r:r['control_effect']==1,lambda r:r['combined_detected']==1),
  ('detection_given_plant',lambda r:r['plant_manifestation']==1,lambda r:r['combined_detected']==1),
  ('detection_given_hazard',lambda r:r['attributable_hazard']==1,lambda r:r['combined_detected']==1),
  ('silent_plant_propagation',lambda r:r['plant_manifestation']==1,lambda r:r['combined_detected']==0),
  ('silent_hazard',lambda r:r['attributable_hazard']==1,lambda r:r['first_alarm_ms'] is None or r['first_alarm_ms']>=r['hazard_entry_ms']),
  ('plant_propagation',lambda r:True,lambda r:r['plant_manifestation']==1)]]


def table_files(out,name,rows,columns):
 write_table(out/(name+'.csv'),rows,columns)
 def value(v):return 'N/A' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v)
 lines=['| '+' | '.join(columns)+' |','| '+' | '.join('---' for _ in columns)+' |']
 lines+=['| '+' | '.join(value(r.get(k)).replace('|','/') for k in columns)+' |' for r in rows]
 (out/(name+'.md')).write_text('\n'.join(lines)+'\n')
 def esc(s):return s.replace('\\',r'\textbackslash{}').replace('_',r'\_').replace('%',r'\%').replace('&',r'\&').replace('#',r'\#')
 latex=['\\begin{tabular}{'+'l'*len(columns)+'}',' & '.join(esc(k) for k in columns)+r' \\ \hline']
 latex+=[' & '.join(esc(value(r.get(k))) for k in columns)+r' \\' for r in rows];latex+=['\\end{tabular}']
 (out/(name+'.tex')).write_text('\n'.join(latex)+'\n')


def write_package(output,rows=None,ablations=None):
 out=Path(output)
 rows=rows if rows is not None else records(out/'summaries/all_runs.csv')
 ablations=ablations if ablations is not None else records(out/'summaries/ablation_runs.csv')
 timing=[r for r in rows if r['study_kind']=='timing' and r['policy']=='observe_only']
 comm=[r for r in rows if r['study_kind']=='communication'];cross=[r for r in rows if r['study_kind']=='cross_layer'];matched=[r for r in rows if r['study_kind']=='matched']
 ts=timing_metrics(timing,group='overall');write_table(out/'timing_holdout_summary.csv',ts)
 grouped=[]
 for dim in ['fault_model','timing_severity','behavior','operating_profile','timing_magnitude','contract_violated','timing_pattern']:
  for val in sorted({str(r.get(dim)) for r in timing}):grouped+=timing_metrics([r for r in timing if str(r.get(dim))==val],dimension=dim,group=val)
 write_table(out/'summaries/timing_grouped_summary.csv',grouped)
 benign=[r for r in grouped if r['metric'] in ['timing_false_alarm_rate','specificity'] and r['denominator']]
 write_table(out/'timing_benign_summary.csv',benign)
 absum=[];abmetrics=[]
 for mode in ['deadline_only','execution_age_only','combined']:
  subset=[r for r in ablations if r['ablation']==mode];metrics=timing_metrics(subset,ablation=mode);abmetrics+=metrics
  wide={'ablation':mode,'run_count':len(subset),'contract_violations':sum(r['contract_violated'] for r in subset),
   'false_negatives':sum(r['contract_violated']==1 and r['timing_monitor_detected']==0 for r in subset),
   'false_positives':sum(r['contract_violated']==0 and r['timing_monitor_detected']==1 for r in subset),
   'complexity':'Same unchanged generic C state; unused evidence channels are disabled, no specialized smaller implementation claimed'}
  for m in metrics:
   if 'value_ms' in m:wide[m['metric']]=m['value_ms']
   else:
    for key in ['numerator','denominator','percent']:wide[m['metric']+'_'+key]=m[key]
  absum.append(wide)
 write_table(out/'timing_ablation_holdout.csv',absum);write_table(out/'summaries/ablation_metrics.csv',abmetrics)
 cps=[]
 for policy in ['observe_only','immediate','graded']:cps+=policy_metrics([r for r in comm if r['policy']==policy],study_kind='communication',policy=policy)
 write_table(out/'communication_policy_summary.csv',cps)
 crosssummary=cross_metrics(cross,dimension='overall',group='all')
 for dim in ['fault_layer','fault_model','behavior','operating_profile']:
  for val in sorted({str(r.get(dim)) for r in cross}):crosssummary+=cross_metrics([r for r in cross if str(r.get(dim))==val],dimension=dim,group=val)
 write_table(out/'cross_layer_holdout_summary.csv',crosssummary)
 triples=[]
 for match in sorted({r['match_id'] for r in matched}):
  group=[r for r in matched if r['match_id']==match];flip=next(r for r in group if r['configured_model']=='bit_flip')
  for polarity in [0,1]:
   permanent=next(r for r in group if r['polarity']==polarity and r['behavior']=='permanent_stuck_bit')
   intermittent=next(r for r in group if r['polarity']==polarity and r['behavior']=='intermittent_stuck_bit')
   result={'match_id':match,'polarity':polarity,'flip_run_id':flip['run_id'],'permanent_run_id':permanent['run_id'],'intermittent_run_id':intermittent['run_id']}
   for label,r in [('flip',flip),('permanent',permanent),('intermittent',intermittent)]:
    for key in ['detected','internal_corruption','propagation_depth','plant_manifestation','fixed_containment','attributable_hazard']:result[label+'_'+key]=r.get(key)
   triples.append(result)
 write_table(out/'stuck_dynamic_matched_comparison.csv',triples)
 matchsummary=[]
 for behavior in ['transient_bit_flip','permanent_stuck_bit','intermittent_stuck_bit']:
  subset=[r for r in matched if r['behavior']==behavior]
  for metric,key in [('internal_corruption','internal_corruption'),('detection','detected'),('plant_propagation','plant_manifestation'),('hazard','attributable_hazard'),('containment','fixed_containment')]:matchsummary.append(rate(metric,[r.get(key) for r in subset],behavior=behavior))
 write_table(out/'summaries/matched_outcome_summary.csv',matchsummary)
 timing_pairs={r['pair_id'] for r in rows if r['study_kind']=='timing' and r['policy']=='immediate'}
 policyrows=comm+[r for r in rows if r['study_kind']=='timing' and r['pair_id'] in timing_pairs]
 costs=[];tps=[]
 for kind in ['timing','communication']:
  for policy in ['observe_only','immediate','graded']:
   subset=[r for r in policyrows if r['study_kind']==kind and r['policy']==policy]
   if kind=='timing':tps+=policy_metrics(subset,study_kind=kind,policy=policy)
   item={'study_kind':kind,'policy':policy,'run_count':len(subset),'injected_or_overload_runs':sum(r['is_perturbed'] for r in subset),
    'hazards':sum(r['attributable_hazard']==1 for r in subset),'critical_exposure_ms':sum(int(r['critical_exposure_time_ms']) for r in subset),
    'interventions':sum(r['policy_intervention'] for r in subset),
    'unnecessary_interventions':sum(r['unnecessary_intervention']==1 for r in subset),'unnecessary_eligible':sum(r['unnecessary_intervention'] is not None for r in subset),
    'false_interventions':sum(r['false_intervention']==1 for r in subset),'benign_runs':sum(not r['is_perturbed'] for r in subset),
    'contained':sum(r['fixed_containment']==1 for r in subset),'containment_eligible':sum(r['fixed_containment'] is not None for r in subset)}
   for key in ['safe_state_activations','safe_state_duration_ms','limp_home_duration_ms','precautionary_cooling_duration_ms','policy_requested_duration_ms','paired_excess_safe_state_duration_ms','unnecessary_intervention_duration_ms']:
    values=[r[key] for r in subset if r.get(key) is not None];item[key+'_total']=sum(values);item[key+'_median']=statistics.median(values) if values else None
   costs.append(item)
 write_table(out/'intervention_cost_summary.csv',costs);write_table(out/'summaries/timing_policy_summary.csv',tps)
 write_table(out/'statistical_confidence_summary.csv',[r for r in ts+grouped+abmetrics+cps+tps+crosssummary+matchsummary if 'ci95_lower_percent' in r])
 tables=out/'tables';tables.mkdir(exist_ok=True)
 scope=[{'scope':'Timing','cases':714,'limitation':'156 legal workloads; deterministic profile clusters; queue/plant multirate approximation'},
  {'scope':'Communication','cases':108,'limitation':'3 paired policies; zero no-action hazards, so prevention is N/A'},
  {'scope':'Cross-layer','cases':540,'limitation':'Balanced counts do not equal physically matched severities'},
  {'scope':'Matched temporal','cases':135,'limitation':'27 flips reused across 54 polarity triples; permanent duration not matched'},
  {'scope':'Recovery','cases':11,'limitation':'Selected v4 development cases, not independent holdout'},
  {'scope':'Overhead','cases':31,'limitation':'Host process/I/O timings; no embedded WCET'},
  {'scope':'Legacy observability boundary','cases':None,'limitation':'Existing residuals use true plant state; diagnostics/bookkeeping retain scenario information. New timing monitor and graded policy receive runtime telemetry only; the whole platform is not production-signal isolated.'}]
 observables=[{'layer':layer,'models':models,'runtime_observables':obs} for layer,models,obs in [
  ('memory','bit_flip, stuck_bit','control target register, command/physical residuals'),('timing','deadline_miss, task_delay','trusted releases, cancellation, deadline and age'),('workload timing','legal jitter, explicit CPU backlog','availability/start/completion, queued deadlines'),('communication','delayed_update, dropped_update, replayed_sample','existing timestamp/freshness and detector alarm'),('sensing/control','sensor_bias','existing residual/observer evidence'),('actuator','pump_degraded, fan_stuck_off','tracking error and thermal consequence')]]
 table_files(tables,'table_A_models_observables',observables,['layer','models','runtime_observables'])
 table_files(tables,'table_B_timing_holdout',ts,['metric','numerator','denominator','percent','ci95_lower_percent','ci95_upper_percent','value_ms'])
 table_files(tables,'table_C_conditional_detection',[r for r in crosssummary if r['dimension']=='overall'],['metric','numerator','denominator','percent','ci95_lower_percent','ci95_upper_percent'])
 table_files(tables,'table_D_communication_tradeoff',[r for r in costs if r['study_kind']=='communication'],['policy','run_count','hazards','critical_exposure_ms','contained','containment_eligible','unnecessary_interventions','unnecessary_eligible','limp_home_duration_ms_total'])
 table_files(tables,'table_E_matched_temporal',matchsummary,['behavior','metric','numerator','denominator','percent'])
 table_files(tables,'table_F_scope',scope,['scope','cases','limitation'])
 figures(out,timing,absum,crosssummary,costs,matchsummary,rows)
 findings(out,ts,absum,costs,crosssummary,matchsummary,rows)
 return {'timing':ts,'ablation':absum,'costs':costs,'cross_layer':crosssummary}


def figures(out,timing,ablation,cross,costs,matched,rows):
 import os
 os.environ.setdefault('MPLCONFIGDIR','/tmp/virtual_ecu_mpl')
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 directory=out/'figures';captions=[]
 def save(fig,name,caption):
  fig.tight_layout();fig.savefig(directory/name,dpi=220);plt.close(fig);captions.append({'figure':name,'caption':caption})
 def bars(name,labels,stats,ylabel,caption):
  fig,ax=plt.subplots(figsize=(max(7,len(labels)*1.3),4.8))
  vals=[r['percent'] if r['percent'] is not None else 0 for r in stats]
  ax.bar(range(len(labels)),vals,color='#287b9c')
  for i,r in enumerate(stats):
   if r.get('ci95_lower_percent') is not None:ax.errorbar(i,r['percent'],yerr=[[max(0,r['percent']-r['ci95_lower_percent'])],[max(0,r['ci95_upper_percent']-r['percent'])]],color='black',capsize=4)
  ax.set_xticks(range(len(labels)),[label+'\n'+(f"{r['numerator']}/{r['denominator']}" if r['denominator'] else 'N/A') for label,r in zip(labels,stats)],rotation=15 if len(labels)>4 else 0)
  ax.set_ylim(0,110);ax.set_ylabel(ylabel);save(fig,name,caption)
 violated=[r for r in timing if r['contract_violated']]
 bars('timing_holdout_detection.png',['Existing detector','Frozen timing monitor','Observed union'],[rate(k,[r[k] for r in violated]) for k in ['detected','timing_monitor_detected','combined_detected']], 'Contract-violating run coverage (%)','Same primary no-action cases; descriptive Wilson 95% bounds; union is not a separate mechanism.')
 legal=[r for r in timing if not r['contract_violated']]
 patterns=sorted({r['timing_pattern'] for r in legal})
 bars('timing_false_positive_validation.png',[p.replace('_',' ') for p in patterns],[rate('false alarm',[r['timing_monitor_detected'] for r in legal if r['timing_pattern']==p]) for p in patterns],'Legal-run false alarms (%)','Zero observed alarms still have nonzero Wilson upper bounds. Seeded jitter cases share profiles and are not IID vehicle samples.')
 bars('timing_ablation_holdout.png',[a['ablation'].replace('_',' ') for a in ablation],[rate('coverage',[r['timing_monitor_detected'] for r in records(out/'summaries/ablation_runs.csv') if r['ablation']==a['ablation'] and r['contract_violated']]) for a in ablation],'Violation coverage (%)','Native C replay on identical holdout trajectories. Misses are retained; all implementations share the generic frozen state struct.')
 stats=[r for r in cross if r['dimension']=='fault_layer' and r['metric']=='combined_detection' and r['denominator']]
 bars('detection_by_fault_layer_holdout.png',[r['group'].replace('_',' ') for r in stats],stats,'Observed union coverage (%)','Balanced model counts; cross-layer severities are not causally matched.')
 comm=[r for r in costs if r['study_kind']=='communication']
 fig,axes=plt.subplots(1,3,figsize=(12,4.7))
 for ax,key,label in zip(axes,['hazards','critical_exposure_ms','unnecessary_interventions'],['Hazard runs','Critical exposure (ms)','Unnecessary interventions']):
  values=[r[key] for r in comm];ax.bar(range(3),values,color=['#7c8996','#287b9c','#d2a25c']);ax.set_xticks(range(3),[r['policy'] for r in comm],rotation=20);ax.set_ylabel(label);ax.margins(y=.25)
  if not any(values):ax.set_ylim(0,1);ax.set_yticks([0,1])
  for i,r in enumerate(comm):ax.annotate(str(r[key])+(f"/{r['unnecessary_eligible']}" if key=='unnecessary_interventions' else f"/{r['injected_or_overload_runs']}" if key=='hazards' else ''),(i,r[key]),xytext=(0,4),textcoords='offset points',ha='center')
 save(fig,'communication_policy_tradeoff.png','Three paired policies, fixed detector thresholds; no-action eligibility defines unnecessary interventions.')
 fig,ax=plt.subplots(figsize=(9,5));coincident={}
 for kind in ['timing','communication']:
  group=[r for r in costs if r['study_kind']==kind];base=next(r for r in group if r['policy']=='observe_only')
  for r in group:
   x=r['policy_requested_duration_ms_total']/1000/r['run_count'];y=base['hazards']-r['hazards'];coincident.setdefault((x,y),[]).append(f"{kind}: {r['policy']} (n={r['run_count']})")
 for (x,y),labels in coincident.items():
  ax.scatter(x,y,s=70);ax.annotate('\n'.join(labels),(x,y),xytext=(0,15),textcoords='offset points',ha='left' if x==0 else 'center',fontsize=8)
 ax.set_xlabel('Mean policy-request duration per run (s)');ax.set_ylabel('Net fewer hazard runs than paired observation')
 if all(y==0 for x,y in coincident):ax.set_ylim(-.05,1);ax.set_yticks([0,1])
 save(fig,'intervention_burden_vs_hazard_prevention.png','Operational time burden, not money/energy. Zero hazards provides no demonstrated prevention benefit.')
 recovery=records(out/'recovery_horizon_analysis.csv') if (out/'recovery_horizon_analysis.csv').exists() else []
 fig,ax=plt.subplots(figsize=(8,5));curves={};annotations=set()
 for policy in ['observe_only','immediate','graded']:
  group=[r for r in recovery if r['policy']==policy and r['anchor_kind']=='fault_recovery'];points=[]
  for h in [5000,15000,30000,60000]:
   r=rate('containment',[x['containment_success'] for x in group if x['horizon_ms']==h]);points.append(r['percent'])
   key=(h,r['percent'])
   if r['percent'] is not None and key not in annotations:
    ax.annotate(f"{r['numerator']}/{r['denominator']}",(h/1000,r['percent']),xytext=(0,5),textcoords='offset points',ha='center',fontsize=8);annotations.add(key)
  curves.setdefault(tuple(points),[]).append(policy)
 for points,policies in curves.items():ax.plot([5,15,30,60],points,marker='o',label=' + '.join(policies))
 ax.set_xlabel('Observation after actual fault recovery (s)');ax.set_ylabel('Containment at horizon (%)');ax.set_ylim(-5,110);ax.legend()
 save(fig,'recovery_horizon_containment.png','Development-case follow-up. Permanent cases lack recovery anchors; denominator excludes unavailable horizons. Prior hazard still fails containment.')
 fig,ax=plt.subplots(figsize=(9,5))
 for i,behavior in enumerate(['transient_bit_flip','permanent_stuck_bit','intermittent_stuck_bit']):
  subset=[next(r for r in matched if r['behavior']==behavior and r['metric']==m) for m in ['internal_corruption','detection','plant_propagation','hazard']]
  positions=[j+(i-1)*.25 for j in range(4)];ax.bar(positions,[r['percent'] or 0 for r in subset],width=.24,label=behavior.replace('_',' '))
  for x,r in zip(positions,subset):ax.text(x,(r['percent'] or 0)+2,f"{r['numerator']}/{r['denominator']}",ha='center',fontsize=7)
 ax.set_xticks(range(4),['Internal effect','Detection','Plant propagation','Hazard']);ax.set_ylim(0,115);ax.set_ylabel('Runs (%)');ax.legend(loc='upper center',bbox_to_anchor=(.5,1.18),ncol=3,fontsize=8)
 save(fig,'stuck_vs_dynamic_outcomes.png','135 unique simulations. Same bit/time/profile; flips reused across both polarity comparisons. Duration/energy equivalence is not claimed.')
 fig,ax=plt.subplots(figsize=(8,5))
 for layer in sorted({r['fault_layer'] for r in rows if r['study_kind']=='cross_layer' and r['is_perturbed']}):
  group=[r for r in rows if r['study_kind']=='cross_layer' and r['fault_layer']==layer and r['is_perturbed']]
  x=100*sum(r['plant_manifestation']==1 for r in group)/len(group);y=100*sum(r['combined_detected']==1 for r in group)/len(group)
  ax.scatter(x,y,s=80);ax.annotate(f'{layer} (n={len(group)})',(x,y),xytext=(5,5),textcoords='offset points',fontsize=9)
 ax.set_xlim(-5,110);ax.set_ylim(-5,110);ax.set_xlabel('Plant propagation (%)');ax.set_ylabel('Observed union detection (%)')
 save(fig,'observability_vs_plant_propagation.png','Separate axes distinguish observability from physical consequence. Group means do not establish a causal origin effect.')
 write_table(directory/'figure_caption_data.csv',captions)


def findings(out,ts,ablation,costs,cross,matched,rows):
 def metric(name):return next(r for r in ts if r['metric']==name)
 def show(r):return 'N/A' if not r['denominator'] else f"{r['numerator']}/{r['denominator']} = {r['percent']:.2f}% (Wilson 95% {r['ci95_lower_percent']:.2f}–{r['ci95_upper_percent']:.2f}%)"
 def crossmetric(name):return next(r for r in cross if r['dimension']=='overall' and r['metric']==name)
 communication=[r for r in costs if r['study_kind']=='communication']
 recovery=records(out/'summaries/recovery_final_outcomes.csv') if (out/'summaries/recovery_final_outcomes.csv').exists() else []
 oldfail=[r for r in recovery if r['policy']=='immediate' and r['original_containment']==0]
 delayed=sum(r['extended_containment']==1 for r in oldfail);persistent=sum(r['extended_containment']==0 for r in oldfail)
 lines=['# V5 scientific findings','',
  'Baseline da126cb; v4 development data and all existing detector/plant/RTL code are frozen. Primary combined monitor and three policies were specified before holdout evaluation. Parser-domain design corrections are recorded in contracts/design_correction.md; no monitor or policy rule was changed in response to outcomes.',
  '',f"Final main matrix: {len(rows)} simulations: 822 timing (714 primary observation cases plus 108 action comparisons), 333 communication, 543 cross-layer and 135 unique matched temporal runs. Three additional fault-free reference simulations support analysis; 33 recovery simulations revisit 11 selected development configurations. Native ablation replay is not an additional physical simulation.",
  '', '## 1–3. Generalization, coverage and benign behavior', '',
  'Primary timing violation coverage: '+show(metric('timing_detection_coverage'))+'.',
  'Legal timing false-alarm rate: '+show(metric('timing_false_alarm_rate'))+'.',
  'Specificity: '+show(metric('specificity'))+'. Precision: '+show(metric('precision'))+'.',
  'The 156 legal workloads exercise new profiles and real seeded release/start variation, near-deadline completion and exact deadline completion. Observed violations include direct injection and workload-induced backlog; the latter is not mislabeled as fault injection. All complete profile/parameter combinations differ from v4.',
  'These are designed deterministic scenarios, not IID draws from a fleet. Wilson bounds are descriptive binomial reference intervals under an independence assumption. Shared profiles, deterministic seeds and correlated conditions limit population inference. Paired policies/ablations are never pooled to inflate the primary sample size.',
  '', '## 4. Plant-propagating timing violations and useful warning', '',
  'Plant-propagating timing detection: '+show(metric('plant_propagating_timing_detection'))+'.',
  'Strictly pre-plant detection: '+show(metric('pre_plant_timing_detection'))+'. Same tick: '+show(metric('same_tick_plant_timing_detection'))+'.',
  f"Median latency {metric('median_detection_latency_ms')['value_ms']} ms; 95th percentile {metric('p95_detection_latency_ms')['value_ms']} ms, among {metric('median_detection_latency_ms')['denominator']} detected violations with both endpoints. Same tick is not counted as advance warning. Alarm/plant sampling is 100 ms, despite 1 ms workload events.",
  '', '## 5–6. Redundancy and justified monitor architecture', '']
 for a in ablation:lines.append(f"- {a['ablation']}: {a['timing_detection_coverage_numerator']}/{a['timing_detection_coverage_denominator']} violations, {a['false_positives']} false positives, {a['false_negatives']} misses; median/p95 latency {a['median_detection_latency_ms']}/{a['p95_detection_latency_ms']} ms.")
 lines+=['','Backlog decouples an overdue job from discarded releases. A short queued overrun can violate a deadline while successful-execution age remains legal. Combined evidence retains deadline-only coverage (558/558 versus age/missed-only 522/558) and lowers the 95th-percentile latency from 100 ms to 0 ms. It adds no coverage over deadline-only and no pre-plant coverage over either ablation: all three detect all 33 plant-propagating violations before manifestation. This supports retaining the frozen combined monitor for its specific coverage/latency trade-off. All ablations use the same generic C state allocation, so a smaller specialized implementation is not claimed. No post-holdout threshold selection is performed.',
  '', '## 7–9. Communication response and intervention cost','']
 for r in communication:lines.append(f"- {r['policy']}: hazards {r['hazards']}/{r['injected_or_overload_runs']}; critical exposure {r['critical_exposure_ms']} ms; fixed-cohort containment {r['contained']}/{r['containment_eligible']}; unnecessary actions {r['unnecessary_interventions']}/{r['unnecessary_eligible']}; false actions {r['false_interventions']}/{r['benign_runs']}; total limp-home {r['limp_home_duration_ms_total']} ms and requested protection {r['policy_requested_duration_ms_total']} ms.")
 lines+=['','Protection is evaluated on matched no-action cohorts. Cooling/limp-home duration is an operational burden, not energy, monetary loss or proven vehicle benefit. Graded action reduces communication limp-home duration by 615,000 ms (18.26%), replacing it with precautionary cooling. Total safe-state duration remains 3,368,700 ms and unnecessary actions remain 11/15 under both action policies. It therefore reduces action severity, not the unnecessary-action count or total safe-state burden. All three communication arms have zero hazards and zero critical exposure. Hazard prevention and its interval are N/A because the no-action hazard denominator is empty; this holdout cannot establish that v4 hazard-prevention findings generalize. No new main holdout cohort has a hazard, so timing-hazard prevention is also unproven.',
  '', '## 10. Recovery horizon and v4 containment failures','',f"Among {len(oldfail)} selected immediate-policy failures at the original horizon, {delayed} satisfy the unchanged containment contract by 360 s; {persistent} still fail at the extended end. The five communication failures are exhaustively included. Remaining failure at a finite end is not proof of permanent failure. Recovery/alarm/action-anchored 5/15/30/60 s outcomes are in recovery_horizon_analysis.csv; missing anchors/horizons are N/A. Thermal recovery and containment remain separate, especially if a hazard occurred earlier.",
  '', '## 11. Matched stuck-at versus dynamic behavior','']
 for r in matched:
  if r['metric'] in ['detection','plant_propagation','hazard']:lines.append(f"- {r['behavior']} {r['metric']}: {show(r)}.")
 triples=records(out/'stuck_dynamic_matched_comparison.csv')
 for metric_name in ['detected','plant_manifestation','attributable_hazard']:
  diff=sum(r['flip_'+metric_name]!=r['permanent_'+metric_name] for r in triples)
  diffinter=sum(r['intermittent_'+metric_name]!=r['permanent_'+metric_name] for r in triples)
  lines.append(f"Matched polarity triples with different {metric_name}: flip versus permanent {diff}/{len(triples)}; intermittent versus permanent {diffinter}/{len(triples)}.")
 lines+=['','Matching holds bit, target, profile and occurrence time fixed. A one-time flip and a permanently imposed value cannot have equal exposure duration/energy. Polarity changes the corruption opportunity; some imposed values already match the register. Detection conditional on actual internal corruption is distinct from imposed-fault count. The 27 flip traces are reused across both polarities and are counted once in unique-run summaries. No superiority claim follows from the pooled percentages.',
  '', '## 12–13. Primary paper direction and strongest supported claim','',
  'Cross-layer observed-union detection: '+show(crossmetric('combined_detection'))+'.',
  'Detection given plant propagation: '+show(crossmetric('detection_given_plant'))+'.',
  'Detection given hazard: '+show(crossmetric('detection_given_hazard'))+'.',
  'Silent plant propagation: '+show(crossmetric('silent_plant_propagation'))+'. Silent hazard: '+show(crossmetric('silent_hazard'))+'.',
  'Strongest bounded quantitative claim: the frozen originating-layer timing monitor achieves '+show(metric('timing_detection_coverage'))+' on unseen configured timing violations, with legal false alarms '+show(metric('timing_false_alarm_rate'))+'. This supports Cross-Layer Fault Observability as the primary direction. It does not establish equal physical severity across origins or universal detection of automotive faults.',
  '', '## 14. Claims that must not appear','',
  '- ISO 26262 compliance, a certified digital twin, embedded WCET, fleet reliability or hardware security isolation.',
  '- Zero population false-alarm probability from zero observed false alarms.',
  '- Universal hazard prevention, or timing-hazard prevention without observed timing hazards.',
  '- Detector retuning as the source of improved timing coverage; existing detectors were unchanged.',
  '- Detection equals containment, safety action equals detection, or a response to plant propagation automatically proves benefit.',
  '- Combined evidence superiority unless the paired ablation supports the particular metric.',
  '- Causal fault-origin rankings or stuck-at/dynamic superiority from unmatched physical severity/exposure.',
  '- Independent confirmation from repeating deterministic trajectories or pooling ablation/policy replicas.',
  '', '## Overhead and model limits','',
  'monitor_overhead_summary.csv reports host ABI state sizes, source/object sizes and repeated interleaved host simulation timings. The binary delta for the entire v5 extension includes the workload scheduler, graded policy and logging; it is not the isolated monitor footprint. Process launch and CSV I/O can dominate tiny monitor costs. No embedded WCET claim is made.',
  'Thermal physics remain the accepted 100 ms macrostep equations. The workload scheduler applies between-boundary task completions at the next macrostep; it does not simulate within-step thermal feedback. Direct faults retain the original dispatcher. Legacy fault containment/FTTI is N/A for non-injection overload workloads; their trusted timing and full-precision plant consequences are evaluated separately.',
  'The legacy observability boundary is preserved: existing detector residuals use true plant state, diagnostic classification and bookkeeping retain scenario information, and the old shutdown path uses true coolant temperature. The new timing monitor and graded policy do not directly consume fault identity, reference trajectories or future hazards; the graded communication arm still depends on legacy alarm evidence. This is not production-signal isolation of the entire platform. See docs/detector_observability_boundary.md in the repository.',
  '', '## Reproduction and statistics reference','',
  'Run `python3 scripts/run_cross_layer_v5_validation.py`. Frozen source/config/profile hashes, exact commands, per-run hashes, native-C ablation bridge, all raw trajectories and per-job workload events are preserved. Candidate tables A–F are CSV/Markdown/LaTeX; this is an evidence package, not a drafted paper.',
  'Wilson construction follows the [NIST confidence-interval reference](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm). The independence caveat is a limitation of this designed campaign, not a guarantee supplied by the interval formula.']
 (out/'v5_scientific_findings.md').write_text('\n'.join(lines)+'\n')
 immediate=next(r for r in communication if r['policy']=='immediate');graded=next(r for r in communication if r['policy']=='graded')
 recommendation=f'''# Final configuration recommendation

Retain the source-frozen **combined timing monitor, observe-only by default**.
It represents the complete trusted contract without merging scheduling into Hybrid.
Use the same 100 ms period/deadline and frozen persistence/age rules. Ablation
results are metric-specific; no post-holdout retuning is performed.

Timing action: retain **observe-only as the default**. Immediate and graded actions
remain separately selectable experimental policies. Coverage and small plant
deviations alone do not demonstrate enough safety benefit to justify broad action.
No timing-hazard prevention claim follows without a no-action timing hazard.

Communication action: **observe-only remains the baseline/default**. For a clearly
labeled protective experimental arm, retain the frozen graded policy as a candidate
for further independent action-cost validation, alongside the accepted immediate
comparator. Holdout hazard counts are immediate {immediate['hazards']} and graded
{graded['hazards']}; unnecessary counts {immediate['unnecessary_interventions']} and
{graded['unnecessary_interventions']}. A candidate preference is not a deployment
recommendation or proof of hazard protection where the no-action hazard denominator
is empty. Do not discard either arm to improve reported results.

Experimental FTTI: preserve the 5,000 ms injection-based budget including the
1,000 ms hold; also retain manifestation-origin timing where available. Neither
is an OEM-derived certified FTTI. Unavailable non-injection containment clocks stay N/A.

Containment: keep the accepted stable final-tail predicate: below 108 C for 1,000 ms,
with protection or resolved effects, and no prior hazard. Use fixed no-action
actuator/plant eligibility for policy comparisons. Extend horizons explicitly;
do not weaken the rule retrospectively. Thermal recovery is a separate endpoint.

Hazard: preserve coolant >=115 C continuously for 1,000 ms. Preexisting hazards
are excluded from attributable outcomes. Report total critical exposure separately.

The paper candidate is the entire frozen dataset, including misses, N/A cohorts,
policy costs, descriptive confidence bounds and all failed/slow recoveries. The
recommended next Prompt 6 is to audit traceability and draft a bounded paper outline
and claim-to-table map, then obtain an independent scheduler/hardware validation
plan. Do not add new detector tuning or write unsupported automotive-safety claims.
'''
 (out/'final_configuration_recommendation.md').write_text(recommendation)
