# Runtime Detection Algorithms

## Runtime and Offline Detection

The project now has two complementary detection paths:

- Runtime detection executes in the C simulator once per 100 ms timestep. It
  observes the residuals and ECU DTC state after the normal safety-monitor
  pass, then any enabled detector action is included in the final safe-state
  request before metrics and logging.
- Offline detection remains in
  `python/virtual_ecu/detection_algorithms.py`. It evaluates saved CSV traces
  after a run and is still used by `scripts/run_detection_algorithm_study.py`
  for fair same-trace comparisons.

Runtime intervention is optional. The default `observe_only` action does not
set or clear ECU DTCs, request a safe state, change actuator commands, or alter
the existing safety-monitor behavior.

## Supported Algorithms

The runtime module supports:

- `builtin_ecu`: alarms when the existing ECU primary DTC is not `none`.
- `threshold`: alarms when any absolute residual exceeds its fixed limit.
- `ewma`: applies an EWMA with `alpha = 0.20` to each absolute residual and
  alarms when a normalized EWMA score reaches 1.0.
- `cusum`: accumulates sustained absolute residual evidence and alarms when a
  normalized CUSUM score reaches 1.0.
- `thermal_observer`: compares observed coolant-temperature evolution with a
  lightweight one-step healthy thermal model and accumulates sustained excess
  heating relative to that model.
- `kalman_filter`: estimates coolant temperature with a lightweight scalar
  Kalman-style observer and alarms on abnormal normalized innovation.
- `adaptive_kalman_filter`: extends the scalar Kalman-style observer with a
  bounded context-aware innovation sensitivity based on thermal operating
  context.
- `hybrid_adaptive_kalman`: experimental low-latency variant that keeps the
  adaptive Kalman observer and adds a guarded, bounded fast-evidence path.

The direct residual/freshness detectors use fan tracking error, pump tracking
error, coolant sensor residual, and ECU-level coolant sensor freshness score.
Constants match the Python offline detector configuration.

## Coolant Sensor Freshness Monitoring

The Virtual ECU tracks coolant sensor freshness as part of the current sensor
state. The sensor module records `coolant_sensor_last_update_ms`,
`coolant_sensor_update_age_ms`, `coolant_sensor_expected_period_ms`,
`coolant_sensor_freshness_score`, and `coolant_sensor_freshness_ok`.

Normal coolant sensor refreshes reset the update timestamp, so the update age
stays low during healthy operation. Stale sampled-data behavior holds the
previous coolant measurement; while the value is held, the timestamp does not
advance and the update age rises. The freshness score is derived from that
runtime-observable age relative to the expected sensor period. Detectors do
not read fault type, scenario ID, injected-fault state, or fault timing to
decide whether a sample is stale.

The freshness signal is logged in every runtime CSV trace and can be used by
runtime detectors. `threshold`, `ewma`, and `cusum` treat it as another
bounded evidence channel. The Kalman-family detectors fold freshness into
their existing score/confirmation logic. The built-in ECU DTC path also treats
stale coolant freshness as coolant-sensor rationality evidence.

## Thermal Observer Detector

The thermal observer complements the direct command-versus-actual residual
detectors. At each 100 ms simulator step it predicts the next coolant
temperature change using the nominal 92 C cooling target, engine load, vehicle
speed, ambient temperature, and expected healthy pump/fan demand. It compares
that prediction with the observed coolant-temperature change and accumulates
positive mismatch after a small allowance.

This makes indirect thermal/control faults more observable. For example,
calibration-memory corruption can delay cooling demand while pump and fan
commands still match their actuator feedback, leaving the direct residuals
near zero. The healthy-model prediction still expects the nominal cooling
policy, so sustained extra heating can raise
`thermal_observer_mismatch`.

The implementation is intentionally a deterministic research-grade heuristic.
It is not a Kalman filter, a calibrated production observer, or an ECU safety
mechanism. Its behavior depends on the simplified virtual plant, nominal
controller model, allowance, and decision threshold.

## Kalman Filter Observer

The Kalman filter observer estimates the expected coolant temperature state
with a one-dimensional thermal model. At each simulator timestep it predicts
the next coolant temperature from engine load, vehicle speed, ambient
temperature, campaign thermal metadata, and a healthy cooling expectation
derived from pump and fan demand. It then compares this prediction with the
observed coolant-temperature measurement.

The prediction residual is the innovation:

```text
innovation = observed coolant temperature - predicted coolant temperature
```

The detector normalizes the innovation by the scalar innovation variance,
updates the temperature estimate with a scalar Kalman gain, and accumulates
sustained innovation evidence with a small leak. The runtime label is
`kalman_filter_innovation`.

This differs from `threshold`, `ewma`, and `cusum`, which operate directly on
fan tracking, pump tracking, and coolant sensor residuals. It also differs
from `thermal_observer`: the thermal observer is a deterministic mismatch
accumulator over observed temperature deltas, while `kalman_filter` maintains
an explicit coolant-temperature estimate, covariance, process noise, and
measurement noise.

