# Causal change-point findings

Retained architecture: MEMORY. CP promotion: False.
Gate: {"gain_ge_2pp": false, "no_cp_losses": true, "incremental_benign_le_005": true, "zero_wrong_fault_origins": true, "plant_ge_97": false, "first_localized_accuracy_ge_999": true, "unknown_increase_le_5pp": true, "MEMORY_preserved": true, "TIMING_preserved": true, "COMMUNICATION_preserved": true}.

| Method | Detection | Wilson95% | Benign (Wilson95%) | Plant | Precision | Median/P95 ms |
|---|---|---|---|---|---|---|
| A0 | 1013/1200 | 82.26–86.36% | 39/1200 (2.39–4.41%) | 597/662 | 0.96293 | 0.0/21780.999999999978 |
| A1 | 1014/1200 | 82.34–86.44% | 39/1200 (2.39–4.41%) | 597/662 | 0.96296 | 0.0/6026.49999999997 |
| A2 | 1030/1200 | 83.75–87.69% | 39/1200 (2.39–4.41%) | 597/662 | 0.96352 | 0.0/19094.54999999977 |
| A3 | 1031/1200 | 83.83–87.77% | 39/1200 (2.39–4.41%) | 597/662 | 0.96355 | 0.0/5496.0 |
| SVM-X default | 1106/1200 | 90.51–93.56% | 666/1200 (52.68–58.29%) | 650/662 | 0.62415 | 0.0/741.0 |
| SVM-X matched | 105/1200 | 7.28–10.48% | 4/1200 (0.13–0.85%) | 57/662 | 0.96330 | 3800.0/19097.0 |
| SVM-CP default | 1104/1200 | 90.33–93.40% | 554/1200 (43.36–49.00%) | 650/662 | 0.66586 | 0.0/4374.999999999996 |
| SVM-CP matched | 85/1200 | 5.76–8.68% | 15/1200 (0.76–2.05%) | 41/662 | 0.85000 | 4781.0/18015.0 |

CP incremental A1/A0: 1; A3/A2: 1. Losses: {'A1_vs_A0': [], 'A3_vs_A0': ['cp_5480', 'cp_6681'], 'A3_vs_A2': []}. Incremental benign: {'A1_vs_A0': 0, 'A3_vs_A2': 0}. Memory: [{"comparison": "A2_vs_A0", "group": "effective_memory", "cases": 164, "before": 164, "after": 164, "gained": 0, "lost": 0, "benign_alarm_delta": 0}, {"comparison": "A2_vs_A0", "group": "dormant_memory", "cases": 76, "before": 49, "after": 66, "gained": 19, "lost": 2, "benign_alarm_delta": 0}, {"comparison": "A3_vs_A1", "group": "effective_memory", "cases": 164, "before": 164, "after": 164, "gained": 0, "lost": 0, "benign_alarm_delta": 0}, {"comparison": "A3_vs_A1", "group": "dormant_memory", "cases": 76, "before": 49, "after": 66, "gained": 19, "lost": 2, "benign_alarm_delta": 0}].

Hypothesis-only replay overlap H1/H2/H3 bitmask (000 means requires combined evidence or different temporal interaction): {'001': 1}. Isolated hypotheses use the frozen combination threshold and full multiplicity; they are explanatory ablations, not optimized separate detectors. H1/H2/H3 scores and winning temporal metadata at first additional alarm are in hypothesis_gain_summary.csv. H-only replays include250ms memory; sensor gains are unaffected by that separate channel.

First UNKNOWN: 37/1031; first accuracy among localized 1.0. Runtime FAULT localized accuracy 1.0. No new confident origin from CP; C/AB remains ambiguous. Benign wrong-origin samples are reported separately in NORMAL localization rows.

Strongest default: SVM-X default. Additional A3 detections needed to exceed it: 76. Strongest CAL≤1% model: SVM-X matched; BOTH actual≤1%: False. Do not describe the latter as matched if false. SVM feature sets include all legitimate cross-layer evidence; descriptive comparator parity transforms do not enable the rejected evidence provider.

The same unchanged physical runs feed all methods. Whitened change scores can also respond to legal offsets; run-level calibration budgets this collision. Equal ABC common-mode shifts lack an independent absolute reference. Unexcited-throughout actuator performance degradation remains physically unobservable. No validation tuning; no unseen. Covariance/model/protocol/manifest/source locks and overlap audit are embedded in change_point_calibration.json. CIs and exact McNemar are descriptive for grouped deterministic cases.

