# Virtual ECU PhD Project

Modular C prototype of a virtual ECU for automotive thermal-management research.

## Overview

The prototype models a simple engine cooling controller with:

- a fixed-step scheduler
- sensors, control, actuators, diagnostics, fault injection, and safety-monitor modules
- a lightweight thermal plant
- CSV logging for repeatable experiments

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

Built-in campaigns include:

- `baseline`: no injected faults
- `sensor_bias_only`: transient sensor fault campaign
- `fan_stuck_only`: permanent actuator fault campaign
- `fan_stuck_hot_stress`: permanent fan fault under hotter, lower-airflow stress conditions
- `paper_default`: combined multi-fault paper scenario

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
