# IEEE origin-aware RF comparison

**One locked secondary cohort:** 1,200 faults (240 per origin) + 600 benign, zero overlap across991 historical sources. No post-result tuning or physical reruns. The original primary unseen, frozen robustness and qualified ten-method study remain unchanged.

## Binary and safety outcomes

| Method | Detection /1200 | Recall; Wilson95% CI | Benign /600 | Precision | Plant /645 | Silent | Median/P95 ms |
|---|---|---|---|---|---|---|---|
| CLOVER-ECU | 1124 | 93.67%; 92.14–94.91% | 0 | 100.00% | 645 | 0 | 0/167 |
| Origin RF | 1124 | 93.67%; 92.14–94.91% | 0 | 100.00% | 645 | 0 | 0/167 |
| Frozen SVM-INT | 1124 | 93.67%; 92.14–94.91% | 0 | 100.00% | 645 | 0 | 0/167 |

All three have identical per-origin detections: Memory235/240, Timing240/240, Communication240/240, Sensor/control232/240, Actuator177/240. Their common76 misses comprise5memory,8sensor/control and63actuator cases. Misses are not counted as correctly localized.

CLOVER versus RF: both1124, CLOVER-only0, RF-only0, neither76; exact McNemar p=1 with no discordance. RF versus frozen SVM has the same counts. The common-first-origin correctness comparison is also a tie: both1124 correct, neither method uniquely correct. These are observed ties, not statistical equivalence proofs.

**Paired latency differs despite identical medians/P95:** RF is100ms earlier in70 timing cases;1054 cases tie; CLOVER is earlier in0. Frozen SVM shares CLOVER latency on all1124 detections. No latency parameters were changed after outcomes.

## Localization on own and common detections

| Method | Set | Detected cases | First localized | First correct | First wrong | First UNKNOWN | Runtime localized accuracy | Wrong-origin runs/samples | Runtime UNKNOWN |
|---|---|---|---|---|---|---|---|---|---|
| CLOVER-ECU | OWN | 1124 | 1124 | 1124 | 0 | 0 | 100.0000% | 0/0 | 1858/437563 (0.42462%) |
| CLOVER-ECU | COMMON_DETECTED | 1124 | 1124 | 1124 | 0 | 0 | 100.0000% | 0/0 | 1858/437563 (0.42462%) |
| Origin RF | OWN | 1124 | 1124 | 1124 | 0 | 0 | 100.0000% | 0/0 | 34/445895 (0.00763%) |
| Origin RF | COMMON_DETECTED | 1124 | 1124 | 1124 | 0 | 0 | 100.0000% | 0/0 | 34/445895 (0.00763%) |

Own and common detected sets are identical here:1124 cases. First-alarm coverage/conditional accuracy are100% for both, but first-correct coverage of ALL injected faults is1124/1200=93.67%. Runtime accuracy is conditional on localized alarm samples and uses run-origin truth, not active-frame classification labels. SVM is binary and has no origin-localization head.

**Matched alarm timestamps:** on433,523 timestamps where both methods alarm within the common detected cases, CLOVER has433,354 correct localized samples and169 UNKNOWN; RF has433,489 correct and34 UNKNOWN. Both have zero wrong samples. This separates abstention from different alarm durations; it does not prove that either uncertainty estimate is statistically calibrated.

## RF multiclass first-outcome confusion

Rows are true run classes; NORMAL in a fault row means no detected post-onset alarm. UNKNOWN denotes an alarm without a confident origin. This includes all1800 cases and is not an active-frame confusion matrix.

