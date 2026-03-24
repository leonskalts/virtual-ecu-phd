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

## Build

```sh
make
```

## Run

```sh
make run
```

Or provide a custom CSV path:

```sh
./virtual_ecu logs/my_run.csv
```

The executable writes CSV output to `logs/thermal_run.csv` by default.
