# Cross-layer safety foundation (v1)

This extension establishes a **cross-layer automotive Virtual ECU safety
experimentation platform**. It connects two concrete fault origins to runtime
ECU state, control execution, actuator commands and realizations, thermal-plant
manifestation, existing runtime alarms, and protective modes. It is an
engineering implementation and validation package, not a complete digital twin
or a functional-safety certification claim.

## Modules and separation

- `include/fault_model.h`: typed descriptor and injection runtime state.
- `src/cross_layer_fault.c`: CLI configuration, validation, register injection,
  restoration, and control-execution permission.
- `src/scheduler.c`: the actual skipped control call; optional independently
  evolved, fault-free reference using the same scheduler and ECU modules.
- `src/propagation_monitor.c`: experiment-only comparisons and safety metrics.
- `src/logger.c`: appended telemetry, preserving all previous column positions.
- `python/virtual_ecu/cross_layer_safety.py`: reporting and nullable CSV loading.
- `scripts/run_cross_layer_safety_study.py`: five-case engineering study.
- `python/virtual_ecu/cross_layer_gui.py`: minimal functional GUI panel.

The reference is a local scheduler variable. No reference pointer is added to
`ecu_state_t`. Only instrumentation receives both states; the controller,
diagnostics, detector, safety monitor, actuators, and plant receive their own
state as before. Detector implementations and thresholds are unchanged.

## Unified fault descriptor

`fault_descriptor_t` contains `enabled`, numeric `fault_id`, typed `layer`,
`model`, `behavior`, `target`, `start_ms`, `duration_ms`, `parameter`, `bit_index`,
32-bit `seed`, `intermittent_on_ms`, and `intermittent_off_ms`.

| Dimension | Representable values |
| --- | --- |
| Layer | hardware, memory, timing, communication, sensing_control, actuator |
| Model | legacy, bit_flip, stuck_bit, deadline_miss, task_delay, stale_data, dropped_update, value_corruption, degraded_actuator |
| Behavior | transient, permanent, intermittent (plus legacy none) |
| Target | control_target_register, control_task, coolant_sensor, pump, fan (plus none) |

Only memory/bit_flip/control_target_register/transient and
timing/deadline_miss/control_task/transient have executable new injectors in v1.
Other descriptor values are architectural extension points, not claimed
implementations; CLI requests for unsupported configurations fail explicitly.
The generic parameter and intermittent fields are reserved and do not affect
these deterministic injectors. `fault_id` is an unsigned experiment identifier,
not a detector signal or free-form target name.

The original `fault_mode_t`, `fault_event_t`, campaigns, custom single/multiple
fault interfaces, and their numeric enum values remain intact. The shared
behavior enum preserves none=0, transient=1, permanent=2 and appends
intermittent=3. Legacy activation continues through `fault_injection_step`.
Reporting maps legacy modes to descriptive cross-layer metadata without
claiming that their injectors now implement the new models. Full legacy
migration and mixed legacy/new injections are deferred.

## Real memory corruption

`control.target_register_c` is a mutable `uint16_t` backing the nominal
whole-degree control target, initialized to 92. The normal controller reads
this register on every control execution. Existing calibration offsets and
RTL replay retain their prior float semantics; their values are not quantized.

Immediately before the configured control execution, injection saves the
original register, performs `original ^ (1U << bit_index)`, and writes the result
back. Valid indices 0–5 produce respectively 93, 94, 88, 84, 76, and 124 °C from
92 °C. All are within the simulator's 60–130 °C target range. No floating-point
bit patterns, NaNs, compile-time constant writes, random indices, or downstream
plant edits are involved.

The register is flipped **once**, held during `[start, start + duration)`, and
restored to its saved original at the first execution at the end of that
interval. Duration is a positive multiple of 100 ms. This models a transient
register upset with scheduled restoration, not ECC or a stuck bit. The raw CSV
records original/corrupted whole-degree values, bit index, descriptor, active
window, and injection timestamp. Original/corrupted fields remain blank before
injection and are retained afterward for reproducibility.

## Real timing fault

The scheduler calls `cross_layer_control_execution` only when the control task
is due. For `deadline_miss`, it skips exactly the configured `control_step`
call. The previous control computation and its execution timestamp remain in
place. Sensors, actuator realization, diagnostics, safety, detector, logging,
and plant integration still run. Safety may legitimately override a held
command; skipping control does not suppress safety.

At the skipped slot, expected execution time is logged, actual execution time
and delay-to-execution are blank, and deadline-miss/skipped flags are 1. There
is no invented delayed execution: the job is discarded. At the next nominal
slot, actual execution resumes and the recovery flag is 1 for that slot only.
The nominal period is 100 ms, and this model accepts only duration=100 ms.
`control_task_last_execution_ms` exposes retained execution age independently
of whether command values happen to change. No physical-plant field is written
by the injector.

