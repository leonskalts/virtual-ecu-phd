# Dynamic consensus findings

Promotion: False; calibration eligible: False. Retained: TRIPLEX (existing retained architecture; M1 remains available unchanged; selected M2 is an evaluated schedule, not silently promoted; rejected provider remains switchable study code only).
Gate: {"gain_ge_2pp": false, "total_benign_le_015": false, "incremental_dynamic_le_005": true, "zero_wrong_fault_origins": true, "first_accuracy_ge_999": true, "plant_ge_97": false, "MEMORY_preserved": true, "TIMING_preserved": true, "COMMUNICATION_preserved": true}.

| Method | Detection | Wilson95% | Benign | Plant | Precision | Median/P95 ms |
|---|---|---|---|---|---|---|
| A0 | 1011/1200 | 82.08–86.20% | 41/1200 | 580/640 | 0.96103 | 0.0/1000.0 |
| A1 | 1011/1200 | 82.08–86.20% | 41/1200 | 580/640 | 0.96103 | 0.0/1000.0 |
| A2 | 1011/1200 | 82.08–86.20% | 41/1200 | 580/640 | 0.96103 | 0.0/1000.0 |
| A3 | 1011/1200 | 82.08–86.20% | 41/1200 | 580/640 | 0.96103 | 0.0/1000.0 |
| A4 | 1029/1200 | 83.66–87.61% | 41/1200 | 580/640 | 0.96168 | 0.0/400.0 |
| SVM-DYN default | 1102/1200 | 90.15–93.25% | 714/1200 | 627/640 | 0.60683 | 0.0/400.0 |
| SVM-DYN CAL1 | 125/1200 | 8.81–12.27% | 19/1200 | 51/640 | 0.86806 | 211.0/34835.0 |

Benign root causes: {'SENSOR_CONTROL': 41}; H0 status: {'fault_like': 41}; suppressed: {'A2': 0, 'A3': 0}; new dynamic alarms: {'A1_vs_A0': 0, 'A3_vs_A2': 0}.
Gains: {'A1_vs_A0': 0, 'A2_vs_A0': 0, 'A3_vs_A0': 0, 'A3_vs_A1': 0, 'A3_vs_A2': 0, 'A4_vs_A0': 18, 'A4_vs_A3': 18}; lost: {'A1_vs_A0': [], 'A2_vs_A0': [], 'A3_vs_A0': [], 'A3_vs_A1': [], 'A3_vs_A2': [], 'A4_vs_A0': [], 'A4_vs_A3': []}. Discount losses A2/A0 and A3/A1 must be considered before calling suppression safe.
Memory results: [{"partition": "VALIDATION", "method": "M1", "group": "effective_memory", "cases": 162, "before": 162, "after": 162, "gained": 0, "lost": 0, "benign_delta": 0}, {"partition": "VALIDATION", "method": "M1", "group": "dormant_memory", "cases": 78, "before": 54, "after": 71, "gained": 17, "lost": 0, "benign_delta": 0}, {"partition": "VALIDATION", "method": "M2", "group": "effective_memory", "cases": 162, "before": 162, "after": 162, "gained": 0, "lost": 0, "benign_delta": 0}, {"partition": "VALIDATION", "method": "M2", "group": "dormant_memory", "cases": 78, "before": 54, "after": 72, "gained": 18, "lost": 0, "benign_delta": 0}, {"partition": "VALIDATION", "method": "A4", "group": "effective_memory", "cases": 162, "before": 162, "after": 162, "gained": 0, "lost": 0, "benign_delta": 0}, {"partition": "VALIDATION", "method": "A4", "group": "dormant_memory", "cases": 78, "before": 54, "after": 72, "gained": 18, "lost": 0, "benign_delta": 0}].
FAULT localization: {"runs": 1200, "faulty_runs": 1200, "benign_runs": 0, "detected": 1029, "coverage": 0.8575, "macro_coverage": 0.8575, "silent_plant": 60, "benign_false_alarms": 0, "benign_false_alarm_rate": null, "precision": 1.0, "recall": 0.8575, "latency_median_ms": 0.0, "latency_p95_ms": 400.0, "localized": 1029, "localization_coverage": 1.0, "correct_localizations": 1029, "wrong_localizations": 0, "localization_accuracy": 1.0, "macro_localization_accuracy": 1.0, "accuracy_when_localized": 1.0, "wrong_localization_rate": 0.0, "unknown": 0, "unknown_rate": 0.0, "localized_before_plant": 518, "preinjection_alarm_runs": 0, "propagation_supported_runs": 0, "control_effect_runs": 903, "coverage_given_control_effect": 0.9335548172757475, "actuator_effect_runs": 883, "coverage_given_actuator_effect": 0.9320498301245753, "plant_manifestation_runs": 640, "coverage_given_plant_manifestation": 0.90625, "pre_plant_alarms": 518, "same_plant_alarms": 35, "post_plant_alarms": 27, "mean_anomaly_ignorance": 0, "mean_origin_ignorance": 0, "mean_detection_conflict": 0, "mean_localization_conflict": 0, "high_detection_conflict_runs": 0, "high_localization_conflict_runs": 0, "runtime_alarm_samples": 305083, "runtime_localized_samples": 303292, "runtime_correct_samples": 303292, "runtime_wrong_samples": 0, "runtime_wrong_runs": 0, "runtime_unknown_samples": 1791, "runtime_unknown_rate": 0.005870533592497779, "runtime_accuracy_among_localized": 1.0, "runtime_correct_fraction_all_alarms": 0.9941294664075022, "runtime_localization_coverage": 0.9941294664075022, "ci_low": 0.8365798918383809, "ci_high": 0.8761385427306636, "localization_provided": true, "plant_detected": 580, "wrong_confident_fault_runs": 0, "wrong_confident_fault_samples": 0}. Benign assigned origins are counted separately; detector member-hypothesis support is not a proven faulty-member identity.
BOTH actual low-FPR<=1%: False. Strong: False; very strong: False.

