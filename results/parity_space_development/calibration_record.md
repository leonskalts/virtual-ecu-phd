# Calibration and execution record

The primary endpoint is an alarmed benign run, not a sample. For n=600 benign CAL episodes, sort R_j=max_t max_(h,w) G_h,w and use strict G>R_(k), k=ceil((n+1)*.99)=595. This includes the time, direction and scale maximum in calibration. Ties count as non-exceedances. The empirical zero-exceedance descriptive threshold is the observed maximum; it does not promise zero population false alarms. Descriptive 0.5%, 1%, 2%, 5% thresholds use the finite-sample rank rule, without post-validation adjustment.

The covariance estimator is selected using BENIGN TRAIN/CAL distribution stability, not faults. CAL reuse for choosing the covariance estimator, grouped profiles, temporal dependence and deterministic scenarios mean the order-statistic construction is an empirical calibration rule here, not an unconditional exchangeable conformal-coverage theorem. Actual run-level validation alarms and confidence intervals are reported. Covariance parameters themselves are fitted only to benign TRAIN.

Fault labels enter offline SVM fitting/scoring and post-hoc reporting only. Runtime parity input contains only timestamp, A-C, B-C and qualification. SVM-R has all six prior cross-layer evidence streams, availability, causal means/maxima and raw parity/qualification; SVM-P adds exactly the deterministic parity statistics. Both receive the faster memory diagnostic observations. Neither receives final DS decisions, fault IDs, injection magnitude, scenario ID, hidden truth or future samples.

The memory extension is the unchanged existing 250-ms-average alternating200/300ms probe. A0/A1 retain their original memory observations; A2/A3 and SVM get the candidate observations. Atomic probes assert unchanged stored register after restoration. Sensors, controller and plant are shared and unchanged. No staggered acquisition, ML provider, analytical predictor, sequential latch or modified DS rule is enabled.

Four new targeted tests pass: Cholesky score agreement/finite handling/qualification; forbidden-feature separation; future-sample independence; actual DS UNKNOWN output when ambiguous parity has no physical origin support. Final metrics, checks and immutable hash verification will be appended after validation.

Final completion

{
  "regression": {
    "build": 0,
    "compile": 0,
    "tests": 0,
    "diff_check": 0,
    "legacy": 48,
    "rtl": 64,
    "historical_unchanged": 37244,
    "Triplex_symmetry": true,
    "Sensor_C_independence": true,
    "Hybrid_HETIA_unchanged": true,
    "GUI_unchanged": true,
    "locked_science_unchanged": true
  },
  "numerical": {
    "frames": 1801500,
    "all_finite": true,
    "GLRT_le_Mahalanobis": true,
    "C_AB_scores_identical": true,
    "max_svm_margin_parity_error": 2.02136085647453e-11
  },
  "performance": {
    "A0": {
      "TRAIN": 0.82625,
      "CALIBRATION": 0.8255555555555556,
      "VALIDATION": 0.8316666666666667
    },
    "A1": {
      "TRAIN": 0.83,
      "CALIBRATION": 0.8355555555555556,
      "VALIDATION": 0.85
    },
    "A2": {
      "TRAIN": 0.8425,
      "CALIBRATION": 0.8377777777777777,
      "VALIDATION": 0.8466666666666667
    },
    "A3": {
      "TRAIN": 0.84625,
      "CALIBRATION": 0.8477777777777777,
      "VALIDATION": 0.865
    },
    "SVM-R default": {
      "TRAIN": 0.89375,
      "CALIBRATION": 0.8866666666666667,
      "VALIDATION": 0.9
    },
    "SVM-R matched": {
      "TRAIN": 0.046875,
      "CALIBRATION": 0.04,
      "VALIDATION": 0.03666666666666667
    },
    "SVM-P default": {
      "TRAIN": 0.908125,
      "CALIBRATION": 0.9044444444444445,
      "VALIDATION": 0.9191666666666667
    },
    "SVM-P matched": {
      "TRAIN": 0.056875,
      "CALIBRATION": 0.058888888888888886,
      "VALIDATION": 0.060833333333333336
    }
  },
  "gain_robustness": {
    "TRAIN": {
      "gained": 6,
      "by_amplitude": {
        "0.49": 2,
        "-0.49": 2,
        "0.43": 2
      },
      "by_kind": {
        "step": 6
      },
      "by_domain": {
        "B": 1,
        "C": 5
      },
      "by_phase": {
        "37": 1,
        "3": 3,
        "19": 2
      },
      "unknown": 6
    },
    "CALIBRATION": {
      "gained": 9,
      "by_amplitude": {
        "0.46": 1,
        "-0.49": 2,
        "0.49": 3,
        "0.52": 3
      },
      "by_kind": {
        "step": 9
      },
      "by_domain": {
        "C": 4,
        "AB": 3,
        "B": 2
      },
      "by_phase": {
        "11": 4,
        "43": 2,
        "61": 3
      },
      "unknown": 9
    },
    "VALIDATION": {
      "gained": 22,
      "by_amplitude": {
        "0.49": 16,
        "-0.49": 6
      },
      "by_kind": {
        "step": 22
      },
      "by_domain": {
        "B": 8,
        "AB": 9,
        "C": 5
      },
      "by_phase": {
        "17": 11,
        "53": 6,
        "83": 5
      },
      "unknown": 22
    }
  },
  "extra_benign_alarm": [
    {
      "run_id": "parity_5084",
      "workload": "static_target",
      "legal_reference_magnitude": -0.32,
      "legal_reference_duration": 1100,
      "first_alarm_ms": 31800,
      "G": 162.37465619490445,
      "window": 8,
      "direction": 0,
      "strength": 0.25,
      "origin": "UNKNOWN"
    }
  ]
}

