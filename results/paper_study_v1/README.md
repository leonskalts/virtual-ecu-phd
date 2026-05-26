# Paper Study v1

This folder is a compact, reproducible evidence package for the virtual ECU research prototype. It demonstrates cross-layer fault propagation beyond the GUI: fault origin -> ECU-visible disturbance -> diagnostic evidence / DTC -> safe-state response -> thermal outcome.

## Reproduce

From the repository root:

```bash
make
python3 scripts/generate_paper_study_v1.py
```

To rebuild summaries from existing raw CSV files only:

```bash
python3 scripts/generate_paper_study_v1.py --skip-run
```

## Included Scenarios

- `baseline`: Nominal reference with no injected fault.
- `fan_stuck_hot_stress`: Thermally stressed stuck-off fan actuation path case.
- `pump_degraded_only`: Single degraded-pump actuation path case.
- `stale_sensor_data_hot_stress`: Thermally stressed stale sampled-data timing/communication case.
- `sensor_bias_only`: Single coolant sensor bias sensing path case.
- `calibration_memory_corruption`: Single corrupted calibration memory/computation case.
- `paper_default_multi_fault`: Built-in multi-event scenario combining sensing and actuation faults.

## Key Outputs

- `study_report.html`: compact browser report for research meetings.
- `aggregate_summary.csv`: one row per representative scenario with extracted propagation metrics.
- `fault_taxonomy_table.csv`: hardware-origin fault mapping to ECU-visible and system-level evidence.
- `representative_comparison_summary.md`: baseline vs fan hot-stress narrative.
- `claim_summary.md`: cautious claim candidates and explicit non-claims.
- `raw/`: simulator CSV traces and simulator summary CSV files.
- `figures/`: optional simple PNG figures when matplotlib is installed.

## Extracted Metrics

scenario_id, campaign_id, campaign_label, fault_class, fault_type, fault_behavior, fault_origin, ecu_visible_disturbance, primary_dtc_label, first_dtc_label, final_safe_state_label, detection_latency_s, safe_state_entry_latency_s, safe_state_duration_s, max_coolant_temp_c, final_coolant_temp_c, max_sensor_residual_c, max_fan_tracking_error, max_pump_tracking_error, faults_seen, dtcs_seen, safe_states_seen, event_count, first_fault_start_s, raw_csv_path, summary_csv_path

Latency metrics are measured relative to the first configured fault start time. Values are `n/a` when the scenario has no injected fault or the event was not observed.

## Figures

- `results/paper_study_v1/figures/max_coolant_by_scenario.png`
- `results/paper_study_v1/figures/safe_state_duration_by_scenario.png`
- `results/paper_study_v1/figures/detection_latency_by_scenario.png`
- `results/paper_study_v1/figures/coolant_temperature_by_scenario.png`
- `results/paper_study_v1/figures/safe_state_timeline_by_scenario.png`
- `results/paper_study_v1/figures/baseline_vs_fan_hot_stress.png`

## What This Study Does Not Claim

- It does not validate physical semiconductor failure mechanisms.
- It does not certify an automotive safety case.
- It does not provide statistical reliability estimates.
- It does not assert real-vehicle calibration accuracy.
- It does not change simulator behavior, CSV schemas, GUI state, or preset formats.
