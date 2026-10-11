# IEEE secondary multi-baseline benchmark

CLOVER-ECU is the publication name of frozen refined A2; source/result identifiers remain unchanged. This is a new secondary cohort, not a replacement or extension of the primary final unseen.

| Method | Detection (95% Wilson CI) | Benign /600 | Precision | Plant | Silent | Median/P95 ms |
|---|---|---|---|---|---|---|
| Threshold OR | 1124/1200; 93.67% (92.14–94.91) | 7 | 99.38% | 645/645 | 0 | 0.0/167.0 |
| Weighted Sum | 892/1200; 74.33% (71.79–76.72) | 0 | 100.00% | 522/645 | 123 | 0.0/200.0 |
| Plain DS | 1124/1200; 93.67% (92.14–94.91) | 7 | 99.38% | 645/645 | 0 | 0.0/167.0 |
| EWMA | 1078/1200; 89.83% (87.99–91.42) | 0 | 100.00% | 628/645 | 17 | 100.0/271.95 |
| CUSUM | 1094/1200; 91.17% (89.43–92.64) | 0 | 100.00% | 628/645 | 17 | 100.0/300.0 |
| Logistic Regression | 1124/1200; 93.67% (92.14–94.91) | 0 | 100.00% | 645/645 | 0 | 0.0/167.0 |
| Random Forest | 1129/1200; 94.08% (92.60–95.28) | 0 | 100.00% | 645/645 | 0 | 0.0/200.0 |
| Frozen SVM-INT | 1124/1200; 93.67% (92.14–94.91) | 0 | 100.00% | 645/645 | 0 | 0.0/167.0 |
| Original Triplex A0 | 1021/1200; 85.08% (82.96–86.99) | 7 | 99.32% | 586/645 | 59 | 0.0/1000.0 |
| CLOVER-ECU | 1124/1200; 93.67% (92.14–94.91) | 0 | 100.00% | 645/645 | 0 | 0.0/167.0 |

All decision backends share frozen provider preprocessing including integrity and M2. OR/WS/DS/EWMA/CUSUM intentionally reduce the shared runtime input to six bounded provider streams; supervised methods receive the original 41 runtime features. This equal provider availability is not an identical feature representation or a raw-signal algorithm benchmark. No A2 alarm/origin or metadata is an inference input. Original A0 is an architecture ablation lacking the additions.

OR and Plain DS use original fixed .5 criteria; WS and sequential baselines have CAL-selected thresholds. LR/RF use exactly the original SVM TRAIN configurations/frame sampling, and original CAL configurations; SVM parameters/threshold are untouched. Selection and evaluation cohort were locked before secondary outcomes.

EWMA and CUSUM monitor anomaly-strength streams (not Gaussian physical residuals); no theoretical average-run-length claim. LR/RF/EWMA/CUSUM/SVM have no localization head. OR/WS/DS retain existing limited origin rules; detailed conditional localization and errors are reported separately.

Detection uses the established first post-onset rising edge. Sustained pre-onset alarms can mask later detection; benign alarms and precision must be read with recall. Latency is conditional on detected runs; paired jointly detected faster/equal/slower counts are in paired.csv.

Exact McNemar p-values and Holm corrections are descriptive for correlated simulator families. A greater raw count alone is not a superiority claim. Host Python batch overhead is not embedded WCET and cannot be ranked against unmeasured native A2. Common-mode corruption of both data and trusted witness, physical pre-protection faults, field reliability and independent simulator validation remain outside coverage.

Historical comparative results, primary integrity_final_unseen, frozen_robustness and this secondary benchmark remain separate evidence; no cross-cohort subtraction as paired improvement.

Strict full-feature equality does not apply to the strength-only methods; see [pre-evaluation qualification](observability_scope.md) and [findings](findings.md).
