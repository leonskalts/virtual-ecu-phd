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

Recommended integrated workflow:

```sh
make recommended-study
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

## Recommended Studies

The strongest final single-run study bundle uses:

- `baseline`
- `fan_stuck_hot_stress`
- `calibration_memory_corruption`
- `stale_sensor_data_only`
- `stale_sensor_data_hot_stress`
- `paper_default`

This set gives a compact final platform view across nominal behavior,
timing/communication faults, computation/memory faults, strong actuation-path
stress, and mixed cross-layer propagation.

## Fast Start for Thesis/Paper Use

Run the recommended end-to-end workflow:

```sh
make recommended-study
```

This workflow:

- generates the recommended single-run campaign logs in `logs/recommended_study/`
- writes the single-run paper/demo bundle to `results/paper/`
- regenerates curated cross-layer propagation bundles beside selected recommended logs
- refreshes the compact batch study in `results/batch/paper_quick/`
- regenerates the batch-analysis and claim-focused outputs

The same integrated workflow can also be run directly:

```sh
python3 scripts/run_recommended_study.py
```

Most important outputs to inspect first:

- `results/paper/table_2_cross_campaign_results.csv`
- `results/paper/figure_1_coolant_temperature_vs_time.png`
- `results/paper/figure_2_safe_state_timeline.png`
- `logs/recommended_study/fan_stuck_hot_stress_propagation/propagation_summary.txt`
- `results/batch/paper_quick/aggregate_summary.csv`
- `results/batch/paper_quick/analysis/table_batch_2_fault_type_summary.csv`
- `results/batch/paper_quick/analysis_claims/table_claim_1_main_comparison.csv`

## Demo Workflow

For live demos, the GUI includes a built-in recommended comparison shortlist:

- `baseline` vs `fan_stuck_hot_stress`
- `baseline` vs `calibration_memory_corruption`
- `baseline` vs `stale_sensor_data_only`
- `stale_sensor_data_only` vs `stale_sensor_data_hot_stress`
- `stale_sensor_data_hot_stress` vs `fan_stuck_hot_stress`

These pairings are intended to show nominal behavior against the strongest
timing, computation/memory, and actuation-path cases, plus a mild-versus-hot
timing comparison.

## Output Structure

The recommended final workflow keeps outputs in four main places:

- `logs/`
  single-run simulator CSV files, including `logs/recommended_study/`, plus curated propagation bundles for selected recommended runs
- `results/batch/`
  compact and larger batch studies such as `results/batch/paper_quick/`
- `results/paper/`
  the recommended paper/demo-ready single-run bundle
- `results/gui_comparison_reports/`
  exported GUI comparison reports and figures

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
- one-click recommended demo-comparison shortcuts for the strongest live walkthrough cases
- side-by-side summary metrics for:
  `final DTC`, `final safe state`, `maximum coolant temperature`,
  `detection latency`, and `safe-state latency`
- compact left/right campaign context for the fault class, hardware source, and ECU manifestation

The GUI also plots:

- a selector-driven large comparison plot area for:
  coolant temperature comparison,
  safe-state comparison,
  fan command / actual comparison when one or both campaigns include a permanent fault,
  and a cross-layer propagation timeline that reads top-to-bottom as:
  hardware-origin fault,
  ECU manifestation,
  diagnostic effect,
  and safe-state/system effect

The `Comparison Figures` tab also includes a lightweight `Propagation Evidence`
panel beside the propagation-timeline workflow. For each loaded run, it lists
the hardware-origin fault evidence, ECU-visible manifestation, first diagnostic
evidence, first safe-state transition, and peak thermal severity. This makes the
hardware-origin fault -> ECU manifestation -> diagnostic evidence -> safe-state
/ thermal outcome chain easier to explain during demos without opening the raw
CSV files.

The GUI also includes a `Fault Path` tab with two image-based comparison cards
for the selected left and right campaigns. Each card uses local PNG subsystem
assets from `assets/fault_path/` to show a clearer left-to-right ECU story:
coolant sensing hardware, sampled-data / communication transfer, ECU control
and calibration memory, actuation hardware, and the plant-level thermal
outcome. The faulty origin stage is highlighted and the thermal outcome can be
lightly emphasized, making the tab easier to use for demos and thesis figures
without claiming circuit-level or device-level realism.

The GUI also includes a `Custom Experiment` tab for driving the simulator's
custom single-fault and lightweight multi-fault CLI paths from Tkinter. The
single-fault builder lets you configure:

- fault type
- fault behavior (`transient` or `permanent`)
- fault start time in milliseconds
- fault duration in milliseconds
- fault parameter / severity

Supported custom fault types in the GUI are:

- `sensor_bias`
- `sensor_interface_intermittent`
- `stale_sensor_data`
- `pump_degraded`
- `fan_stuck_off`
- `calibration_memory_corruption`

Typical GUI custom-run workflow:

1. open `python3 scripts/virtual_ecu_gui.py`
2. go to the `Custom Experiment` tab
3. choose the fault type, behavior, start time, duration, and parameter
4. for the fastest demo flow, use `Run Custom and Show Figures` or
   `Compare Custom vs Baseline and Show Figures`
5. the GUI automatically loads the custom run into the comparison workflow and
   opens the `Comparison Figures` tab
6. inspect the loaded result in the existing comparison figures, propagation
   evidence, comparison summary, and fault-path views

The `Comparison Summary` tab can also load results that were generated earlier,
without rerunning the simulator. Use `Load Existing as Left` or
`Load Existing as Right`, then select a raw result CSV such as
`logs/recommended_study/fan_stuck_hot_stress.csv` or a file from
`logs/gui_custom/`. The GUI expects the matching summary file beside it using
the deterministic naming convention `<name>_summary.csv`. Once loaded, the run
feeds into the normal comparison summary, figures, propagation evidence,
fault-path view, report export, and snapshot export workflow.

The same comparison tab includes `Showcase / Demo Presets` for thesis and live
demo use. A showcase preset is a curated saved left/right result pair with a
short title and demo description, loaded in one click without rerunning the
simulator. The preset definitions are stored in:

- `presets/showcase_demo_presets.json`

These presets point at existing CSV result pairs such as files in
`logs/recommended_study/` and `logs/gui_custom/`. Loading one refreshes the
comparison summary, figures, propagation evidence, fault-path visualization,
and export/snapshot workflow exactly like a normal comparison. This makes it
easy to start meetings or thesis walkthroughs from a stable, reproducible set
of saved results.

The GUI usability flow is intentionally optimized around common next actions:
start with `Open Showcase Comparison` for the fastest saved demo, use
`Run Built-In Comparison` for selected built-in campaigns, use
`Compare vs Baseline & Open Figures` for custom faults or multi-fault scenarios,
and use `Load Saved CSV as Left/Right` when reusing existing experiment files.
Less common placement options are grouped as advanced actions so first-time use
stays focused.

The main comparison tab also includes a compact `Quick Start / Guided Use`
panel. It is not a wizard; it simply points first-time users to the right tab or
section for showcase demos, built-in comparisons, saved CSV loading, single
custom faults, multi-fault scenarios, and batch-trend inspection.

For live interpretation, the comparison tab also includes a compact
`Comparison Verdict / Key Takeaway` section. It generates a short rule-based
summary from the loaded left/right metrics so thesis or demo users can quickly
see which side is thermally stronger, detects faster, reaches the harsher
safe-state outcome, or serves as the stronger demonstration case overall.

The same comparison area also includes lightweight `Save Session` and
`Restore Session` actions plus optional `Auto-Restore Last Session` startup
behavior. Session state is stored in:

- `presets/gui_session_state.json`

The saved session keeps only lightweight GUI state such as loaded result paths,
selected comparison plot, selected showcase/favorite, custom-form values,
multi-fault scenario builder state, and tab/view context. It does not copy raw
CSV contents, so restore reuses the normal GUI loading pipelines.

Recent GUI activity is kept in a small `Recent Results / Comparisons` section on
the comparison tab. It stores the last few saved comparisons, loaded CSV pairs,
showcase presets, and custom GUI runs in:

- `presets/recent_results.json`

Use the recent buttons to reload a previous result directly into the normal
comparison summary, figures, propagation evidence, fault-path view, and export
workflow. `Clear Recent History` removes the local recent list without touching
the underlying experiment CSV files.

Important recurring comparisons can also be pinned in a separate
`Favorites / Pinned Comparisons` section. Favorites are intentionally saved
left/right result pairs with a title and optional note, stored in:

- `presets/favorite_comparisons.json`

Use favorites for stable thesis/demo pairings or research checkpoints you want
to reopen quickly without relying on short-term recent history.

The same tab now also includes a `Multi-Fault Scenario` builder for small
ordered scenarios with 2 to 4 fault events. Each event stores:

- fault type
- fault behavior
- fault start time in milliseconds
- fault duration in milliseconds
- fault parameter / severity

The multi-fault builder also includes a lightweight live `Scenario Timeline`
panel. It draws the current ordered event list on a shared horizontal time axis
so you can quickly see fault type, start time, duration, and transient versus
permanent behavior before running the scenario. The view is intentionally kept
clean and presentation-friendly so it works well in thesis/demo screenshots.

The GUI uses a minimal simulator CLI extension for this path:

- `./virtual_ecu <log_path> custom_multi <event_count> <fault_type> <start_ms> <duration_ms> <fault_behavior> <parameter> [...]`

Typical multi-fault workflow:

1. open `python3 scripts/virtual_ecu_gui.py`
2. go to the `Custom Experiment` tab and open `Multi-Fault Scenario`
3. add, update, remove, or reorder 2 to 4 events
4. use the live scenario timeline to sanity-check the staged sequence
5. for the fastest demo flow, use `Run Scenario and Show Figures` or
   `Compare Scenario vs Baseline and Show Figures`
6. the GUI automatically loads the scenario into the comparison workflow and
   opens the `Comparison Figures` tab
7. use the existing comparison summary, propagation evidence, fault-path view,
   exports, and snapshots exactly as with built-in campaigns

The same `Custom Experiment` tab also supports lightweight named presets for
repeated demo and experiment setup for both single-fault and multi-fault
configurations. Use:

- `Save Preset` to store the current custom form settings
- `Load Preset` to restore a saved or built-in starter preset into the form
- `Delete Preset` to remove a user-saved preset
- `Save Scenario Preset`, `Load Scenario Preset`, and `Delete Scenario Preset`
  from the multi-fault builder for ordered multi-event scenarios

Presets are stored deterministically in:

- `presets/gui_custom/<preset_name>.json`

Each preset stores:

- preset name
- either a single event:
  fault type,
  fault behavior,
  start time,
  duration,
  and parameter
- or an ordered multi-fault event list with the same fields per event

Starter presets such as `sensor_bias_demo`, `stale_sensor_data_demo`, and
`fan_stuck_off_demo` are available directly in the GUI for fast single-fault
walkthroughs, and multi-fault starter presets such as
`sensor_bias_then_fan_loss_demo` and `stale_then_pump_demo` are included for
staged scenario demos. Presets are useful because they let you repeat the same
custom configuration across meetings, figures, and comparison runs without
retyping parameters or rebuilding the ordered event list.

Custom GUI runs are saved deterministically in:

- `logs/gui_custom/<custom_configuration>.csv`
- `logs/gui_custom/<custom_configuration>_summary.csv`

This keeps both the single-fault and multi-fault custom paths reproducible and
makes it easy to rerun the same scenario for demos, thesis figures, or paper
appendix material.

The GUI also includes a lightweight `Batch Results` tab for loading an existing
aggregate summary CSV such as `results/batch/paper_quick/aggregate_summary.csv`.
That tab provides:

- number of runs in the loaded batch
- fault classes present
- fault types present
- per-fault-type averages for detection latency, safe-state latency, maximum coolant temperature, and safe-mode duration
- dominant final safe-state visibility by fault type
- a selector-driven batch plot area for:
  mean detection latency,
  mean safe-state latency,
  mean maximum coolant temperature,
  mean safe-mode duration,
  and final safe-state distribution by fault type

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
- `results/gui_comparison_reports/<left>_vs_<right>/cross_layer_propagation_timeline.csv`
- `results/gui_comparison_reports/<left>_vs_<right>/cross_layer_propagation_summary.txt`
- `results/gui_comparison_reports/<left>_vs_<right>/cross_layer_propagation_timeline.png`

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

Before a batch profile is rerun, the batch runner removes its previous
`aggregate_summary.csv` and `runs/` directory for that batch ID. This keeps the
run folder reproducible and prevents stale CSV files from surviving beside the
current aggregate.

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

## Propagation Reports

For a single raw campaign CSV, generate a compact cross-layer propagation
bundle that highlights the explicit chain from hardware-origin fault to ECU
manifestation, diagnostic effect, and safe-state/system effect:

```sh
python3 scripts/generate_propagation_report.py logs/recommended_study/fan_stuck_hot_stress.csv
```

This writes a small bundle beside the input CSV (or to a custom `--output-dir`)
containing:

- `propagation_timeline.csv`
- `propagation_summary.txt`
- `propagation_timeline.png`

The propagation summary is intended to be thesis/demo friendly:

- a short campaign-aware research framing line
- a four-step propagation chain with evidence and timing
- key timings from first fault to ECU, diagnostic, and system consequences
- a chronological milestone list

The propagation CSV is intended to stay easy to inspect in a spreadsheet:

- `chain_stage` rows for the four-step causal story
- `timeline_item` rows for the chronological supporting evidence
- phase labels, observed signals, and latency-from-first-fault fields

The same propagation view is also available directly inside the GUI comparison
plot selector and is included in exported GUI comparison/snapshot bundles.
The recommended workflow also regenerates curated propagation bundles for the
strongest recommended cases:

- `fan_stuck_hot_stress`
- `calibration_memory_corruption`
- `stale_sensor_data_hot_stress`
- `paper_default`

## Paper Tables and Figures

Generate the main paper tables and figures from the current campaign logs:

```sh
python3 scripts/generate_paper_results.py
```

This writes the following outputs to `results/paper/` by default:

- `results/paper/table_1_campaign_definition.csv`
- `results/paper/table_2_cross_campaign_results.csv`
- `results/paper/figure_1_coolant_temperature_vs_time.png`
- `results/paper/figure_2_safe_state_timeline.png`
- `results/paper/figure_3_fan_command_vs_actual.png`

For the recommended thesis/paper bundle, prefer the integrated workflow:

```sh
make recommended-study
```

If using `generate_paper_results.py` directly, it reads campaign logs from
`logs/recommended_study/` by default. You can override the input and output
locations with `--logs-dir` and `--results-dir`.

The script uses Python 3 and Matplotlib, which are available on a typical WSL Python setup.