| True / predicted | NORMAL | MEMORY | TIMING | COMMUNICATION | SENSOR_CONTROL | ACTUATOR | UNKNOWN |
|---|---|---|---|---|---|---|---|
| NORMAL | 600 | 0 | 0 | 0 | 0 | 0 | 0 |
| MEMORY | 5 | 235 | 0 | 0 | 0 | 0 | 0 |
| TIMING | 0 | 0 | 240 | 0 | 0 | 0 | 0 |
| COMMUNICATION | 0 | 0 | 0 | 240 | 0 | 0 | 0 |
| SENSOR_CONTROL | 8 | 0 | 0 | 0 | 232 | 0 | 0 |
| ACTUATOR | 63 | 0 | 0 | 0 | 0 | 177 | 0 |

The CLOVER matrix is identical; the common-detected matrix contains only the235/240/240/232/177 correct fault-class diagonal counts. Full first/runtime matrices and paired/common-alarm tables accompany this report.

## Fairness and provenance

The RF uses the same trusted upstream sensing/diagnostic interface and frozen providers:67 packet fields become174 causal features, including acquisition timing, actual actuator responses, ambient/control context, independent C, memory probing, integrity status and qualified provider provenance. No CLOVER predictions, DS belief/direct-origin state, injected labels or offline plant outcomes are inference inputs. Absolute timestamp ages and finite windows are RF feature choices, not copied CLOVER temporal state. Shared information access does not imply identical representations/capacity or that all upstream fields are used equally. The previous ten-method study remains a qualified system comparison.

RF fitting uses54,635 labeled frames from the exact2400 TRAIN cases of benign_alarm_development. Its2400 CAL cases are also the same cohort that selected retained CLOVER confirmation. Class labels fit trees only on TRAIN; CAL labels select thresholds/parameters, not trees; unseen labels score outputs only. The predefined four-member RF hyperparameter family selected200trees/depth12/minimumleaf16. Locked alarm score is1-P(NORMAL)>0.9155568509788313; origin requires conditional fault-class probability>=0.7 (margin>=0). CAL produced1126detections,0/1200benign,1126correct first origins and zero wrong runtime origins. Thresholds stayed fixed for the secondary cohort.

Frozen SVM/scaler/default margin0 remains unchanged and uses its original41-feature representation. It is a binary reference, not an origin-aware full-schema challenger.

The sole native executable change is a logging-only temporary adapter linked to unchanged frozen detector/provider objects. All original native metrics, physical/runtime hashes and original evidence/SVM-input streams matched on24 predetermined authorized TRAIN parity cases. The original executable and all frozen source/config/model/result files remain byte-identical. Instrumentation is not a new detector candidate. Exact patch/object/executable hashes are recorded.

Lossless compressed runtime input packets, provider streams and separately identified predictions are retained for retrospective replay; bulk simulator/plant traces were deleted. The stored-output audit checked all1800 members without refitting, model inference or new physical execution. A future replay is not new unseen evidence.

## Interpretation

**Strongest finding:** the origin-aware RF matches CLOVER binary detection, benign behavior, plant coverage and first-origin accuracy on this cohort. It has70 earlier timing detections and fewer UNKNOWN samples, including on shared alarm timestamps. There is no demonstrated CLOVER superiority or unique localization capability over this challenger.

**Limits:** one simulator, shared engineered providers and related fault-family templates; zero exact overlap is not independent fault-mechanism novelty. The strict empirical CAL zero-error constraints are not field guarantees. Active/previous99ms training targets and run-origin runtime scoring serve different purposes. Missing/unexcited/unsampled faults remain, and the protected integrity boundary does not establish pre-protection or consistent data+witness corruption coverage. Scheduler counters and operating context remain potential correlates despite excluding absolute elapsed time. RF and CLOVER differ in temporal representation; no broad ranking of DS versus RF follows.

RF batch inference plus alarm/origin gating cost6.3393 microseconds/frame over2,161,800frames, excluding feature/provider generation. No comparable isolated native CLOVER timing or embedded WCET is measured.

Regression:366unit tests, build, compile, diff check,48legacy,64RTL passed. Frozen results, Hybrid/HETIA, GUI and prior scientific files unchanged. No commit or push. RF is an evaluated challenger; no production detector is replaced.
