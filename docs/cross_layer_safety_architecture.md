# Cross-layer safety v2

V2 extends the accepted `9299c04` foundation. It adds temporal fault behavior,
real sensor-delivery and control-delay models, an explicit observation/evaluation
boundary, and opt-in experimental hazard/containment assessment. The original
v1 architecture and metric definitions are retained below as a versioned record.
They describe v1 runs with hazard monitoring disabled; this section defines v2.

## Modules

`cross_layer_config.c` parses and validates typed descriptors; the shared
`cross_layer_fault_step` schedules all active windows. `sensor_delivery.c`
implements generated-sample history and delivery changes. The real scheduler
continues to call or defer `control_step`. `runtime_observation.c` constructs
separate runtime and evaluation snapshots. `hazard_model.c` is an evaluation
module, never a runtime detector or a safety actuator. YAML/JSON campaign expansion,
statistics, and figures live in `python/virtual_ecu/cross_layer_campaign.py`.
No detector, Hybrid Adaptive Kalman threshold, RTL payload, or safety policy
was retuned. YAML uses the already available PyYAML package, now declared in requirements.txt;
JSON input remains supported without it.

## Temporal behavior and memory faults

All times are simulated integer milliseconds on 100 ms ticks. Activation precedes
sensing/control in the same tick. All fault models share these policies:

- **Transient:** active on `[start_ms, start_ms + duration_ms)`; restoration at
  the interval end. The original transient `deadline_miss` accepts 100 ms and
  skips exactly one job, preserving v1.
- **Permanent:** active from start through the last simulated tick. Duration
  is ignored; there is no synthetic recovery at simulation end.
- **Intermittent:** duration bounds the entire train. The train begins ON;
  phase is `(time-start) % (on+off)`. Phase less than ON is active. ON/OFF
  periods must be positive, aligned, and bounded. Windows are deterministic.

`fault_active` (also the preserved `fault_injection_active`),
`fault_activation_count`, `current_fault_phase`, `last_activation_ms`, and
`last_recovery_ms` describe these transitions. Phases are disabled, waiting,
active, inactive, and recovered. First injection and propagation timestamps
remain first-ever observations. Repeated activation does not reset propagation
history. Last recovery refers to the injected condition, not guaranteed recovery
of outstanding jobs, plant effects, or hazards.

`bit_flip` saves and XORs the real whole-degree target register **once per ON
window**, holds it, and restores it at OFF/recovery. A permanent flip persists;
it is not continuously toggled. `stuck_bit` forces bit 0–5 to `stuck_polarity`
0 or 1 on every active scheduler update before the controller consumes the
register. Rewriting the register during activation is corrected at its next
scheduled consumption. OFF/recovery restores the saved original. This is a
sampled register fault, not a gate-level continuous-time electrical simulation.

Both models use the existing bounded `uint16_t` target. From 92 °C, each single
bit operation produces 76–124 °C, within existing target bounds. No float bit
reinterpretation occurs. Forcing a bit already equal to the stuck polarity is
a real activated constraint with **no observed corruption**: internal timestamps
remain N/A, and containment/FTTI are N/A when no effect occurs. Original and
effective values, polarity, index, activation count, and recovery are logged.

## Sensor data-path semantics

Each sensor tick first generates a real sample from the existing sensor model.
A bounded ring holds 256 samples and their acquisition timestamps. The new
models intercept delivery between this generator and `coolant_temp_meas_c`;
they never write the plant. Existing `stale_sensor_data` and RTL replay remain
unchanged. Combined new/legacy faults and monitored external replay remain
unsupported rather than creating ambiguous references.

