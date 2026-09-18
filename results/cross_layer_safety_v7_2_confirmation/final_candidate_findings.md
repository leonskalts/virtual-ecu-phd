# CLO-DSF final candidate findings

DEVELOPMENT CONFIRMATION — NOT FINAL HOLDOUT.

**Freeze decision: YES.** The simplest supported Candidate 2 revision preserves its competitive binary detection, removes unsupported numeric origin discounting and propagation modulation, improves accepted origin coverage without observed wrong labels, and retains explicit uncertainty/abstention. Mathematical freeze preceded implementation optimization. No scientific parameters changed after confirmation. A completely new holdout remains to be generated in the next task.

## History, correction and provenance

Committed baseline 894cf12; Candidate 1 and Candidate 2 source, configuration, hashes and evidence are unchanged. The historical Candidate 2 no-origin-discount gate reproduced 262 detections, 202 correct origins, 60 UNKNOWN and zero wrong origins across all 396 prior validation cases; every historical raw/summary and comparison-metric output matched. This is a reproduction check, not new evidence.

The first proposed confirmation attempt stopped on an illegal memory bit 6 after 16 completed runs. Static validation additionally found non-aligned delay settings. All partial artifacts were retained and excluded before inspecting outcome metrics. The corrected study uses valid settings and fresh onset times 30500/72500 ms, with zero overlap with those 16 partial runs. See campaign_correction.md. The corrected 900-case cohort was checked through the unchanged C option parser/validator before execution. Neither detector nor Weighted Sum parameters changed. This is a disclosed campaign-definition correction, not post-outcome tuning.

The completed cohort comprises 900 unique configurations: 720 faults, 180 benign, 144 faults per origin, four operating profiles, three behaviors, multiple onsets/durations/magnitudes, and declared seeds 17/41/83. These seeds do not create independent stochastic replicas: the configured injector mechanisms here are deterministic. There is no exact physical overlap with any Candidate 1/2 train/validation configuration or within the confirmation cohort. No favorable case subset was selected. The fixed reference, parameter provenance, protocol, study, configuration manifest and evaluator were hashed before execution.

## Frozen algorithm

Detection frame {NORMAL,ABNORMAL}; origin frame {MEMORY,TIMING,COMMUNICATION,SENSOR_CONTROL,ACTUATOR}. Positive anomaly evidence and structurally justified origin subsets are unchanged. Dempster combination, independent temporal retention .8, detection reliability 1, suspect .35, confirmed .5, persistence 1, origin score .55, margin .15 and maximum ignorance .5 are copied exactly from Candidate 2. Extra origin reliability discount is removed. Propagation has no decision path; only diagnostic episode metadata remains. Observability-Aware describes available runtime signals, legitimate subsets, ignorance and abstention, not a numeric discount. No new feature or threshold search occurred.

## Detection and comparison

| Method | Detected | Coverage | Silent plant | Benign alarms | Median/P95 ms | Correct origins | UNKNOWN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Simple OR | 564/720 | 78.33% | 78 | 0/180 | 0/200 | N/A | N/A |
| Weighted Sum | 606/720 | 84.17% | 36 | 0/180 | 0/200 | N/A | N/A |
| Plain DS | 564/720 | 78.33% | 78 | 0/180 | 0/200 | 420 | 144 |
| Candidate 1 | 492/720 | 68.33% | 150 | 0/180 | 100/500 | 420 | 72 |
| Candidate 2 | 606/720 | 84.17% | 36 | 0/180 | 0/300 | 456 | 150 |
| Final CLO-DSF | 606/720 | 84.17% | 36 | 0/180 | 0/300 | 462 | 144 |
| Hybrid | 405/720 | 56.25% | 175 | 0/180 | 0/2200 | N/A | N/A |

Timing Monitor is specialized: 144/144 timing faults detected, 0/180 benign alarms, median/P95 50/100 ms. It is not evaluated as an all-origin detector.

Final coverage and macro detection are 606/720 = 84.17%. Nominal 95% Wilson interval: 81.32%–86.65%. Precision 100%, recall 84.17%. Control-effect coverage 90.61% over 660 cases; actuator-effect coverage 90.25% over 636 cases. Plant-propagating coverage is 511/547 = 93.42% (nominal Wilson 91.02%–95.21%); 36/547 = 6.58% remain silent. Of the 511 detected plant cases, 469 alarm before plant manifestation, zero on the same tick and 42 afterward. There are no pre-injection alarm runs.

