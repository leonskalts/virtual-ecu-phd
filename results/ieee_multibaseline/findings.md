# IEEE multi-baseline benchmark — CLOVER-ECU

**One locked secondary cohort:** 1,200 faults (240/origin) + 600 benign, zero overlap across 989 audited historical sources. Frozen primary unseen and robustness results are unchanged. No secondary reruns or tuning. Ten methods evaluated.

## Main comparison

| Method | Detection /1200 | Rate; Wilson 95% CI | Benign /600 | Precision | Plant /645 | Median/P95 ms |
|---|---|---|---|---|---|---|
| Threshold OR | 1124 | 93.67%; 92.14–94.91% | 7 | 99.38% | 645 | 0/167 |
| Weighted Sum | 892 | 74.33%; 71.79–76.72% | 0 | 100.00% | 522 | 0/200 |
| Plain DS | 1124 | 93.67%; 92.14–94.91% | 7 | 99.38% | 645 | 0/167 |
| EWMA | 1078 | 89.83%; 87.99–91.42% | 0 | 100.00% | 628 | 100/271.95 |
| CUSUM | 1094 | 91.17%; 89.43–92.64% | 0 | 100.00% | 628 | 100/300 |
| Logistic Regression | 1124 | 93.67%; 92.14–94.91% | 0 | 100.00% | 645 | 0/167 |
| Random Forest | 1129 | 94.08%; 92.60–95.28% | 0 | 100.00% | 645 | 0/200 |
| Frozen SVM-INT | 1124 | 93.67%; 92.14–94.91% | 0 | 100.00% | 645 | 0/167 |
| Original Triplex A0 | 1021 | 85.08%; 82.96–86.99% | 7 | 99.32% | 586 | 0/1000 |
| CLOVER-ECU | 1124 | 93.67%; 92.14–94.91% | 0 | 100.00% | 645 | 0/167 |

**Fairness qualification:** strict full-runtime comparison is CLOVER versus LR/RF/frozen SVM-INT; the three learned methods use the same 41 features, original authorized TRAIN/CAL splits and 46,315 training frames. Classical OR/WS/DS/EWMA/CUSUM receive the common integrity/M2-enriched provider strengths, but discard explicit integrity PASS and other raw/provenance features. Their outcomes cannot isolate decision-rule quality under identical sufficient information. This qualification was locked before secondary outcomes: see [observability scope](observability_scope.md). A0 is solely an architecture ablation. No excluded execution methods; five strength-only methods excluded from strict full-feature equality claims.

## Same-case paired fault detections

| Comparator | Both | CLOVER only | Comparator only | Neither | Exact McNemar p | Holm p |
|---|---|---|---|---|---|---|
| Threshold OR | 1124 | 0 | 0 | 76 | 1 | 1 |
| Weighted Sum | 892 | 232 | 0 | 76 | 2.898e-70 | 2.318e-69 |
| Plain DS | 1124 | 0 | 0 | 76 | 1 | 1 |
| EWMA | 1078 | 46 | 0 | 76 | 2.842e-14 | 1.99e-13 |
| CUSUM | 1094 | 30 | 0 | 76 | 1.863e-09 | 1.118e-08 |
| Logistic Regression | 1124 | 0 | 0 | 76 | 1 | 1 |
| Random Forest | 1124 | 0 | 5 | 71 | 0.0625 | 0.3125 |
| Frozen SVM-INT | 1124 | 0 | 0 | 76 | 1 | 1 |
| Original Triplex A0 | 1021 | 103 | 0 | 76 | 1.972e-31 | separate ablation |

CLOVER has higher detected-run coverage than the selected WS/EWMA/CUSUM configurations, with Holm-adjusted paired p<0.05. These are provider-strength comparisons, not proof of algorithmic superiority with identical feature information. The A0 architecture gain is 103/1200 = 8.5833 percentage points, with zero detections lost and 59 additional plant-propagating cases detected.

**No superiority over SVM, LR or RF:** SVM and LR tie CLOVER case-for-case. RF detects five additional runs and loses none: raw detection favors RF, exact p=0.0625, Holm p=0.3125. No claim of statistical equivalence or proof of no difference follows. All five RF-only runs are in one template family and are unexcited pump-degradation cases without recorded plant propagation (see `rf_only_posthoc.csv`); alarms occur during the active interval. Keep the detections in the primary scoring. They do not establish idle mechanical-health observability: matched healthy feature traces were not retained and no new control experiments were run, so a context association cannot be excluded. The five clustered cases are particularly weak support for an independent-sample significance interpretation.

