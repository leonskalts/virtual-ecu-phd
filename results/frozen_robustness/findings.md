# Frozen robustness study

All six profiles locked before execution; one physical run/case, unchanged final executable and frozen SVM default operating point. Scheduler-jitter robustness NOT evaluated: incompatible simulator paths. P4/P5 use fixed Sensor C acquisition phases only.

| Profile | Method | Detection | Benign | Plant | Silent | Median/P95 ms |
|---|---|---|---|---|---|---|
| P0 | A2 | 281/300 | 0/100 | 170/170 | 0 | 0.0/100.0 |
| P0 | SVM-INT | 281/300 | 0/100 | 170/170 | 0 | 0.0/100.0 |
| P1 | A2 | 255/300 | 0/100 | 37/37 | 0 | 0.0/200.0 |
| P1 | SVM-INT | 255/300 | 0/100 | 37/37 | 0 | 0.0/200.0 |
| P2 | A2 | 288/300 | 0/100 | 192/192 | 0 | 0.0/100.0 |
| P2 | SVM-INT | 288/300 | 0/100 | 192/192 | 0 | 0.0/100.0 |
| P3 | A2 | 281/300 | 0/100 | 187/187 | 0 | 0.0/100.0 |
| P3 | SVM-INT | 281/300 | 0/100 | 187/187 | 0 | 0.0/100.0 |
| P4 | A2 | 281/300 | 0/100 | 170/170 | 0 | 0.0/100.0 |
| P4 | SVM-INT | 281/300 | 0/100 | 170/170 | 0 | 0.0/100.0 |
| P5 | A2 | 288/300 | 0/100 | 227/227 | 0 | 0.0/100.0 |
| P5 | SVM-INT | 288/300 | 0/100 | 227/227 | 0 | 0.0/100.0 |
| POOLED | A2 | 1674/1800 | 0/600 | 983/983 | 0 | 0.0/100.0 |
| POOLED | SVM-INT | 1674/1800 | 0/600 | 983/983 | 0 | 0.0/100.0 |

Worst profiles: {'detection': ['P1'], 'benign': ['P0', 'P1', 'P2', 'P3', 'P4', 'P5'], 'plant': ['P0', 'P1', 'P2', 'P3', 'P4', 'P5']}.
A2 miss taxonomy: {'P0': {'temporal: dormant memory outside probes': 2, 'temporal: uncaptured pulse': 1, 'structural: unexcited pump': 16}, 'P1': {'temporal: dormant memory outside probes': 2, 'temporal: uncaptured pulse': 1, 'structural: unexcited pump': 42}, 'P2': {'temporal: dormant memory outside probes': 2, 'temporal: uncaptured pulse': 1, 'structural: unexcited pump': 9}, 'P3': {'temporal: dormant memory outside probes': 2, 'temporal: uncaptured pulse': 1, 'structural: unexcited pump': 16}, 'P4': {'temporal: dormant memory outside probes': 2, 'temporal: uncaptured pulse': 1, 'structural: unexcited pump': 16}, 'P5': {'temporal: dormant memory outside probes': 2, 'temporal: uncaptured pulse': 1, 'structural: unexcited pump': 9}, 'POOLED': {'temporal: dormant memory outside probes': 12, 'temporal: uncaptured pulse': 6, 'structural: unexcited pump': 108}}.
Per-origin, precision, integrity-observable coverage, localization and final-unseen absolute percentage-point differences are in the accompanying CSVs. UNKNOWN is distinct from wrong confident origins. SVM supplies no origin localization.
No retuning or reruns. Same fault definitions across conditions; operating conditions can naturally alter excitation/propagation. New seeds are not paired identical noise realizations. Final-unseen comparison also changes cohort size/composition; profile differences are descriptive, not an isolated causal or field-risk estimate. Unresolved missed evidence is not automatically a proved classifier-only failure.

## Interpretation and complete profile metrics

A2 and frozen SVM-INT have identical case-level binary decisions and first-detection latencies in every condition. No discordant pairs exist; McNemar is not informative (the CSV leaves p blank). SVM provides no localization. Precision is100% for both methods in every profile and pooled; benign alarms and silent plant misses are zero throughout.

| Profile | Memory | Timing | Communication | Sensor/control | Actuator | Integrity-observable | A2 first coverage/accuracy | Runtime localized accuracy | Wrong runs/samples | Runtime UNKNOWN |
|---|---|---|---|---|---|---|---|---|---|---|
| P0 | 58/60 | 60/60 | 60/60 | 59/60 | 44/60 | 59/59 | 100.00% / 100.00% | 100.00% | 0/0 | 0.4149% |
| P1 | 58/60 | 60/60 | 60/60 | 59/60 | 18/60 | 59/59 | 100.00% / 100.00% | 100.00% | 0/0 | 0.1667% |
| P2 | 58/60 | 60/60 | 60/60 | 59/60 | 51/60 | 59/59 | 100.00% / 100.00% | 100.00% | 0/0 | 0.6627% |
| P3 | 58/60 | 60/60 | 60/60 | 59/60 | 44/60 | 59/59 | 100.00% / 100.00% | 100.00% | 0/0 | 0.4221% |
| P4 | 58/60 | 60/60 | 60/60 | 59/60 | 44/60 | 59/59 | 100.00% / 100.00% | 100.00% | 0/0 | 0.3968% |
| P5 | 58/60 | 60/60 | 60/60 | 59/60 | 51/60 | 59/59 | 100.00% / 100.00% | 100.00% | 0/0 | 0.5440% |
| POOLED | 348/360 | 360/360 | 360/360 | 354/360 | 252/360 | 354/354 | 100.00% / 100.00% | 100.00% | 0/0 | 0.4400% |

First localization coverage is conditional on detected faults; runtime accuracy excludes UNKNOWN. UNKNOWN is reported separately over all fault alarm samples.

Matched-template post-hoc accounting versus P0: P1 loses26detections and gains0; P2 gains7 and loses0; P3/P4 have no case-level detection changes; P5 gains7 and loses0. Every changed detection belongs to ACTUATOR. Thus the measured detection spread arises from operating-context excitation, with no new missed-fault classifier category identified.

The prior76-miss taxonomy remains: pooled108unexcited-pump +6uncaptured-pulse +12dormant-memory/probe-window misses. All126have no recorded plant manifestation. P1 has42unexcited pump misses versus16in P0; P2/P5 have9each. This is finite-cohort evidence, not a proof that no other classifier failure is possible.

Compared with frozen final unseen(93.6667%detection,0%benign,100%plant,median0/P95167ms): P0/P3/P4 detection delta0pp; P1−8.6667pp; P2/P5+2.3333pp; pooled−0.6667pp. Precision, benign rate, plant coverage and first/runtime localized accuracy are unchanged. Median latency delta0ms; P95delta+33ms in P1 and−67ms elsewhere/pooled. Per-origin rate differences also reflect the smaller stratified panel, so they must not be attributed solely to environmental stress.

The workload label in each manifest row names its original template; P5 overrides to authorized updates/noise/phase are explicitly encoded in the configuration fields and protocol. Fixed Sensor C phases are1,21,41,61,81,99ms; there is no within-run scheduler jitter.

Main conclusion: zero observed benign alarms, complete plant-propagating coverage and correct confident localization held across these registered legal conditions. Raw coverage is context-dependent, especially when low load leaves pump degradation unexcited. Scheduler-jitter robustness remains unevaluated because the existing stress path is incompatible with direct cross-layer fault injection.