## Propagation observations and reference

New fault runs enable monitoring automatically. `--cross-layer-monitor on`
enables it for baseline or legacy experiments. Without either, no reference
simulation runs and propagation fields are unavailable.

The reference starts from the same initialization and uses the same driving
profile, campaign environment parameters, duration, detector selection, and
safety policy, with all injected events disabled. It evolves its own sensors,
controller, actuators, diagnostics, detector, safety, and plant. Reference
initialization clears event count and injection state. External trace replay
is rejected only when this new monitoring mode is enabled: replaying an
externally corrupted trace would not constitute a clean counterfactual.

At each time t, both states execute sensing/control, the monitor compares
control outputs before safety, both execute reactions, and the monitor compares
final applied commands, realizations, and the plant. Logging precedes plant
integration, as before. Therefore the plant stored at t reflects commands
applied in the previous interval; an injection at t cannot manifest in that
plant sample. Alarms and safety reactions can occur in the same scheduler tick
as injection, before a plant effect. Their within-tick ordering is defined by
the scheduler, not inferred from different millisecond timestamps.

| Timestamp | First qualifying observation at/after injection |
| --- | --- |
| `fault_injection_ms` | Actual register write or skipped job; legacy injector activation for legacy runs |
| `propagation_internal_ms` | New register corruption or stale execution state; for legacy runs, differential sensor residual/freshness or active target corruption |
| `propagation_control_ms` | Pre-safety active target, computed commands, or last-execution timestamp differ from reference |
| `propagation_actuator_command_ms` | Final applied pump or fan command differs from reference by more than 1e-6 |
| `propagation_actuator_realization_ms` | Final realized pump or fan output differs by more than 1e-6 |
| `propagation_plant_ms` | Absolute coolant temperature difference from reference is at least 0.01 °C |
| `propagation_detector_ms` | Selected runtime alarm is active while reference alarm is inactive |
| `propagation_safety_response_ms` | Requested protective mode is more severe than reference request |
| `propagation_safe_state_ms` | Applied protective mode exceeds reference mode and max-cooling override is active |

These tolerances belong only to experiment reporting, not detector calibration.
Comparisons use C float state before CSV rounding. Reference coolant and signed
coolant deviation are appended at nine decimal places so the plant criterion
can be inspected. Legacy command columns retain their existing three-decimal
precision; very small command differences may only be visible in stage flags.

Internal sensor corruption compares measurement-minus-own-plant residuals,
not a difference between true plant trajectories. Thus feedback from a faulty
actuator is not mislabeled as internal sensor corruption. Actuator-origin
faults can enter the chain at realization and only later affect control;
missing earlier stages are not fabricated. For the two new faults, reached
forward stages have causal, nondecreasing timestamps. A missed job at a nearly
steady operating point may never cross the plant criterion.

Each field retains its first qualifying timestamp. C uses -1 for not reached;
CSV emits blanks. Alarm/safety observations are differential evidence relative
to this reference, not proof of causal exclusivity. A fault and clean run can
both alarm, in which case that alarm is not attributed to the fault. Baseline
has no injected event and no fault-attributed alarm/safety timestamp.

## Safety metrics

Raw metric columns are cumulative through the current observation. Study
summaries take the final logged row (120000 ms by default), not the extra plant
update the legacy scheduler performs after its final logged sample.

| Metric | Definition / availability |
| --- | --- |
| `injection_to_internal_latency_ms` | First internal timestamp minus injection |
| `injection_to_control_latency_ms` | First control timestamp minus injection |
| `injection_to_actuator_latency_ms` | First final command deviation minus injection; realization is recorded separately |
| `injection_to_plant_latency_ms` | First plant manifestation minus injection |
| `cross_layer_detection_latency_ms` | Differential runtime alarm timestamp minus injection |
| `detection_to_safety_response_latency_ms` | First differential safety request minus differential alarm; blank if either missing or safety preceded detection |
| `propagation_depth` | Furthest reached effect stage: 0=none, 1=internal, 2=control, 3=command, 4=realization, 5=plant; not a count of all stages |
| `detected_before_plant_manifestation` | Strict alarm time < plant time; defined only when both occur |
| `safe_state_reached` | A differential protective mode was applied; does not mean coolant is safe or hazard contained |
| `unsafe_state_entered` | True coolant temperature reached the existing 115 °C critical threshold at any post-injection observation |
| `unsafe_exposure_time_ms` | Sum of completed post-injection intervals whose left endpoint was >=115 °C; no time beyond final observation |
| `containment_success` | Always unavailable: no fault-tolerant time interval or hazard contract has been defined |
| `silent_corruption` | Internal corruption observed and no differential alarm yet, through the reporting horizon; not necessarily hazardous |