Regression/integrity/overhead status is appended after targeted checks.

Final verification: {
  "offline_processing_note": "Slope-fit computation interrupted before model completion to remove repeated NPZ decompression; existing physical TRAIN/CAL data reused unchanged. Comparator transform vectorization checked against scalar implementation at 1e-12. Diagnostic parameter replay restarted to parallelize the same six fixed configurations in isolated temporary files; no physical campaign rerun or parameter-rule change.",
  "native_cp_tests": {
    "returncode": 0,
    "output": "....\n----------------------------------------------------------------------\nRan 4 tests in 0.648s\n\nOK\n"
  },
  "compile": {
    "returncode": 0,
    "output": ""
  },
  "diff_check": {
    "returncode": 0,
    "output": ""
  },
  "full_regression": "Not run: CP failed preregistered promotion; retained Triplex/previously retained memory unchanged.",
  "historical_file_hashes_verified": 37244,
  "Hybrid_HETIA_unchanged": true,
  "GUI_unchanged": true,
  "locked_science_unchanged": true,
  "HEAD_unchanged": true,
  "validation_no_tuning": true,
  "unseen_run": false,
  "commit_push": false,
  "completed_utc": "2026-10-04T15:51:17.199787+00:00"
}

Additional final audit:
- Collected/replayed A0/A2 endpoint parity: 14800 method-cases passed across all four execution partitions.
- Reduced/full diagnostic replay exact parity checked on cp_0060 before validation; no physical re-execution.
- All3000 TRAIN runs had121 baseline probes and481 candidate probes; seven read/write operations per bounded transaction.

Selected-combination CAL operating points (provider run-score exceedances, not new ECU alarms; the0% row is descriptive):

| Incremental target | Threshold | Raw exceedances /1000 |
|---|---:|---:|
| 0% | 12.1707503 | 0 |
| 0.25% | 12.1559655 | 1 |
| 0.5% | 11.0573532 | 4 |
| 1% | 9.91945846 | 9 |
| 2% | 9.38337677 | 19 |

Selected SVM complexity:
- SVM-X: X_rbf_1.0, 34 features, 8646 support vectors; CAL≤1% margin 2.55293526.
- SVM-CP: CP_rbf_1.0, 38 features, 8009 support vectors; CAL≤1% margin 2.727927.

Promotion failures: gain_ge_2pp, plant_ge_97.
Strong success: False; very strong success: False.

Independent statistical support for field false-alarm bounds is not established by this grouped deterministic development campaign. Warm-engine initialization remains unchanged; true cold-soak startup was not tested. The existing broad piecewise operating-profile structure is shared across campaigns, while exact physical values, identities, seeds and split families are disjoint. No field or mathematical novelty claim is made.

Memory qualification: the previously retained250ms extension is left unchanged, not certified loss-free on this cohort. It gained19 dormant cases but lost2 (net+17). Both losses are100ms exposures hit by the baseline phase sweep and skipped by the denser alternating300/200ms schedule. The two schedules are not nested; greater average probe frequency does not guarantee a superset of detections. No memory redesign or rerun followed.
```json
[
  {
    "run_id": "cp_5480",
    "start_ms": 24400,
    "duration_ms": 100,
    "behavior": "transient",
    "effective_corruption": false,
    "baseline_active_probes": [
      24400
    ],
    "m250_active_probes": [],
    "m250_nearest_probes": [
      24300,
      24500
    ]
  },
  {
    "run_id": "cp_6681",
    "start_ms": 26600,
    "duration_ms": 100,
    "behavior": "intermittent",
    "effective_corruption": false,
    "baseline_active_probes": [
      26600
    ],
    "m250_active_probes": [],
    "m250_nearest_probes": [
      26300,
      26500,
      26800
    ]
  }
]
```

The sole incremental CP detection was cp_5806: a B-only+0.57C weak step, captured by H3 (50-sample slope), first origin UNKNOWN, with no plant manifestation. H1-only and H2-only added no cases. CP accelerated36 jointly detected cases without CP losses, but did not reduce the65 silent plant misses. A3 first UNKNOWN rose to37/1031; fault-runtime UNKNOWN was25126/330600 (7.60%). A3 net gain overA0 is18/1200=1.50pp, not20/1200: twenty gains are offset by the two memory losses. SVM-X default wins raw detection by75 cases but has666/1200 benign alarms; A3 needs76 additional detections to exceed it. Neither comparison at the CAL≤1% SVM threshold is an actual matched-FPR comparison because A3 has39/1200 benign alarms.
