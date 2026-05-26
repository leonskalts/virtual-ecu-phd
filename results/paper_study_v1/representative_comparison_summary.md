# Representative Comparison: Baseline vs Fan Hot Stress

| scenario_id | fault_type | max_coolant_temp_c | final_coolant_temp_c | first_dtc_label | primary_dtc_label | final_safe_state_label | detection_latency_s | safe_state_entry_latency_s | safe_state_duration_s | max_fan_tracking_error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | none | 96.00 | 96.00 | none | none | normal | n/a | n/a | 0.000 | 0.000000 |
| fan_stuck_hot_stress | fan_stuck_off | 114.57 | 114.57 | fan_tracking_fault | fan_tracking_fault | limp_home | 0.400 | 0.400 | 41.600 | 1.000000 |

## Interpretation

In this deterministic representative run, `fan_stuck_hot_stress` reaches a peak coolant temperature 18.57 C above the baseline and records `fan_tracking_fault` as DTC evidence. The final safe state is `limp_home`, compared with `normal` for the baseline.

This comparison supports a propagation story from fan actuation disturbance to diagnostic evidence, safe-state response, and thermal outcome. It does not establish population-level reliability or real-vehicle calibration validity.