Dynamic sensor gain concentration: {'domain': {}, 'kind': {}, 'magnitude': {}, 'duration_ms': {}}; narrow amplitude/channel flag: False.
TRAIN/CAL/VALID remain separate in all summary tables. Registered parameter families are disjoint, but generator structure and physical fault semantics are shared; this is nearby-configuration development generalization, not independent field sampling. Amplitude/duration/phase/channel/benign-regime rows expose concentration of gains, not selection feedback. Five-frame root-cause windows describe active evidence contributors; they do not prove physical cause from labels. Dynamic and discount counterfactual replays provide the direct ablation.
Identical global ABC corruption has no independent physical reference. Unexcited-throughout actuator performance faults and memory outside probe/use overlap remain limits. Constant-velocity latent state is sensor consensus, not truth. Relative sensor variance is not uniquely identifiable under correlated acquisition errors; fitted variance includes benign mismatch. Full Gaussian scoring is comparable across hypotheses, while robust state updates make the robust bank a quasi-likelihood model. Run-max calibration is empirical for grouped deterministic simulator cases, not a field false-alarm guarantee. No validation tuning or unseen.
Scientific/protocol/model locks, full manifest, overlap audit, selection records and comparator model are embedded in calibration.json. Temporary traces are removed after final integrity and accounting.

## Post-hoc accounting audit

{
  "cases_checked": 8400,
  "runtime_frames_checked": 10088400,
  "zero_discount_A2_equals_A0": true,
  "A3_equals_A1": true,
  "finite_outputs": true,
  "mass_bounds": true,
  "mcnemar_binary64_underflow_rows": 1,
  "SVM_default_only_by_origin": {
    "SENSOR_CONTROL": 73
  },
  "SVM_default_only_sensor_subtype": {
    "step": 54,
    "pulse": 19
  },
  "SVM_default_only_unexcited_actuator": 0,
  "endpoint": "Case detection requires a new alarm rising edge at or after injection onset; no injection label is passed to inference. This is case-level recall, not proof that every alarm causally identifies a particular injected subtype.",
  "runtime_localized_accuracy_including_benign": 0.9992883218893736
}

The dynamic provider changed neither first detection nor first-detection latency on VALIDATION. All18 A4 gains are dormant-memory cases;50 jointly detected cases are earlier under M2, none later. A0/M2 median/P95 is0/1000ms versus0/400ms; differing detected-case denominators also affect aggregate percentiles. The selected coherence discount is0 because every registered nonzero discount failed to reduce CAL benign alarms. All41 VALID baseline benign alarms were sensor-only and fault-like to the bank. No cases were safely suppressed. The registered greater-sensitivity search was therefore not authorized by the CAL budget and was not performed.

SVM-DYN default is the best CAL balanced-run-accuracy choice in the registered family, not an oracle selected from validation. All73 SVM-only VALID detections are sensor/control cases, at a cost of673 additional benign alarms. Neither architecture met the actual1% VALID benign bound at its reported low-alarm operating point; do not call this matched low-FPR superiority. No claim that global identical corruption or unexcited actuator faults were solved. Paired tables include a high-precision decimal/log10 representation when a TRAIN p-value underflows binary64; the discordant counts and exact test are unchanged.

Final verification: {
  "offline_processing_note": "Physical campaigns executed once; native trusted-input replay used for registered TRAIN/CAL selection and identical-case ablations. Disabled legacy stagger code was removed from the inherited harness before validation freeze; native endpoint and bank parity checked. No validation retuning.",
  "native_dynamic_tests": {
    "returncode": 0,
    "output": "....\n----------------------------------------------------------------------\nRan 4 tests in 0.936s\n\nOK\n"
  },
  "compile": {
    "returncode": 0,
    "output": ""
  },
  "diff_check": {
    "returncode": 0,
    "output": ""
  },
  "full_regression": "Not run: Dynamic consensus failed preregistered promotion; retained Triplex/previously retained memory unchanged.",
  "historical_file_hashes_verified": 37244,
  "build_cleanup": {
    "change": "Removed disabled legacy stagger provider functions and link object from inherited collection harness before validation freeze. No sensor acquisition, detector parameters or physical data changed.",
    "checked_cases": [
      "dc_0000",
      "dc_0100",
      "dc_3008",
      "dc_5908"
    ],
    "alarm_origin_and_bank_parity": true,
    "rejected_provider_symbols_in_final_binary": false,
    "full_case_endpoint_parity_required": true
  },
  "native_replay_parity_cases": 8400,
  "native_replay_parity_method_cases": 25200,
  "Hybrid_HETIA_unchanged": true,
  "GUI_unchanged": true,
  "locked_science_unchanged": true,
  "HEAD_unchanged": true,
  "validation_no_tuning": true,
  "unseen_run": false,
  "commit_push": false,
  "completed_utc": "2026-10-04T17:26:21.744868+00:00"
}