Missing endpoints produce blank latencies, never fabricated zeroes. Zero
latency means events occurred in the same 100 ms tick. Baseline has depth=0
and zero seen flags, but injection-dependent safety metrics are N/A. Old
uninstrumented CSVs have all cross-layer metrics N/A, including seen flags;
they are not silently reported as fault-free experiments.

## CLI and reproducibility

```bash
make
./virtual_ecu logs/cross_layer_bitflip.csv baseline \
  --cross-layer-fault bit_flip --fault-layer memory \
  --fault-target control_target_register --fault-behavior transient \
  --fault-start-ms 45000 --fault-duration-ms 100 --bit-index 3 --seed 42

./virtual_ecu logs/cross_layer_deadline.csv baseline \
  --cross-layer-fault deadline_miss --fault-layer timing \
  --fault-target control_task --fault-start-ms 45000 --seed 42

python3 scripts/run_cross_layer_safety_study.py
python3 -m unittest discover -s tests -v
```

New options are removed before the existing CLI parser runs, so existing
positional custom-event groups and detector/profile suffix options remain
valid. Layer/target default to the selected model's implementation; explicit
mismatches fail. Defaults are start=45000 ms, duration=100 ms, bit=3, fault ID=1,
seed=0. Start and duration must align to the control period, and restoration /
recovery must fit inside the simulation. Negative/overflowing numeric values,
unsupported behavior, and combinations with legacy faults fail before logging.

`--seed` accepts 0..4294967295, including on baseline/legacy runs. It is recorded
but not used by either deterministic injector; changing it alone does not change
execution. Same build, configuration, and seed reproduce identical CSVs. No
cross-machine floating-point bitwise equivalence or random fault coverage is
claimed. Future stochastic injectors must use descriptor-local seeded state.

## Study and GUI

The study writes `results/cross_layer_safety_v1/` with `raw/`,
`cross_layer_run_summary.csv`, `propagation_summary.csv`,
`safety_metrics_summary.csv`, `cross_layer_safety_summary.md`, and
`commands.json`. Generated output is ignored by git. `--output-dir` and `--seed`
can select an isolated output directory and experiment seed.

It runs baseline, a bit-5 flip (92→124 °C for 100 ms), one missed control job,
a 6 °C sensor bias, and a degraded pump (scale 0.45). All injections start at
45000 ms; legacy comparison faults last 10000 ms. All use the default 120 s
profile and Hybrid Adaptive Kalman with limp-home action. The longer legacy
faults are comparisons of propagation paths, not matched-severity experiments.

The **Cross-Layer Safety** GUI page exposes layer, model, target, transient
behavior, start, duration, bit index, and seed. Model/layer choices synchronize;
inapplicable timing fields are disabled. The three buttons run a single
experiment, run the five-case study, and load raw/aggregate results. Execution
uses the existing background-task mechanism. The summary displays injection,
detection, plant manifestation, applied protective mode, latency, and depth.
Old CSVs load with N/A for new fields. Existing pages remain in their previous
notebook order; this page is appended.

## Compatibility audit and limitations

The C and Python detector files, their thresholds, diagnostics, safety policy,
RTL logic/study, and accepted results are unchanged. Legacy columns are
appended to, never reordered. The C summary reader's buffer is enlarged for
extended headers. Existing summary files retain their schema; the new study
uses its dedicated metrics summaries. New results should use
`cross_layer_detection_latency_ms` for fault attribution. Existing
`runtime_detection_latency_ms`, false-positive count, and legacy summary
fault timing still refer to the legacy campaign mechanism and must not be
interpreted as new fault metrics.

**Pre-existing isolation limitations discovered during audit:**
`src/detection_algorithm.c` uses simulator true coolant temperature in sensor
residual evidence, scenario phase / environment parameters in thermal
prediction, and legacy campaign start metadata for detected/action bookkeeping.
`src/diagnostics.c` uses injected behavior/mode for permanent DTC classification.
The safety monitor also uses true coolant temperature for shutdown. These
pre-existing dependencies are preserved to honor the requirement not to change
accepted detector, DTC, safety, or paper-facing behavior. Strict whole-system
production-signal / metadata isolation is therefore **not satisfied** by the
existing platform. No new cross-layer descriptor, active flag, reference state,
or propagation metric is read by those decision implementations. Resolving the
legacy dependencies requires a separately validated detector-interface change.

Other boundaries: one new transient fault per run, one fixed-period control
job, no CPU contention or wall-clock WCET model, no delayed-job queue, no ECC,
no persistent/intermittent new injector, no monitored external RTL replay,
no certified safe-state/hazard contract, and a simplified thermal plant. The
reference roughly doubles simulated work when monitoring is enabled. Runtime
alarms can fail to detect a short upset or missed execution; the monitor keeps
those stages unavailable rather than retuning detectors.

Recommended next step: define an ECU-observable detector input interface and
separate legacy ground-truth bookkeeping from alarm/action state, with explicit
compatibility baselines, before extending fault campaigns and containment/FTTI
metrics.
