# Virtual ECU Research Explorer

Virtual ECU Research Explorer is a C + Python research framework for
security-oriented fault injection, runtime detector benchmarking, and
representative RTL Hardware Trojan analysis in an automotive-inspired
thermal-control ECU.

The project combines a deterministic modular C simulator, reproducible Python
study runners, and a Tkinter desktop GUI. It is designed to compare how
ECU-visible sensing, actuation, timing/communication, calibration, and RTL
security disturbances propagate through control, diagnostics, runtime
detection, safety responses, and the modeled thermal plant.

## Research Scope

This repository is an academic research prototype for controlled and
repeatable cross-layer experiments. It provides:

- a deterministic fixed-step Virtual ECU simulator;
- security-oriented fault and multi-event injection at ECU-visible interfaces;
- online runtime detector evaluation using current and previously observed ECU
  state;
- representative RTL Hardware Trojan trigger/payload case studies; and
- reproducible CSV evidence, engineering summaries, figures, and GUI views.

The framework is not a production ECU, a calibrated real-vehicle predictor, a
transistor- or circuit-level model, silicon-proven Trojan validation, embedded
hardware certification, or a hard real-time guarantee. Its results apply to
the evaluated model, profiles, parameters, traces, and host environment.

## Current Research Focus

The current paper direction centers on the proposed **Hybrid Adaptive Kalman**
runtime detector and its evaluation across conventional fault injection,
representative RTL Trojan case studies, clean and negative-stress profiles,
and the seven comparison detectors. Supporting work includes detector
coverage/latency benchmarking, timestep-by-timestep execution and causality
auditing, host-side simulation timing, and GUI-based evidence visualization.

RTL Trojans are one representative security study family within this broader
runtime detection and fault-injection framework; they are not the only project
focus.

## System Overview

```text
Fault campaign or RTL replay trace
-> sensors / control / diagnostics / actuators
-> selected online runtime detector
-> optional detector action / safe-state request
-> thermal plant response
-> CSV evidence, validation summaries, figures, and GUI views
```

The C scheduler advances simulated time in deterministic 100 ms steps. Python
scripts orchestrate validation matrices and evidence generation, while the GUI
supports interactive execution, comparison, path inspection, and export.

## Key Capabilities

- Modular C Virtual ECU with separated sensors, control, actuators,
  diagnostics, safety monitoring, fault injection, plant dynamics, and logging.
- Configurable built-in campaigns, custom single faults, and ordered multi-event
  fault scenarios.
- Security-oriented abnormal-behavior experiments across sensing, actuation,
  timing/communication, and computation/memory paths.
- Eight runtime detector choices executed inside the C simulator loop.
- Proposed/custom Hybrid Adaptive Kalman detector with multi-signal ECU-visible
  evidence fusion.
- Optional detector-requested precautionary-cooling and limp-home actions.
- Custom driving/environment profiles and configurable simulation duration.
- HT1–HT4 representative RTL Hardware Trojan security case studies.
- Verilator trace generation and replay into unchanged Virtual ECU detectors.
- Full and expanded runtime detector validation matrices.
- Negative-stress clean-run false-positive validation.
- Online detector timing and future-lookahead/causality audit.
- Host-side simulation real-time execution benchmark.
- Tkinter GUI pages for conventional fault paths, RTL Trojan paths, security
  analysis, detector comparisons, batch results, and exports.
- CSV time-series logs, one-row summaries, reports, and presentation figures.

## Runtime Detection Algorithms

All eight selectable detector configurations are evaluated online inside the
fixed-step C scheduler:

1. **Built-in ECU diagnostics** (`builtin_ecu`)
2. **Threshold** (`threshold`)
3. **EWMA** (`ewma`)
4. **CUSUM** (`cusum`)
5. **Thermal observer** (`thermal_observer`)
6. **Kalman filter** (`kalman_filter`)
7. **Adaptive Kalman filter** (`adaptive_kalman_filter`)
8. **Hybrid Adaptive Kalman** (`hybrid_adaptive_kalman`) — the proposed/custom
   detector evaluated by the current research.