All1500 CAL cases reproduced the baseline and memory-only alarm/origin streams in replay, and parity statistics matched the native series implementation. The scientific lock covers14files and remains unchanged. No validation rerun or retuning. Full regression was run once because the independent memory extension was retained under the registered rule.348tests passed. Runtime state/config overhead is224/72bytes; existing memory diagnostic state16bytes is reused. No embedded WCET claim.

Final git status (pre-existing GUI modification preserved):
```
 M presets/gui_session_state.json
?? docs/comparative_benchmark.md
?? include/analytical_thermal.h
?? include/ml_sensor_weak.h
?? include/multirate_memory.h
?? include/multirate_triplex.h
?? include/triplex_parity.h
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
?? results/parity_space_development/
?? results/svm_only_root_cause_audit/
?? results/triplex_plus_development/
?? scripts/benchmark_clo_dsf_multirate.py
?? scripts/benchmark_heterogeneous_observability.py
?? scripts/benchmark_parity_space.py
?? scripts/benchmark_triplex_plus.py
?? scripts/export_ml_sensor_runtime.py
?? scripts/freeze_comparative_benchmark.py
?? scripts/regress_comparative_benchmark.py
?? scripts/regress_parity_space.py
?? scripts/regress_triplex_plus.py
?? scripts/report_clo_dsf_multirate.py
?? scripts/report_comparative_benchmark.py
?? scripts/report_heterogeneous_observability.py
?? scripts/report_ml_assisted_clodsf.py
?? scripts/report_parity_space.py
?? scripts/report_triplex_plus.py
?? scripts/run_clo_dsf_multirate.py
?? scripts/run_comparative_benchmark.py
?? scripts/run_heterogeneous_observability.py
?? scripts/run_ml_assisted_clodsf.py
?? scripts/run_parity_space.py
?? scripts/run_triplex_plus.py
?? scripts/select_ml_assisted_clodsf.py
?? scripts/select_parity_space.py
?? scripts/select_triplex_plus.py
?? src/v7_3/analytical_thermal.c
?? src/v7_3/ml_sensor_weak.c
?? src/v7_3/multirate_memory.c
?? src/v7_3/multirate_triplex.c
?? src/v7_3/triplex_parity.c
?? src/v7_3/triplex_plus.c
?? src/v7_3/triplex_plus_sequential.c
?? tests/test_analytical_thermal.py
?? tests/test_comparative_backends.py
?? tests/test_ml_sensor_weak.py
?? tests/test_multirate_observability.py
?? tests/test_triplex_parity.py
?? tests/test_triplex_plus.py
?? tests/test_triplex_plus_sequential.py
```

Storage cleanup complete:13requested result files, zero raw/representative traces. Temporary per-frame packets/features/margins/replays and benchmark input traces removed. Manifest/model payloads and immutable locks are embedded in thresholds.json; reproducible source remains in repository. All37244protected historical files and prior study artifact manifests verified unchanged. No commit/push/unseen.
