# CLO-DSF final frozen pre-holdout contract

Scientific freeze: 2026-09-18T13:28:04.421808+00:00. Baseline 894cf12a98444d8fb830eb4b528925430c989759.
This is a frozen DEVELOPMENT candidate for a future independently generated holdout. No final holdout has been created, inspected or run. Do not change parameters, evidence mappings, rules, cadence, state logic or abstention after this contract.

## Scientific identity

The complete normative machine-readable specification is `results/cross_layer_safety_v7_2_confirmation/clo_dsf_final_config.json`; the exact runtime configuration is `final_reference.cfg`. The normative reference is `src/v7_2/clo_dsf_final.c`, with the unchanged DS core and inherited Candidate 2 extraction/structural origin map. The mathematical development is in `docs/clo_dsf_final_algorithm.md`.

Detection frame {NORMAL,ABNORMAL} and origin frame {MEMORY,TIMING,COMMUNICATION,SENSOR_CONTROL,ACTUATOR} are independent. Positive evidence supports ABNORMAL; healthy/unavailable sources are vacuous. Origin evidence supports its legitimate subset or ignorance. No numeric extra origin discount exists. No propagation modulation exists. Diagnostic graph output cannot affect masses, scores or decisions. Logical BetP counts FIVE origin hypotheses in the reference's partition embedding, never six storage bits.

Frozen values:
```json
{
  "confirmation_persistence": 1,
  "confirmed_threshold": 0.5,
  "ignorance_limit": 0.5,
  "lambda_temporal": 0.8,
  "localization_margin_threshold": 0.15,
  "localization_threshold": 0.55,
  "r_detection": 1.0,
  "suspect_threshold": 0.35
}
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