Hybrid Adaptive Kalman combines Kalman-style residual reasoning with ECU-level
observability signals such as sensor freshness, actuator consistency, thermal
response, and calibration/control-target deviation. In the evaluated
deterministic validation matrices, it achieved the strongest balance of
coverage, latency, and clean-run robustness among the evaluated detectors.
That result is bounded to the current scenarios and parameterizations; it is
not a claim that the detector is universally best or production-ready.

More detail is available in
[docs/runtime_detection_algorithms.md](docs/runtime_detection_algorithms.md).

## Detector Actions

Detector selection and detector action are separate:

- `observe_only` records evidence without requesting a safe-state change;
- `precautionary_cooling` allows a detector to request increased cooling; and
- `limp_home` allows a detector to request the modeled limp-home state.

The action layer does not change how a detector computes its alarm evidence.

## Fault and Security Scenario Classes

The simulator models ECU-visible abstractions rather than transistor- or
device-level failure physics:

- **Sensing path:** `sensor_bias`, `sensor_interface_intermittent`
- **Timing/communication:** `stale_sensor_data`
- **Actuation path:** `pump_degraded`, `fan_stuck_off`
- **Computation/memory:** `calibration_memory_corruption`
- **RTL security replay:** triggered sensor, actuator, and calibration-interface
  payload effects generated by the representative Verilog case studies

Custom campaigns can contain one event or an ordered sequence of up to four
supported events.

## Build and Quick Start

Build the C simulator:

```bash
make
```

Set up and launch the project on a new Linux/WSL machine:

```bash
git clone https://github.com/leonskalts/virtual-ecu-phd.git virtual-ecu-phd
cd virtual-ecu-phd
bash scripts/setup_local.sh
bash scripts/launch_gui.sh
```

The setup script creates a local `.venv`, installs the Python dependencies,
builds `virtual_ecu`, and creates the local generated-output directories.
Installation details and the optional desktop shortcut are documented in
[INSTALL.md](INSTALL.md).

## Quick CLI Usage

Run a clean baseline and a built-in fault campaign:

```bash
./virtual_ecu logs/baseline.csv baseline
./virtual_ecu logs/fan.csv fan_stuck_hot_stress
```

Run a custom event with the proposed detector in observe-only mode:

```bash
./virtual_ecu logs/hybrid_fan.csv \
  custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector hybrid_adaptive_kalman \
  --detector-action observe_only
```

Run an ordered multi-event scenario:

```bash
./virtual_ecu logs/multi_event.csv \
  custom_multi 3 \
  sensor_bias 30000 15000 transient 6.0 \
  pump_degraded 60000 25000 transient 0.45 \
  fan_stuck_off 90000 0 permanent 0.0 \
  --detector hybrid_adaptive_kalman \
  --detector-action observe_only
```

List the built-in campaigns:

```bash
./virtual_ecu --list-campaigns
```

## Custom Driving and Environment Profiles

Default Thermal Plant mode uses the built-in deterministic drive phases.
Optional custom profiles define time segments with vehicle speed, engine load,
ambient temperature, simplified external airflow, and simplified road slope.
When a custom simulation duration is used, its profile must explicitly cover
the complete requested interval.

```bash
./virtual_ecu logs/custom_profile.csv \
  custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector hybrid_adaptive_kalman \
  --detector-action observe_only \
  --driving-profile profiles/driving/example_driving_profile.csv \
  --simulation-duration-ms 300000
```

Profile schema:

```csv
start_ms,end_ms,vehicle_speed_kph,engine_load,ambient_temp_c,external_airflow_factor,road_slope_percent
0,100000,100,0.45,30,0.4,0
100000,200000,80,0.60,32,0.3,0
200000,300000,20,0.90,38,0.0,6
```

These airflow and slope fields are lightweight thermal/load modifiers rather
than aerodynamic or full-vehicle models. See
[docs/driving_environment_profiles.md](docs/driving_environment_profiles.md).

## GUI Research Explorer

Launch the desktop GUI with the environment-aware helper:

```bash
bash scripts/launch_gui.sh
```

The GUI pages are:

- **Dashboard**
- **Run / Load**
- **Compare**
- **Fault / Trojan Path**
- **Batch Results**
- **Runtime Study**
- **Security / RTL Analysis**
- **Exports**
- **Custom Faults**

The **Fault / Trojan Path** page supports conventional fault-propagation
visualization, Security/RTL Trojan path visualization, and a detector-neutral
overview table. It presents how evidence moves through sensing,
timing/communication, control/memory, actuation, diagnostics, and plant-outcome
stages without implying that one selected detector defines the physical path.

The **Security / RTL Analysis** page exposes the four documented targets:

- **HT1 — Coolant Sensor Interface**
- **HT2 — Fan Driver Interface**
- **HT3 — Calibration Memory Interface**
- **HT4 — Multi-Stage RTL Chain**

It loads the latest RTL study evidence, supports target and detector selection,
and presents event-oriented signal views, detector latency, summaries, and
benchmark evidence. Normal GUI use does not require Verilator unless the user
explicitly runs the RTL study.

Other GUI workflows support experiment execution/loading, two-run comparison,
custom single- and multi-event construction, batch inspection, detector/action
studies, and report/figure exports.

## Representative RTL Hardware Trojan Case Studies

The optional RTL security study contains clean and Trojan-infected Verilog
interfaces for three representative targets:

- **HT1 — Coolant Sensor Interface:** triggered masking of the ECU-facing
  coolant sample.
- **HT2 — Fan Driver Interface:** triggered suppression of realized fan output.
- **HT3 — Calibration Memory Interface:** counter-triggered shift of the
  cooling control target.
- **HT4 — Multi-Stage RTL Chain:** trace-driven composition of the existing HT3,
  HT1, and HT2 outputs. HT4 is not a fourth independent RTL module.

The study uses Verilator to generate clean and Trojan traces, then replays those
interface outputs through the unchanged Virtual ECU and all eight detector
configurations. Verilator is required only for RTL trace generation; it is not
required for normal simulator builds, existing-trace replay, or ordinary GUI
use.

```bash
make rtl-trojan-study
```

Outputs are generated under `results/rtl_hardware_trojan_study_v1/`. These are
representative cross-layer case studies—not silicon/fabrication evidence,
physical insertion proof, exhaustive Trojan coverage, or a claim about a
specific production ECU. See
[docs/rtl_hardware_trojan_model.md](docs/rtl_hardware_trojan_model.md).

## Validation and Evidence

Current validation scripts generate deterministic engineering evidence under
evaluated profiles and parameters:

- **RTL Trojan study:** HT1–HT4 clean/Trojan replay across eight detectors,
  producing 64 normalized detector rows.
- **Expanded runtime validation:** 320 normalized detector rows across 40
  clean/event variants. The 31 activated event variants comprise 27
  conventional-fault variants and four RTL Trojan variants.
- **Negative-stress validation:** 60 deterministic no-fault stress variants
  across eight detectors (480 runs). The current evaluated matrix reported zero
  false-alarm runs; this does not establish that false alarms are impossible.
- **Online detector timing/causality audit:** source-order and sampled
  prefix-equivalence checks found no future-sample access in the evaluated alarm
  implementations. On the evaluated host, all measured update calls remained
  below the 100 ms simulated timestep budget.
- **Simulation real-time benchmark:** repeated clean, conventional-fault,
  duration-scaling, and replay-only HT1–HT4 cases. On the evaluated host, all
  benchmarked cases completed faster than wall-clock real time.

These assets provide comparative host-side and deterministic-model evidence.
They do not demonstrate detection of every possible fault/Trojan, embedded
worst-case execution time, production readiness, certification, or silicon
validation.

### Paper evidence package

Generate or refresh the consolidated security-paper tables, figures, claims,
limitations, and reproduction notes with:

```bash
python3 scripts/run_paper_security_results_v1.py
```

The generated package is written under
`results/paper_evidence_security_v1/`. Use `--skip-existing` to export from
available study results without rerunning completed validation matrices.

## Useful Scripts

Core GUI and evidence runners:

| Script | Purpose |
|---|---|
| `scripts/virtual_ecu_gui.py` | Desktop research explorer |
| `scripts/run_full_runtime_validation.py` | Combined clean, fault, and RTL detector validation |
| `scripts/run_expanded_runtime_validation.py` | Expanded 320-row detector matrix |
| `scripts/run_negative_stress_validation.py` | Clean stress and false-positive evaluation |
| `scripts/run_simulation_realtime_benchmark.py` | Host simulation real-time-factor benchmark |
| `scripts/run_online_detector_timing_audit.py` | Online execution, prefix causality, and per-update timing audit |
| `scripts/run_rtl_hardware_trojan_study.py` | Verilator HT1–HT4 trace generation and replay study |

Optional and earlier focused workflows:

| Script | Purpose |
|---|---|
| `scripts/run_runtime_intervention_study.py` | Detector/action intervention comparison |
| `scripts/run_runtime_custom_matrix.py` | Detector/action matrix for one custom scenario |
| `scripts/run_batch_experiments.py` | Reproducible batch experiment profiles |

Run core evidence scripts from the repository root:

```bash
python3 scripts/run_full_runtime_validation.py
python3 scripts/run_expanded_runtime_validation.py
python3 scripts/run_negative_stress_validation.py
python3 scripts/run_simulation_realtime_benchmark.py
python3 scripts/run_online_detector_timing_audit.py
python3 scripts/run_rtl_hardware_trojan_study.py
```

The RTL runner—and full/expanded validations when they invoke RTL trace
generation—requires Verilator. The timing audit also requires `gcc`, which is
already required to build the simulator.

## Outputs and Repository Hygiene

Each simulator run writes a raw time-series CSV and a matching one-row summary
CSV. Study runners add aggregate matrices, evidence manifests, bounded claim
summaries, and optional matplotlib figures.

Common generated locations include:

```text
logs/
results/
results/batch/
results/expanded_runtime_validation/
results/negative_stress_validation/
results/online_detector_timing_audit/
results/simulation_realtime_benchmark/
results/rtl_hardware_trojan_study_v1/
```

`logs/` and `results/` are generated-output locations. New logs, generated
results, and figures should not be committed. Curated example presets may be
versioned intentionally, but local GUI session-state changes should not be
committed accidentally. Reproducible scripts regenerate study evidence from
source and configuration. Do not delete or rewrite existing generated material
merely to clean Git history; review repository changes explicitly.

## Repository Layout

```text
src/        C simulator core
include/    C headers and shared data types
scripts/    GUI, validation runners, and export helpers
python/     Python helper modules
docs/       technical and presentation documentation
profiles/   driving/environment profile examples
assets/     GUI visual assets
logs/       generated simulator logs
results/    generated study outputs
presets/    curated examples and local GUI/custom experiment state
```

Research source is concentrated in `src/`, `include/`, `scripts/`, and
`python/`. The module boundaries keep simulator, detector, diagnostics, safety,
fault injection, and logging concerns separate.

## More Documentation

- [Installation](INSTALL.md)
- [Runtime detection algorithms](docs/runtime_detection_algorithms.md)
- [RTL Hardware Trojan model and claim boundaries](docs/rtl_hardware_trojan_model.md)
- [Driving environment profiles](docs/driving_environment_profiles.md)
- [Demo walkthrough](docs/demo_walkthrough.md)
- [Detection algorithm study](docs/detection_algorithm_study.md)
- [Results and claims brief](docs/results_claims_brief.md)
- [Presentation assets guide](docs/presentation_assets_guide.md)

## Recommended Development Checks

```bash
make
python3 -m py_compile \
  scripts/virtual_ecu_gui.py \
  scripts/run_simulation_realtime_benchmark.py \
  scripts/run_online_detector_timing_audit.py
git diff --check
```

## Academic Use Note

Virtual ECU Research Explorer is under active academic development for
automotive-inspired runtime detection, security-oriented fault injection,
cross-layer abnormal-behavior analysis, and representative RTL security case
studies. Present results as bounded evidence from the evaluated deterministic
model and host—not as production, certification, silicon, or full-vehicle
claims.
