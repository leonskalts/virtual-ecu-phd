# Candidate 2 development findings

DEVELOPMENT / TUNING DATA — NOT FINAL HOLDOUT. This revision is implemented and evaluated; the selected operating point is **not promoted to a frozen final-holdout candidate**. Candidate 1 remains frozen and reproducible. No validation-driven algorithm or parameter change was made.

## Main result and decision

Candidate 2 detects 262/300 injected cases (87.33%) versus frozen Candidate 1's 162/300 (54.00%) on the same NEW validation cohort. Both have 0/96 benign alarm runs. Silent plant propagation falls from 104 to 14 of 221 plant-propagating cases. Candidate 2 correctly localizes 176 alarms, abstains on 86, and gives zero wrong origins. Localization coverage is 67.18%, accuracy conditional on localization 100%, and correct origins among all alarms 67.18%. Reporting 100% accuracy without its coverage would be misleading.

Calibrated Weighted Sum matches Candidate 2's 262 detections and 14 silent plant cases at the same median/P95 latency. Candidate 2 supplies origin and uncertainty outputs that this baseline does not, but has no demonstrated binary-detection superiority. Its no-origin-discount ablation produces 202 correct origins, 60 UNKNOWN and zero wrong origins at the same detection coverage. Thus the selected discounting policy is dominated on the measured decision endpoints by a simpler ablation. This is sufficient reason **not to freeze the selected configuration for final holdout**, despite its substantial improvement over Candidate 1. Preserve this completed validation as development evidence; a simplification would require another preregistered candidate and fresh assessment, not changing this one after looking.

## Campaign and selection

Exactly 1140 unique 120-second configurations: 900 faults (180 per origin), 240 benign, five operating profiles, two base onsets, three behaviors, multiple severities/durations. Grouped split: TRAIN 744 (600 faults, 144 benign), VALIDATION 396 (300 faults, 96 benign). No semantic duplicates, train/validation group overlap or exact Candidate 1 validation configuration overlap. Profile contents are included in physical signatures; identical seed 1 is not a stochastic replicate. This deterministic prototype campaign does not establish population safety rates or independent-trial confidence bounds.

Eight detection configurations × six global localization readouts × matched propagation on/off = 96 recorded search rows; twelve Weighted Sum settings. Architecture and searches were fixed before TRAIN; both operating points were saved with validation_seen=false before validation ran once.

Selected detection threshold .5, suspect .35, persistence 1, temporal retention .8, detection reliability 1, origin direct/indirect .9/.6, origin threshold .55, margin .15, ignorance maximum .5, propagation bonus 0, window 3000 ms. Weighted Sum weights [.2,.2,.2,.1,.2,.1], threshold .04, persistence 1. TRAIN propagation on/off produced exactly 386 correct localizations and no wrong origins at the selected point, so propagation was disabled before validation.

TRAIN: 521/600 detected (86.83%), 0/144 benign alarms; 381/393 plant-propagating cases detected, 12 silent (3.05%). Correct localization 386/521 (74.09%), UNKNOWN 135/521 (25.91%), zero wrong origins, 100% accuracy when localized; macro localization accuracy 76.88%. Median/P95 detection latency 0/200 ms. Correct localization precedes plant manifestation in 243 TRAIN runs. The selected .55/.15 readout equals the actual online search-bank readout, so its later-localization timestamps are retained. Other offline readouts cannot reconstruct later timestamps; see reporting_adjustments.json. TRAIN sidecars show the initial configuration; selected TRAIN scores are from actual online bank states.

## New validation comparison

| Method | Detection | Detection given plant | Silent plant | Benign alarms | Median/P95 ms | Correct origins | UNKNOWN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Candidate 1 | 162/300 | 52.94% | 104 | 0/96 | 100/300 | 162 | 0 |
| Plain DS | 230/300 | 79.19% | 46 | 0/96 | 0/200 | 170 | 60 |
| Simple OR | 252/300 | 89.14% | 24 | 0/96 | 0/200 | N/A | N/A |
| Weighted Sum | 262/300 | 93.67% | 14 | 0/96 | 0/200 | N/A | N/A |
| Candidate 2 | 262/300 | 93.67% | 14 | 0/96 | 0/200 | 176 | 86 |
| Hybrid | 154/300 | 61.54% | 85 | 0/96 | 0/475 | N/A | N/A |