CLOVER/OR/DS share all 1,124 detections, but OR/DS each alarm on 7/600 benign cases versus zero for CLOVER. Exact benign p=0.015625, Holm p=0.125: report the numerical reduction without a multiplicity-adjusted significance claim. The other new methods and frozen SVM also have zero benign alarms here. Zero observed alarms is not zero population risk.

## Safety, timing and localization

CLOVER per-origin detections: Memory 235/240; Timing 240/240; Communication 240/240; Sensor/control 232/240; Actuator 177/240. RF differs only on Actuator (182/240). All per-origin rates/CIs and method-specific safety counts are in `per_origin.csv`.

CLOVER, OR, DS, LR, RF and SVM detect 645/645 plant-propagating cases; WS misses 123, EWMA and CUSUM each miss 17; A0 misses 59. CLOVER has 76 remaining misses. No extra plant detection is obtained by RF. Precision is 100% for all methods except OR/DS (99.38%) and A0 (99.32%), conditional on this fault-heavy cohort prevalence.

CLOVER first-localization coverage and accuracy are 1124/1124 (100% among detections; 93.67% of all injected faults). Runtime localized accuracy 100%, zero wrong-origin runs/samples; runtime UNKNOWN 0.42327%. OR/DS first localizations are correct but each has 29 fault runs/90 runtime samples with wrong origins. WS and A0 have zero wrong-origin samples, with lower detection. Binary classifiers and EWMA/CUSUM provide localization N/A. `localization.csv` reports fault-run denominators, and `summary.csv` additionally includes benign alarm behavior.

CLOVER median/P95 latency is 0/167 ms. All shared detections have identical latency to OR, WS, DS, LR, RF and SVM. The higher RF marginal P95 (200 ms) reflects its extra detections: it is not a paired latency advantage for CLOVER. CLOVER is earlier on all jointly detected EWMA (1078) and CUSUM (1094) cases and 191 A0 cases; remaining 830 shared A0 detections tie.

## Measured overhead

| Backend | Host CPU microseconds/frame |
|---|---|
| Threshold OR | 0.0661 |
| Weighted Sum | 0.2172 |
| Plain DS | 2.3275 |
| EWMA | 1.6395 |
| CUSUM | 0.0833 |
| Logistic Regression | 0.3159 |
| Random Forest | 4.0456 |
| Frozen SVM-INT | 0.2587 |

2,161,800 frames per backend, one inference pass. Measurements exclude shared evidence/features, simulator/logging and scoring; Python/library implementation and vectorized batching differ. Native A0/CLOVER overhead was not isolated in the unchanged executable and is N/A. No WCET or cross-language/embedded speed ranking.

## Scope and reproducibility

No fault metadata or offline plant labels enters inference. Frozen executable SHA256 `4cf5884c0989cd8f31bc6ee6cf824b5fe96ca4bc8d85c8ebc299ac301fb7d7e3`; frozen SVM SHA256 `784738ad33c8459664f313e7ea908fc58da905e071bf70246b503ae13b67119c`. `protocol.md`, registration/locks, selection grid/model, environment, source/preservation hashes and compact case metrics support reproduction. One pre-CAL reporting correction removed an unused zero plant-count placeholder; no inference or selection changed. The secondary cohort uses new profiles/seeds with original subtype/parameter allocation; it is new configurations, not independent fault mechanisms.

Strongest positive: the refined architecture gains 103 detections and all 59 missing plant detections over A0 with no benign alarms or wrong origins; it ties two fair full-feature classifiers while providing origin diagnosis. Strongest negative: it does not beat the best raw recall (RF), nor SVM/LR, and the classical comparison loses explicit provenance information.

The primary final unseen, historical benchmark, development calibration and frozen robustness remain distinct evidence. Results cannot establish field performance, physical/pre-protection integrity coverage, shared data+witness resilience, or general backend superiority. Wilson/McNemar figures are descriptive for grouped simulator cohorts.

Full regression: 362 unit tests, build, Python compile, diff check, 48 legacy and 64 RTL passed; prior scientific/results/Hybrid/HETIA/GUI hashes unchanged. No commit/push. No raw traces retained. See `validation_record.md`.