The Kalman-style observer can help expose faults where direct residuals are
weak or delayed, including coolant sensor spoofing, stale/replay behavior,
calibration-memory corruption, and indirect thermal anomalies. It is still a
simplified research detector. The model is scalar and heuristic, the constants
are tuned for conservative virtual-ECU experiments, and the implementation is
not production ECU validation, real-vehicle validation, or a certified safety
mechanism.

## Adaptive Kalman Filter Observer

`adaptive_kalman_filter` uses the same scalar coolant-temperature observer as
`kalman_filter`, then combines bounded runtime-observable evidence into a
context-aware score. Kalman innovation remains the primary evidence source.
Actuator command/actual mismatch can add bounded support, coolant rising trend
can add bounded support only when innovation or actuator evidence is already
present, coolant sensor freshness can add bounded support, and thermal context
can moderately multiply existing evidence.

The context score is deterministic and heuristic. It uses ECU-visible or
simulator-observable operating variables such as measured coolant temperature,
coolant temperature trend, engine load, vehicle speed, ambient temperature,
custom-profile external airflow factor, and custom-profile road slope. Context
alone cannot trigger detection, and trend alone cannot trigger detection.

Higher thermal stress lowers the effective Kalman decision limits moderately,
while low-stress operation raises them slightly. The threshold scale is bounded
from `0.70` to `1.20` of the base Kalman limits. A bounded confirmation counter
requires persistence for weak/medium evidence while allowing strong multi-signal
evidence to confirm quickly. The runtime label is
`adaptive_kalman_filter_contextual_innovation`.

This detector does not read fault type, scenario ID, fault start time, fault
duration, injected-fault-active flags, or ground-truth fault labels. It is a
deterministic context-aware research heuristic intended for comparative runtime
detection experiments, not a production ECU monitor or real-vehicle validation
method.

## Hybrid Adaptive Kalman Detector

`hybrid_adaptive_kalman` is an experimental detector variant. It does not
replace the accepted `adaptive_kalman_filter` behavior. It reuses the same
scalar Kalman-style observer, adaptive threshold scaling, context score,
actuator evidence, and trend gate, then adds a guarded fast path for bounded
runtime-observable residual evidence.

The fast path considers fan command/actual mismatch, pump command/actual
mismatch, and coolant sensor residual evidence already available to the
runtime detector infrastructure. Strong fast evidence can confirm quickly only
when at least one support signal is present: Kalman innovation support,
accumulated innovation support, coolant rising-trend support behind the
existing evidence gate, or high thermal context severity. Medium evidence
requires confirmation. Weak residual evidence, context alone, and trend alone
cannot trigger detection.

For stale-sensor cases, a conservative sensor residual fast path can confirm
one timestep earlier only when the residual is strong and the hybrid
Kalman/context score is already high. This keeps the hybrid distinct from a
pure threshold detector: coolant sensor residual alone is not sufficient.

The hybrid score also includes a bounded thermal-fusion evidence term. It
accumulates positive healthy-model thermal mismatch, similar in shape to the
standalone `thermal_observer`, but folds that value back into the same hybrid
confidence score and confirmation counter. Thermal mismatch is not used as an
OR fallback alarm; it needs residual support plus Kalman support before it can
accelerate confirmation.

Coolant sensor freshness is fused into the same hybrid confidence score. A
stale freshness signal can provide bounded medium evidence and must pass the
same dynamic confirmation path; it is not ORed into the alarm result as a
separate threshold detector.

Hybrid runtime labels describe the dominant evidence:
`hybrid_adaptive_kalman_fast_actuator_evidence`,
`hybrid_adaptive_kalman_fast_sensor_evidence`,
`hybrid_adaptive_kalman_contextual_innovation`,
`hybrid_adaptive_kalman_sensor_freshness_fusion`,
`hybrid_adaptive_kalman_thermal_mismatch_evidence`,
`hybrid_adaptive_kalman_contextual_thermal_fusion`, or
`hybrid_adaptive_kalman_multi_signal_evidence`.