Timing Monitor is specialized: 60/60 timing cases detected, 0/96 benign alarms, median/P95 100/100 ms; it is not assigned all-origin coverage. OR, Weighted Sum and DS variants share six eligible strengths and the same 100 ms samples. Hybrid uses its existing observation semantics. Plain DS uses matched Candidate 2 decision thresholds, while Candidate 1 uses its frozen full configuration.

Candidate 2 validation precision 100%, recall/macro detection 87.33%. Detection given control effect and actuator effect is 262/300 (87.33%) for each. Plant-propagating detection is 207/221 (93.67%); silent plant rate 14/221 (6.33%). Among those 207 detected plant-propagating runs, 195 alarms precede plant manifestation, 2 occur on the same tick, and 10 follow it. Correct later localization precedes plant manifestation in 115 cases. No pre-injection alarms. Zero-latency entries mean the first sampled injection tick, not continuous-time instantaneous response.

| Origin | Detection | Correct at first alarm | UNKNOWN at first alarm | Silent plant |
|---|---:|---:|---:|---:|
| MEMORY | 60/60 | 40 | 20 | 0 |
| TIMING | 60/60 | 60 | 0 | 0 |
| COMMUNICATION | 40/60 | 40 | 0 | 0 |
| SENSOR_CONTROL | 60/60 | 0 | 60 | 0 |
| ACTUATOR | 42/60 | 36 | 6 | 14 |

## Ablation and attribution

| Variant | Detected | Correct origins | Wrong origins | UNKNOWN | Silent plant |
|---|---:|---:|---:|---:|---:|
| Plain DS | 230 | 170 | 0 | 60 | 46 |
| Single frame positive | 252 | 192 | 0 | 60 | 24 |
| B1 Dual-frame | 252 | 192 | 0 | 60 | 24 |
| B2 Origin reliability | 252 | 170 | 0 | 82 | 24 |
| B3 Propagation | 252 | 170 | 0 | 82 | 24 |
| B4 Temporal | 262 | 176 | 0 | 86 | 14 |
| Detection reliability 0.9 | 258 | 198 | 0 | 60 | 18 |
| No origin reliability | 262 | 202 | 0 | 60 | 14 |

B0→B1 changes positive-evidence policy and frame separation together. The single-frame positive control already matches B1's 252 detections and 192 correct origins: the observed detection gain at this stage cannot be attributed specifically to frame separation. Removing conflicting joint NORMAL evidence explains this cohort's gain. Separate frames establish the architectural independence contract and permit plant-only anomalies with vacuous origin, but no isolated accuracy benefit is established here.

Origin reliability reduces first-alarm localization coverage without reducing observed errors. B2→B3 adds no alarm/localization/UNKNOWN/latency benefit. Matched full propagation on/off likewise changes no primary outcome; propagation is disabled, not retained for novelty. Temporal fusion increases detections by 10 (252→262), reducing silent plant by 10; it also changes when localization is evaluated. Detection discount .9 loses four detections while allowing more origin accumulation before alarm, giving 198 correct first-alarm origins; that is a timing/selectivity tradeoff, not proof that origin inference became more accurate. No-origin-discount retains all 262 detections and gives 202 correct origins, motivating the non-freeze decision.

## Uncertainty and sensor/control limits

Detection conflict is exactly zero by positive-support binary construction; this is a mathematical property, not evidence of calibrated certainty. Mean validation anomaly ignorance 0.902133; origin ignorance 0.905451; localization conflict 0.00025015. High-conflict run counts are zero for both Candidate 2 frames. Frozen Candidate 1 has 164 runs with a high joint-frame conflict step. Full per-origin and benign/faulty/localized/UNKNOWN/correct/incorrect distributions are in the uncertainty CSVs; incorrect-localization cohorts are empty (N=0, undefined statistics), not perfect confidence measurements.

All 60 detected SENSOR_CONTROL validation cases remain UNKNOWN. Its measured-slew source supports {COMMUNICATION,SENSOR_CONTROL}; an identical observation sequence may arise from either hidden origin. Without a trusted independent measurement or packet provenance, those equivalent cases are unidentifiable. Tests show identical output under changed hidden labels and unused diagnostic fields. This is an honest limit of the current observations and mapping, not proof that every richer sensor model is impossible. MEMORY and ACTUATOR also sometimes abstain at their early anomaly alarms; UNKNOWN does not suppress detection.

