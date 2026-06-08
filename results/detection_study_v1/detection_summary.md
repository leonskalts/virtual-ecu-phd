# Detection Algorithm Study v1

This offline study compares residual-based detectors using the existing `results/paper_study_v1/raw/` traces. It does not alter or replace the virtual ECU diagnostic logic.

## Algorithm Summary

| Algorithm | Fault scenarios detected | Detection rate | Mean latency [s] | Baseline false positives | Missed detections |
|---|---:|---:|---:|---:|---:|
| threshold | 5/6 | 83.3% | 4.800 | 0 | 1 |
| ewma | 5/6 | 83.3% | 5.120 | 0 | 1 |
| cusum | 5/6 | 83.3% | 2.340 | 0 | 1 |

## Detector Configuration

- Threshold limits: `{'fan_tracking_error': 0.25, 'pump_tracking_error': 0.2, 'coolant_sensor_residual_c': 2.0}`.
- EWMA smoothing factor: `0.20`; limits: `{'fan_tracking_error': 0.25, 'pump_tracking_error': 0.2, 'coolant_sensor_residual_c': 2.0}`.
- CUSUM allowances: `{'fan_tracking_error': 0.05, 'pump_tracking_error': 0.05, 'coolant_sensor_residual_c': 0.25}`.
- CUSUM decision limits: `{'fan_tracking_error': 0.8, 'pump_tracking_error': 0.8, 'coolant_sensor_residual_c': 8.0}`.

All detectors operate on absolute residual magnitudes. A scenario is detected at the first alarm sample at or after its earliest configured campaign event. The baseline has no detection target.

## Metric Notes

- `false_positive_count` counts distinct alarm episodes before the first configured fault; for the baseline it covers the complete trace.
- `missed_detection` is one only for a fault scenario with no offline alarm at or after the first configured fault start.
- ECU DTC latency is extracted independently from the first non-`none` DTC at or after the same fault start.
- Calibration-memory corruption is not directly represented by the three residual inputs, so a miss is an informative limitation of this initial detector set.

## Scenario Results

| Scenario | Algorithm | Fault type | Detected | Latency [s] | ECU DTC | ECU latency [s] | False positives |
|---|---|---|---:|---:|---|---:|---:|
| baseline | threshold | none | 0 | n/a | none | n/a | 0 |
| baseline | ewma | none | 0 | n/a | none | n/a | 0 |
| baseline | cusum | none | 0 | n/a | none | n/a | 0 |
| fan_stuck_hot_stress | threshold | fan_stuck_off | 1 | 0.000 | fan_tracking_fault | 0.400 | 0 |
| fan_stuck_hot_stress | ewma | fan_stuck_off | 1 | 0.300 | fan_tracking_fault | 0.400 | 0 |
| fan_stuck_hot_stress | cusum | fan_stuck_off | 1 | 0.100 | fan_tracking_fault | 0.400 | 0 |
| pump_degraded_only | threshold | pump_degraded | 1 | 0.100 | pump_tracking_fault | 1.000 | 0 |
| pump_degraded_only | ewma | pump_degraded | 1 | 0.800 | pump_tracking_fault | 1.000 | 0 |
| pump_degraded_only | cusum | pump_degraded | 1 | 0.500 | pump_tracking_fault | 1.000 | 0 |
| stale_sensor_data_hot_stress | threshold | stale_sensor_data | 1 | 23.900 | coolant_sensor_rationality | 27.000 | 0 |
| stale_sensor_data_hot_stress | ewma | stale_sensor_data | 1 | 24.300 | coolant_sensor_rationality | 27.000 | 0 |
| stale_sensor_data_hot_stress | cusum | stale_sensor_data | 1 | 10.900 | coolant_sensor_rationality | 27.000 | 0 |
| sensor_bias_only | threshold | sensor_bias | 1 | 0.000 | coolant_sensor_rationality | 0.000 | 0 |
| sensor_bias_only | ewma | sensor_bias | 1 | 0.100 | coolant_sensor_rationality | 0.000 | 0 |
| sensor_bias_only | cusum | sensor_bias | 1 | 0.100 | coolant_sensor_rationality | 0.000 | 0 |
| calibration_memory_corruption | threshold | calibration_memory_corruption | 0 | n/a | cooling_performance_low | 39.500 | 0 |
| calibration_memory_corruption | ewma | calibration_memory_corruption | 0 | n/a | cooling_performance_low | 39.500 | 0 |
| calibration_memory_corruption | cusum | calibration_memory_corruption | 0 | n/a | cooling_performance_low | 39.500 | 0 |
| paper_default_multi_fault | threshold | sensor_bias+pump_degraded+fan_stuck_off | 1 | 0.000 | coolant_sensor_rationality | 0.000 | 0 |
| paper_default_multi_fault | ewma | sensor_bias+pump_degraded+fan_stuck_off | 1 | 0.100 | coolant_sensor_rationality | 0.000 | 0 |
| paper_default_multi_fault | cusum | sensor_bias+pump_degraded+fan_stuck_off | 1 | 0.100 | coolant_sensor_rationality | 0.000 | 0 |
