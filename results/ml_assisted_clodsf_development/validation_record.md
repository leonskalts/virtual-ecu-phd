# Validation record

Baseline HEAD: a340ca5cf0473d7dc572f7cd63e44fbc25b175a7.
3900 newly registered physical cases: TRAIN1800, CALIBRATION900, VALIDATION1200 (960fault/240benign,192faults per origin). 958 historical manifest records audited: zero configuration/profile/seed overlap. Protocol and manifest registered before execution. TRAIN fitting only; CAL Platt/alpha/gate/standalone operating point only. 15 model/source/protocol files locked before any validation execution. Lock hashes verified after evaluation.

No CAL configuration passed the strict gate (baseline itself had3/180benign alarm runs). The preregistered rejected diagnostic fallback linear/.05/G1 was frozen. Benign validation ran first: A0/A2/A3 each1/240. The single shared benign alarm has five confident-origin samples; no faulty run has a wrong confident origin. No threshold, model, gate, feature, scientific source or protocol change followed validation outcomes. No promotion; retained Triplex implementation unchanged.

All900 zero-mass CAL replay alarm/origin streams matched retained Triplex. Native C confidence parity checked on18900frames; maximum error 7.771561172376096e-16. Four targeted tests pass: qualification/bounds/native score; ML-only UNKNOWN localization; forbidden alarm/origin/metadata column exclusion; no future-sample dependence. Python compile and git diff --check pass. Full regression/48legacy/64RTL not run: user made these conditional on promotion, which failed. Historical full-suite results are not presented as a fresh regression.

The unrestricted standalone RBF scoring computation was interrupted and resumed using vectorized exact-kernel evaluation, without retraining or changing any model. Both kernels/targets passed cached-output parity on representative TRAIN cases; maximum margin error <1e-7 and binary decisions identical. This was a computational change before calibration selection and before validation; see vectorized_inference_parity.json. Selected standalone and provider are linear.

407 pre-existing scientific/configuration files and37244 historical files unchanged, including Hybrid/HETIA and prior evidence. GUI content preserved exactly as found (its pre-existing tracked modification remains). Production detector and build configuration unchanged. Experimental DS hook only in temporary replay build; ML provider is not enabled in retained production. Added research scripts/header/C/test and compact study artifacts remain untracked. No commit, push or final unseen execution.

Execution starts (UTC): {"CALIBRATION_started": "2026-10-04T13:04:35.329571+00:00", "TRAIN_started": "2026-10-04T12:59:29.917812+00:00", "VALIDATION_BENIGN_started": "2026-10-04T13:23:26.802566+00:00", "VALIDATION_started": "2026-10-04T13:24:26.072263+00:00"}.

Storage: all bulk runtime packets, per-frame features/margins/replay output and temporary build workspace deleted after summaries and post-hoc audit. Zero representative raw traces retained. Reproducibility uses campaign manifest, protocol, source/model locks, exported native parameters, case sufficient statistics and model artifacts.

Final git status:
```
 M presets/gui_session_state.json
?? docs/comparative_benchmark.md
?? include/analytical_thermal.h
?? include/ml_sensor_weak.h
?? include/multirate_memory.h
?? include/multirate_triplex.h
?? include/triplex_plus.h
?? include/triplex_plus_sequential.h
?? python/virtual_ecu/comparative_backends.py
?? results/clo_dsf_current/multirate_calibration_subgroups.csv
?? results/clo_dsf_current/multirate_calibration_summary.csv
?? results/clo_dsf_current/multirate_case_summary.csv
?? results/clo_dsf_current/multirate_execution_corrections.json
?? results/clo_dsf_current/multirate_findings.md
?? results/clo_dsf_current/multirate_host_benchmark.csv
?? results/clo_dsf_current/multirate_host_benchmark.json
?? results/clo_dsf_current/multirate_manifest.csv
?? results/clo_dsf_current/multirate_miss_causes.csv
?? results/clo_dsf_current/multirate_overhead.csv
?? results/clo_dsf_current/multirate_paired.csv
?? results/clo_dsf_current/multirate_protocol.md
?? results/clo_dsf_current/multirate_rate_comparison.csv
?? results/clo_dsf_current/multirate_reference_status.md
?? results/clo_dsf_current/multirate_regression.json
?? results/clo_dsf_current/multirate_retention.json
?? results/clo_dsf_current/multirate_selection.json
?? results/clo_dsf_current/multirate_train_subgroups.csv
?? results/clo_dsf_current/multirate_train_summary.csv
?? results/clo_dsf_current/multirate_validation_record.md
?? results/clo_dsf_current/multirate_validation_subgroups.csv
?? results/clo_dsf_current/multirate_validation_summary.csv
?? results/clo_dsf_triplex_final_unseen/
?? results/comparative_benchmark/
?? results/heterogeneous_observability_development/
?? results/ml_assisted_clodsf_development/
?? results/svm_only_root_cause_audit/
?? results/triplex_plus_development/
?? scripts/benchmark_clo_dsf_multirate.py
?? scripts/benchmark_heterogeneous_observability.py
?? scripts/benchmark_triplex_plus.py
?? scripts/export_ml_sensor_runtime.py
?? scripts/freeze_comparative_benchmark.py
?? scripts/regress_comparative_benchmark.py
?? scripts/regress_triplex_plus.py
?? scripts/report_clo_dsf_multirate.py
?? scripts/report_comparative_benchmark.py
?? scripts/report_heterogeneous_observability.py
?? scripts/report_ml_assisted_clodsf.py
?? scripts/report_triplex_plus.py
?? scripts/run_clo_dsf_multirate.py
?? scripts/run_comparative_benchmark.py
?? scripts/run_heterogeneous_observability.py
?? scripts/run_ml_assisted_clodsf.py
?? scripts/run_triplex_plus.py
?? scripts/select_ml_assisted_clodsf.py
?? scripts/select_triplex_plus.py
?? src/v7_3/analytical_thermal.c
?? src/v7_3/ml_sensor_weak.c
?? src/v7_3/multirate_memory.c
?? src/v7_3/multirate_triplex.c
?? src/v7_3/triplex_plus.c
?? src/v7_3/triplex_plus_sequential.c
?? tests/test_analytical_thermal.py
?? tests/test_comparative_backends.py
?? tests/test_ml_sensor_weak.py
?? tests/test_multirate_observability.py
?? tests/test_triplex_plus.py
?? tests/test_triplex_plus_sequential.py
```