Selective coverage/accuracy plots sweep TRAIN only. The validation plot contains one fixed operating point. Belief, plausibility and BetP scores are not Bayesian probabilities. Correlation between channels and repeated temporal evidence remains a limitation; no calibrated uncertainty claim is made.

## Host cost and implementation

Candidate 2 persistent state 1568 bytes versus Candidate 1 824; each mass 512 bytes, two masses 1024 bytes, evidence 160 bytes, output 272 bytes; configuration 104 additional bytes. Stack, stdio and adapter banks are excluded from detector-state figures.

Thirty interleaved host samples after warmup: legacy median 6.809 ms, Candidate 1 13.663 ms, Candidate 2 20.058 ms per 1201-step simulation; Candidate 2 overhead 194.6% versus legacy and 46.8% versus Candidate 1. This includes process/log formatting and host scheduling, never embedded WCET. Binary text/data/BSS deltas versus legacy are {'text': 23506, 'data': 424, 'bss': 48144}; versus Candidate 1 {'text': 8296, 'data': 160, 'bss': 31952}. Executable BSS includes dormant development banks and is not deployable detector memory.

## Preservation and disposition

Only two preexisting files receive additive integration: Makefile includes a separate Candidate 2 fragment; the GUI launcher installs a new view module outside existing method bodies. All Candidate 1 files, frozen hashes and evidence remain byte-identical. Historical scientific source/evidence verification, 48 legacy cases, 64 RTL cases, representative v5 and Candidate 1 replay, complete unit tests and actual desktop checks are recorded in validation_record.md. No git staging, commits, pushes or destructive commands; user session bytes are preserved.

Candidate 2 is a completed, reproducible development revision with a locked evaluation operating point, **not a newly frozen final-holdout candidate**. Candidate 1 remains available. No final holdout was created or examined.

## Explicit research questions

1. Detection/localization separation: the full revision improves coverage from 54.00% to 87.33%; separation alone has no isolated measured benefit over the single-frame positive control. Do not conflate architecture with the removal of joint NORMAL evidence.
2. Silent plant propagation: reduced from 104 to 14 cases on this new validation cohort.
3. Benign behavior: retained zero alarms in 96 validation and 144 training benign runs.
4. Localization strength: 100% accuracy when localized, with only 67.18% of detected validation alarms localized.
5. Wrong confident origins: none observed; this does not establish a zero population error rate.
6. UNKNOWN: 86/262 alarms (32.82%); 60 are structurally ambiguous sensor/control cases, with 20 memory and six actuator abstentions at first alarm. Abstention avoids unsupported guesses; its universal optimality is not established.
7. Detection reliability: discount .9 loses four detections versus reliability 1; no detection improvement demonstrated.
8. Origin reliability: no benefit in measured wrong-origin rate; it loses 26 first-alarm correct localizations versus the no-discount control.
9. Propagation: no measured detection, latency, localization, wrong-origin or UNKNOWN benefit; disabled in the selected point using TRAIN.
10. Temporal fusion: adds ten detections and removes ten silent plant cases versus B3.
11. Versus Candidate 1: a meaningful tradeoff improves coverage and silent propagation while preserving zero wrong origins, but conditional localization coverage falls as previously missed ambiguous cases now alarm.
12. Versus fair Weighted Sum: no binary-detection superiority; origin and uncertainty outputs are additional capabilities, with greater host cost.
13. Versus Plain DS: 262 versus 230 detections; 14 versus 46 silent plant cases; 176 versus 170 correct first-alarm origins, with more UNKNOWN because more cases alarm.
14. Versus OR: ten more detections (87.33% versus 84.00%) and ten fewer silent plant cases.
15. Beyond OR coverage: explicit origin estimates, abstention, separate ignorance/conflict and temporal memory; these outputs are not proof of calibrated probabilities.
16. Hardest origins: COMMUNICATION has the lowest detection (40/60); SENSOR_CONTROL has no accepted origin labels; ACTUATOR accounts for all 14 remaining silent plant cases.
17. Sensor identifiability: impossible for observationally equivalent sensor/communication streams under current inputs; not a universal claim about every possible richer model.
18. Remaining silent plant faults: 14/221 plant-propagating cases (6.33%).
19. Strongest positive: 100 additional detected faults and 90 fewer silent plant cases than frozen Candidate 1, without observed benign or wrong-origin penalties.
20. Strongest negative: fair Weighted Sum matches detection, and a simpler no-origin-discount ablation dominates the selected localization point. The selected configuration is therefore not promoted to a frozen final-holdout candidate.
