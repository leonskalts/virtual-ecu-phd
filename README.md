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
- `timing/communication faults`: stale sampled-data transfer, delayed sensor update, scheduler-induced refresh delay

These are modeled as ECU-visible abstractions, not as circuit-accurate device faults.

Built-in campaigns include:

- `baseline`: no injected faults
- `sensor_bias_only`: ADC/reference/front-end offset fault campaign
- `sensor_interface_intermittent`: intermittent sensor-interface corruption campaign
- `stale_sensor_data_only`: delayed sampled-data coolant-sensor update campaign
- `stale_sensor_data_hot_stress`: thermally stressed stale sampled-data timing/communication campaign
- `pump_degraded_only`: weak-driver / aging / supply-droop pump campaign
- `calibration_memory_corruption`: corrupted coolant-control target calibration campaign
- `fan_stuck_only`: gate-driver / PWM-output / power-stage stuck-off fan campaign
- `fan_stuck_hot_stress`: thermally stressed stuck-off fan power-stage campaign
- `paper_default`: mixed hardware-origin fault scenario

## Hardware-to-System Mapping

| Hardware-origin fault | ECU-level manifestation | Diagnostic effect | System-level thermal / safety effect |
|---|---|---|---|
| ADC / reference / front-end offset | biased coolant measurement | coolant sensor rationality DTC | incorrect cooling demand, possible false mitigation |
| intermittent sensor-interface corruption | bursty coolant reading glitches | coolant sensor rationality DTC with transient or persistent behavior | control disturbance and possible temporary safe-state entry |
| stale sampled-data coolant transfer / delayed refresh | ECU reuses an older coolant sample for multiple control steps | possible sensor rationality evidence during fast transients, plus delayed cooling-performance or overtemperature evidence | delayed cooling request, higher peak coolant temperature, and earlier protective action under stress |
| stressed stale sampled-data timing fault | persistent reuse of aged coolant data during hot traffic / idle phases | sensor rationality evidence with clearer thermal escalation and earlier protection | delayed control action becomes a strong thermal/safety case rather than a mild timing artifact |
| weak driver / aging / supply droop | reduced pump authority | pump tracking or cooling-performance diagnostics | reduced heat rejection and elevated coolant temperature |
| calibration memory corruption | delayed cooling response due to corrupted control target | overtemperature-related DTCs and possible secondary cooling diagnostics | higher peak coolant temperature and earlier safety intervention |
| gate-driver / PWM-output / power-stage stuck-off | commanded fan remains off | fan tracking DTC | safe-state escalation and thermal stress under low-airflow conditions |
| mixed hardware-origin scenario | combined sensing and actuation degradation | multiple DTCs over time | sequential safety escalation and extended degraded operation |

## Cross-Layer Fault Propagation View

The intended interpretation is:

