"""Deterministic reporting from completed Candidate 2 development artifacts."""
from __future__ import annotations
import csv,gzip,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .clo_dsf_candidate2_development import OUTPUT,ROOT,ORIGINS,write_csv,write_json,mean,quantile,ratio,aggregate

def records(path):
 result=[]
 for row in csv.DictReader(Path(path).open()):
  r={}
  for k,v in row.items():
   if not v:r[k]=None;continue
   try:r[k]=float(v) if any(x in v for x in ['.','e']) else int(v)
   except ValueError:r[k]=v
  result.append(r)
 return result

def save(fig,out,name):
 fig.text(.5,-.025,'DEVELOPMENT — NOT FINAL HOLDOUT',ha='center',fontsize=10,color='#7b3344')
 fig.savefig(out/'figures'/f'{name}.png',dpi=170,bbox_inches='tight');fig.savefig(out/'figures'/f'{name}.pdf',bbox_inches='tight');plt.close(fig)
def report(out=OUTPUT):
 rows=records(out/'candidate2_dev_runs.csv');summaries=records(out/'candidate2_baseline_comparison.csv');layers=records(out/'candidate2_layer_summary.csv');selection=json.loads((out/'selection_record.json').read_text())
 # The selected readout happens to match the online search-bank readout exactly.
 # Recover its actual later-localization timestamps; other offline readouts remain unavailable.
 cfg=selection['parameters'];later_available=cfg['localization_threshold']==.55 and cfg['localization_margin_threshold']==.15
 if later_available:
  method=f"candidate_{selection['selected_candidate']}"+('_no_prop' if cfg['propagation_bonus']==0 else '')
  bank={r['run_id']:r for r in rows if r['partition']=='development-train' and r['method']==method}
  for r in rows:
   if r['partition']=='development-train' and r['method']=='Candidate 2':
    for field in ['first_localization_ms','first_origin','localization_before_plant']:r[field]=bank[r['run_id']][field]
    r['later_localization_available']=True
  write_csv(out/'candidate2_dev_runs.csv',rows)
  selected_train=[r for r in rows if r['partition']=='development-train' and r['method']=='Candidate 2']
  for s in summaries:
   if s['partition']=='development-train' and s['method']=='Candidate 2':s.update(aggregate(selected_train))
  for s in layers:
   if s['partition']=='development-train' and s['method']=='Candidate 2':s.update(aggregate([r for r in selected_train if r['origin']==s['origin']]))
  write_json(out/'reporting_adjustments.json',dict(runtime_or_selection_changed=False,validation_reexecuted=False,adjustment='Selected TRAIN readout .55/.15 equals the actual online search-bank readout. Recover later-localization times from that bank instead of discarding them as unavailable. Search-table historical later-localization zeros were not selection inputs and remain archived.'))
 # Derived reporting only: explicit denominators/rates and availability.

 for s in summaries+layers:
  s['silent_plant_rate']=ratio(s['silent_plant'],s['plant_manifestation_runs']);s['later_localization_available']=not(s['method']=='Candidate 2' and s['partition']=='development-train' and not later_available)
  if not s['later_localization_available']:s['localized_before_plant']=None
 write_csv(out/'candidate2_baseline_comparison.csv',summaries);write_csv(out/'candidate2_layer_summary.csv',layers)
 for part,name in [('development-train','train'),('development-validation','validation')]:write_csv(out/f'candidate2_{name}_summary.csv',[s for s in summaries if s['partition']==part])
 write_csv(out/'candidate2_localization_summary.csv',[s for s in summaries if s['accuracy_when_localized'] is not None])
 write_csv(out/'candidate2_selective_localization_validation_fixed.csv',[s for s in summaries if s['method']=='Candidate 2' and s['partition']=='development-validation'])
 val=[s for s in summaries if s['partition']=='development-validation'];by={s['method']:s for s in val};c2=by['Candidate 2'];train=next(s for s in summaries if s['method']=='Candidate 2' and s['partition']=='development-train')
 uncertainty=[]
 for part in ['development-train','development-validation']:
  base=[r for r in rows if r['method']=='Candidate 2' and r['partition']==part]
  cohorts={'benign':[r for r in base if not r['injected']],'faulty':[r for r in base if r['injected']],'localized':[r for r in base if r['detected'] and not r['unknown_at_alarm']],'unknown':[r for r in base if r['unknown_at_alarm']],'correct':[r for r in base if r['localized_correct']],'incorrect':[r for r in base if r['localized_wrong']]}
  for cohort,subset in cohorts.items():
   for field in ['mean_anomaly_ignorance','mean_origin_ignorance','mean_detection_conflict','mean_localization_conflict','origin_score_at_alarm','origin_margin_at_alarm','origin_ignorance_at_alarm']:
    values=[r[field] for r in subset if not field.endswith('_at_alarm') or r['detected']]
    uncertainty.append(dict(partition=part,cohort=cohort,quantity=field,n=len(values),mean=mean(values),p05=quantile(values,.05),median=quantile(values,.5),p95=quantile(values,.95)))
 write_csv(out/'candidate2_uncertainty_cohorts.csv',uncertainty)
 methods=['Candidate 1','Plain DS','Simple OR','Weighted Sum','Candidate 2','Hybrid']
 fig,ax=plt.subplots(figsize=(9,4));ax.bar(methods,[100*by[m]['coverage'] for m in methods],color=['#8493a5']*4+['#176b87','#8493a5']);ax.set(ylabel='Fault detection (%)',ylim=(0,105),title='New development-validation: 300 faults, 96 benign runs');ax.tick_params(axis='x',rotation=15);save(fig,out,'detection_comparison')
 fig,ax=plt.subplots(figsize=(8,4));values=[next(s['coverage'] for s in layers if s['partition']=='development-validation' and s['method']=='Candidate 2' and s['origin']==o) for o in ORIGINS];ax.bar([o.replace('_','/') for o in ORIGINS],[100*v for v in values],color='#176b87');ax.set(ylabel='Detection (%)',ylim=(0,105),title='Candidate 2 detection by origin (60 faults each)');ax.tick_params(axis='x',rotation=15);save(fig,out,'detection_by_origin')
 curve=records(out/'candidate2_selective_localization_train.csv');curve=[s for s in curve if s['candidate']==selection['selected_candidate'] and s['propagation_bonus']==selection['parameters']['propagation_bonus']]
 fig,axes=plt.subplots(1,2,figsize=(10,4));axes[0].scatter([100*s['localization_coverage'] for s in curve],[100*s['accuracy_when_localized'] for s in curve],label='TRAIN threshold/margin sweep');axes[0].scatter([100*c2['localization_coverage']],[100*c2['accuracy_when_localized']],marker='*',s=120,label='VALIDATION fixed point');axes[0].set(xlabel='Fraction of alarms localized (%)',ylabel='Accuracy when localized (%)',ylim=(95,101),title='Selective localization');axes[0].legend(fontsize=8)
 for s in curve:axes[1].scatter(100*s['localization_coverage'],s['wrong_localizations']);axes[1].annotate(f"{s['localization_threshold']}/{s['localization_margin_threshold']}",(100*s['localization_coverage'],s['wrong_localizations']),fontsize=7)
 axes[1].set(xlabel='TRAIN localization coverage (%)',ylabel='Wrong origins',title='Threshold / margin operating points');fig.tight_layout();save(fig,out,'selective_localization')
 confusion=records(out/'candidate2_origin_confusion.csv');matrix=[[r[o] for o in ORIGINS+['UNKNOWN','misses']] for r in confusion if r['method']=='Candidate 2'];fig,ax=plt.subplots(figsize=(9,4));ax.imshow(matrix,cmap='Blues');ax.set_xticks(range(7),[o.replace('_','/') for o in ORIGINS+['UNKNOWN','misses']],rotation=25,ha='right');ax.set_yticks(range(5),ORIGINS)
 for i,row in enumerate(matrix):
  for j,value in enumerate(row):ax.text(j,i,str(value),ha='center',va='center',color='white' if value>=40 else 'black')
 ax.set(title='Candidate 2: first-alarm origin (misses kept separate)',ylabel='Evaluation-only true origin');save(fig,out,'origin_confusion')
 vr=[r for r in rows if r['partition']=='development-validation' and r['method']=='Candidate 2'];fig,axes=plt.subplots(1,2,figsize=(10,4))
 for ax,field,title in zip(axes,['mean_anomaly_ignorance','mean_origin_ignorance'],['Anomaly ignorance','Origin ignorance']):
  ax.boxplot([[r[field] for r in vr if not r['injected']],[r[field] for r in vr if r['injected']]],labels=['Benign','Faulty']);ax.set(title=title,ylabel='Per-run mean mass on whole frame',ylim=(-.02,1.02))
 fig.tight_layout();save(fig,out,'ignorance_distributions')
 selected=[]
 predicates=[('timing',lambda r:r['origin']=='TIMING' and r['detected']),('sensor_unknown',lambda r:r['origin']=='SENSOR_CONTROL' and r['unknown_at_alarm']),('weak_memory',lambda r:r['origin']=='MEMORY' and r['unknown_at_alarm']),('communication',lambda r:r['origin']=='COMMUNICATION' and r['detected']),('actuator',lambda r:r['origin']=='ACTUATOR' and r['detected']),('silent_plant',lambda r:r['silent_plant']),('benign',lambda r:not r['injected'])]
 for name,predicate in predicates:
  r=next(x for x in vr if predicate(x));path=out/'traces'/f"{r['run_id']}.candidate2.csv.gz"
  with gzip.open(path,'rt') as f:trace=list(csv.DictReader(f))
  x=[int(t['time_ms'])/1000 for t in trace];fig,axes=plt.subplots(7,1,figsize=(11,13),sharex=True)
  for field in ['timing_evidence','communication_evidence','memory_control_evidence','sensor_control_evidence','actuator_evidence','plant_evidence']:axes[0].plot(x,[float(t[field]) for t in trace],label=field.replace('_evidence',''))
  for field in ['anomaly_belief','anomaly_ignorance']:axes[1].plot(x,[float(t[field]) for t in trace],label=field)
  axes[2].step(x,[{'NORMAL':0,'SUSPECT':1,'CONFIRMED':2}[t['detector_state']] for t in trace],where='post');axes[2].set_yticks([0,1,2],['NORMAL','SUSPECT','CONFIRMED']);axes[2].set_ylabel('Anomaly state')
  for subset,label in [(1,'MEMORY'),(2,'TIMING'),(4,'COMMUNICATION'),(8,'SENSOR_CONTROL'),(16,'ACTUATOR'),(12,'COMM/SENSOR'),(31,'Origin ignorance')]:axes[3].plot(x,[float(t[f'origin_mass_{subset}']) for t in trace],label=label)
  for field in ['origin_score','origin_margin','origin_ignorance']:axes[4].plot(x,[float(t[field]) for t in trace],label=field)
  origin_ids={name:i for i,name in enumerate(['UNKNOWN',*ORIGINS])};axes[5].step(x,[origin_ids[t['estimated_origin']] for t in trace],where='post');axes[5].set_yticks(range(6),['UNKNOWN','MEM','TIM','COMM','SENSOR','ACT']);axes[5].set_ylabel('Estimated origin')
  axes[6].step(x,[int(t['propagation_support']) for t in trace],where='post',label='Runtime propagation support (selected bonus = 0)')
  for i,ax in enumerate(axes):
   if r['injected']:ax.axvline(r['start_ms']/1000,color='black',linestyle=':',label='Injected onset (EVALUATION ONLY)' if i==0 else None)
   if r['propagation_plant_ms'] is not None:ax.axvline(r['propagation_plant_ms']/1000,color='#bd4f91',linestyle='--',label='Plant manifestation (EVALUATION ONLY)' if i==0 else None)
   if i not in [2,5]:ax.legend(fontsize=7,ncol=3);ax.set_ylim(-.05,1.05)
   ax.grid(alpha=.15)
  axes[0].set_title(f"{name}: {r['run_id']} — selected validation runtime");axes[6].set_xlabel('Simulation time (s)');fig.tight_layout();save(fig,out,'trace_'+name)
  selected.append(dict(example=name,run_id=r['run_id'],trace=str(path.relative_to(ROOT)),origin_evaluation_only=r['origin']))
 write_csv(out/'representative_traces.csv',selected)
 for field,label,name in [('coverage_given_plant_manifestation','Detection given plant manifestation (%)','plant_propagating_detection'),('silent_plant','Silent plant-propagating runs','silent_plant_propagation'),('benign_false_alarms','Benign alarm runs / 96','benign_false_alarms')]:
  fig,ax=plt.subplots(figsize=(9,4));ax.bar(methods,[(100 if field.startswith('coverage') else 1)*by[m][field] for m in methods],color='#176b87');ax.set(ylabel=label,title='New development-validation comparison');ax.tick_params(axis='x',rotation=15);save(fig,out,name)
 abl=['Plain DS','Single frame positive','B1 Dual-frame','B2 Origin reliability','B3 Propagation','B4 Temporal','No origin reliability'];fig,ax=plt.subplots(figsize=(10,4));positions=list(range(len(abl)));ax.bar([i-.18 for i in positions],[by[m]['detected'] for m in abl],width=.36,label='Detected');ax.bar([i+.18 for i in positions],[by[m]['correct_localizations'] for m in abl],width=.36,label='Correct origin at first alarm');ax.set_xticks(positions,abl,rotation=20,ha='right');ax.set(ylabel='Runs',title='Candidate 2 architectural ablation');ax.legend();save(fig,out,'candidate2_ablation')

 pct=lambda value:'N/A' if value is None else f'{100*value:.2f}%'
 table='\n'.join(f"| {m} | {by[m]['detected']}/300 | {pct(by[m]['coverage_given_plant_manifestation'])} | {by[m]['silent_plant']} | {by[m]['benign_false_alarms']}/96 | {by[m]['latency_median_ms']:g}/{by[m]['latency_p95_ms']:g} | {by[m]['correct_localizations'] if by[m]['correct_localizations'] is not None else 'N/A'} | {by[m]['unknown'] if by[m]['unknown'] is not None else 'N/A'} |" for m in methods)
 ablation='\n'.join(f"| {m} | {by[m]['detected']} | {by[m]['correct_localizations']} | {by[m]['wrong_localizations']} | {by[m]['unknown']} | {by[m]['silent_plant']} |" for m in ['Plain DS','Single frame positive','B1 Dual-frame','B2 Origin reliability','B3 Propagation','B4 Temporal','Detection reliability 0.9','No origin reliability'])
 layertext='\n'.join(f"| {s['origin']} | {s['detected']}/{s['faulty_runs']} | {s['correct_localizations']} | {s['unknown']} | {s['silent_plant']} |" for s in layers if s['partition']=='development-validation' and s['method']=='Candidate 2')
 overhead=json.loads((out/'candidate2_overhead.json').read_text())
 findings=f'''# Candidate 2 development findings

DEVELOPMENT / TUNING DATA — NOT FINAL HOLDOUT. This revision is implemented and evaluated; the selected operating point is **not promoted to a frozen final-holdout candidate**. Candidate 1 remains frozen and reproducible. No validation-driven algorithm or parameter change was made.

## Main result and decision

Candidate 2 detects 262/300 injected cases (87.33%) versus frozen Candidate 1's 162/300 (54.00%) on the same NEW validation cohort. Both have 0/96 benign alarm runs. Silent plant propagation falls from 104 to 14 of 221 plant-propagating cases. Candidate 2 correctly localizes 176 alarms, abstains on 86, and gives zero wrong origins. Localization coverage is 67.18%, accuracy conditional on localization 100%, and correct origins among all alarms 67.18%. Reporting 100% accuracy without its coverage would be misleading.

Calibrated Weighted Sum matches Candidate 2's 262 detections and 14 silent plant cases at the same median/P95 latency. Candidate 2 supplies origin and uncertainty outputs that this baseline does not, but has no demonstrated binary-detection superiority. Its no-origin-discount ablation produces 202 correct origins, 60 UNKNOWN and zero wrong origins at the same detection coverage. Thus the selected discounting policy is dominated on the measured decision endpoints by a simpler ablation. This is sufficient reason **not to freeze the selected configuration for final holdout**, despite its substantial improvement over Candidate 1. Preserve this completed validation as development evidence; a simplification would require another preregistered candidate and fresh assessment, not changing this one after looking.

## Campaign and selection

Exactly 1140 unique 120-second configurations: 900 faults (180 per origin), 240 benign, five operating profiles, two base onsets, three behaviors, multiple severities/durations. Grouped split: TRAIN 744 (600 faults, 144 benign), VALIDATION 396 (300 faults, 96 benign). No semantic duplicates, train/validation group overlap or exact Candidate 1 validation configuration overlap. Profile contents are included in physical signatures; identical seed 1 is not a stochastic replicate. This deterministic prototype campaign does not establish population safety rates or independent-trial confidence bounds.

Eight detection configurations × six global localization readouts × matched propagation on/off = 96 recorded search rows; twelve Weighted Sum settings. Architecture and searches were fixed before TRAIN; both operating points were saved with validation_seen=false before validation ran once.

Selected detection threshold .5, suspect .35, persistence 1, temporal retention .8, detection reliability 1, origin direct/indirect .9/.6, origin threshold .55, margin .15, ignorance maximum .5, propagation bonus 0, window 3000 ms. Weighted Sum weights [.2,.2,.2,.1,.2,.1], threshold .04, persistence 1. TRAIN propagation on/off produced exactly 386 correct localizations and no wrong origins at the selected point, so propagation was disabled before validation.

TRAIN: 521/600 detected (86.83%), 0/144 benign alarms; 381/393 plant-propagating cases detected, 12 silent (3.05%). Correct localization 386/521 (74.09%), UNKNOWN 135/521 (25.91%), zero wrong origins, 100% accuracy when localized; macro localization accuracy {pct(train['macro_localization_accuracy'])}. Median/P95 detection latency 0/200 ms. Correct localization precedes plant manifestation in {train['localized_before_plant']} TRAIN runs. The selected .55/.15 readout equals the actual online search-bank readout, so its later-localization timestamps are retained. Other offline readouts cannot reconstruct later timestamps; see reporting_adjustments.json. TRAIN sidecars show the initial configuration; selected TRAIN scores are from actual online bank states.

## New validation comparison

| Method | Detection | Detection given plant | Silent plant | Benign alarms | Median/P95 ms | Correct origins | UNKNOWN |
|---|---:|---:|---:|---:|---:|---:|---:|
{table}

Timing Monitor is specialized: 60/60 timing cases detected, 0/96 benign alarms, median/P95 100/100 ms; it is not assigned all-origin coverage. OR, Weighted Sum and DS variants share six eligible strengths and the same 100 ms samples. Hybrid uses its existing observation semantics. Plain DS uses matched Candidate 2 decision thresholds, while Candidate 1 uses its frozen full configuration.

Candidate 2 validation precision 100%, recall/macro detection 87.33%. Detection given control effect and actuator effect is 262/300 (87.33%) for each. Plant-propagating detection is 207/221 (93.67%); silent plant rate 14/221 (6.33%). Among those 207 detected plant-propagating runs, 195 alarms precede plant manifestation, 2 occur on the same tick, and 10 follow it. Correct later localization precedes plant manifestation in 115 cases. No pre-injection alarms. Zero-latency entries mean the first sampled injection tick, not continuous-time instantaneous response.

| Origin | Detection | Correct at first alarm | UNKNOWN at first alarm | Silent plant |
|---|---:|---:|---:|---:|
{layertext}

## Ablation and attribution

| Variant | Detected | Correct origins | Wrong origins | UNKNOWN | Silent plant |
|---|---:|---:|---:|---:|---:|
{ablation}

B0→B1 changes positive-evidence policy and frame separation together. The single-frame positive control already matches B1's 252 detections and 192 correct origins: the observed detection gain at this stage cannot be attributed specifically to frame separation. Removing conflicting joint NORMAL evidence explains this cohort's gain. Separate frames establish the architectural independence contract and permit plant-only anomalies with vacuous origin, but no isolated accuracy benefit is established here.

Origin reliability reduces first-alarm localization coverage without reducing observed errors. B2→B3 adds no alarm/localization/UNKNOWN/latency benefit. Matched full propagation on/off likewise changes no primary outcome; propagation is disabled, not retained for novelty. Temporal fusion increases detections by 10 (252→262), reducing silent plant by 10; it also changes when localization is evaluated. Detection discount .9 loses four detections while allowing more origin accumulation before alarm, giving 198 correct first-alarm origins; that is a timing/selectivity tradeoff, not proof that origin inference became more accurate. No-origin-discount retains all 262 detections and gives 202 correct origins, motivating the non-freeze decision.

## Uncertainty and sensor/control limits

Detection conflict is exactly zero by positive-support binary construction; this is a mathematical property, not evidence of calibrated certainty. Mean validation anomaly ignorance {c2['mean_anomaly_ignorance']:.6f}; origin ignorance {c2['mean_origin_ignorance']:.6f}; localization conflict {c2['mean_localization_conflict']:.8f}. High-conflict run counts are zero for both Candidate 2 frames. Frozen Candidate 1 has {by['Candidate 1']['high_localization_conflict_runs']} runs with a high joint-frame conflict step. Full per-origin and benign/faulty/localized/UNKNOWN/correct/incorrect distributions are in the uncertainty CSVs; incorrect-localization cohorts are empty (N=0, undefined statistics), not perfect confidence measurements.

All 60 detected SENSOR_CONTROL validation cases remain UNKNOWN. Its measured-slew source supports {{COMMUNICATION,SENSOR_CONTROL}}; an identical observation sequence may arise from either hidden origin. Without a trusted independent measurement or packet provenance, those equivalent cases are unidentifiable. Tests show identical output under changed hidden labels and unused diagnostic fields. This is an honest limit of the current observations and mapping, not proof that every richer sensor model is impossible. MEMORY and ACTUATOR also sometimes abstain at their early anomaly alarms; UNKNOWN does not suppress detection.

Selective coverage/accuracy plots sweep TRAIN only. The validation plot contains one fixed operating point. Belief, plausibility and BetP scores are not Bayesian probabilities. Correlation between channels and repeated temporal evidence remains a limitation; no calibrated uncertainty claim is made.

## Host cost and implementation

Candidate 2 persistent state {overhead['candidate2_state_bytes']} bytes versus Candidate 1 {overhead['candidate1_state_bytes']}; each mass {overhead['mass_bytes']} bytes, two masses {overhead['two_frame_bytes']} bytes, evidence {overhead['evidence_bytes']} bytes, output {overhead['candidate2_output_bytes']} bytes; configuration {overhead['candidate2_config_bytes']} additional bytes. Stack, stdio and adapter banks are excluded from detector-state figures.

Thirty interleaved host samples after warmup: legacy median {overhead['median_seconds']['legacy']*1000:.3f} ms, Candidate 1 {overhead['median_seconds']['candidate1']*1000:.3f} ms, Candidate 2 {overhead['median_seconds']['candidate2']*1000:.3f} ms per 1201-step simulation; Candidate 2 overhead {overhead['candidate2_over_legacy_percent']:.1f}% versus legacy and {overhead['candidate2_over_candidate1_percent']:.1f}% versus Candidate 1. This includes process/log formatting and host scheduling, never embedded WCET. Binary text/data/BSS deltas versus legacy are {overhead['binary_delta_vs_legacy']}; versus Candidate 1 {overhead['binary_delta_vs_candidate1']}. Executable BSS includes dormant development banks and is not deployable detector memory.

## Preservation and disposition

Only two preexisting files receive additive integration: Makefile includes a separate Candidate 2 fragment; the GUI launcher installs a new view module outside existing method bodies. All Candidate 1 files, frozen hashes and evidence remain byte-identical. Historical scientific source/evidence verification, 48 legacy cases, 64 RTL cases, representative v5 and Candidate 1 replay, complete unit tests and actual desktop checks are recorded in validation_record.md. No git staging, commits, pushes or destructive commands; user session bytes are preserved.

Candidate 2 is a completed, reproducible development revision with a locked evaluation operating point, **not a newly frozen final-holdout candidate**. Candidate 1 remains available. No final holdout was created or examined.
'''
 findings += '\n## Explicit research questions\n\n1. Detection/localization separation: the full revision improves coverage from 54.00% to 87.33%; separation alone has no isolated measured benefit over the single-frame positive control. Do not conflate architecture with the removal of joint NORMAL evidence.\n2. Silent plant propagation: reduced from 104 to 14 cases on this new validation cohort.\n3. Benign behavior: retained zero alarms in 96 validation and 144 training benign runs.\n4. Localization strength: 100% accuracy when localized, with only 67.18% of detected validation alarms localized.\n5. Wrong confident origins: none observed; this does not establish a zero population error rate.\n6. UNKNOWN: 86/262 alarms (32.82%); 60 are structurally ambiguous sensor/control cases, with 20 memory and six actuator abstentions at first alarm. Abstention avoids unsupported guesses; its universal optimality is not established.\n7. Detection reliability: discount .9 loses four detections versus reliability 1; no detection improvement demonstrated.\n8. Origin reliability: no benefit in measured wrong-origin rate; it loses 26 first-alarm correct localizations versus the no-discount control.\n9. Propagation: no measured detection, latency, localization, wrong-origin or UNKNOWN benefit; disabled in the selected point using TRAIN.\n10. Temporal fusion: adds ten detections and removes ten silent plant cases versus B3.\n11. Versus Candidate 1: a meaningful tradeoff improves coverage and silent propagation while preserving zero wrong origins, but conditional localization coverage falls as previously missed ambiguous cases now alarm.\n12. Versus fair Weighted Sum: no binary-detection superiority; origin and uncertainty outputs are additional capabilities, with greater host cost.\n13. Versus Plain DS: 262 versus 230 detections; 14 versus 46 silent plant cases; 176 versus 170 correct first-alarm origins, with more UNKNOWN because more cases alarm.\n14. Versus OR: ten more detections (87.33% versus 84.00%) and ten fewer silent plant cases.\n15. Beyond OR coverage: explicit origin estimates, abstention, separate ignorance/conflict and temporal memory; these outputs are not proof of calibrated probabilities.\n16. Hardest origins: COMMUNICATION has the lowest detection (40/60); SENSOR_CONTROL has no accepted origin labels; ACTUATOR accounts for all 14 remaining silent plant cases.\n17. Sensor identifiability: impossible for observationally equivalent sensor/communication streams under current inputs; not a universal claim about every possible richer model.\n18. Remaining silent plant faults: 14/221 plant-propagating cases (6.33%).\n19. Strongest positive: 100 additional detected faults and 90 fewer silent plant cases than frozen Candidate 1, without observed benign or wrong-origin penalties.\n20. Strongest negative: fair Weighted Sum matches detection, and a simpler no-origin-discount ablation dominates the selected localization point. The selected configuration is therefore not promoted to a frozen final-holdout candidate.\n'
 (out/'candidate2_findings.md').write_text(findings)
 (out/'candidate2_development_findings.md').write_text(findings)
 write_json(out/'candidate2_freeze_decision.json',dict(frozen=False,status='COMPLETED DEVELOPMENT; NOT PROMOTED TO FINAL-HOLDOUT CANDIDATE',candidate1_still_frozen=True,selected_parameters_changed_after_validation=False,holdout_created=False,reason='Selected origin reliability is dominated on measured decision endpoints by the no-origin-discount ablation; calibrated Weighted Sum matches binary detection. Preserve evidence, require a new preregistered assessment before simplification.',candidate2_detected=c2['detected'],no_origin_reliability_correct=by['No origin reliability']['correct_localizations'],candidate2_correct=c2['correct_localizations']))
 print('Reports and figures generated. Decision: do not freeze the selected configuration.',flush=True)