Zero benign alarms in 180 cases has a nominal Wilson upper bound of 2.09%, not zero population false-alarm probability. Designed configuration families are correlated; these intervals are descriptive binomial summaries, not validated population safety bounds. [Wilson method reference: NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

| Origin | Detected | Coverage | Correct first-alarm origins | UNKNOWN | Silent plant |
|---|---:|---:|---:|---:|---:|
| MEMORY | 108/144 | 75.00% | 108 | 0 | 0 |
| TIMING | 144/144 | 100.00% | 144 | 0 | 0 |
| COMMUNICATION | 96/144 | 66.67% | 96 | 0 | 6 |
| SENSOR_CONTROL | 144/144 | 100.00% | 0 | 144 | 0 |
| ACTUATOR | 114/144 | 79.17% | 114 | 0 | 30 |

## Paired outcomes and Weighted Sum

Final versus frozen Weighted Sum: both detect 606, only final 0, only Weighted Sum 0, neither 114. No discordance means no McNemar test is needed; there is no observed binary detection advantage. Weighted Sum has lower P95 latency (200 versus 300 ms), with equal median 0 ms, silent plant cases and benign alarms. It remains a serious, unweakened baseline using [.2,.2,.2,.1,.2,.1], threshold .04 and one-sample persistence, selected on Candidate 2 TRAIN only.

Final versus OR: both detect 564, only final 42, only OR 0, neither 114. The exact conditional two-sided McNemar/binomial tail is 4.54747e−13; it is exploratory only because deterministic related configurations are not independent trials. It is not a final paper significance claim or freeze criterion. Final versus Candidate 2 has 606 both, zero discordance and 114 neither. [Paired-test definition](https://www.stat.ethz.ch/R-manual/R-devel/library/stats/html/mcnemar.test.html).

Beyond this calibrated binary Weighted Sum implementation, CLO-DSF provides **462 correct selective origin outputs**, explicit abstention for 144 first alarms, separate anomaly/origin ignorance, localization conflicts and timestamped diagnostic traces. It does not prove that Weighted Sum cannot be extended with a localization method; such an extension was not implemented or evaluated here.

## Localization, UNKNOWN and uncertainty

Correct origins among all alarms: 462/606 = 76.24%. Localization coverage: 76.24%, nominal Wilson 72.69%–79.45%. Accuracy when localized: 462/462 = 100%, nominal Wilson 99.18%–100%. UNKNOWN: 144/606 = 23.76%. Wrong non-UNKNOWN: 0, and the full runtime trace audit also finds zero wrong localized steps. Macro localization accuracy among detected origin cohorts is 80%. Always report accuracy together with coverage.

All 144 first-alarm UNKNOWN cases are SENSOR_CONTROL; all reached control, actuator and plant effects. At any runtime step, 248 fault runs have CONFIRMED + UNKNOWN: 14 memory, 144 sensor/control and 90 actuator. These transient later abstentions are distinct from the first-alarm endpoint. Correct localization precedes plant manifestation in 325 runs. First accepted localization latency median/P95 is 0/300 ms.

Mean per-run anomaly ignorance 0.902040, origin ignorance 0.902100, detection conflict 0.000000, localization conflict 0.001718. Detection conflict is mathematically zero in the positive binary frame. There are 29 runs with a high localization-conflict step and none with high detection conflict. These do not imply calibrated probabilities. Detailed margin/ignorance distributions and empty incorrect-localization cohorts are retained in the uncertainty CSV.

## Identifiability: distinguish the evidence map from all available observations

There are **zero mixed-origin exact complete runtime-observation histories**, **three mixed-origin complete extracted-evidence histories**, and zero mixed-origin first-alarm snapshot groups. Therefore this cohort does not establish full-observation sensor/communication equivalence. The three evidence-map groups demonstrate information discarded by this fixed representation; see exact member lists and origin labels in final_candidate_identifiability_analysis.csv. No rounding or invented equivalence threshold is used.

SENSOR_CONTROL remains structurally unresolved because its source supports {COMMUNICATION,SENSOR_CONTROL}, giving tied origin scores without another distinguishing source. Current CLO-DSF cannot identify those cases, and identical complete feature histories cannot be deterministically separated by this detector. Richer processing of already available raw history might help some cases; trusted additional observables might help others, but neither was introduced here. Hidden-label invariance is proved separately by tests, not misrepresented as an observed sensor/communication collision. Sensor/control identifiability from the current raw observables is **PARTIAL / not established universally**; from this frozen evidence mapping it remains unresolved.

## Simplification ablation

| Variant | Detected | Correct origins | Wrong origins | UNKNOWN | Silent plant |
|---|---:|---:|---:|---:|---:|
| Candidate 2 | 606 | 456 | 0 | 150 | 36 |
| Candidate 2 no origin discount | 606 | 462 | 0 | 144 | 36 |
| Final CLO-DSF | 606 | 462 | 0 | 144 | 36 |
| Final no temporal | 564 | 420 | 0 | 144 | 78 |

Removing origin discount adds six correct accepted origins and removes six UNKNOWN first alarms versus selected Candidate 2, with identical detection and zero errors. Final decisions/metrics match Candidate 2's no-origin-discount, zero-propagation configuration on every run. Removing propagation modulation does not harm detection or localization; diagnostic paths never feed back. Temporal fusion remains useful: +42 detections and −42 silent plant cases versus temporal retention zero. It also increases P95 latency from 200 to 300 ms by admitting weaker evidence after accumulation; this is a real tradeoff.

## Exact optimization and host cost

The mathematical contract was written before optimized code. Optimization enumerates nonzero mass products in the unchanged accumulation order and caches logical subset/cardinality tables. It keeps generic validation, normalization, masses, thresholds and scientific outputs unchanged. Across all 900 archived observation streams / 1,080,900 samples, the **entire persistent state is bit-identical**. Numerical tolerance used: zero. State/alarms/origins/validity/timestamps have zero discrepancies.

| Scenario | Mode | Median ms | Mean ms | Std dev ms | P95 ms | Overhead vs legacy |
|---|---|---:|---:|---:|---:|---:|
| benign | legacy | 8.311 | 8.332 | 0.414 | 8.808 | 0.00% |
| benign | candidate1 | 15.550 | 15.439 | 0.528 | 16.030 | 87.09% |
| benign | candidate2 | 21.691 | 21.802 | 0.393 | 22.595 | 160.98% |
| benign | final_reference | 22.440 | 22.494 | 0.585 | 23.469 | 170.00% |
| benign | final_optimized | 22.190 | 22.226 | 0.431 | 22.832 | 166.98% |
| timing | legacy | 9.498 | 9.244 | 0.792 | 10.178 | 0.00% |
| timing | candidate1 | 16.701 | 16.385 | 0.750 | 17.167 | 75.84% |
| timing | candidate2 | 23.098 | 22.833 | 0.846 | 23.859 | 143.20% |
| timing | final_reference | 23.503 | 23.341 | 0.728 | 24.158 | 147.47% |
| timing | final_optimized | 23.350 | 23.184 | 0.696 | 24.016 | 145.85% |

Each row has 31 interleaved measured repetitions after three warmup cycles. The optimized median improves only 1.12% on benign and 0.65% on timing workloads versus reference. This is a small observed end-to-end change, not a robust broad performance claim. Final optimized overhead remains 166.98%/145.85% versus legacy for these scenarios. Do not describe this measured implementation as lightweight. Detector-specific CSV formatting, process and host scheduling are included; final logs retain 17-digit numeric precision, historical formatting is unchanged. No aggressive further optimization was pursued to manufacture a speedup.

Persistent final reference/optimized state: 1472 bytes; Candidate 1 824, Candidate 2 1568. Detection mass 512, origin mass 512, evidence 160, configuration 64 additional bytes. Stack and stdio buffers excluded. Binary deltas versus legacy: reference {'text': 26786, 'data': 936, 'bss': 9616}; optimized {'text': 30106, 'data': 936, 'bss': 9616}. Executable BSS includes dormant research comparison states and is not isolated deployment memory. **Embedded WCET claim: NONE.**

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
