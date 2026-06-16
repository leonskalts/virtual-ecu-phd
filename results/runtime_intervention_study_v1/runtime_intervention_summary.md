# Runtime Detector Intervention Study v1

This study uses the virtual ECU research simulator. Runtime detectors run inside the C simulation loop, while detector actions are optional research interventions. Observe-only preserves the built-in ECU behavior.

- Scenarios: 5
- Detectors: 6
- Detector actions: 3
- Total simulator runs: 90

## Detector Summary

| Detector | Detected scenarios | Missed | Mean latency [ms] | False positives |
|---|---:|---:|---:|---:|
| builtin_ecu | 5/5 | 0 | 12700.0 | 0 |
| threshold | 4/5 | 1 | 4025.0 | 0 |
| ewma | 4/5 | 1 | 4425.0 | 0 |
| cusum | 4/5 | 1 | 1275.0 | 0 |
| thermal_observer | 5/5 | 0 | 3680.0 | 0 |
| kalman_filter | 5/5 | 0 | 3700.0 | 0 |

## Action Summary

| Action | Runs | Actions requested | Mean max coolant [C] | Mean safe-state latency [ms] | Shutdown runs |
|---|---:|---:|---:|---:|---:|
| observe_only | 30 | 0 | 101.28 | 14833.3 | 0 |
| precautionary_cooling | 30 | 27 | 92.19 | 8593.3 | 0 |
| limp_home | 30 | 27 | 92.19 | 8593.3 | 0 |

## Key Findings

- cusum had the lowest mean runtime detection latency among detected observe-only scenarios (1275.0 ms; 4/5 scenarios detected).
- precautionary_cooling and limp_home produced the lowest descriptive mean maximum coolant temperature (92.19 C), a -9.09 C difference from observe_only.
- Missed detections across the five observe-only scenario traces were builtin_ecu: 0, threshold: 1, ewma: 1, cusum: 1, thermal_observer: 0, kalman_filter: 0.
- Controlled shutdown was requested in 0 of 90 runs.
- Observe-only runs retain the simulator's built-in diagnostic and safe-state behavior; intervention comparisons add only the selected detector request.

## Outputs

- `raw/`: one raw CSV and one summary CSV per simulator run.
- `runtime_intervention_comparison.csv`: one aggregate row per run.
- `figures/`: five Matplotlib comparison figures.
- `runtime_intervention_report.html`: compact browser report.

## Limitations

- Results are deterministic simulation outcomes for the configured scenarios and detector calibrations.
- The study is not production ECU validation and does not represent real-vehicle validation.
- Mean thermal outcomes are descriptive; they do not establish statistical significance.
- The direct residual set has limited observability for calibration-memory corruption.

## Reproduction

```bash
make
python3 scripts/run_runtime_intervention_study.py
```
