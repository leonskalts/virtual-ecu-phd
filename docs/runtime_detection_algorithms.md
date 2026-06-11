# Runtime Detection Algorithms

## Runtime and Offline Detection

The project now has two complementary detection paths:

- Runtime detection executes in the C simulator once per 100 ms timestep. It
  observes the final residuals and ECU DTC state for that timestep and writes
  its score, alarm, and timing results into the raw CSV.
- Offline detection remains in
  `python/virtual_ecu/detection_algorithms.py`. It evaluates saved CSV traces
  after a run and is still used by `scripts/run_detection_algorithm_study.py`
  for fair same-trace comparisons.

The runtime detector is currently an observer only. It does not set or clear
ECU DTCs, request a safe state, change actuator commands, or alter the existing
safety-monitor behavior.

## Supported Algorithms

The runtime module supports:

- `builtin_ecu`: alarms when the existing ECU primary DTC is not `none`.
- `threshold`: alarms when any absolute residual exceeds its fixed limit.
- `ewma`: applies an EWMA with `alpha = 0.20` to each absolute residual and
  alarms when a normalized EWMA score reaches 1.0.
- `cusum`: accumulates sustained absolute residual evidence and alarms when a
  normalized CUSUM score reaches 1.0.

The residuals are fan tracking error, pump tracking error, and coolant sensor
residual. Constants match the Python offline detector configuration.

## Terminal Use

The default remains `builtin_ecu`, so existing commands continue to work:

```bash
./virtual_ecu logs/default.csv paper_default
```

Select a runtime detector by appending `--detector`:

```bash
./virtual_ecu logs/cusum.csv paper_default --detector cusum
./virtual_ecu logs/threshold.csv custom fan_stuck_off 75000 0 permanent 0.0 --detector threshold
./virtual_ecu logs/ewma.csv custom sensor_bias 30000 15000 transient 6.0 --detector ewma
```

Valid values are `builtin_ecu`, `threshold`, `ewma`, and `cusum`.

## CSV Outputs

The raw CSV appends these columns after all existing columns:

- `runtime_detection_algorithm`
- `runtime_detection_score`
- `runtime_detection_alarm`
- `runtime_detection_detected`
- `runtime_detection_first_detection_ms`
- `runtime_detection_latency_ms`
- `runtime_detection_false_positive_count`
- `runtime_detection_label`

`runtime_detection_alarm` is the current timestep alarm. Detection is latched
in `runtime_detection_detected`; for fault campaigns, first detection is the
first alarm at or after the earliest configured fault start. A value of `-1`
means that a detection time or latency is unavailable.

The summary CSV also appends the selected algorithm, first detection time,
detection latency, and detected flag.

## GUI Use

In the **Custom Experiment** tab:

1. Choose an item in **Detection Algorithm**.
2. Configure a single-fault or multi-fault scenario.
3. Run the custom experiment.
4. Review the **Detection Result** card for detection time, latency, ECU DTC
   timing, missed detection, and false positives.
5. Open the generated raw CSV or plot the run to inspect behavior around the
   reported detection time.

The GUI passes the selected value to the simulator with `--detector`. It reads
the runtime columns after the run. When an older CSV lacks those columns, it
falls back to the Python offline evaluator.

**Compare All Algorithms** intentionally continues to evaluate all algorithms
offline on the same saved trace. This keeps the existing comparison study
methodology separate from the selected detector that ran inside the simulator.
