# Heterogeneous observability development

Retained: **TRIPLEX**. Ready for a new unseen campaign: **False**. No detector promotion, commit, push or unseen run is implicit in this study.

## Scientific result

A0 618/720; A1 631/720; A2 618/720; A3 631/720. Fair SVM 677/720 with 53/180 benign alarms. A3 benign alarms 0/180; plant 363/394; wrong-origin runs/samples 0/0. No raw-detection superiority is claimed without the paired counts.

The analytical provider yields no incremental detections. Memory and analytical gains are assigned without double counting: memory if A1 already detects the A3-only-over-A0 case, analytical otherwise. Component comparisons A3/A1 and A2/A0 are provided independently. All model and classifier choices were fixed before validation. The retained Triplex scientific implementation remains unchanged; new provider/runner files are unpromoted research artifacts.

## Analytical quality and uncertainty

Selected P1, initialization 87.941666 C, BENIGN CAL RMS-equivalent sigma 4.200011 C, diagnostic envelope 11.743369 C. Untouched BENIGN validation pooled A/B/aligned-C errors: RMSE 3.816701 C, MAE 2.941485 C, P95 8.137742 C, worst 12.350700 C; envelope coverage 99.98873%. These errors are relative to independent measured outputs, not hidden plant truth. Member-specific/regime-specific statistics and RMS-equivalent coverages are in benign_model_validation.csv. A common wide bound conservatively covers unmeasured effects and model discrepancy; it cannot establish the precision needed to reliably distinguish weak0.49C events. Do not mistake calibration max-envelope coverage for a guaranteed physical uncertainty bound.

The state API has no coolant input. Predictor initialization is one fixed benign-TRAIN estimate, not a runtime acquisition. Commands affect the next integration interval. A pre-validation timing correction replaced retrospective current-command use with previous-command use; same benign TRAIN identification/CAL bounds were repeated and incomplete SVM fitting discarded. The correction and superseded parameters are recorded explicitly, not hidden. No validation result existed then. The serialization failure during the initial parameter write was repaired without changing its selection rule. Physical simulations were collected once per registered case; deterministic development inference was replayed after this implementation correction.

Benign validation was executed, quantified and written before the720fault validation executions. Its outcomes did not change model coefficients, uncertainty, topology, thresholds, localization or classifier. No new holdout was run.

## Limitations and preserved semantics

The new operating profiles exercise the frozen detector beyond historical validation. Wrong-origin runs present in A3: []; cases with increased wrong-origin samples relative to A0: []. Do not hide inherited baseline errors or describe historical zero-error performance as a guarantee under new profiles. No relaxed benign/localization gate is used.

Cold-ambient startup is covered under the unchanged simulator's fixed warm-engine initial state; true cold-soak initialization is unsupported and not claimed. Unexcited-throughout pump degradation remains physically unobservable without additional actuator health information. C-only diagnostic faults and ABC common-mode faults remain in the balanced fault denominator; subgroup counts are reported separately. Slow drift includes independent A, B and C domains. A+B and global A+B+C are distinct.

The predictor is analytical redundancy, not a perfect fourth sensor. It uses commands, not hidden realized thermal truth, and its global residual cannot distinguish every physical-model error from common-mode sensing. Coherent all-member analytical discrepancy is UNKNOWN unless an earlier independent origin exists. All other Triplex fusion/threshold/provenance rules remain unchanged.

## Reproducibility and promotion

Protocol, manifest, overlap audit, source/model validation lock and per-case sufficient statistics are retained. Zero historical configuration/profile/seed overlap was verified. A0 and A1 alarm streams match physical collection exactly during offline replay; all variants use the same packets. Predictors fit only benign TRAIN; uncertainty only benign CAL; the fair SVM receives all analytical runtime inputs/features and no truth metadata. Baseline SVM has no localization model.

Promotion gates and exact paired tests are in retention.json and paired_statistics.csv. Confidence intervals/McNemar are descriptive because configurations are grouped and deterministic. No per-case threshold or fault-specific rescue was added. Targeted C unit/independence, memory, Triplex symmetry, sensor-C independence, Python compile and diff checks passed. Full48legacy/64RTL promotion regression is not triggered when no candidate qualifies. 37244historical protected files, including Hybrid/HETIA evidence, were hash-verified. Existing GUI modifications were preserved byte-for-byte.

Host timing is an incremental diagnostic-kernel benchmark on eight already-seen TRAIN streams, not an embedded WCET or full-control-loop estimate. See overhead.md for state, operation counts and timing scope. Temporary binary runtime packets and feature tapes are removed after scoring; no bulk traces retained.

## Additional uncertainty accounting

Analytical evidence adds1,049 UNKNOWN alarm samples without adding any detected fault run or improving plant coverage. A3 has2,049/190,919 UNKNOWN alarm samples (1.073%), versus A1 1,000/189,870 (0.527%). Confident localization accuracy remains100%; this should not be mistaken for unchanged localization coverage. The additional uncertain alarms provide no promotion benefit. Gain subgroup slices are in gain_summary.csv; overlapping domain/shape slices must not be summed.