1. a hardware-origin fault occurs in sensing, actuation, memory, or timing electronics
2. the fault appears at ECU interfaces as bias, intermittency, stale sampled data, stuck-off behavior, or reduced actuation
3. diagnostics, control, and safety logic react to those manifestations, including corrupted calibrations in computation/memory paths
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
./virtual_ecu logs/stale_sensor.csv stale_sensor_data_only
./virtual_ecu logs/stale_sensor_stress.csv stale_sensor_data_hot_stress
./virtual_ecu logs/calibration_memory.csv calibration_memory_corruption
./virtual_ecu logs/permanent.csv fan_stuck_only
./virtual_ecu logs/permanent_stress.csv fan_stuck_hot_stress
```

## GUI Frontend

A lightweight Python GUI frontend is available for campaign selection,
comparison runs, CSV loading, and quick visualization:

```sh
python3 scripts/virtual_ecu_gui.py
```

The GUI keeps the ECU simulator itself unchanged. It launches the compiled
`virtual_ecu` executable for the selected left/right campaigns, then reads the
generated raw CSV and summary CSV files from `logs/`.

Included campaign options cover:

- `baseline`
- `sensor_bias_only`
- `sensor_interface_intermittent`
- `stale_sensor_data_only`
- `stale_sensor_data_hot_stress`
- `pump_degraded_only`
- `fan_stuck_only`
- `fan_stuck_hot_stress`
- `calibration_memory_corruption`
- `paper_default`

Comparison mode is the main research/demo workflow and provides:

- left and right campaign selection
- side-by-side summary metrics for:
  `final DTC`, `final safe state`, `maximum coolant temperature`,
  `detection latency`, and `safe-state latency`
- compact left/right campaign context for the fault class, hardware source, and ECU manifestation

The GUI also plots:

- a selector-driven large comparison plot area for:
  coolant temperature comparison,
  safe-state comparison,
  and fan command / actual comparison when one or both campaigns include a permanent fault

The GUI also includes a lightweight `Batch Results` tab for loading an existing
aggregate summary CSV such as `results/batch/paper_quick/aggregate_summary.csv`.
That tab provides:

- number of runs in the loaded batch
- fault classes present
- fault types present
- per-fault-type averages for detection latency, maximum coolant temperature, and safe-mode duration
- a quick mean detection-latency comparison plot by fault type

The batch tab is intentionally a viewing layer for live inspection and demos.
It does not replace the scripted batch-analysis workflow in `scripts/`, which
should still be used for reproducible paper tables and publication-quality
figures.

The campaign-context view supports the cross-layer interpretation by mapping:

- plausible hardware-origin fault source
- ECU-level manifestation
- expected diagnostic and safe-state behavior

This GUI is intended as a research and demonstration aid:

- it gives a quick visual front-end for live campaign walkthroughs in meetings, demos, and teaching
- it makes campaign-to-campaign behavior easier to inspect without manually opening CSV files
- it helps connect low-level injected fault scenarios to ECU diagnostics, safety response, and thermal outcomes
- it provides a simple reproducible interface for paper preparation and result sanity checks

The GUI can also export the current comparison into:

- `results/gui_comparison_reports/<left>_vs_<right>/comparison_summary.csv`
- `results/gui_comparison_reports/<left>_vs_<right>/comparison_summary.txt`
- `results/gui_comparison_reports/<left>_vs_<right>/coolant_temperature_comparison.png`
- `results/gui_comparison_reports/<left>_vs_<right>/safe_state_comparison.png`
- `results/gui_comparison_reports/<left>_vs_<right>/fan_comparison.png` when applicable

For minimal setup, the GUI uses Python's built-in Tkinter library. On Windows,
Tkinter is typically included with Python. On WSL, it runs with WSLg or another
X-capable display setup.

Run a custom parameterized fault:

```sh
./virtual_ecu logs/custom_sensor.csv custom sensor_bias 20000 10000 transient 8.0
./virtual_ecu logs/custom_stale.csv custom stale_sensor_data 45000 30000 transient 5000
```

List available campaigns:

```sh
./virtual_ecu --list-campaigns
```

Each run produces:

- a time-series CSV such as `logs/permanent.csv`
- a one-row summary CSV such as `logs/permanent_summary.csv`

The executable writes `logs/thermal_run.csv` by default when no log path is provided.

## Batch Evaluation

To move beyond a few hand-crafted runs, the project now includes a lightweight
batch sweep runner for repeatable large-scale evaluation:

```sh
python3 scripts/run_batch_experiments.py --profile conference
```

For a smaller smoke test:

```sh
python3 scripts/run_batch_experiments.py --profile quick
```

The batch runner keeps the C simulator unchanged and orchestrates the compiled
executable from Python. It systematically varies:

- fault start time
- fault duration
- fault parameter / severity
- campaign type at the sweep-definition level through different fault families

Supported sweep families include:

- sensing-path fault sweeps:
  `sensor_bias`, `sensor_interface_intermittent`
- timing/communication-path fault sweeps:
  `stale_sensor_data` with both stronger transient stale-data windows and severe persistent stale-data cases
- actuation-path fault sweeps:
  `pump_degraded`, `fan_stuck_off`
- computation/memory-path fault sweeps:
  `calibration_memory_corruption`

Outputs are written to:

```text
results/batch/<profile>/
  aggregate_summary.csv
  runs/
    run_*.csv
    run_*_summary.csv
```

Each run keeps:

- one raw time-series CSV
- one one-row summary CSV

The aggregate summary CSV collects one row per run and includes at least:

- `campaign_id`
- `fault_type`
- `fault_parameter`
- `fault_start_time_ms`
- `fault_duration_ms`
- `detection_latency_ms`
- `safe_state_latency_ms`
- `max_coolant_temperature_c`
- `safe_mode_duration_ms`
- `final_safe_state`
- `final_dtc`

Interpretation notes for `aggregate_summary.csv`:

- each row is one experiment configuration from the sweep
- `campaign_id` identifies the sweep family, not just the simulator's built-in campaign label
- `simulator_campaign_id` shows whether the run came from a built-in reference or the custom single-fault path
- `detection_latency_ms = -1` means no DTC became primary after the injected fault
- `safe_state_latency_ms = -1` means no non-normal safe state was reached
- `safe_mode_duration_ms` captures how long the controller remained in a protective mode

This strengthens the research contribution because the platform is no longer
limited to a few illustrative traces. It now supports systematic sensitivity
studies, repeatable latency comparisons, and cross-fault trend analysis using a
simple workflow that remains easy to explain in a conference paper.

The timing/communication-path study is now a stronger explicit part of the
evaluation story:

- `stale_sensor_data_only` shows the core sampled-data timing fault in a clean, explainable form
- `stale_sensor_data_hot_stress` turns the same abstraction into a clearer thermal/safety demonstration case
- the batch runner now sweeps stale-data hold time, start time, duration, and persistence strongly enough to expose meaningful detection and protection trends

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
