#!/usr/bin/env python3
"""Post-hoc reporting only. No input from here reaches inference or selection."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_revised_development import OUT,ORIGINS,METHODS,aggregate,write_csv,write_json,sha
from virtual_ecu.clo_dsf_final_reporting import records

def paired(rows,method):
 a={r['run_id']:r for r in rows if r['method']=='Revised CLO-DSF' and r['injected']};b={r['run_id']:r for r in rows if r['method']==method and r['injected']}
 return dict(comparator=method,both_detect=sum(a[k]['detected'] and b[k]['detected'] for k in a),only_revised=sum(a[k]['detected'] and not b[k]['detected'] for k in a),only_comparator=sum(not a[k]['detected'] and b[k]['detected'] for k in a),neither=sum(not a[k]['detected'] and not b[k]['detected'] for k in a))

def run():
 rows=records(OUT/'validation_runs.csv');summary=records(OUT/'revised_validation_summary.csv');by={r['method']:r for r in summary};a=by['Revised CLO-DSF'];b=by['v7.2 CLO-DSF'];w=by['Weighted Sum']
 write_csv(OUT/'revised_baseline_comparison.csv',summary)
 write_csv(OUT/'revised_ablation.csv',[dict(ablation=label,**by[method]) for label,method in [('A0: frozen v7.2','v7.2 CLO-DSF'),('A1: actuator contract only','Revised CLO-DSF')]])
 layers=[];confusion=[]
 for method in METHODS:
  for origin in ORIGINS:
   subset=[r for r in rows if r['method']==method and r['origin']==origin]
   if method=='Timing Monitor' and origin!='TIMING':continue
   layers.append(dict(method=method,origin=origin,**aggregate(subset)))
   if method in ['Revised CLO-DSF','v7.2 CLO-DSF','Candidate 2','Plain DS']:
    confusion.append(dict(method=method,true_origin_evaluation_only=origin,**{o:sum(r['detected'] and r['origin_at_alarm']==o for r in subset) for o in ORIGINS+['UNKNOWN']},misses=sum(not r['detected'] for r in subset)))
 write_csv(OUT/'revised_layer_summary.csv',layers);write_csv(OUT/'revised_origin_confusion.csv',confusion)
 pairs=[paired(rows,m) for m in ['Weighted Sum','v7.2 CLO-DSF']];write_csv(OUT/'revised_paired_comparison.csv',pairs)
 q=pairs[1]
 justified=(a['silent_plant']<b['silent_plant'] or a['correct_localizations']>b['correct_localizations']) and q['only_comparator']==0 and a['benign_false_alarms']<=b['benign_false_alarms'] and a['wrong_localizations']==0 and a['wrong_localized_runtime_samples']==0
 write_json(OUT/'scientific_decision.json',dict(scientifically_justified=justified,freeze_pending_regression=True,no_parameter_changes=True,no_holdout=True,reason='Apply the preregistered material safety/localization trade-off rule, no extra numerical target or baseline tuning',paired=pairs))
 pct=lambda v:'N/A' if v is None else f'{100*v:.2f}%'
 table='\n'.join(f"| {r['method']} | {r['detected']}/{r['faulty_runs']} | {pct(r['coverage'])} | {r['silent_plant']} | {r['benign_false_alarms']}/{r['benign_runs']} | {r['latency_median_ms']}/{r['latency_p95_ms']} | {r['correct_localizations']} | {r['unknown']} |" for r in summary)
 per='\n'.join(f"| {r['origin']} | {r['detected']}/{r['faulty_runs']} | {pct(r['localization_coverage'])} | {pct(r['accuracy_when_localized'])} | {r['unknown']} | {r['wrong_localizations']} |" for r in layers if r['method']=='Revised CLO-DSF')
 root=json.loads((OUT/'miss_analysis.json').read_text())
 from collections import Counter
 revised=[r for r in rows if r['method']=='Revised CLO-DSF'];old_runs={r['run_id']:r for r in rows if r['method']=='v7.2 CLO-DSF'}
 gains=Counter((r['origin'],r['model'],r['behavior'],r['magnitude']) for r in revised if r['detected'] and not old_runs[r['run_id']]['detected'])
 remaining=Counter(r['origin'] for r in revised if r['injected'] and not r['detected'])
 silent=Counter((r['origin'],r['model']) for r in revised if r['silent_plant'])
 text=f'''# CLO-DSF v7.3 findings — DEVELOPMENT ONLY

No final paper holdout was created or inspected. These are new development
TRAIN/VALIDATION cases, not final unseen generalization evidence.

## Miss audit and principled choice

Every historical v7.2 miss is classified: {root['v7.2']}. The 78 algorithm-limited
cases comprise 48 communication cases with visible 100/200 ms reception age
suppressed by the inherited 300 ms grace, and 30 actuator cases with a visible
tracking mismatch but insufficient scaled/temporally retained mass. All 36
silent plant misses are algorithm-limited (30 actuator, 6 communication).
The 36 observability-limited cases are latent stuck bits that agree with the
current stored target. Passive values cannot identify those dormant defects;
trusted active memory BIST would be needed. No checksum claim is made for a
bit whose observed value remains correct. Candidate 2 corroboration over all
its development cases: {root['Candidate 2']}.

The per-case CSV records comparator detections and exact supporting signal
ranges. No reference-run residual was supplied to inference. Classification is
an offline engineering diagnosis, not a theorem of universal observability.

One change replaces actuator residual severity scaling with an exact synchronous
command/response conformance check. The source model guarantees clamp(command)
before detector sampling. A one-representable-float envelope accepts numerical
neighbors; it is not a severity parameter fitted to faults. Replace the source,
do not duplicate it. Keep all other evidence, DS fusion, independent frames,
temporal retention, thresholds, origin gates and UNKNOWN behavior unchanged.
No additional trusted observable is introduced. The label-derived simulated
fan self-test is explicitly excluded. Historical Hybrid retains its own original
inputs; this revision gains nothing from that self-test.

## Registered campaign and selection

1,125 new unique configurations: 900 faulty, 225 benign. TRAIN: 735 (600 faulty,
135 benign); VALIDATION: 390 (300 faulty, 90 benign). Every validation origin
has 60 cases. Each model contributes one whole behavior group to validation,
chosen by a fixed hash; severity/profile/onset siblings never cross partitions.
All three behaviors occur across the campaign. Five new operating profiles,
multiple magnitudes/durations/onsets and recorded seeds are used. Seed labels
do not make these deterministic injectors independent stochastic replicates.
Zero physical overlap with Candidate 1, Candidate 2, v7.2 or its excluded draft.

A static duplicate-profile check caught clipped-speed duplicates during design,
before registration or any simulation; the speed base was corrected. All final
configurations passed the unchanged C validator before execution. No partial
simulation campaign, outcome-driven definition change or validation rerun occurred.

The algorithm, generator, split, fixed objective and dependencies were hashed
before TRAIN. No parameter search was necessary. All eight configuration values
are byte-identical to v7.2. A selection record with validation_seen=false was
written after TRAIN passed the predeclared contradiction checks and before any
VALIDATION simulation. Source identities were verified at that boundary.

## Same-cohort validation

| Method | Detected | Coverage | Silent plant | Benign alarms | Median/P95 ms | Correct origins | UNKNOWN |
|---|---:|---:|---:|---:|---:|---:|---:|
{table}

Timing Monitor's denominator is timing-only (plus benign for false alarms).
All frozen baselines retain original evidence/parameters; Weighted Sum remains
Candidate 2 TRAIN choice 6. Its evidence does not inherit the new actuator rule.
There is no comparison against a separately enhanced Weighted Sum, and no claim
that DS uniquely enables a contract checker. A generic pool could incorporate
the same evidence; that is a different, untested baseline.

Revised macro detection: {pct(a['macro_coverage'])}. Plant-propagating detection:
{a['plant_manifestation_runs']-a['silent_plant']}/{a['plant_manifestation_runs']}
({pct(a['coverage_given_plant_manifestation'])}). Silent plant cases:
{a['silent_plant']}. Localization coverage {pct(a['localization_coverage'])},
accuracy when localized {pct(a['accuracy_when_localized'])}, UNKNOWN
{a['unknown']} ({pct(a['unknown_rate'])}), wrong non-UNKNOWN first origins
{a['wrong_localizations']}, wrong localized runtime samples
{a['wrong_localized_runtime_samples']}. Coverage and conditional accuracy must
always be reported together. Benign counts do not establish population safety.

| Origin | Detection | Localization coverage | Accuracy when localized | UNKNOWN | Wrong |
|---|---:|---:|---:|---:|---:|
{per}

Paired against Weighted Sum: {pairs[0]}.
Paired against v7.2: {pairs[1]}.
No population-significance claim: designed families are correlated.

## Minimum ablation and interpretation

A0 is frozen v7.2. A1 changes only the actuator source. There is no A2 or hidden
supporting change. Detection changes from {b['detected']} to {a['detected']};
silent plant cases from {b['silent_plant']} to {a['silent_plant']}; benign alarms
from {b['benign_false_alarms']} to {a['benign_false_alarms']}; correct origins
from {b['correct_localizations']} to {a['correct_localizations']}; UNKNOWN
from {b['unknown']} to {a['unknown']}. Median/P95 latency changes from
{b['latency_median_ms']}/{b['latency_p95_ms']} to {a['latency_median_ms']}/{a['latency_p95_ms']} ms.

Gained-case families (origin/model/behavior/magnitude): {dict(gains)}.
All eight gains over v7.2 are weak intermittent pump degradations; they span
four operating profiles and two onsets, but are a related deterministic family,
not eight independent demonstrations of broad generalization. Remaining misses
by origin: {dict(remaining)}. Remaining silent-plant families: {dict(silent)}.
The six remaining actuator misses have no witnessed response violation; a
degraded pump commanded at zero throughout both injected intervals cannot be
exposed by passive command tracking alone. Archived observations confirm zero
pump command and zero response gap in all six of these cases.

Scientific freeze eligibility under the registered rule: {justified}.
Final freeze is gated on the separate final regression/preservation record.

Strongest positive: the new contract evidence tests whether discarded weak
actuator residuals explain missed plant propagation, with an isolated A0/A1
comparison and no numerical tuning.
Strongest limitation: this is an instantaneous, noiseless virtual actuator
contract. Physical hardware needs trusted response feedback and a justified
error/dynamics envelope; this one-ULP bound cannot be exported as a physical
sensor tolerance. Unchanged communication freshness blind spots, dormant memory
faults and sensor/control origin ambiguity remain. Improvement over frozen
Weighted Sum would establish the value of added evidence, not DS superiority.

Runtime isolation tests mutate injector fields, true plant state, propagation
truth, and diagnosis/safety/detector labels while keeping allowed inputs fixed.
Historical hashes, full final regression and manifests are recorded separately.
Exact allowlisted runtime observations and compact online metrics are retained;
commands plus raw/summary/trace hashes permit reproducibility without retaining
duplicate large raw logs or screenshots. No GUI changes or performance claims.
'''
 (OUT/'revised_findings.md').write_text(text)
 print(json.dumps(dict(revised=a,previous=b,weighted=w,paired=pairs,scientific_eligibility=justified),indent=2))
if __name__=='__main__':run()
