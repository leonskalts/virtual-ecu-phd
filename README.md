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

Run a custom parameterized fault:

```sh
./virtual_ecu logs/custom_sensor.csv custom sensor_bias 20000 10000 transient 8.0
```

List available campaigns:

```sh
./virtual_ecu --list-campaigns
```

The executable writes CSV output to `logs/thermal_run.csv` by default.