The hybrid detector is intended for comparative experiments about latency and
robustness tradeoffs. It remains deterministic and scenario-blind: it does not
read fault type, scenario ID, fault start time, fault duration, injected-fault
state, or ground-truth labels.

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
./virtual_ecu logs/thermal_observer.csv custom calibration_memory_corruption 52000 0 permanent 16.0 --detector thermal_observer
./virtual_ecu logs/kalman_filter.csv custom calibration_memory_corruption 52000 0 permanent 16.0 --detector kalman_filter
./virtual_ecu logs/adaptive_kalman_filter.csv custom calibration_memory_corruption 52000 0 permanent 16.0 --detector adaptive_kalman_filter
./virtual_ecu logs/hybrid_adaptive_kalman.csv custom sensor_bias 75000 0 permanent 6.0 --detector hybrid_adaptive_kalman
```

Valid values are `builtin_ecu`, `threshold`, `ewma`, `cusum`,
`thermal_observer`, `kalman_filter`, `adaptive_kalman_filter`, and
`hybrid_adaptive_kalman`.

## Detector Actions

The optional `--detector-action` argument controls whether the selected
runtime detector can request a safety response:

- `observe_only`: log detection results without intervention. This is the
  default and preserves the original simulator behavior.
- `precautionary_cooling`: after first detection, request precautionary
  cooling and max-cooling behavior.
- `limp_home`: after first detection, request limp-home operation.

The detector request is combined with the existing diagnostic request using
the maximum safe-state severity. It can raise the request but never lower or
bypass an ECU request. Neither action can suppress an existing controlled
shutdown request, and this milestone does not provide a detector shutdown
action.

```bash
./virtual_ecu logs/test_observe.csv custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector cusum --detector-action observe_only

./virtual_ecu logs/test_precautionary.csv custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector cusum --detector-action precautionary_cooling

./virtual_ecu logs/test_limp.csv custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector cusum --detector-action limp_home
```

Omitting `--detector-action` is equivalent to
`--detector-action observe_only`.

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
- `runtime_detection_action`
- `runtime_detection_action_requested`
- `runtime_detection_requested_safe_state`
- `runtime_detection_action_time_ms`
- `runtime_detection_action_reason`

`runtime_detection_alarm` is the current timestep alarm. Detection is latched
in `runtime_detection_detected`; for fault campaigns, first detection is the
first alarm at or after the earliest configured fault start. A value of `-1`
means that a detection time or latency is unavailable.

The summary CSV also appends detector timing and the detector-action fields.
The raw requested-safe-state field records the final maximum-severity request
after detector and built-in diagnostic requests are combined.

## GUI Use

In the **Custom Experiment** tab:

1. Choose an item in **Detection Algorithm**.
2. Choose **Detector Action**. Keep **Observe only** for non-intervention runs.
3. Configure a single-fault or multi-fault scenario.
4. Run the custom experiment.
5. Review the **Detection Result** card for detection and action timing,
   requested safe state, ECU DTC timing, missed detection, and false positives.
6. Open the generated raw CSV or plot the run to inspect behavior around the
   reported detection and action time.

The GUI passes the selections with `--detector` and `--detector-action`. It
reads the runtime columns after the run. When an older CSV lacks those
columns, it falls back to the Python offline evaluator and marks action
evidence as unavailable.

**Compare All Algorithms** intentionally continues to evaluate all algorithms
offline on the same saved trace. This keeps the existing comparison study
methodology separate from the selected detector that ran inside the simulator.

## Runtime Intervention Study

Run the reproducible detector/action comparison from the repository root:

```bash
make
python3 scripts/run_runtime_intervention_study.py
```

The study runs five custom single-fault scenarios across all seven runtime
detectors and all three detector actions. Its simulator runs are written to:

```text
results/runtime_intervention_study_v1/
```

The output includes raw and summary CSV files for every run, an aggregate
comparison CSV, five Matplotlib figures, a Markdown summary, and the compact
browser report:

```text
results/runtime_intervention_study_v1/runtime_intervention_report.html
```

The report compares runtime detection latency, action timing, missed
detections, final safe states, maximum coolant temperature, ECU DTC timing,
and shutdown requests. `observe_only` is the non-intervention reference and
preserves the simulator's built-in safe-state behavior.

The results are deterministic virtual ECU research simulations. They are not
production ECU validation or real-vehicle validation, and thermal averages
are descriptive rather than evidence of statistical significance.

### Latest Custom Scenario Matrix

The GUI **Runtime Study** page can also run the latest custom scenario through
the complete detector by action matrix. Choose **Latest custom
scenario matrix**, then click **Run Matrix for Latest Custom Scenario**.

The GUI prefers the configuration from the most recently completed custom run.
If no custom run is loaded, it uses the currently active Single Fault or
Multi-Fault builder configuration. The simulator runs and generated
artifacts are replaced on each invocation under:

```text
results/runtime_custom_matrix/latest/
```

The output includes raw and summary CSVs, the aggregate
`runtime_custom_matrix_comparison.csv`, four Matplotlib figures, a Markdown
summary, and `runtime_custom_matrix_report.html`. The report compares runtime
detection latency, maximum coolant temperature, detector action timing, missed
detections, and final safe-state outcomes for that exact custom scenario.

This matrix is a deterministic virtual ECU research simulation. It is not
production ECU validation or real-vehicle validation. It evaluates only one
configured scenario at a time, and descriptive thermal differences do not
establish statistical significance. `observe_only` remains the
non-intervention reference and preserves built-in simulator behavior.

## Research Limitation

Detector intervention is a research abstraction for repeatable virtual ECU
experiments. It is not production ECU safety validation, a certified safety
mechanism, or evidence of compliance with an automotive functional-safety
standard.
