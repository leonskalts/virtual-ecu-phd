# Virtual ECU PhD Project

Modular C prototype of a virtual ECU for automotive thermal-management and
cross-layer automotive electronics dependability research.

## Overview

The prototype models a simple engine cooling controller with:

- a fixed-step scheduler
- sensors, control, actuators, diagnostics, fault injection, and safety-monitor modules
- a lightweight thermal plant
- CSV logging for repeatable experiments

The platform is intended as a hardware-origin fault abstraction framework:

- it represents plausible VLSI and automotive-electronics faults at ECU interfaces
- it studies fault propagation from electronics-level origin to ECU and vehicle-level behavior
- it does not claim transistor-level, SPICE-level, or circuit-accurate fidelity

The simulated drive cycle includes:

- nominal warm operation
- a biased coolant sensor phase
- a degraded pump phase
- a fan-stuck-off phase under hot low-speed conditions

The diagnostics layer now includes:

- explicit diagnostic IDs / DTC-style identifiers
- per-fault fail counters for persistence analysis
- transient, persistent, and permanent fault classification
- a named safe-state policy with logged state transitions

The experiment layer now includes:

- reusable built-in fault campaigns
- parameterized custom single-fault runs
- explicit experiment metadata in every CSV row
- campaign event definitions embedded in the log for run-to-run comparison
- one-row summary CSV files for direct metric extraction

## Hardware-Origin Fault Taxonomy

This framework distinguishes four hardware-origin fault classes:

- `sensing-path faults`: ADC offset, reference drift, analog front-end bias, sensor-interface intermittency
- `actuation-path faults`: weak driver behavior, PWM-output fault, gate-driver stuck-off behavior, power-stage degradation
- `computation/memory faults`: calibration corruption, register upset, state-memory disturbance
- `timing/communication faults`: scheduler jitter, stale transfer, corrupted sampled-data communication

These are modeled as ECU-visible abstractions, not as circuit-accurate device faults.

Built-in campaigns include:

- `baseline`: no injected faults
- `sensor_bias_only`: ADC/reference/front-end offset fault campaign
- `sensor_interface_intermittent`: intermittent sensor-interface corruption campaign
- `pump_degraded_only`: weak-driver / aging / supply-droop pump campaign
- `fan_stuck_only`: gate-driver / PWM-output / power-stage stuck-off fan campaign
- `fan_stuck_hot_stress`: thermally stressed stuck-off fan power-stage campaign
- `paper_default`: mixed hardware-origin fault scenario

## Hardware-to-System Mapping

| Hardware-origin fault | ECU-level manifestation | Diagnostic effect | System-level thermal / safety effect |
|---|---|---|---|
| ADC / reference / front-end offset | biased coolant measurement | coolant sensor rationality DTC | incorrect cooling demand, possible false mitigation |
| intermittent sensor-interface corruption | bursty coolant reading glitches | coolant sensor rationality DTC with transient or persistent behavior | control disturbance and possible temporary safe-state entry |
| weak driver / aging / supply droop | reduced pump authority | pump tracking or cooling-performance diagnostics | reduced heat rejection and elevated coolant temperature |
| gate-driver / PWM-output / power-stage stuck-off | commanded fan remains off | fan tracking DTC | safe-state escalation and thermal stress under low-airflow conditions |
| mixed hardware-origin scenario | combined sensing and actuation degradation | multiple DTCs over time | sequential safety escalation and extended degraded operation |

## Cross-Layer Fault Propagation View

The intended interpretation is:

1. a hardware-origin fault occurs in sensing, actuation, memory, or timing electronics
2. the fault appears at ECU interfaces as bias, intermittency, stuck-off behavior, or reduced actuation
3. diagnostics, control, and safety logic react to those manifestations
4. thermal-management behavior and safe-state transitions emerge at system level

This makes the project suitable for VLSI + automotive dependability papers as a
cross-layer fault-propagation framework while staying honest about the level of abstraction.

## Example DTCs

- `1001`: coolant sensor rationality fault
- `2001`: coolant overtemperature warning
- `2002`: coolant overtemperature critical
- `3001`: cooling performance degradation
- `3002`: pump tracking fault
- `3003`: fan tracking fault

## Safe-State Policy

- `normal`: controller operates without safety override
- `precautionary_cooling`: maximum cooling is requested while normal load is preserved
- `limp_home`: maximum cooling is requested and engine load is derated
- `controlled_shutdown`: severe thermal conditions trigger strong derating and shutdown intent

## Research Use

This platform is suitable for experiments on:

- fault detection and isolation for thermal-management subsystems
- hardware-origin fault propagation from automotive electronics to ECU behavior
- cross-campaign comparison with identical logging fields
- transient versus permanent fault behavior
- persistence-threshold tuning for diagnostic confirmation
- safe-state transition timing and hysteresis
- control-performance degradation under sensor and actuator faults

The CSV logs support paper figures such as:

- coolant temperature trajectories under nominal and faulty conditions
- pump and fan command versus actual actuator tracking
- DTC fail-counter growth and confirmation timing
- safe-state transition timelines
- residual plots for model-based sensor rationality checks

Typical paper tables can summarize:

- injected fault scenarios and their timing
- DTC definitions and confirmation thresholds
- detection latency and safe-state entry latency
- maximum, minimum, and steady-state temperatures by scenario
- controller and safety actions observed per fault class

## Build

```sh
make
```

## Run

```sh
make run
```

Run a built-in campaign:

```sh
./virtual_ecu logs/paper_default.csv paper_default
```

Example baseline, transient, and permanent campaigns:

```sh
./virtual_ecu logs/baseline.csv baseline
./virtual_ecu logs/transient.csv sensor_bias_only
./virtual_ecu logs/sensor_interface.csv sensor_interface_intermittent
./virtual_ecu logs/permanent.csv fan_stuck_only
./virtual_ecu logs/permanent_stress.csv fan_stuck_hot_stress
```

Run a custom parameterized fault:

```sh
./virtual_ecu logs/custom_sensor.csv custom sensor_bias 20000 10000 transient 8.0
```

List available campaigns:

```sh
./virtual_ecu --list-campaigns
```

Each run produces:

- a time-series CSV such as `logs/permanent.csv`
- a one-row summary CSV such as `logs/permanent_summary.csv`

The executable writes `logs/thermal_run.csv` by default when no log path is provided.

## Paper Tables and Figures

Generate the main paper tables and figures from the current campaign logs:

```sh
python3 scripts/generate_paper_results.py
```

This writes the following outputs to `results/`:

- `table_1_campaign_definition.csv`
- `table_2_cross_campaign_results.csv`
- `figure_1_coolant_temperature_vs_time.png`
- `figure_2_safe_state_timeline.png`
- `figure_3_fan_command_vs_actual.png`

If needed, generate or refresh the required campaign logs first:

```sh
./virtual_ecu logs/baseline.csv baseline
./virtual_ecu logs/transient.csv sensor_bias_only
./virtual_ecu logs/permanent.csv fan_stuck_only
./virtual_ecu logs/permanent_stress.csv fan_stuck_hot_stress
./virtual_ecu logs/paper_default.csv paper_default
```

The script uses Python 3 and Matplotlib, which are available on a typical WSL Python setup.
