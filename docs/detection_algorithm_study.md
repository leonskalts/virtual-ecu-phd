# Offline Detection Algorithm Study

## Purpose

The detection study compares simple, known anomaly-detection algorithms using
the raw CSV traces already produced by the virtual ECU. The algorithms are an
offline/post-processing layer: they do not modify the C simulator, its CSV
schema, or the ECU's built-in diagnostic and safe-state logic.

The reusable implementation lives in the source-layout Python package
`python/virtual_ecu/detection_algorithms.py`. The root name `virtual_ecu` is
kept for the compiled simulator executable, so scripts add `python/` to
`sys.path` before importing `virtual_ecu.detection_algorithms`.

The initial study uses three logged residuals:

- `fan_tracking_error` for fan actuation-path faults
- `pump_tracking_error` for pump actuation-path faults
- `coolant_sensor_residual_c` for sensor and sampled-data timing faults

These algorithms were selected because they are lightweight, interpretable,
and establish reproducible reference methods before introducing a plant model
or state observer. Each detector parameter is defined explicitly in
`python/virtual_ecu/detection_algorithms.py` so that later sensitivity studies
can report and vary the calibration.

## Threshold Detection

Threshold detection raises an alarm when the absolute value of any available
residual exceeds its configured limit. It is easy to explain and gives a clear
reference for detection latency, but it can be sensitive to noise and brief
residual spikes. It does not accumulate evidence over time.

## EWMA Detection

The exponentially weighted moving average (EWMA) detector smooths each
absolute residual:

```text
ewma[k] = alpha * abs(residual[k]) + (1 - alpha) * ewma[k - 1]
```

An alarm is raised when a smoothed residual exceeds its configured limit.
EWMA reduces sensitivity to isolated samples while retaining more recent
evidence than older evidence. Its latency depends on both the smoothing factor
and the decision limit.

## CUSUM Detection

The one-sided cumulative sum (CUSUM) detector accumulates positive residual
evidence above a configurable allowance:

```text
cusum[k] = max(0, cusum[k - 1] + abs(residual[k]) - allowance)
```

An alarm is raised when the accumulated value exceeds its decision limit.
CUSUM can detect sustained small changes that remain below a direct threshold,
although its allowance and decision limit must be calibrated to control false
alarms.

## Extracted Metrics

The study writes one result row for each scenario and algorithm. It reports:

- scenario and configured fault type
- earliest configured fault start time
- whether the offline algorithm detected the scenario
- first absolute detection time and latency from the first fault start
- first ECU DTC label after the same fault start
- ECU DTC detection latency, when available
- final safe state and maximum true coolant temperature
- false-positive alarm episodes before fault injection
- whether a fault scenario was missed

The baseline scenario is the false-positive reference. Its complete trace is
used as the false-positive observation window. For a fault scenario, an
offline detection is counted only at or after the earliest configured
`campaign_event_*_start_ms` value. Fault type and timing are read from the
`campaign_event_*` fields in the first CSV row.

The comparison currently evaluates a multi-fault trace relative to its first
configured event. Per-event detection and isolation metrics can be added in a
later study when each event needs a separate result row.

## Difference From ECU DTC Logic

The offline detectors consume recorded residuals after a simulation has
finished. They do not command safe states, affect control, or replace the
diagnostics module. The ECU DTC logic runs online inside the simulator and
includes its own persistence counters, priorities, fault labels, thermal
conditions, and safety-policy interactions.

The `builtin_ecu` algorithm option is a comparison/readout mode rather than a
new detector. It reports the ECU's first post-fault DTC timing from the CSV.

The study therefore treats the ECU's first post-fault DTC as a comparison
measurement, not as ground truth for the offline detector. A disagreement can
identify different sensitivity, a residual that does not represent the fault,
or diagnostic logic that uses evidence unavailable to these three algorithms.
For example, calibration-memory corruption changes control behavior without
directly changing the selected sensor or actuator residuals.

## Running the Study

From the repository root:

```bash
python3 scripts/run_detection_algorithm_study.py
```

The script reads `results/paper_study_v1/raw/` and writes:

- `results/detection_study_v1/algorithm_comparison.csv`
- `results/detection_study_v1/detection_summary.md`
- `results/detection_study_v1/figures/detection_latency_by_algorithm.png`
- `results/detection_study_v1/figures/detection_rate_by_algorithm.png`

Matplotlib is used only for the optional figures. The CSV and Markdown outputs
use the Python standard library.

The GUI uses the same module for custom experiment post-processing. On the
Custom Experiment page, select a detection algorithm before running a single
fault or multi-fault scenario; the Detection Result card is filled from the
generated CSV after the simulator exits.

## Future Extensions

A next stage can add a thermal observer or Kalman-filter innovation residual
to detect faults that are weakly represented by direct signal differences.
That would support model-based detection of calibration corruption, cooling
performance degradation, and coupled faults.

The campaign taxonomy can also be extended to security-origin attacks such as
sensor spoofing, replayed or delayed measurements, malicious calibration
changes, and actuator-command tampering. Such experiments should distinguish
attack origin from physical fault origin while retaining the same measurable
detection, latency, false-positive, safe-state, and thermal-outcome metrics.