| Model | Delivery behavior |
| --- | --- |
| delayed_update | During each ON window, newly generated samples are held for `communication_delay_ms`; after the initial delay, a sample generated at t is delivered exactly at t+delay. Until then the last delivered sample is retained. Recovery flushes pending delayed samples and delivers the current sample. |
| dropped_update | Without a pattern, discard the first `drop_count` scheduled deliveries of each ON window. With period P=`drop_every_n_updates`, repeat N=`drop_count` dropped deliveries followed by P−N delivered updates, aligned to the window start. N≤P; N=P drops all. No randomness. |
| replayed_sample | At every active tick deliver the real historical sample generated `replay_age_ms` earlier. It retains its historical packet acquisition timestamp. Replay requires enough history before first activation; unavailable history is rejected through configuration constraints. |

Delay and replay age must be positive multiples of 100 ms and less than 25600
ms. Replay age must not exceed start time. Inactive communication models deliver
current samples normally. Delivery and generation are distinct: a new sample
can be generated even when no update reaches the ECU.

Telemetry includes generated/current value, last delivered value and delivery
time, delivered sample age, generated/delivered/dropped flags, consecutive and
total drops, delayed/replay flags, configured delay, and replay source timestamp.
`sample_generated_ms` refers to the newest sample, not the retained one.
`sample_delivered_ms` retains the last successful delivery time during a hold.
`sample_age_ms` is now minus the delivered sample's acquisition timestamp.

The ECU-facing packet exposes its acquisition timestamp for freshness checks.
In this replay model that timestamp is preserved, not forged. The dedicated
`replay_source_timestamp_ms` provenance field is evaluation-only. A model with
forged fresh timestamps is a different future threat model; no detector receives
hidden replay labels or history indices.

## Real task delay

`task_delay_ms` is a positive multiple of 100 ms. An active release at t creates
one pending job due at t+delay. The controller does **not** execute at t. At the
due tick it computes using then-current sensor/context inputs. This models
dispatch delay, not a frozen-input execution-time calculation.

There is at most one outstanding control job. Nominal releases while it is
pending are discarded, including the release coincident with its completion.
There is no catch-up burst or second control computation in that tick. The next
tick can release another job. A queued job completes even if its injection
window has since ended. Sensing, diagnostics, detector, safety, actuator
realization, and plant integration continue on their nominal schedule.

`nominal_release_ms`, `actual_execution_ms`, actual `task_delay_ms`, `deadline_ms`,
`deadline_missed`, `execution_skipped`, `control_release_discarded`, and configured
delay are appended. Relative deadline is one 100 ms control period. Execution
exactly at deadline meets it; a pending job still unfinished at that timestamp
has missed it. A deliberately skipped `deadline_miss` job records the known miss
at its release (the v1 convention). `execution_skipped` means no computation
this tick; `control_release_discarded` separately identifies discarded releases
on ticks that may execute the older job. Delay is blank while no job executes.

## Observability boundary

See [detector_observability_boundary.md](detector_observability_boundary.md).
`runtime_observation_t` is an allowlisted value snapshot without fault labels,
plant truth, reference state, propagation, or hazard fields.
`experiment_ground_truth_t` is declared in a separate header and contains the
fault descriptor, actual/reference plant values, reference runtime snapshot,
and propagation truth. Only evaluation constructs/consumes that second type.
No new detector was added; accepted legacy detectors retain their explicit,
documented historical exceptions.

## Experimental hazard model

Enable with `--hazard-monitor on`, or supply a hazard/FTTI option. This also
enables reference monitoring. Defaults are existing warning=108 °C,
critical=115 °C, maximum consecutive critical exposure=1000 ms, FTTI=5000 ms,
and containment hold=1000 ms. Values are study parameters, not certified OEM
limits. Hazard options do not alter any runtime detector or safety threshold.

Critical temperature means true coolant ≥ configured critical threshold. Every
completed interval contributes to total critical exposure when its left endpoint
was critical. No interval after the final logged time is counted. Consecutive
exposure resets on a noncritical sample. Hazard starts at the first critical
sample whose continuous episode has lasted at least the configured allowance;
allowance=0 declares hazard at the crossing itself. A brief crossing is recorded
by `critical_threshold_entered` even when it never becomes a sustained hazard.

