#!/usr/bin/env python3
"""Mathematical freeze only, before any optimized implementation is written."""
import csv,datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/cross_layer_safety_v7_2_confirmation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def run():
 target=OUT/'clo_dsf_final_config.json'
 if target.exists():raise ValueError('Scientific contract already frozen; never overwrite')
 pre=json.loads((OUT/'preregistered_confirmation.json').read_text())
 for name,digest in pre['source_sha256'].items():assert sha(ROOT/name)==digest,name
 provenance=json.loads((OUT/'parameter_provenance.json').read_text());params={k:float(v) if k!='confirmation_persistence' else int(v) for k,v in provenance['copied_exact_lexical_values'].items()}
 with (OUT/'final_candidate_baseline_comparison.csv').open() as f:stats={r['method']:r for r in csv.DictReader(f)}
 identity=json.loads((OUT/'identifiability_summary.json').read_text());reg=json.loads((OUT/'validation/preservation.json').read_text())
 assert reg['status']=='PASS' and reg['legacy_cases']==48 and reg['rtl_cases']==64
 assert (OUT/'validation/reference_tests.log').read_text().rstrip().endswith('OK')
 subprocess.run(['python3','scripts/verify_clo_dsf_final_preservation.py'],cwd=ROOT,check=True,capture_output=True)
 # Preserve the full regression report; the read-only verification refreshes preservation only.
 (OUT/'validation/preservation.json').write_text(json.dumps(reg,indent=2)+'\n')
 final=stats['Final CLO-DSF'];abl=stats['Candidate 2 no origin discount']
 for key in ['detected','correct_localizations','wrong_localizations','unknown','silent_plant','benign_false_alarms']:assert final[key]==abl[key]
 assert int(final['wrong_localizations'])==0 and identity['wrong_localized_runtime_runs']==0
 assert int(final['localized'])>0 and int(final['unknown'])>0 and int(final['benign_false_alarms'])==0
 channels=[dict(channel=name,origin_subset=subset,transform=transform) for name,subset,transform in [
 ('timing',['TIMING'],'max(deadline flag, missed execution, completion lateness, clip((execution age-period-deadline)/period))'),
 ('communication',['COMMUNICATION'],'1 on freshness failure or backward timestamp, otherwise clip((age-300)/300); future timestamp unavailable'),
 ('memory_control',['MEMORY'],'clip(abs(target-92)/4)'),
 ('sensor_control',['COMMUNICATION','SENSOR_CONTROL'],'max(measured temperature outside [-40,150],clip((abs(delta)-2.5*dt_seconds)/2))'),
 ('actuator',['ACTUATOR'],'clip(max(abs(fan command-actual)/.25,abs(pump command-actual)/.20))'),
 ('plant',['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR'],'clip((measured temperature-108)/7); vacuous origin mass')]]
 config=dict(status='FROZEN PRE-HOLDOUT DEVELOPMENT CANDIDATE',algorithm='CLO-DSF',schema_version=7.2,committed_baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parameters=params,parameter_provenance=provenance,frames={'detection':['NORMAL','ABNORMAL'],'origin':['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR']},reference_storage={'detection_blocks':[1,62],'origin_blocks':[33,2,4,8,16],'theta':63,'logical_origin_cardinality':5},channels=channels,origin_extra_reliability_discount=False,propagation_decision_modulation=False,propagation_diagnostic_only=True,diagnostic_window_ms=3000,propagation_graph={'timing':['sensor_control','actuator','plant'],'communication':['sensor_control','actuator','plant'],'memory_control':['sensor_control','actuator','plant'],'sensor_control':['actuator','plant'],'actuator':['plant'],'plant':[]},diagnostic_activation=.5,diagnostic_rule='Both episodes active, upstream onset strictly before downstream, no future/reversed/expired path; diagnostics run after inference',mass_assignment='Positive source strength e on ABNORMAL for detection; e on legitimate origin subset, remainder on whole frame. Whole-frame subset stays vacuous. Unavailable evidence vacuous.',detection_discount='Only copied global r_detection; never origin discounts',conflict_rule='Dempster',total_conflict_epsilon=1e-12,total_conflict_action='Flagged vacuous fallback',fold_order=[c['channel'] for c in channels]+['discounted previous same-frame mass'],state_machine='Consecutive score >= confirmed_threshold; reset below. CONFIRMED when persistence reached; else SUSPECT if score>=suspect_threshold, else NORMAL. Score=Bel(ABNORMAL).',origin_readout='Logical five-origin BetP. CONFIRMED plus top score >= threshold, top-minus-second >= margin, ignorance <= limit; else UNKNOWN. Deterministic stable first-index tie handling.',timestamp_rule='Ignore non-increasing timestamps; first-ever alarm/localization timestamps persist; sample cadence 100 ms.',sampling_interval_ms=100,truth_boundary='Only allowed runtime observations; labels/onsets/reference trajectories are evaluation-only',weighted_sum={'weights':[.2,.2,.2,.1,.2,.1],'threshold':.04,'persistence':1,'selection':'Unchanged Candidate 2 TRAIN selection index 6'},holdout_created=False,parameters_may_change=False,optimization_requirement='Only exact implementation changes after this scientific freeze; retain reference; every archived observation must give identical decisions/timestamps and bit-identical outputs if practical, else <=1e-12 numeric error with no decision changes')
 write(target,config)
 maprows=[dict(channel=c['channel'],detection_support='ABNORMAL',origin_support='|'.join(c['origin_subset']),origin_extra_discount='REMOVED',transform=c['transform']) for c in channels]
 with (OUT/'final_evidence_mapping.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(maprows[0]));w.writeheader();w.writerows(maprows)
 contract=f'''# CLO-DSF final frozen pre-holdout contract

Scientific freeze: {config['frozen_at_utc']}. Baseline {config['committed_baseline']}.
This is a frozen DEVELOPMENT candidate for a future independently generated holdout. No final holdout has been created, inspected or run. Do not change parameters, evidence mappings, rules, cadence, state logic or abstention after this contract.

## Scientific identity

The complete normative machine-readable specification is `results/cross_layer_safety_v7_2_confirmation/clo_dsf_final_config.json`; the exact runtime configuration is `final_reference.cfg`. The normative reference is `src/v7_2/clo_dsf_final.c`, with the unchanged DS core and inherited Candidate 2 extraction/structural origin map. The mathematical development is in `docs/clo_dsf_final_algorithm.md`.

Detection frame {{NORMAL,ABNORMAL}} and origin frame {{MEMORY,TIMING,COMMUNICATION,SENSOR_CONTROL,ACTUATOR}} are independent. Positive evidence supports ABNORMAL; healthy/unavailable sources are vacuous. Origin evidence supports its legitimate subset or ignorance. No numeric extra origin discount exists. No propagation modulation exists. Diagnostic graph output cannot affect masses, scores or decisions. Logical BetP counts FIVE origin hypotheses in the reference's partition embedding, never six storage bits.

Frozen values:
```json
{json.dumps(params,indent=2,sort_keys=True)}
```

Use Dempster normalized intersection in fixed channel order and then the separately discounted prior of the same frame. Total conflict 1−K≤1e−12 yields flagged vacuous fallback. The detector reads abnormal belief only. Confirmation requires the frozen consecutive count; recovery resets the count. Localize only when CONFIRMED and score, margin and ignorance gates pass; otherwise UNKNOWN. Belief and BetP are not Bayesian probabilities. Timestamp cadence is 100 ms, duplicate/backward samples are ignored. First-event timestamps persist.

## Confirmation decision and limits

Freeze decision: YES. The final simplification reproduces the useful no-origin-discount behavior on 900 new valid configurations: 606/720 faults detected, 0/180 benign alarms, 462/606 alarms localized correctly (76.24% coverage, 100% accuracy conditional on localization), 144 UNKNOWN and zero wrong origins, including the full runtime-step audit. There are still 36/547 silent plant-propagating faults. Weighted Sum detects exactly the same cases and has better P95 latency (200 versus 300 ms). Selective origin output, abstention and frame uncertainty are the defensible additional implemented capability, not a binary detection win.

The temporal-zero ablation detects 564 faults and leaves 78 silent plant cases; keeping temporal fusion has measured value. Removing origin discount adds six correct first-alarm origins versus selected Candidate 2; removing propagation modulation exactly preserves its already-zero-bonus decision behavior. All preservation, numerical independence and scientific regressions pass. No numerical target was tuned toward.

Exact full runtime histories have zero mixed-origin groups in this cohort. Three mixed-origin groups share the full six-channel evidence representation. Sensor/control remains structurally ambiguous in the inherited composite subset; do not claim empirical full-observation sensor collisions that were not found. Correlated designed cases, dependence among evidence sources and uncalibrated uncertainty limit statistical interpretation.

An earlier partial campaign attempt used illegal injector settings and stopped after 16 completed runs. It is preserved, excluded and disclosed in campaign_correction.md. Corrected settings were checked by the unchanged C validator before fresh-onset confirmation; scientific detector and baseline parameters were never changed.

## Optimization constraint and execution

This contract is written BEFORE any optimized implementation. Optimization may only specialize exact operations and remove implementation overhead. Retain the reference. Every archived confirmation observation must be replayed through reference and optimized implementations with identical detector state, alarm/origin decisions, localization validity and first-event timestamps. Prefer bit-identical full outputs; otherwise numerical error must be <=1e−12 with no decision discrepancies. Reject any optimization that changes a scientific decision. Benchmark at least 31 interleaved measured repetitions after warmup; report host cost, never embedded WCET.

Reference build: `make -f clo_dsf_final.mk`.
Reference execution:
```
./virtual_ecu_v7_2_reference /tmp/final.csv baseline --detector clo_dsf_final --detector-action observe_only --final-config results/cross_layer_safety_v7_2_confirmation/final_reference.cfg
```

`clo_dsf_final_scientific_hashes.json` fixes the mathematical contract and reference before optimization. `clo_dsf_final_hashes.json`, produced after all equivalence/GUI/benchmark checks, adds the accepted implementation dependencies. Verify both before future use. Historical Candidate 1/2 files and manifests remain untouched. The final GUI is an additive launcher and never changes the default Hybrid detector.
'''
 (ROOT/'docs/clo_dsf_final_frozen_contract.md').write_text(contract)
 files=[ROOT/'docs/clo_dsf_final_frozen_contract.md',ROOT/'docs/clo_dsf_final_algorithm.md',target,OUT/'final_evidence_mapping.csv',*[(ROOT/p) for p in pre['source_sha256']],ROOT/'src/v7/ds_evidence.c',ROOT/'include/ds_evidence.h',ROOT/'src/v7/clo_observability.c',ROOT/'src/v7/clo_dsf.c',ROOT/'include/clo_dsf.h',ROOT/'src/v7_1/candidate2_evidence.c',ROOT/'src/v7_1/candidate2_observability.c',ROOT/'include/clo_dsf_candidate2.h',ROOT/'include/runtime_observation.h',ROOT/'include/runtime_timing_observation.h',ROOT/'include/config.h',ROOT/'src/runtime_observation.c',ROOT/'src/main.c',ROOT/'src/scheduler.c']
 write(OUT/'clo_dsf_final_scientific_hashes.json',dict(frozen=True,optimization_started=False,sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))}))
 write(OUT/'freeze_decision.json',dict(freeze=True,mathematical_freeze_before_optimization=True,scientific_reason='Exact no-discount simplification preserves competitive detection, improves selective origin coverage, has no observed wrong origins or benign alarms, and passes isolation/regression. Localization and explicit abstention provide measured capability beyond calibrated binary pooling; detection superiority over Weighted Sum is not claimed.',no_parameter_search=True,no_postconfirmation_tuning=True,holdout_created=False))
 print('Scientific freeze YES; optimization may now begin. All parameters immutable.')
if __name__=='__main__':run()
