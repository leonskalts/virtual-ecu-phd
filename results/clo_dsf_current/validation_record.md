# Benign-only thermal contract experiment

Contract frozen 2026-09-24T13:16:31.224964+00:00 before any fault evaluation.240 clean TRAIN profiles;120 separate benign VALIDATION profiles;720 fault profiles (480 TRAIN/240 VALIDATION). Total1080 unique simulations.

Protocol: fit ridge(.1) six-coefficient rate model only to measured benign one-second differences. Inputs:intercept/load/speed/ambient/mean actual pump-fan action/previous predicted temperature. Collapse pump/fan into one feature; no thermal plant equations/constants copied. Free-run20s from a measured conditional baseline; do not learn a measured long-term slope. Bound=1.25*maximum TRAIN20s prediction error+0.20C. Runtime requires5 same-sign violating ticks, uses2C normalization and existing global thresholds. Every20s the relative evolution window expires and reanchors; constant pre-existing offsets are not identifiable. Outside calibrated context plus5% margin:abstain. Recover when residual returns inside envelope. No tuning on benign VALIDATION or any faults.

A0=current (existing300ms forecast); contract-only disables only300ms predictor; combined retains it. Original sensor primitives and every other channel/causal rule are common. Research executables built in temporary storage from recorded source and this script; production CURRENT unchanged unless retention criteria pass.

Predeclared retention:at least25% slow-drift detection on VALIDATION, fewer silent plant misses, at most1 benign validation alarm, no wrong origin, no A0 fault detection losses, full effective-memory and preserved origin detection. No cosmetic TRAIN gain retained.

Contract fits 28800 one-second samples; bound=5.940322998641041C.

Freeze identities:
```json
{
  "src/v7_3/clo_dsf_revised.c": "9c46e5f7d71ab7bbd09e0d5528aeada0bfa4bfb69d2e7452f528b585e9c75901",
  "include/clo_dsf_revised.h": "54583131ff8723d465585c78b712b29949a11fb2e5290993794c8c5f6140d3f5",
  "src/v7_3/revised_runtime.c": "8bb9e755499fad47e4aa5dc39d972efa5f3f1c6cfe4d7597938bb987e31b9e4e",
  "scripts/run_clo_dsf_benign_contract.py": "c89104bce5b31ce797a8a4360f192e596fa0d3898b20199b464930934ca3b41b",
  "results/clo_dsf_current/thermal_contract.cfg": "ff206728eb72b4d6394b9f42a8434cba8b51cc0694f6b5512be6eec167c8fdee",
  "results/clo_dsf_current/benign_contract_dataset_manifest.csv": "0f216bfb71bd081ce40e08534cc012453e4593dc276182b62d602632ba07ba49"
}
```

1080 unique simulations complete. No fault-driven fitting/tuning. All frozen identities unchanged. Contract retention gate: False.

## Final rejection, regression and preservation

Contract rejected: VALIDATION drift0/36 for A0/contract-only/combined; combined
silent misses54 equal A0; contract-only63. Benign0/120 all three. Combined adds624
UNKNOWN alarm samples with no additional detection; no wrong confident origins.
No monitor was installed and no scientific production source was changed.
Frozen contract is retained as a rejected experimental artifact, not activated.
All recorded contract/scientific/script/manifest hashes remain unchanged.

One final full regression: build/compile/diff check PASS;308 tests PASS;
48 legacy PASS;64 RTL PASS. No reruns or parameter search. Every initially tracked
file outside CURRENT results, including CURRENT executable and prior final-unseen
artifacts, matches its original hash. Hybrid/HETIA and GUI preserved. The two
historical executables rebuilt during regression were restored to verified original
Git bytes. No commit/push or unseen holdout. Eight compressed representative traces.

GUI SHA256 3fdf2d807ea8661def7e447ff32be0ccf46d70e160e28390bff81aeffbab957a
CURRENT core SHA256 9c46e5f7d71ab7bbd09e0d5528aeada0bfa4bfb69d2e7452f528b585e9c75901

Final git status:
```
 M docs/clo_dsf_current.md
 M include/clo_dsf_revised.h
 M presets/gui_session_state.json
 M results/clo_dsf_current/case_summary.csv
 D results/clo_dsf_current/comparison.csv
 D results/clo_dsf_current/confidence_summary.csv
 D results/clo_dsf_current/configuration_manifest.csv
 D results/clo_dsf_current/confusion_matrix.csv
 D results/clo_dsf_current/current_0000_trace.csv.gz
 D results/clo_dsf_current/current_0036_trace.csv.gz
 D results/clo_dsf_current/current_0060_trace.csv.gz
 D results/clo_dsf_current/current_0087_trace.csv.gz
 D results/clo_dsf_current/current_0099_trace.csv.gz
 D results/clo_dsf_current/current_0105_trace.csv.gz
 D results/clo_dsf_current/current_0585_trace.csv.gz
 D results/clo_dsf_current/current_0708_trace.csv.gz
 M results/clo_dsf_current/findings.md
 D results/clo_dsf_current/latency_tail_summary.csv
 M results/clo_dsf_current/localization_summary.csv
 D results/clo_dsf_current/memory_summary.csv
 D results/clo_dsf_current/miss_classification.csv
 D results/clo_dsf_current/miss_classification_summary.csv
 D results/clo_dsf_current/origin_summary.csv
 D results/clo_dsf_current/paired_comparison.csv
 D results/clo_dsf_current/runtime_confusion_matrix.csv
 D results/clo_dsf_current/runtime_localization_summary.csv
 M results/clo_dsf_current/validation_record.md
 D results/clo_dsf_current/weak_bias_inspection.csv
 M src/v7_3/clo_dsf_revised.c
 M src/v7_3/revised_runtime.c
 M tests/clo_revised_unit.c
 M tests/test_clo_dsf_revised.py
 M virtual_ecu_v7_3
?? results/clo_dsf_current/ablation_comparison.csv
?? results/clo_dsf_current/benign_contract_dataset_manifest.csv
?? results/clo_dsf_current/characterization_summary.csv
?? results/clo_dsf_current/confusion_summary.csv
?? results/clo_dsf_current/contract_0000_trace.csv.gz
?? results/clo_dsf_current/contract_0024_trace.csv.gz
?? results/clo_dsf_current/contract_0042_trace.csv.gz
?? results/clo_dsf_current/contract_0060_trace.csv.gz
?? results/clo_dsf_current/contract_0072_trace.csv.gz
?? results/clo_dsf_current/contract_0090_trace.csv.gz
?? results/clo_dsf_current/contract_0102_trace.csv.gz
?? results/clo_dsf_current/contract_benign_0240_trace.csv.gz
?? results/clo_dsf_current/thermal_contract.cfg
?? results/clo_dsf_current/validation_summary.csv
?? results/clo_dsf_final_unseen/
?? scripts/run_clo_dsf_benign_contract.py
?? scripts/run_clo_dsf_final_unseen.py
?? scripts/run_clo_dsf_sensor_response.py
?? scripts/run_clo_dsf_slow_bias_development.py
?? tests/test_clo_dsf_sensor_response.py
```
