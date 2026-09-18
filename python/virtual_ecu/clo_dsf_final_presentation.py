"""Publication-readable DEVELOPMENT CONFIRMATION figures and candid findings."""
import csv,gzip,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .clo_dsf_final_reporting import OUTPUT,ROOT,ORIGINS,records

def save(fig,name):
 fig.canvas.draw()
 bottom=fig.get_tightbbox(fig.canvas.get_renderer()).y0
 fig.text(.5,(bottom-.18)/fig.get_figheight(),'DEVELOPMENT CONFIRMATION — NOT FINAL HOLDOUT',ha='center',va='top',fontsize=9,color='#873445')
 for extension in ['png','pdf']:fig.savefig(OUTPUT/'figures'/f'{name}.{extension}',dpi=175,bbox_inches='tight')
 plt.close(fig)
def run():
 out=OUTPUT;rows=records(out/'final_candidate_runs.csv');summary=records(out/'final_candidate_baseline_comparison.csv');by={r['method']:r for r in summary};layers=records(out/'final_candidate_layer_summary.csv');final=by['Final CLO-DSF'];identity=json.loads((out/'identifiability_summary.json').read_text());bench=json.loads((out/'benchmark/overhead.json').read_text());confusion=records(out/'final_candidate_origin_confusion.csv');breakdown=records(out/'confirmed_unknown_breakdown.csv')
 selected_layers=[r for r in layers if r['method']=='Final CLO-DSF']
 fig,ax=plt.subplots(figsize=(9,4));ax.bar([r['origin'] for r in selected_layers],[100*r['coverage'] for r in selected_layers],color='#176b87');ax.set(ylabel='Detected faults (%)',ylim=(0,105),title='Frozen CLO-DSF: 144 fault cases per origin');ax.tick_params(axis='x',rotation=15);save(fig,'final_detection_by_origin')
 methods=['Simple OR','Weighted Sum','Plain DS','Candidate 1','Candidate 2','Final CLO-DSF','Hybrid']
 for field,title,name in [('coverage_given_plant_manifestation','Detection given plant manifestation (%)','final_plant_propagating_detection'),('silent_plant','Silent plant-propagating faults','final_silent_plant_propagation')]:
  fig,ax=plt.subplots(figsize=(10,4));ax.bar(methods,[by[m][field]*(100 if field.startswith('coverage') else 1) for m in methods],color=['#91a0b4']*5+['#176b87','#91a0b4']);ax.set(ylabel=title,title='Same 900-case confirmation cohort');ax.tick_params(axis='x',rotation=20);save(fig,name)
 matrix=[[r[k] for k in [*ORIGINS,'UNKNOWN','misses']] for r in confusion];fig,ax=plt.subplots(figsize=(9,4));ax.imshow(matrix,cmap='Blues');ax.set_xticks(range(7),[*ORIGINS,'UNKNOWN','misses'],rotation=25,ha='right');ax.set_yticks(range(5),ORIGINS)
 for i,row in enumerate(matrix):
  for j,v in enumerate(row):ax.text(j,i,str(v),ha='center',va='center',color='white' if v>=90 else 'black')
 ax.set(title='First-alarm origin; missed detections kept separate',ylabel='True origin (evaluation only)');save(fig,'final_localization_confusion')
 fig,ax=plt.subplots(figsize=(8,4))
 for method in ['Candidate 1','Candidate 2','Final CLO-DSF']:
  s=by[method];ax.scatter(100*s['localization_coverage'],100*s['accuracy_when_localized'],s=60,label=method)
 ax.set(xlabel='Fraction of detected cases localized (%)',ylabel='Accuracy when localized (%)',ylim=(95,101),title='Fixed operating points; no confirmation threshold sweep');ax.legend();save(fig,'localization_coverage_vs_accuracy')
 fig,ax=plt.subplots(figsize=(9,4));x=list(range(5));ax.bar([i-.18 for i in x],[r['unknown_at_first_alarm'] for r in breakdown],width=.36,label='At first alarm');ax.bar([i+.18 for i in x],[r['any_confirmed_unknown'] for r in breakdown],width=.36,label='At any runtime step');ax.set_xticks(x,ORIGINS,rotation=15);ax.set(ylabel='Runs',title='CONFIRMED + UNKNOWN is valid abstention');ax.legend();save(fig,'confirmed_unknown_breakdown')
 fig,axes=plt.subplots(1,2,figsize=(10,4));axes[0].bar(['Both','Only CLO-DSF','Only WS','Neither'],[606,0,0,114],color='#176b87');axes[0].set(ylabel='Fault runs',title='Paired detection: final vs frozen Weighted Sum');axes[0].tick_params(axis='x',rotation=15)
 axes[1].boxplot([[r['latency_ms'] for r in rows if r['method']==m and r['detected']] for m in ['Final CLO-DSF','Weighted Sum']],labels=['Final CLO-DSF','Weighted Sum']);axes[1].set(ylabel='Detection latency (ms)',title='Same detected cases; latency may differ');fig.tight_layout();save(fig,'final_vs_weighted_sum')
 ablations=['Candidate 2','Candidate 2 no origin discount','Final CLO-DSF','Final no temporal'];fig,ax=plt.subplots(figsize=(10,4));x=list(range(4));ax.bar([i-.18 for i in x],[by[m]['detected'] for m in ablations],width=.36,label='Detected');ax.bar([i+.18 for i in x],[by[m]['correct_localizations'] for m in ablations],width=.36,label='Correct first-alarm origins');ax.set_xticks(x,ablations,rotation=15,ha='right');ax.set(ylabel='Fault runs',title='Removing unsupported components preserves useful behavior');ax.legend();save(fig,'simplification_ablation')
 fig,ax=plt.subplots(figsize=(9,4));ax.bar(['Full allowed observation history','Full extracted evidence history','First-alarm snapshot'],list(identity['mixed_origin_groups'][k] for k in ['full_runtime_observation_history','full_evidence_history','first_alarm_snapshot_only']),color='#176b87');ax.set(ylabel='Exact mixed-origin groups',title='Feature equivalence does not establish full-observation equivalence');ax.tick_params(axis='x',rotation=10);save(fig,'identifiability_groups')
 fig,ax=plt.subplots(figsize=(9,4));modes=['legacy','candidate1','candidate2','final_reference','final_optimized'];x=list(range(5))
 for offset,scenario in [(-.18,'benign'),(.18,'timing')]:ax.bar([i+offset for i in x],[1000*next(r['median_seconds'] for r in bench['summary'] if r['scenario']==scenario and r['mode']==mode) for mode in modes],width=.36,label=scenario)
 ax.set_xticks(x,[m.replace('_',' ') for m in modes],rotation=15);ax.set(ylabel='Median host wall time (ms / simulation)',title='31 interleaved measured repetitions per mode and scenario');ax.legend();save(fig,'runtime_overhead')
 examples=[]
 for origin in ORIGINS+['NORMAL']:
  r=next(r for r in rows if r['method']=='Final CLO-DSF' and r['origin']==origin and (r['detected'] or origin=='NORMAL'))
  with gzip.open(out/'traces'/f"{r['run_id']}.final.csv.gz",'rt') as f:trace=list(csv.DictReader(f))
  t=[int(v['time_ms'])/1000 for v in trace];fig,axes=plt.subplots(4,1,figsize=(10,8),sharex=True)
  for field in ['anomaly_belief','anomaly_ignorance']:axes[0].plot(t,[float(v[field]) for v in trace],label=field)
  for field in ['origin_score','origin_margin','origin_ignorance']:axes[1].plot(t,[float(v[field]) for v in trace],label=field)
  for subset,label in [(1,'MEMORY'),(2,'TIMING'),(4,'COMMUNICATION'),(8,'SENSOR_CONTROL'),(16,'ACTUATOR'),(12,'COMM/SENSOR'),(31,'Ignorance')]:axes[2].plot(t,[float(v[f'origin_mass_{subset}']) for v in trace],label=label)
  axes[3].step(t,[int(v['alarm']) for v in trace],where='post',label='CONFIRMED');axes[3].step(t,[int(v['alarm']=='1' and v['estimated_origin']=='UNKNOWN') for v in trace],where='post',label='CONFIRMED + UNKNOWN');axes[3].step(t,[int(int(v['observed_evidence_path'])!=0) for v in trace],where='post',linestyle=':',label='Observed path (diagnostic only)')
  for ax in axes:
   if r['injected']:ax.axvline(r['start_ms']/1000,color='black',linestyle=':',label='Injection (evaluation only)' if ax==axes[0] else None)
   if r['propagation_plant_ms'] is not None:ax.axvline(r['propagation_plant_ms']/1000,color='#b33e79',linestyle='--',label='Plant (evaluation only)' if ax==axes[0] else None)
   ax.legend(fontsize=7,ncol=3);ax.set_ylim(-.05,1.05)
  axes[0].set_title(f"{origin}: {r['run_id']}");axes[3].set_xlabel('Simulation time (s)');fig.tight_layout();save(fig,'trace_'+origin.lower());examples.append(dict(origin=origin,run_id=r['run_id']))
 pct=lambda x:'N/A' if x is None else f'{100*x:.2f}%'
 comparison='\n'.join(f"| {m} | {by[m]['detected']}/720 | {pct(by[m]['coverage'])} | {by[m]['silent_plant']} | {by[m]['benign_false_alarms']}/180 | {by[m]['latency_median_ms']:g}/{by[m]['latency_p95_ms']:g} | {by[m]['correct_localizations'] if by[m]['correct_localizations'] is not None else 'N/A'} | {by[m]['unknown'] if by[m]['unknown'] is not None else 'N/A'} |" for m in methods)
 layer_table='\n'.join(f"| {r['origin']} | {r['detected']}/144 | {pct(r['coverage'])} | {r['correct_localizations']} | {r['unknown']} | {r['silent_plant']} |" for r in selected_layers)
 ablation_table='\n'.join(f"| {m} | {by[m]['detected']} | {by[m]['correct_localizations']} | {by[m]['wrong_localizations']} | {by[m]['unknown']} | {by[m]['silent_plant']} |" for m in ablations)
 bench_table='\n'.join(f"| {r['scenario']} | {r['mode']} | {r['median_seconds']*1000:.3f} | {r['mean_seconds']*1000:.3f} | {r['stddev_seconds']*1000:.3f} | {r['p95_seconds']*1000:.3f} | {r['overhead_vs_legacy_percent']:.2f}% |" for r in bench['summary'])
 text=f'''# CLO-DSF final candidate findings

DEVELOPMENT CONFIRMATION — NOT FINAL HOLDOUT.

**Freeze decision: YES.** The simplest supported Candidate 2 revision preserves its competitive binary detection, removes unsupported numeric origin discounting and propagation modulation, improves accepted origin coverage without observed wrong labels, and retains explicit uncertainty/abstention. Mathematical freeze preceded implementation optimization. No scientific parameters changed after confirmation. A completely new holdout remains to be generated in the next task.

## History, correction and provenance

Committed baseline 894cf12; Candidate 1 and Candidate 2 source, configuration, hashes and evidence are unchanged. The historical Candidate 2 no-origin-discount gate reproduced 262 detections, 202 correct origins, 60 UNKNOWN and zero wrong origins across all 396 prior validation cases; every historical raw/summary and comparison-metric output matched. This is a reproduction check, not new evidence.

The first proposed confirmation attempt stopped on an illegal memory bit 6 after 16 completed runs. Static validation additionally found non-aligned delay settings. All partial artifacts were retained and excluded before inspecting outcome metrics. The corrected study uses valid settings and fresh onset times 30500/72500 ms, with zero overlap with those 16 partial runs. See campaign_correction.md. The corrected 900-case cohort was checked through the unchanged C option parser/validator before execution. Neither detector nor Weighted Sum parameters changed. This is a disclosed campaign-definition correction, not post-outcome tuning.

The completed cohort comprises 900 unique configurations: 720 faults, 180 benign, 144 faults per origin, four operating profiles, three behaviors, multiple onsets/durations/magnitudes, and declared seeds 17/41/83. These seeds do not create independent stochastic replicas: the configured injector mechanisms here are deterministic. There is no exact physical overlap with any Candidate 1/2 train/validation configuration or within the confirmation cohort. No favorable case subset was selected. The fixed reference, parameter provenance, protocol, study, configuration manifest and evaluator were hashed before execution.

## Frozen algorithm

Detection frame {{NORMAL,ABNORMAL}}; origin frame {{MEMORY,TIMING,COMMUNICATION,SENSOR_CONTROL,ACTUATOR}}. Positive anomaly evidence and structurally justified origin subsets are unchanged. Dempster combination, independent temporal retention .8, detection reliability 1, suspect .35, confirmed .5, persistence 1, origin score .55, margin .15 and maximum ignorance .5 are copied exactly from Candidate 2. Extra origin reliability discount is removed. Propagation has no decision path; only diagnostic episode metadata remains. Observability-Aware describes available runtime signals, legitimate subsets, ignorance and abstention, not a numeric discount. No new feature or threshold search occurred.

## Detection and comparison

| Method | Detected | Coverage | Silent plant | Benign alarms | Median/P95 ms | Correct origins | UNKNOWN |
|---|---:|---:|---:|---:|---:|---:|---:|
{comparison}

Timing Monitor is specialized: 144/144 timing faults detected, 0/180 benign alarms, median/P95 50/100 ms. It is not evaluated as an all-origin detector.

Final coverage and macro detection are 606/720 = 84.17%. Nominal 95% Wilson interval: {pct(final['coverage_wilson_low'])}–{pct(final['coverage_wilson_high'])}. Precision 100%, recall 84.17%. Control-effect coverage {pct(final['coverage_given_control_effect'])} over {final['control_effect_runs']} cases; actuator-effect coverage {pct(final['coverage_given_actuator_effect'])} over {final['actuator_effect_runs']} cases. Plant-propagating coverage is 511/547 = 93.42% (nominal Wilson {pct(final['plant_coverage_wilson_low'])}–{pct(final['plant_coverage_wilson_high'])}); 36/547 = 6.58% remain silent. Of the 511 detected plant cases, 469 alarm before plant manifestation, zero on the same tick and 42 afterward. There are no pre-injection alarm runs.

Zero benign alarms in 180 cases has a nominal Wilson upper bound of {pct(final['benign_false_alarm_rate_wilson_high'])}, not zero population false-alarm probability. Designed configuration families are correlated; these intervals are descriptive binomial summaries, not validated population safety bounds. [Wilson method reference: NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

| Origin | Detected | Coverage | Correct first-alarm origins | UNKNOWN | Silent plant |
|---|---:|---:|---:|---:|---:|
{layer_table}

## Paired outcomes and Weighted Sum

Final versus frozen Weighted Sum: both detect 606, only final 0, only Weighted Sum 0, neither 114. No discordance means no McNemar test is needed; there is no observed binary detection advantage. Weighted Sum has lower P95 latency (200 versus 300 ms), with equal median 0 ms, silent plant cases and benign alarms. It remains a serious, unweakened baseline using [.2,.2,.2,.1,.2,.1], threshold .04 and one-sample persistence, selected on Candidate 2 TRAIN only.

Final versus OR: both detect 564, only final 42, only OR 0, neither 114. The exact conditional two-sided McNemar/binomial tail is 4.54747e−13; it is exploratory only because deterministic related configurations are not independent trials. It is not a final paper significance claim or freeze criterion. Final versus Candidate 2 has 606 both, zero discordance and 114 neither. [Paired-test definition](https://www.stat.ethz.ch/R-manual/R-devel/library/stats/html/mcnemar.test.html).

Beyond this calibrated binary Weighted Sum implementation, CLO-DSF provides **462 correct selective origin outputs**, explicit abstention for 144 first alarms, separate anomaly/origin ignorance, localization conflicts and timestamped diagnostic traces. It does not prove that Weighted Sum cannot be extended with a localization method; such an extension was not implemented or evaluated here.

## Localization, UNKNOWN and uncertainty

Correct origins among all alarms: 462/606 = 76.24%. Localization coverage: 76.24%, nominal Wilson {pct(final['localization_coverage_wilson_low'])}–{pct(final['localization_coverage_wilson_high'])}. Accuracy when localized: 462/462 = 100%, nominal Wilson {pct(final['localized_accuracy_wilson_low'])}–100%. UNKNOWN: 144/606 = 23.76%. Wrong non-UNKNOWN: 0, and the full runtime trace audit also finds zero wrong localized steps. Macro localization accuracy among detected origin cohorts is 80%. Always report accuracy together with coverage.

All 144 first-alarm UNKNOWN cases are SENSOR_CONTROL; all reached control, actuator and plant effects. At any runtime step, 248 fault runs have CONFIRMED + UNKNOWN: 14 memory, 144 sensor/control and 90 actuator. These transient later abstentions are distinct from the first-alarm endpoint. Correct localization precedes plant manifestation in 325 runs. First accepted localization latency median/P95 is 0/300 ms.

Mean per-run anomaly ignorance {final['mean_anomaly_ignorance']:.6f}, origin ignorance {final['mean_origin_ignorance']:.6f}, detection conflict {final['mean_detection_conflict']:.6f}, localization conflict {final['mean_localization_conflict']:.6f}. Detection conflict is mathematically zero in the positive binary frame. There are {final['high_localization_conflict_runs']} runs with a high localization-conflict step and none with high detection conflict. These do not imply calibrated probabilities. Detailed margin/ignorance distributions and empty incorrect-localization cohorts are retained in the uncertainty CSV.

## Identifiability: distinguish the evidence map from all available observations

There are **zero mixed-origin exact complete runtime-observation histories**, **three mixed-origin complete extracted-evidence histories**, and zero mixed-origin first-alarm snapshot groups. Therefore this cohort does not establish full-observation sensor/communication equivalence. The three evidence-map groups demonstrate information discarded by this fixed representation; see exact member lists and origin labels in final_candidate_identifiability_analysis.csv. No rounding or invented equivalence threshold is used.

SENSOR_CONTROL remains structurally unresolved because its source supports {{COMMUNICATION,SENSOR_CONTROL}}, giving tied origin scores without another distinguishing source. Current CLO-DSF cannot identify those cases, and identical complete feature histories cannot be deterministically separated by this detector. Richer processing of already available raw history might help some cases; trusted additional observables might help others, but neither was introduced here. Hidden-label invariance is proved separately by tests, not misrepresented as an observed sensor/communication collision. Sensor/control identifiability from the current raw observables is **PARTIAL / not established universally**; from this frozen evidence mapping it remains unresolved.

## Simplification ablation

| Variant | Detected | Correct origins | Wrong origins | UNKNOWN | Silent plant |
|---|---:|---:|---:|---:|---:|
{ablation_table}

Removing origin discount adds six correct accepted origins and removes six UNKNOWN first alarms versus selected Candidate 2, with identical detection and zero errors. Final decisions/metrics match Candidate 2's no-origin-discount, zero-propagation configuration on every run. Removing propagation modulation does not harm detection or localization; diagnostic paths never feed back. Temporal fusion remains useful: +42 detections and −42 silent plant cases versus temporal retention zero. It also increases P95 latency from 200 to 300 ms by admitting weaker evidence after accumulation; this is a real tradeoff.

## Exact optimization and host cost

The mathematical contract was written before optimized code. Optimization enumerates nonzero mass products in the unchanged accumulation order and caches logical subset/cardinality tables. It keeps generic validation, normalization, masses, thresholds and scientific outputs unchanged. Across all 900 archived observation streams / 1,080,900 samples, the **entire persistent state is bit-identical**. Numerical tolerance used: zero. State/alarms/origins/validity/timestamps have zero discrepancies.

| Scenario | Mode | Median ms | Mean ms | Std dev ms | P95 ms | Overhead vs legacy |
|---|---|---:|---:|---:|---:|---:|
{bench_table}

Each row has 31 interleaved measured repetitions after three warmup cycles. The optimized median improves only 1.12% on benign and 0.65% on timing workloads versus reference. This is a small observed end-to-end change, not a robust broad performance claim. Final optimized overhead remains 166.98%/145.85% versus legacy for these scenarios. Do not describe this measured implementation as lightweight. Detector-specific CSV formatting, process and host scheduling are included; final logs retain 17-digit numeric precision, historical formatting is unchanged. No aggressive further optimization was pursued to manufacture a speedup.

Persistent final reference/optimized state: {bench['persistent_state_bytes']['final_reference']} bytes; Candidate 1 824, Candidate 2 1568. Detection mass 512, origin mass 512, evidence 160, configuration 64 additional bytes. Stack and stdio buffers excluded. Binary deltas versus legacy: reference {bench['binary_delta_vs_legacy']['final_reference']}; optimized {bench['binary_delta_vs_legacy']['final_optimized']}. Executable BSS includes dormant research comparison states and is not isolated deployment memory. **Embedded WCET claim: NONE.**

## Freeze, readiness and strongest findings

Freeze YES is justified by faithful simplification, meaningful correct selective origins with explicit abstention, preserved low observed benign alarms, correct independent frames and complete regression/isolation/equivalence checks. It does not require beating Weighted Sum. The strongest positive result is that the simpler final candidate preserves 606 detections while accepting 462 correct origins and retaining honest UNKNOWN, with useful temporal detection gains. The strongest negative result is the Weighted Sum detection tie and lower P95 latency, together with unresolved sensor/control origin and substantial host cost. Thirty-six plant-propagating faults remain silent.

The algorithm is ready for a **completely new unseen final holdout**, subject to verifying the frozen manifests first. No holdout configurations, final paper tables or production/safety claims are created here. The first invalid campaign attempt remains disclosed and excluded. Candidate 1/2 history and the session edit are preserved; all v7.2 work remains unstaged.

Frozen contract: docs/clo_dsf_final_frozen_contract.md. Frozen configuration and mathematical manifest: clo_dsf_final_config.json and clo_dsf_final_scientific_hashes.json. Final implementation/dependency identity is sealed in clo_dsf_final_hashes.json after all checks. Build both implementations with make -f clo_dsf_final_optimized.mk; launch the additive frozen view with python3 scripts/virtual_ecu_final_gui.py. Hybrid remains default. Historical launchers/build files are untouched so their hashes still verify.

## Explicit research answers

1. Useful Candidate 2 behavior on a fresh cohort: YES, final exactly matches the no-origin-discount ablation.
2. Removing origin discount: six more accepted correct origins, same detection/errors.
3. Wrong-confident origins: zero at first alarm and throughout runtime.
4. Removing propagation changed detection: NO.
5. Removing propagation changed localization: NO.
6. Temporal fusion useful: YES, 42 additional detections and 42 fewer silent plant cases.
7. Versus Weighted Sum: identical detected cases; Weighted Sum lower P95 latency.
8. Measured additional capability: 462 selective correct origins, 144 first-alarm abstentions and separate origin uncertainty/conflict outputs.
9. Versus OR: 42 more detections, 42 fewer silent plant cases.
10. Versus Plain DS: 42 more detections and correct origins; 42 fewer silent plant cases.
11. Versus Hybrid: 606 versus 405 detections; no blanket claim across other cohorts.
12. Timing Monitor: both detect all 144 timing cases; specialized scope and different latency semantics retained.
13. Silent plant faults: 36/547.
14. Benign alarms: 0/180.
15. CONFIRMED + UNKNOWN: 144 at first alarm, 248 runs at any time.
16. Wrong localized predictions: zero observed.
17. Hardest: communication detection (96/144); sensor/control localization (no accepted origins).
18. Sensor/control limitation remains: YES for this structural feature map.
19. Mixed-origin equivalence: zero full raw observation histories, three full extracted-evidence histories.
20. Consequence: the fixed evidence representation cannot distinguish its equivalent streams; no universal raw-observation impossibility follows.
21. Observability-Aware terminology justified: YES, structurally, without numeric origin discount.
22. Host overhead: optimized +166.98% benign, +145.85% timing relative to legacy.
23. Optimization: bit-identical, with only modest measured end-to-end speedup.
24. Strongest positive: faithful simplification retains competitive detection and meaningful selective origins.
25. Strongest negative: calibrated Weighted Sum ties detection, is faster at P95, and final host overhead remains high.
'''
 (out/'final_candidate_findings.md').write_text(text)
 print('Final confirmation figures and findings generated.',flush=True)