Hazard exits at the first subsequent noncritical sample. `hazard_entered` is
latched, `hazard_active` is current, and `hazard_entry_ms`/`hazard_exit_ms` retain
the first entry and its first exit; subsequent episodes contribute to exposure
and current flags. Exposure covers the observed run, including pre-injection
history. Hazards present at or before the injection tick are pre-existing (that plant
sample precedes the injection's physical effect). These are explicitly flagged and excluded from
fault-attributed containment/FTTI and hazard-rate denominators.

## Containment and FTTI contract

A run is eligible after injection has produced an observed internal, control,
actuator, or plant effect and no hazard already existed before injection.
Baseline, activation with no observed effect, and pre-existing hazards are N/A.
Detection alone is never a containment condition.

A containment candidate requires true coolant **strictly below warning** and
one of:

1. an applied protective mode; or
2. inactive injection with resolved runtime/physical effects relative to the
   independent reference: coolant and delivered temperature within 0.01 °C,
   calibration/commands/actuator values within 1e-6, and acquisition/execution
   timestamps equal.

The condition must remain true for the configured hold. `containment_time_ms`
is that stable interval's confirmation time. A later violation clears the
candidate/time; final metrics describe the stable tail of the observed run,
not an early success that a later intermittent episode invalidated. A passive
fault recovery can therefore satisfy the contract without any alarm. Permanent
corruption may satisfy it through a thermally effective protective mode.

`containment_success=1` requires that stable tail and **no hazard entered** in
the observed run. Prior hazard makes success 0 even if temperature later recovers.
`containment_latency_ms` measures stable-tail confirmation minus injection and
can describe late thermal recovery even when the no-hazard success criterion
failed. It is blank if stability was never demonstrated.

FTTI is measured from first injection to stable-tail confirmation, **including
the hold**, with equality accepted. `ftti_met=1` requires no hazard and latency
≤ FTTI. A hazard or expiration without maintained confirmation gives 0. An
incomplete run before the FTTI deadline with no outcome remains N/A. Eventual
containment can succeed after FTTI has failed. Metrics are observation-horizon
statements, not guarantees about future unobserved operation.

| Field | V2 rule |
| --- | --- |
| detected_before_plant_manifestation | V1 strict ordering, only when both events occur |
| detected_before_hazard | If an attributable hazard occurs, 1 when differential alarm precedes it; 0 otherwise. N/A without hazard |
| safe_state_reached | Preserved v1 differential applied protective-mode observation, not hazard containment |
| safe_state_before_hazard | Same ordering rule using v1 protective-mode timestamp; absence of a mode before an observed hazard is 0 |
| hazard_entered | Actual configured sustained-hazard observation, independent of detector success |
| critical_exposure_time_ms | Total run exposure at the configurable critical threshold |
| unsafe_exposure_time_ms | Preserved v1 post-injection exposure at fixed 115 °C; use critical_exposure_time_ms for configurable v2 study exposure |
| containment_success | Eligible stable tail and no observed hazard; opt-in filling of v1's formerly blank column |
| containment_latency_ms | Stable-tail confirmation − injection; N/A without confirmation |
| ftti_met | Above experimental timing contract; explicit N/A for ineligible/censored cases |
| silent_corruption | Preserved v1: internal corruption was observed but no differential alarm occurred through the horizon, even if corruption recovered |

All other existing v1 fields retain their definitions. No missing latency is
converted to zero. The runtime legacy false-positive/latency bookkeeping still
uses legacy campaigns; new reports use the separate cross-layer alarm timing.

## Normalized analysis stages

The hazard-enabled evaluation appends `max_propagation_stage` and
`propagation_path_signature` while preserving v1 `propagation_depth` unchanged.

| Stage | Evidence |
| --- | --- |
| 0 | Injection, no further stage required |
| 1 | Internal ECU corruption |
| 2 | Control-visible effect |
| 3 | Actuator command or realization deviation |
| 4 | Defined physical-plant manifestation |
| 5 | Defined attributable sustained hazard |
| 6 | Safety response or successful containment/recovery outcome |

The signature contains only observed stages in normalized analysis order, e.g.
`communication>sensing>control>actuator>plant>hazard>safety`. It is not a claim
that every stage occurred or that safety chronologically followed the plant.
A protective response can precede plant/hazard manifestation. Use the timestamp
table for chronology. No injection means stage/path N/A. Current containment
can be invalidated by later samples; stage 6 from a recorded safety response
or earlier successful recovery remains observed even if final containment fails.

## Campaign format and reproduction

```bash
make
python3 -m unittest discover -s tests -v
python3 scripts/run_cross_layer_campaign.py studies/cross_layer_vts_candidate_v1.yaml
```

The candidate uses YAML because PyYAML is available. JSON is also supported.
The runner expands configuration-defined
Cartesian products; it contains no candidate matrix. The config specifies
profiles (path, duration, optional per-profile injection times), detector/action
pairs, seeds, hazard settings, baseline inclusion, and `fault_cases`. Each case
has ID, model, layer/target, behavior, fixed `parameters`, and nonempty list-valued
`grid` dimensions. Supported dimensions include timing, duration, bit index,
polarity, delivery delay, drop count/pattern, replay age, task delay, ON/OFF, and
seed. The default matrix has 182 runs: 180 injected cases and two baselines.

The nominal profile lasts 120 s with injections at 20100, 60100, and 90100 ms.
The existing `example_driving_profile.csv` lasts 300 s, includes a high-load/hot
final phase, and uses 20100, 150100, and 220100 ms. All candidate runs select
unchanged Hybrid Adaptive Kalman with observe-only detector action; built-in
safety remains active. All models are deterministic, so seed 42 is used once
rather than inventing independent random replications. The schema supports
seed lists for future random models or explicit reproducibility checks.

Output is `results/cross_layer_safety_v2/`: raw/summary traces, campaign runs,
overall and layer/model/behavior/profile tables, propagation, hazard/FTTI,
containment, silent-corruption tables, Markdown report, six data-driven figures
where eligible, figure caption counts, captured JSON/commands, and raw SHA-256
manifest. Baselines and N/A outcomes are excluded from fault-rate denominators;
no-effect stuck constraints are included in injection/detection denominators but
excluded from inapplicable containment/FTTI denominators. Means/medians exclude
missing latencies, not legitimate zeros. Grouped distributions and figure
counts remain inspectable. Pooled deterministic case proportions are not
population failure probabilities; severities/durations are not matched.

The runner refuses to write inside v1 evidence. The GUI's single experiments and
five-case compatibility study also write under v2, leaving `results/cross_layer_safety_v1/`
untouched. Only the existing Cross-Layer Safety page changes: new model/behavior
controls, FTTI and hazard settings, campaign run/load, outcome cards, and a
selectable stage/timestamp/latency table. Campaign controls select a YAML or JSON study;
single-run controls apply to single experiments. Old/v1 files show N/A for
unavailable new fields.

## V2 limitations and next step

One injected new descriptor per run, fixed 100 ms sampling, bounded history,
one pending control job, deterministic timing, and simplified plant physics
remain deliberate boundaries. The stuck-bit model is enforced at scheduler
consumption, replay preserves packet timestamps, and delay recovery flushes
queued samples. Hazard/FTTI/containment rules are experimental model contracts.
No transistor behavior, CPU WCET contention, production runtime-signal purity,
functional-safety certification, or full digital twin is claimed.

Next: define fault-specific safety contracts and an explicit legacy-detector
migration plan, then study sensitivity to those contracts and validated plant
parameters without retuning the detector against these results.

---

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
