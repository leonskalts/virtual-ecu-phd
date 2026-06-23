# Virtual ECU Research Explorer

A research-oriented virtual ECU simulator for automotive thermal-management
fault injection, runtime detection, safety-action studies, and cross-layer
dependability experiments.

Virtual ECU Research Explorer is a lightweight C + Python/Tkinter research
platform for controlled, repeatable experiments around ECU-visible effects of
hardware-origin automotive electronics faults.

## Research Scope

This project models ECU-visible effects of hardware-origin faults in an
automotive thermal-management context. It is a simplified virtual ECU research
simulator intended for comparative experiments, paper figures, teaching, and
prototype evaluation.

It is not a transistor-level, SPICE-level, circuit-level, CFD, production
vehicle, or production ECU model. The goal is controlled and repeatable
cross-layer experimentation, not production calibration or real-vehicle
prediction.

## Key Capabilities

- Modular C virtual ECU simulator.
- Lightweight thermal plant with default built-in phases.
- Fault injection for sensing, actuation, timing/communication, and
  computation/memory paths.
- Built-in campaigns and custom single-fault / multi-fault scenarios.
- Runtime detection algorithms inside the C simulator loop.
- Optional detector-requested safe-state interventions.
- Custom driving/environment profiles.
- Optional custom simulation duration with strict profile coverage.
- CSV time-series logging and one-row summary metrics.
- Batch studies and runtime detector intervention studies.
- Python/Tkinter GUI for running, comparing, visualizing, and exporting
  experiments.

## Runtime Detection Algorithms

Current runtime detection algorithms:

- built-in ECU diagnostics
- threshold
- EWMA
- CUSUM
- thermal observer
- Kalman filter

Runtime detectors observe evidence inside the simulator loop. They can remain
observe-only or request a configured safe-state response, depending on the
selected detector action.

## Detector Actions

Detection algorithm and detector action are separate concepts:

- the algorithm detects evidence
- the action determines whether the runtime detector requests a safe-state
  response

Supported detector actions:

- `observe_only`
- `precautionary_cooling`
- `limp_home`

## Fault Classes

The simulator uses ECU-visible abstractions of hardware-origin fault classes:

- sensing path
- actuation path
- computation/memory
- timing/communication

Example custom fault types:

- `sensor_bias`
- `sensor_interface_intermittent`
- `stale_sensor_data`
- `pump_degraded`
- `fan_stuck_off`
- `calibration_memory_corruption`

## Build

```bash
make
```

## Quick CLI Usage

Run built-in campaigns:

```bash
./virtual_ecu logs/baseline.csv baseline
./virtual_ecu logs/fan.csv fan_stuck_hot_stress
./virtual_ecu logs/custom_fan.csv custom fan_stuck_off 75000 0 permanent 0.0
```

Run with a runtime detector:

```bash
./virtual_ecu logs/kalman_fan.csv custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector kalman_filter \
  --detector-action observe_only
```

Run with a detector-requested intervention:

```bash
./virtual_ecu logs/kalman_limp.csv custom sensor_bias 75000 0 permanent 6.0 \
  --detector kalman_filter \
  --detector-action limp_home
```

List built-in campaigns:

```bash
./virtual_ecu --list-campaigns
```

## Custom Driving / Environment Profiles

Default Thermal Plant mode remains the baseline and uses the built-in thermal
phases. Custom Driving Profile mode is optional and can define time segments
with vehicle speed, engine load, ambient temperature, simplified external
airflow, and simplified road slope.

Custom Simulation Duration is also optional. When a custom duration is used with
a custom driving profile, the profile must explicitly cover the full interval
from `0` to the requested duration. In the GUI strict custom-duration mode,
there is no hidden reuse of the final segment.

CLI example:

```bash
./virtual_ecu logs/custom_profile.csv custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector kalman_filter \
  --detector-action observe_only \
  --driving-profile profiles/driving/example_driving_profile.csv \
  --simulation-duration-ms 300000
```

CSV schema:

```csv
start_ms,end_ms,vehicle_speed_kph,engine_load,ambient_temp_c,external_airflow_factor,road_slope_percent
0,100000,100,0.45,30,0.4,0
100000,200000,80,0.60,32,0.3,0
200000,300000,20,0.90,38,0.0,6
```

`external_airflow_factor` is a simplified cooling modifier, not a real
aerodynamic wind model. `road_slope_percent` is a simplified load modifier.
More detail is in [docs/driving_environment_profiles.md](docs/driving_environment_profiles.md).

## GUI

Launch the Python/Tkinter desktop GUI:

```bash
python3 scripts/virtual_ecu_gui.py
```

Main pages:

- Dashboard
- Run / Load
- Compare
- Fault Path
- Batch Results
- Runtime Study
- Exports
- Custom Faults

The GUI can:

- run and load experiments
- compare results
- inspect fault-path visualizations
- load batch results
- run runtime studies
- export reports and figures
- build custom single-fault and multi-fault scenarios
- select detection algorithms and detector actions
- configure custom driving/environment profiles
- set custom simulation duration for custom driving profiles
- show running/ready status in the sidebar
- use persistent Virtual ECU sidebar branding and attribution

## Runtime Study / Batch Results

Runtime Study compares detection algorithms and detector actions. The runtime
custom matrix can reuse the latest custom scenario, driving profile, and custom
duration. Predefined runtime studies remain controlled default-mode studies.

Batch Results loads aggregate CSVs for quick inspection. Scripted studies remain
the reproducible path for paper tables and publication-quality artifacts.

Useful scripts:

```bash
python3 scripts/run_runtime_intervention_study.py
python3 scripts/run_runtime_custom_matrix.py
python3 scripts/run_batch_experiments.py --profile quick
```

## Outputs

Common output locations:

```text
logs/
results/
results/runtime_custom_matrix/
results/runtime_intervention_study_v1/
results/batch/
results/paper/
results/gui_comparison_reports/
profiles/driving/
docs/
```

Each simulator run writes a raw time-series CSV and a matching one-row summary
CSV. GUI and study scripts write derived reports, figures, and aggregate CSVs
under `results/`.

## More Documentation

- [Runtime detection algorithms](docs/runtime_detection_algorithms.md)
- [Driving environment profiles](docs/driving_environment_profiles.md)
- [Detection algorithm study](docs/detection_algorithm_study.md)
- [Demo walkthrough](docs/demo_walkthrough.md)
- [Presentation assets guide](docs/presentation_assets_guide.md)
- [Results claims brief](docs/results_claims_brief.md)

## Recommended Development Checks

```bash
make
python3 -m py_compile scripts/virtual_ecu_gui.py scripts/run_runtime_custom_matrix.py
git diff --check
```

## Academic Use Note

This is an academic research prototype under active development for VLSI
testing, hardware-origin fault abstraction, and automotive ECU dependability
studies. Use it as a controlled virtual experiment platform, and keep the model
scope clear when presenting results.
