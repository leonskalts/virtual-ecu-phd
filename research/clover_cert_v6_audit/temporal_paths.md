# CLOVER-CERT v6 — source-anchored audit

Audited HEAD: `a340ca5cf0473d7dc572f7cd63e44fbc25b175a7`. The working tree is part of the snapshot:
pre-existing untracked research sources were inspected and not promoted to committed
or deployed status. `workspace_baseline.json` records SHA256/size (or symlink target)
for **43,688 pre-existing files / 13,570,258,677 bytes**, including ignored results.
`git_status_before.txt` records the initial modified/untracked paths. HEAD alone is
not sufficient to reproduce these untracked additions.

**VERIFIED** means supported by the particular source operation or interface cited.
**INFERRED** means a deduction conditional on the stated model and trust assumptions.
**UNVERIFIED** means evidence is missing. None means certified hardware behavior.
The source anchors are implementation evidence; comments, labels such as “trusted,”
protocol prose and historical success percentages are not proof of independence.

## Concrete temporal ordering

Base simulated tick `t`: legacy/new fault handling → acquisition → conditional
control → actuator/diagnostics/safety → detector → possible detector safety action
→ optional runtime policy → metrics/paired scoring → CSV → plant integration.
A revised detector wrapper captures at the detector call; a policy capture can
occur after another actuator application. Therefore two rows labeled `t` need not
refer to the same intra-tick command state. No wall-clock duration is measured by
normal `runtime_timing_start/complete`: both receive the same `time_ms`.
A changed command can be visible at `t`, while a newly integrated temperature
change first reaches a sampled observation at a later tick. Coincident effects
must be ordered by code phase as well as timestamp.

`inject_first`: [src/scheduler.c:63](../../src/scheduler.c#L63) (`scheduler_inputs`); `acquire`: [src/scheduler.c:65](../../src/scheduler.c#L65) (`scheduler_inputs`); `control_call`: [src/scheduler.c:73](../../src/scheduler.c#L73) (`scheduler_inputs`); `reaction`: [src/scheduler.c:98](../../src/scheduler.c#L98) (`scheduler_reactions`); `runtime_capture`: [src/scheduler.c:107](../../src/scheduler.c#L107) (`scheduler_reactions`); `revised_capture`: [src/v7_3/revised_runtime.c:178](../../src/v7_3/revised_runtime.c#L178) (`__wrap_detection_algorithm_step`); `log`: [src/scheduler.c:168](../../src/scheduler.c#L168) (`scheduler_run`); `plant_call`: [src/scheduler.c:170](../../src/scheduler.c#L170) (`scheduler_run`); `timing_start`: [src/runtime_timing_observation.c:47](../../src/runtime_timing_observation.c#L47) (`runtime_timing_start`); `timing_complete`: [src/runtime_timing_observation.c:54](../../src/runtime_timing_observation.c#L54) (`runtime_timing_complete`)

## Timing contracts and qualifications

### T_BASE — VERIFIED

Base tick/acquisition/control/actuator/log cadence 100 ms; diagnostics 500 ms. Order: inject, acquire, conditional control, actuator/diagnostic/safety, detector, optional policy, scoring/logging, plant integration.

`tick`: [include/config.h:4](../../include/config.h#L4) (`<file-scope>`); `sensor_period`: [include/config.h:9](../../include/config.h#L9) (`<file-scope>`); `control_period`: [include/config.h:11](../../include/config.h#L11) (`<file-scope>`); `actuator_period`: [include/config.h:12](../../include/config.h#L12) (`<file-scope>`); `diag_period`: [include/config.h:16](../../include/config.h#L16) (`<file-scope>`); `inject_first`: [src/scheduler.c:63](../../src/scheduler.c#L63) (`scheduler_inputs`); `acquire`: [src/scheduler.c:65](../../src/scheduler.c#L65) (`scheduler_inputs`); `control_call`: [src/scheduler.c:73](../../src/scheduler.c#L73) (`scheduler_inputs`); `reaction`: [src/scheduler.c:98](../../src/scheduler.c#L98) (`scheduler_reactions`); `log`: [src/scheduler.c:168](../../src/scheduler.c#L168) (`scheduler_run`); `plant_call`: [src/scheduler.c:170](../../src/scheduler.c#L170) (`scheduler_run`); `log_period`: [include/config.h:18](../../include/config.h#L18) (`<file-scope>`); `safety_period`: [include/config.h:17](../../include/config.h#L17) (`<file-scope>`)

Assumptions: A_CLOCK.

### T_MEMORY — INFERRED

Changing register can be exposed in same-tick runtime capture even if control does not execute; base capture is after reaction, not an implemented pre-consumption sampler. Stuck bit already equal to forced value has no value mismatch until a differing write/probe. Saturation can mask commands.

`flip`: [src/cross_layer_fault.c:85](../../src/cross_layer_fault.c#L85) (`cross_layer_fault_step`); `stuck`: [src/cross_layer_fault.c:96](../../src/cross_layer_fault.c#L96) (`cross_layer_fault_step`); `consume`: [src/control.c:43](../../src/control.c#L43) (`control_step`); `obs_memory`: [src/runtime_observation.c:21](../../src/runtime_observation.c#L21) (`runtime_observation_capture`); `revised_memory`: [src/v7_3/clo_dsf_revised.c:29](../../src/v7_3/clo_dsf_revised.c#L29) (`clo_revised_extract`); `probe_call`: [src/v7_3/revised_runtime.c:45](../../src/v7_3/revised_runtime.c#L45) (`__wrap_cross_layer_fault_step`); `pump_cmd`: [src/control.c:76](../../src/control.c#L76) (`control_step`)

Assumptions: A_SHADOW, A_BUILD, A_CLOCK.

### T_DELAY — VERIFIED

Positive aligned configured delay holds one job; due check happens at subsequent 100 ms releases. Pending jobs survive injection recovery; coincident releases are discarded, not queued for catch-up. Normal control start/complete share now.

`delay_due`: [src/cross_layer_fault.c:134](../../src/cross_layer_fault.c#L134) (`cross_layer_control_execution`); `delay_complete`: [src/cross_layer_fault.c:122](../../src/cross_layer_fault.c#L122) (`cross_layer_control_execution`); `discard`: [src/cross_layer_fault.c:121](../../src/cross_layer_fault.c#L121) (`cross_layer_control_execution`); `timing_start`: [src/runtime_timing_observation.c:47](../../src/runtime_timing_observation.c#L47) (`runtime_timing_start`); `timing_complete`: [src/runtime_timing_observation.c:54](../../src/runtime_timing_observation.c#L54) (`runtime_timing_complete`); `delay_alignment`: [src/cross_layer_config.c:193](../../src/cross_layer_config.c#L193) (`cross_layer_validate`)

Assumptions: A_CLOCK.

### T_SKIP — VERIFIED

Deadline-miss model cancels current release, has no execution timestamp and no deferred job. Fault flag and recorder deadline semantics are distinct; completion exactly at deadline is not late.

`skip`: [src/cross_layer_fault.c:144](../../src/cross_layer_fault.c#L144) (`cross_layer_control_execution`); `exec_missing`: [src/cross_layer_fault.c:46](../../src/cross_layer_fault.c#L46) (`cross_layer_control_execution`); `timing_deadline`: [src/runtime_timing_observation.c:70](../../src/runtime_timing_observation.c#L70) (`runtime_timing_observe`)

Assumptions: A_CLOCK.

### T_STRESS — VERIFIED

Optional stress services simulated 1 ms substeps, control at job completion using then-held input state; runtime snapshot still at 100 ms boundary. Not real wall-clock scheduling. New cross-layer injector cannot be composed via this CLI.

`stress_inner`: [src/scheduler.c:59](../../src/scheduler.c#L59) (`scheduler_inputs`); `stress_complete`: [src/scheduler_stress.c:30](../../src/scheduler_stress.c#L30) (`complete_job`); `stress_queue`: [src/scheduler_stress.c:74](../../src/scheduler_stress.c#L74) (`scheduler_stress_tick`); `stress_publish`: [src/scheduler_stress.c:101](../../src/scheduler_stress.c#L101) (`scheduler_stress_sample`); `stress_exclusive`: [src/main.c:307](../../src/main.c#L307) (`main`)

Assumptions: A_CLOCK, A_BUILD.

### T_COMM — VERIFIED

Delivery/history update only at primary acquisition. Delay/replay/drop differ in internal bookkeeping; age and source timestamp reach runtime. Logging reception timestamp is not equivalent to exporting it in runtime_observation.

`sensor_period`: [include/config.h:9](../../include/config.h#L9) (`<file-scope>`); `history`: [src/sensor_delivery.c:13](../../src/sensor_delivery.c#L13) (`cross_layer_sensor_delivery`); `comm_delay`: [src/sensor_delivery.c:27](../../src/sensor_delivery.c#L27) (`cross_layer_sensor_delivery`); `comm_drop`: [src/sensor_delivery.c:35](../../src/sensor_delivery.c#L35) (`cross_layer_sensor_delivery`); `comm_replay`: [src/sensor_delivery.c:38](../../src/sensor_delivery.c#L38) (`cross_layer_sensor_delivery`); `timestamp_publish`: [src/sensors.c:129](../../src/sensors.c#L129) (`sensors_step`); `obs_timestamp`: [src/runtime_observation.c:9](../../src/runtime_observation.c#L9) (`runtime_observation_capture`); `delivery_time`: [src/sensor_delivery.c:49](../../src/sensor_delivery.c#L49) (`cross_layer_sensor_delivery`)

Assumptions: A_TAP, A_CLOCK.

### T_PULSE — INFERRED

A non-latching sensor-only pulse supported strictly between consecutive acquisition instants produces no sampled deviation. No continuous acquisition in base loop. New injector rejects sub-tick durations; legacy event gates can miss an unaligned interval entirely.

`loop`: [src/scheduler.c:146](../../src/scheduler.c#L146) (`scheduler_run`); `sensor_period`: [include/config.h:9](../../include/config.h#L9) (`<file-scope>`); `sensor_bias`: [src/sensors.c:68](../../src/sensors.c#L68) (`sensors_step`); `sensor_intermittent`: [src/sensors.c:13](../../src/sensors.c#L13) (`intermittent_sensor_error`); `legacy_window`: [src/fault_injection.c:100](../../src/fault_injection.c#L100) (`fault_event_active`); `legacy_config`: [src/experiment.c:287](../../src/experiment.c#L287) (`experiment_configure_custom_single_fault`); `alignment`: [src/cross_layer_config.c:183](../../src/cross_layer_config.c#L183) (`cross_layer_validate`)

Assumptions: A_FAULTSET, A_CLOCK.

### T_PROBE — VERIFIED

With wrapper called each base tick, memory diagnostic checks at 0,1100,...,9900,10000 ms: maximum scheduled gap 1100 ms. Optional multirate helper alternates 600/400 or 300/200 ms; no generic 250 ms WCET promise.

`probe_schedule`: [src/memory_diagnostic.c:11](../../src/memory_diagnostic.c#L11) (`memory_diagnostic_step`); `probe_call`: [src/v7_3/revised_runtime.c:45](../../src/v7_3/revised_runtime.c#L45) (`__wrap_cross_layer_fault_step`); `mr_probe`: [src/v7_3/multirate_memory.c:5](../../src/v7_3/multirate_memory.c#L5) (`mr_memory_step`); `probe_max`: [include/memory_diagnostic.h:7](../../include/memory_diagnostic.h#L7) (`<file-scope>`); `probe_phase`: [include/memory_diagnostic.h:6](../../include/memory_diagnostic.h#L6) (`<file-scope>`)

Assumptions: A_SHADOW, A_BUILD, A_CLOCK.

### T_ADC — VERIFIED

Optional diagnostic sensor catches up period/phase instants <= caller now using endpoint interpolation and publishes latest result. Sample timestamp can predate its actual publication to detector.

`adc_sample`: [src/v7_3/diagnostic_temperature.c:12](../../src/v7_3/diagnostic_temperature.c#L12) (`diagnostic_temperature_sample`); `adc_interpolate`: [src/v7_3/diagnostic_temperature.c:17](../../src/v7_3/diagnostic_temperature.c#L17) (`diagnostic_temperature_sample`); `adc_publish`: [src/v7_3/diagnostic_temperature.c:24](../../src/v7_3/diagnostic_temperature.c#L24) (`diagnostic_temperature_sample`); `triplex_link`: [scripts/run_clo_dsf_triplex.py:178](../../scripts/run_clo_dsf_triplex.py#L178) (`build`)

Assumptions: A_SENSOR, A_BUILD, A_SUBTICK.

### T_MULTIRATE — VERIFIED

Optional template calculates 25/50 ms model samples in a loop at outer now, interpolates endpoints, applies sample-time faults and forwards evidence at outer detector invocation. Control does not consume these additional streams.

`mr_loop`: [scripts/run_clo_dsf_multirate.py:46](../../scripts/run_clo_dsf_multirate.py#L46) (`embedded C: mr_acquire`); `mr_interpolate`: [scripts/run_clo_dsf_multirate.py:49](../../scripts/run_clo_dsf_multirate.py#L49) (`embedded C: mr_acquire`); `mr_inject`: [scripts/run_clo_dsf_multirate.py:55](../../scripts/run_clo_dsf_multirate.py#L55) (`embedded C: mr_acquire`); `revised_capture`: [src/v7_3/revised_runtime.c:178](../../src/v7_3/revised_runtime.c#L178) (`__wrap_detection_algorithm_step`); `source_period_variant`: [scripts/run_clo_dsf_multirate.py:45](../../scripts/run_clo_dsf_multirate.py#L45) (`embedded C: mr_acquire`)

Assumptions: A_BUILD, A_SENSOR, A_SUBTICK.

### T_PUMP — INFERRED

With a matched prior state and clamped pump command identically zero throughout window, scale*0 is zero: pump response/thermal term supply no degradation distinction. Positive excitation can create a same-reaction model gap; sampled plant effect follows integration.

`pump_scale`: [src/actuators.c:90](../../src/actuators.c#L90) (`actuators_step`); `pump_publish`: [src/actuators.c:114](../../src/actuators.c#L114) (`actuators_step`); `pump_thermal`: [src/thermal_plant.c:187](../../src/thermal_plant.c#L187) (`thermal_plant_step`); `plant_integrate`: [src/thermal_plant.c:198](../../src/thermal_plant.c#L198) (`thermal_plant_step`); `log`: [src/scheduler.c:168](../../src/scheduler.c#L168) (`scheduler_run`)

Assumptions: A_PUMP, A_FAULTSET.

### T_DEPLOYMENT — UNVERIFIED

No certified bound from physical fault occurrence to available, intact runtime witness or alarm.

`loop`: [src/scheduler.c:146](../../src/scheduler.c#L146) (`scheduler_run`); `timing_start`: [src/runtime_timing_observation.c:47](../../src/runtime_timing_observation.c#L47) (`runtime_timing_start`); `mr_loop`: [scripts/run_clo_dsf_multirate.py:46](../../scripts/run_clo_dsf_multirate.py#L46) (`embedded C: mr_acquire`)

Assumptions: A_CLOCK, A_SUBTICK. Unresolved: No measured embedded WCET, interrupt response, physical sample timestamp integrity or transport deadline established in this audit.

In stress mode, control completion during substeps can precede the next primary
acquisition. A base same-tick acquisition/consumption rule must not classify every
older consumed sample in stress mode as a communication fault. The recorder's
pending-job fields also differ from complete event histories. For task-delay mode,
`control_task_expected_execution_ms` is the current gate call, while
`nominal_release_ms`/`timing.job_release_ms` track the admitted delayed job. Do not
subtract incomparable release fields when claiming latency.

`stress_inner`: [src/scheduler.c:59](../../src/scheduler.c#L59) (`scheduler_inputs`); `stress_complete`: [src/scheduler_stress.c:30](../../src/scheduler_stress.c#L30) (`complete_job`); `stress_publish`: [src/scheduler_stress.c:101](../../src/scheduler_stress.c#L101) (`scheduler_stress_sample`); `delay_complete`: [src/cross_layer_fault.c:122](../../src/cross_layer_fault.c#L122) (`cross_layer_control_execution`); `discard`: [src/cross_layer_fault.c:121](../../src/cross_layer_fault.c#L121) (`cross_layer_control_execution`); `release`: [src/cross_layer_fault.c:111](../../src/cross_layer_fault.c#L111) (`cross_layer_control_execution`)

## Source-anchored fault-provenance paths

### memory_bit_flip — MEMORY

**VERIFIED source path; variant:** base. One XOR at activation; restore saved value at deactivation.

Injection/operation: `memory_save`: [src/cross_layer_fault.c:82](../../src/cross_layer_fault.c#L82) (`cross_layer_fault_step`); `flip`: [src/cross_layer_fault.c:85](../../src/cross_layer_fault.c#L85) (`cross_layer_fault_step`); `restore`: [src/cross_layer_fault.c:91](../../src/cross_layer_fault.c#L91) (`cross_layer_fault_step`)

Affected state: `control.target_register_c`.

Propagation: register → effective target at executed control → command clamp → actuator realization → next-step plant.

Runtime-visible evidence: E_MEMORY, E_PROBE, E_COMMAND. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_BASE, T_MEMORY. **INFERRED earliest observability:** First intact runtime register/shadow capture after value change; commands need not differ. No separate pre-control monitor invocation in base. No unconditional physical fault-to-observation bound established.

Competing explanations: Unauthorized/legitimate target write when authorization unknown; effective-target offset if only downstream target observed; sensor offset under restricted command view.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_SHADOW. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### memory_stuck_bit — MEMORY

**VERIFIED source path; variant:** base. Force chosen register bit every active step; write callback also enforces stuck bit during optional probes.

Injection/operation: `stuck`: [src/cross_layer_fault.c:96](../../src/cross_layer_fault.c#L96) (`cross_layer_fault_step`); `restore`: [src/cross_layer_fault.c:91](../../src/cross_layer_fault.c#L91) (`cross_layer_fault_step`); `probe_backend`: [src/memory_diagnostic_backend.c:21](../../src/memory_diagnostic_backend.c#L21) (`cross_layer_memory_write`)

Affected state: `control.target_register_c`.

Propagation: stuck storage → target consumption or diagnostic writes → register/shadow/probe evidence → control/plant effects if any.

Runtime-visible evidence: E_MEMORY, E_PROBE, E_COMMAND. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_MEMORY, T_PROBE. **INFERRED earliest observability:** Value mismatch immediately only if forced bit differs. Otherwise next intact opposite-write probe or differing legal target exposes it; may remain unobservable for entire window. No unconditional physical fault-to-observation bound established.

Competing explanations: Healthy storage while bit already equals polarity; bit flip with same changed value without write-response witness; common-corrupted shadow/probe.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_SHADOW, A_BUILD. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### legacy_calibration_offset — MEMORY

**VERIFIED source path; variant:** base. Legacy injector adds offset to local effective target; does not corrupt stored calibration register.

Injection/operation: `legacy_offset`: [src/control.c:53](../../src/control.c#L53) (`control_step`); `target_publish`: [src/control.c:68](../../src/control.c#L68) (`control_step`)

Affected state: `control_step effective_target_c`, `control.active_control_target_c`.

Propagation: local offset → temperature error → commands → actuator/plant.

Runtime-visible evidence: E_MEMORY, E_COMMAND, E_DELIVERED. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_BASE, T_MEMORY. **INFERRED earliest observability:** Executed control publishes modified target; no register mismatch is required. No unconditional physical fault-to-observation bound established.

Competing explanations: RTL calibration replacement; arbitrary effective-target corruption; sensor bias if only temp-error/command observed.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_SHADOW. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### deadline_skip — TIMING

**VERIFIED source path; variant:** base. Cancel active release and skip actual control execution.

Injection/operation: `skip`: [src/cross_layer_fault.c:144](../../src/cross_layer_fault.c#L144) (`cross_layer_control_execution`); `exec_missing`: [src/cross_layer_fault.c:46](../../src/cross_layer_fault.c#L46) (`cross_layer_control_execution`)

Affected state: `control.last_execution_ms held`, `timing recorder cancellation`.

Propagation: release → cancel → old commands retained → actuator/plant.

Runtime-visible evidence: E_TIMING, E_COMMAND. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_SKIP, T_BASE. **INFERRED earliest observability:** Same outer tick recorder cancellation/missing-execution state, if recorder intact. No unconditional physical fault-to-observation bound established.

Competing explanations: Delayed job under command-only view; benign held command without timestamps; recorder tampering.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_CLOCK. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### task_delay — TIMING

**VERIFIED source path; variant:** base. One outstanding job waits until due; actual C execution delayed, not just log relabeling.

Injection/operation: `delay_due`: [src/cross_layer_fault.c:134](../../src/cross_layer_fault.c#L134) (`cross_layer_control_execution`); `delay_complete`: [src/cross_layer_fault.c:122](../../src/cross_layer_fault.c#L122) (`cross_layer_control_execution`); `discard`: [src/cross_layer_fault.c:121](../../src/cross_layer_fault.c#L121) (`cross_layer_control_execution`)

Affected state: `pending_job`, `nominal_release_ms`, `job_due_ms`, `held control output`.

Propagation: release → pending/discarded releases → later actual control using then-current sensor → actuation/plant.

Runtime-visible evidence: E_TIMING, E_COMMAND, E_AGE. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_DELAY. **INFERRED earliest observability:** Pending job/execution absence may be visible immediately; elapsed delay to execution only known on completion. No unconditional physical fault-to-observation bound established.

Competing explanations: Skip under incomplete timing view; stress overload or scheduler interruption; timestamp corruption.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_CLOCK. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### scheduler_overload — TIMING

**VERIFIED source path; variant:** optional scheduler stress. Optional finite-queue scheduler with modeled CPU occupancy/jitter.

Injection/operation: `stress_queue`: [src/scheduler_stress.c:74](../../src/scheduler_stress.c#L74) (`scheduler_stress_tick`); `stress_complete`: [src/scheduler_stress.c:30](../../src/scheduler_stress.c#L30) (`complete_job`); `stress_publish`: [src/scheduler_stress.c:101](../../src/scheduler_stress.c#L101) (`scheduler_stress_sample`)

Affected state: `scheduler_stress.jobs`, `timing_recorder.observation`.

Propagation: modeled release/start/occupancy → completion control → outer sampled timing → actuation.

Runtime-visible evidence: E_TIMING, E_COMMAND. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_STRESS. **INFERRED earliest observability:** First outer publication of delayed/absent execution or violation; internal 1 ms events alone are not an online monitor invocation. No unconditional physical fault-to-observation bound established.

Competing explanations: Configured benign jitter; task delay with matching observed trace; clock/recorder fault.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_BUILD. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### communication_delay — COMMUNICATION

**VERIFIED source path; variant:** base. Suppress early deliveries then select now-delay history.

Injection/operation: `comm_delay`: [src/sensor_delivery.c:27](../../src/sensor_delivery.c#L27) (`cross_layer_sensor_delivery`); `history_match`: [src/sensor_delivery.c:46](../../src/sensor_delivery.c#L46) (`cross_layer_sensor_delivery`); `delivery_source`: [src/sensor_delivery.c:55](../../src/sensor_delivery.c#L55) (`cross_layer_sensor_delivery`)

Affected state: `cross_layer_runtime history/delivery`, `sensors coolant value and source time`.

Propagation: generated sample → history/transport selection → delivered value/time → age → control → actuator/plant.

Runtime-visible evidence: E_DELIVERED, E_AGE, E_TAP, E_TIMING. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_COMM, T_BASE. **INFERRED earliest observability:** First affected acquisition with honest timestamp or different delivered value. Old value can equal current value; source-time difference may still be visible. No unconditional physical fault-to-observation bound established.

Competing explanations: Other transport mechanisms with identical value/time sequence; stale producer/acquisition or corrupt timestamp; normal constant value when metadata unavailable.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_TAP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### communication_drop — COMMUNICATION

**VERIFIED source path; variant:** base. Drop first N updates or repeating configured burst; retain old delivered state.

Injection/operation: `comm_drop`: [src/sensor_delivery.c:35](../../src/sensor_delivery.c#L35) (`cross_layer_sensor_delivery`); `history_match`: [src/sensor_delivery.c:46](../../src/sensor_delivery.c#L46) (`cross_layer_sensor_delivery`); `delivery_source`: [src/sensor_delivery.c:55](../../src/sensor_delivery.c#L55) (`cross_layer_sensor_delivery`)

Affected state: `cross_layer_runtime history/delivery`, `sensors coolant value and source time`.

Propagation: generated sample → history/transport selection → delivered value/time → age → control → actuator/plant.

Runtime-visible evidence: E_DELIVERED, E_AGE, E_TAP, E_TIMING. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_COMM, T_BASE. **INFERRED earliest observability:** First affected acquisition with honest timestamp or different delivered value. Old value can equal current value; source-time difference may still be visible. No unconditional physical fault-to-observation bound established.

Competing explanations: Other transport mechanisms with identical value/time sequence; stale producer/acquisition or corrupt timestamp; normal constant value when metadata unavailable.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_TAP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### communication_replay — COMMUNICATION

**VERIFIED source path; variant:** base. Select older timestamped history at each active acquisition.

Injection/operation: `comm_replay`: [src/sensor_delivery.c:38](../../src/sensor_delivery.c#L38) (`cross_layer_sensor_delivery`); `history_match`: [src/sensor_delivery.c:46](../../src/sensor_delivery.c#L46) (`cross_layer_sensor_delivery`); `delivery_source`: [src/sensor_delivery.c:55](../../src/sensor_delivery.c#L55) (`cross_layer_sensor_delivery`)

Affected state: `cross_layer_runtime history/delivery`, `sensors coolant value and source time`.

Propagation: generated sample → history/transport selection → delivered value/time → age → control → actuator/plant.

Runtime-visible evidence: E_DELIVERED, E_AGE, E_TAP, E_TIMING. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_COMM, T_BASE. **INFERRED earliest observability:** First affected acquisition with honest timestamp or different delivered value. Old value can equal current value; source-time difference may still be visible. No unconditional physical fault-to-observation bound established.

Competing explanations: Other transport mechanisms with identical value/time sequence; stale producer/acquisition or corrupt timestamp; normal constant value when metadata unavailable.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_TAP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### legacy_stale_hold — COMMUNICATION

**VERIFIED source path; variant:** base. Legacy hold mechanism gates refresh of prior sample.

Injection/operation: `legacy_hold`: [src/sensors.c:103](../../src/sensors.c#L103) (`sensors_step`); `age`: [src/sensors.c:33](../../src/sensors.c#L33) (`update_coolant_sensor_freshness`)

Affected state: `faults.stale_coolant_temp_c`, `sensors last update time`.

Propagation: acquisition tap → hold → delivered sample → freshness → control.

Runtime-visible evidence: E_TAP, E_DELIVERED, E_AGE. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_COMM. **INFERRED earliest observability:** First non-refresh acquisition changes age; threshold alarm can occur later. No unconditional physical fault-to-observation bound established.

Competing explanations: Dropped updates with same delivered timestamps; stalled acquisition; metadata corruption.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_TAP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### sensor_bias — SENSOR_CONTROL

**VERIFIED source path; variant:** base. Legacy additive error is injected before acquisition tap.

Injection/operation: `sensor_bias`: [src/sensors.c:68](../../src/sensors.c#L68) (`sensors_step`); `source_tap`: [src/sensors.c:84](../../src/sensors.c#L84) (`sensors_step`)

Affected state: `coolant_meas`, `source and delivered sensor fields`.

Propagation: plant-derived front-end → biased tap → transport → controller.

Runtime-visible evidence: E_TAP, E_DELIVERED, E_REFERENCE. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_BASE, T_PULSE. **INFERRED earliest observability:** First acquisition inside active interval; a plausible bias can be indistinguishable from actual physical input without a trusted reference. No unconditional physical fault-to-observation bound established.

Competing explanations: Physical temperature change; common sensor bias; shared source/delivery software corruption.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_TAP, A_SENSOR. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### sensor_interface_intermittent — SENSOR_CONTROL

**VERIFIED source path; variant:** base. Sample-synchronous six-phase interface amplitude pattern.

Injection/operation: `sensor_intermittent`: [src/sensors.c:13](../../src/sensors.c#L13) (`intermittent_sensor_error`); `source_tap`: [src/sensors.c:84](../../src/sensors.c#L84) (`sensors_step`)

Affected state: `coolant_meas at acquired instants`.

Propagation: front-end pattern → tap → delivered measurement → control.

Runtime-visible evidence: E_TAP, E_DELIVERED, E_REFERENCE. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_BASE, T_PULSE. **INFERRED earliest observability:** First acquired nonzero phase within active interval, not continuous intersample fault time. No unconditional physical fault-to-observation bound established.

Competing explanations: Real fast thermal variation under unknown plant bounds; other channel value injection; missed pulse versus healthy trace.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_TAP, A_SENSOR. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### triplex_sample_injection — SENSOR_CONTROL

**VERIFIED source path; variant:** inspected script-generated C template; not executed. Optional generated adapter injects step/ramp/pulse/stuck/freeze by member mask at sampling calls.

Injection/operation: `triplex_pulse`: [scripts/run_clo_dsf_triplex.py:124](../../scripts/run_clo_dsf_triplex.py#L124) (`embedded C: inject_value`); `triplex_shared`: [scripts/run_clo_dsf_triplex.py:136](../../scripts/run_clo_dsf_triplex.py#L136) (`embedded C: diagnostic_acquire`); `triplex_preserve`: [scripts/run_clo_dsf_triplex.py:152](../../scripts/run_clo_dsf_triplex.py#L152) (`build`)

Affected state: `A source/delivered`, `B reference`, `C diagnostic output`.

Propagation: sample model → member-specific injected transform → captured runtime or Triplex inputs → existing detector.

Runtime-visible evidence: E_TAP, E_DELIVERED, E_REFERENCE. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_ADC, T_MULTIRATE, T_PULSE. **INFERRED earliest observability:** At first matching acquisition and subsequent outer publication. Correlated multi-member injections defeat naive independent-vote claims. No unconditional physical fault-to-observation bound established.

Competing explanations: Single faulty channel versus faulty agreeing pair; all-channel common mode versus true physical change; post-acquisition software corruption.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_BUILD, A_SENSOR, A_TAP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### diagnostic_adc_transfer — SENSOR_CONTROL

**VERIFIED source path; variant:** optional diagnostic ADC model. Optional sensor C models lag, gain, offset, noise, ADC reference gain and quantization. Configuration is a model parameter, not transistor-level fault proof.

Injection/operation: `adc_gain`: [src/v7_3/diagnostic_temperature.c:22](../../src/v7_3/diagnostic_temperature.c#L22) (`diagnostic_temperature_sample`); `adc_publish`: [src/v7_3/diagnostic_temperature.c:24](../../src/v7_3/diagnostic_temperature.c#L24) (`diagnostic_temperature_sample`); `adc_interpolate`: [src/v7_3/diagnostic_temperature.c:17](../../src/v7_3/diagnostic_temperature.c#L17) (`diagnostic_temperature_sample`)

Affected state: `diagnostic_temperature_t state/output`.

Propagation: shared physical input → lag/interpolation → gain/reference/noise → quantization → latest readout.

Runtime-visible evidence: E_REFERENCE. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_ADC. **INFERRED earliest observability:** First modeled sample affected, observable only when published by caller. No unconditional physical fault-to-observation bound established.

Competing explanations: Front-end gain versus ADC gain with same transfer; physical temperature shift versus offset; correlated sensor errors.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_BUILD, A_SENSOR. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### pump_degradation — ACTUATOR

**VERIFIED source path; variant:** base. Realized pump equals clamped command times configured scale.

Injection/operation: `pump_scale`: [src/actuators.c:90](../../src/actuators.c#L90) (`actuators_step`); `pump_publish`: [src/actuators.c:114](../../src/actuators.c#L114) (`actuators_step`); `pump_thermal`: [src/thermal_plant.c:187](../../src/thermal_plant.c#L187) (`thermal_plant_step`)

Affected state: `actuators.pump_actual`.

Propagation: control command → multiplicative loss → software actual → plant cooling.

Runtime-visible evidence: E_COMMAND, E_ACTUAL, E_PUMP_HEALTH. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_PUMP, T_BASE. **INFERRED earliest observability:** Nonzero response gap requires nonzero excitation and scale different from healthy model. Zero command offers no such distinction. No unconditional physical fault-to-observation bound established.

Competing explanations: Healthy idle pump; command corruption or realization-field corruption; other cooling changes if only temperature observed.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_PUMP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### fan_stuck_off — ACTUATOR

**VERIFIED source path; variant:** base. Fan realization forced to zero; additional health feedback is synthesized from active fault mode.

Injection/operation: `fan_stuck`: [src/actuators.c:22](../../src/actuators.c#L22) (`actuators_step`); `fan_oracle`: [src/actuators.c:48](../../src/actuators.c#L48) (`update_fan_actuator_feedback`)

Affected state: `actuators.fan_actual`, `actuator health fields`.

Propagation: command → forced zero → thermal effect and oracle-derived health output.

Runtime-visible evidence: E_COMMAND, E_ACTUAL, E_FAN_HEALTH. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_BASE. **INFERRED earliest observability:** Positive command produces response gap; zero-command health flag exists but is injected-label-derived, not an independent physical witness. No unconditional physical fault-to-observation bound established.

Competing explanations: Healthy fan off under admissible non-oracle view; drive or feedback corruption.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_ORACLE. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### external_sensor_trace — EXTERNAL_TRACE

**VERIFIED source path; variant:** explicit trace mode; source generator/security mechanism outside this bounded audit. Opt-in external RTL replay replaces ECU-facing coolant after tap; current refresh time does not establish original physical acquisition.

Injection/operation: `sensor_trace`: [src/sensors.c:109](../../src/sensors.c#L109) (`sensors_step`)

Affected state: `sensors.coolant_temp_meas_c`.

Propagation: external trace file → designated replacement point → existing downstream component.

Runtime-visible evidence: E_TAP, E_DELIVERED, E_AGE. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_BASE. **INFERRED earliest observability:** First scheduled trace read; original physical acquisition and authenticity are not established by replay-file coverage. No unconditional physical fault-to-observation bound established.

Competing explanations: Native fault with same substituted value; malformed/misleading trace provenance.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_BUILD, A_TAP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### external_calibration_trace — EXTERNAL_TRACE

**VERIFIED source path; variant:** explicit trace mode; source generator/security mechanism outside this bounded audit. Opt-in replay replaces effective target after register read; stored register may remain nominal.

Injection/operation: `cal_trace`: [src/control.c:60](../../src/control.c#L60) (`control_step`)

Affected state: `effective_target_c`, `active_control_target_c`.

Propagation: external trace file → designated replacement point → existing downstream component.

Runtime-visible evidence: E_MEMORY, E_COMMAND. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_BASE. **INFERRED earliest observability:** First scheduled trace read; original physical acquisition and authenticity are not established by replay-file coverage. No unconditional physical fault-to-observation bound established.

Competing explanations: Native fault with same substituted value; malformed/misleading trace provenance.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_BUILD, A_TAP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

### external_fan_trace — EXTERNAL_TRACE

**VERIFIED source path; variant:** explicit trace mode; source generator/security mechanism outside this bounded audit. Opt-in replay replaces realized fan response before publication.

Injection/operation: `fan_trace`: [src/actuators.c:101](../../src/actuators.c#L101) (`actuators_step`)

Affected state: `actuators.fan_actual`.

Propagation: external trace file → designated replacement point → existing downstream component.

Runtime-visible evidence: E_COMMAND, E_ACTUAL. Ground-truth-only: E_FAULT, E_TRUTH. See manifest evidence records for producer anchors and exact field lists.

Acquisition/observation timing: T_BASE. **INFERRED earliest observability:** First scheduled trace read; original physical acquisition and authenticity are not established by replay-file coverage. No unconditional physical fault-to-observation bound established.

Competing explanations: Native fault with same substituted value; malformed/misleading trace provenance.

Shared domain: D_PROCESS, plus each evidence record’s memory/sensor/clock/actuator logical domains. Common-cause corruption of a producer, clock, copied state or its monitor can corrupt multiple dependent observations. Required assumptions: A_PROCESS, A_CLOCK, A_FAULTSET, A_BUILD, A_TAP. **Attribution:** UNKNOWN without the stated trust and fault-set assumptions.

## Five critical ambiguity analyses

### CASE_1: Dormant register corruption before consumption

**Status: INFERRED; sound unconditional origin: UNKNOWN.**

Dormant-to-control is not automatically dormant-to-all-evidence. Register/shadow mismatch can be observable even when commands have not changed. Base injector and control normally run at the same 100 ms boundary: a long injected-before-consume interval is not automatically an executable case. New memory and task-delay faults cannot be combined through ordinary CLI. A stuck bit initially matching nominal leaves no value mismatch; optional write/read/restore probe can reveal persistent write failure before semantic target use. A past bit flip need not fail that probe. The probe validity and deployment must be established.

Competing explanations: Healthy register with bit already at forced polarity; Changed register versus authorized write; Bit flip versus stuck bit yielding same value; Shared target/shadow corruption.

Available observations: E_MEMORY, E_PROBE, E_COMMAND. Timing constraints: T_MEMORY, T_PROBE, T_BASE. Trust assumptions: A_SHADOW, A_BUILD, A_FAULTSET.

Conditional result: Under protected shadow and constrained target-only corruption, mismatch supports a memory-state violation; probe failure supports a modeled storage write-response violation. Neither is unconditional physical-origin attribution.

Source support: `stuck`: [src/cross_layer_fault.c:96](../../src/cross_layer_fault.c#L96) (`cross_layer_fault_step`); `flip`: [src/cross_layer_fault.c:85](../../src/cross_layer_fault.c#L85) (`cross_layer_fault_step`); `consume`: [src/control.c:43](../../src/control.c#L43) (`control_step`); `obs_memory`: [src/runtime_observation.c:21](../../src/runtime_observation.c#L21) (`runtime_observation_capture`); `probe_call`: [src/v7_3/revised_runtime.c:45](../../src/v7_3/revised_runtime.c#L45) (`__wrap_cross_layer_fault_step`); `probe_backend`: [src/memory_diagnostic_backend.c:21](../../src/memory_diagnostic_backend.c#L21) (`cross_layer_memory_write`); `revised_memory`: [src/v7_3/clo_dsf_revised.c:29](../../src/v7_3/clo_dsf_revised.c#L29) (`clo_revised_extract`); `control_dispatch`: [src/scheduler.c:71](../../src/scheduler.c#L71) (`scheduler_inputs`)

### CASE_2: Sensor pulse wholly between acquisition instants

**Status: INFERRED; sound unconditional origin: UNKNOWN.**

For a sensor-only non-latching pulse with identical sampled endpoints, no base observation distinguishes the pulse from healthy behavior. This is a conditional sampling argument, not evidence that such a physical pulse was simulated continuously. Base new injector rejects sub-tick timing; legacy gate never visits an interval strictly between ticks. Generated optional ADC/multirate templates have additional modeled samples, but compute them at a later outer invocation using endpoint interpolation. A pulse missed by every available acquisition remains ambiguous.

Competing explanations: Healthy sensor; Unsampled non-latching pulse of any eligible origin; Subsample failure without persistence.

Available observations: E_TAP, E_DELIVERED, E_REFERENCE. Timing constraints: T_PULSE, T_ADC, T_MULTIRATE. Trust assumptions: A_SENSOR, A_SUBTICK, A_FAULTSET.

Conditional result: A pulse overlapping a verified optional sample may generate evidence at its later publication; no guaranteed online 25/50 ms reaction follows from backdated sample time.

Source support: `loop`: [src/scheduler.c:146](../../src/scheduler.c#L146) (`scheduler_run`); `acquire`: [src/scheduler.c:65](../../src/scheduler.c#L65) (`scheduler_inputs`); `sensor_period`: [include/config.h:9](../../include/config.h#L9) (`<file-scope>`); `legacy_window`: [src/fault_injection.c:100](../../src/fault_injection.c#L100) (`fault_event_active`); `alignment`: [src/cross_layer_config.c:183](../../src/cross_layer_config.c#L183) (`cross_layer_validate`); `triplex_pulse`: [scripts/run_clo_dsf_triplex.py:124](../../scripts/run_clo_dsf_triplex.py#L124) (`embedded C: inject_value`); `adc_sample`: [src/v7_3/diagnostic_temperature.c:12](../../src/v7_3/diagnostic_temperature.c#L12) (`diagnostic_temperature_sample`); `mr_loop`: [scripts/run_clo_dsf_multirate.py:46](../../scripts/run_clo_dsf_multirate.py#L46) (`embedded C: mr_acquire`); `mr_interpolate`: [scripts/run_clo_dsf_multirate.py:49](../../scripts/run_clo_dsf_multirate.py#L49) (`embedded C: mr_acquire`)

### CASE_3: Pump degradation at zero command

**Status: INFERRED; sound unconditional origin: UNKNOWN.**

For finite scale and identical prior state, pump_actual=clamp(0)*scale=0 in both worlds. The pump thermal term is also equal. No separate pump-health sample is established. Fan self-test feedback cannot be repurposed: it concerns a different actuator and reads the injected fault label. Prior excitation/history could distinguish worlds, so indistinguishability is conditional on matched history and a zero-command observation interval.

Competing explanations: Healthy idle pump; Degraded idle pump; Different latent pump scales with identical prior state.

Available observations: E_COMMAND, E_ACTUAL, E_PUMP_HEALTH. Timing constraints: T_PUMP. Trust assumptions: A_PUMP, A_FAULTSET.

Conditional result: Later positive excitation can expose a modeled response gap if command and realized-response integrity are assumed; a physical sensor/actuator diagnosis still needs verified feedback provenance.

Source support: `pump_scale`: [src/actuators.c:90](../../src/actuators.c#L90) (`actuators_step`); `pump_publish`: [src/actuators.c:114](../../src/actuators.c#L114) (`actuators_step`); `pump_thermal`: [src/thermal_plant.c:187](../../src/thermal_plant.c#L187) (`thermal_plant_step`); `fan_oracle`: [src/actuators.c:48](../../src/actuators.c#L48) (`update_fan_actuator_feedback`); `plant_integrate`: [src/thermal_plant.c:198](../../src/thermal_plant.c#L198) (`thermal_plant_step`)

### CASE_4: Downstream corruption with shared compromised provenance

**Status: INFERRED; sound unconditional origin: UNKNOWN.**

Different upstream paths can yield the same downstream error and saturated command; full observations may distinguish them only if their provenance remains intact. The implementation co-locates these fields and provides an explicit optional source/delivered shared-write example. It does not establish arbitrary post-control corruption coverage or hardware isolation. CRC verifies equality against software witness state; a consistently corrupted witness/verifier need not expose a mismatch. This is a conditional adversarial scenario, not a newly claimed implemented fault model.

Competing explanations: Target/effective-control corruption; Upstream sensor bias producing equal temperature error; Coherent corruption of source and delivered observations; Coherent corruption of value, metadata, shadow or CRC witness.

Available observations: E_MEMORY, E_TAP, E_DELIVERED, E_COMMAND, E_DIGITAL. Timing constraints: T_BASE. Trust assumptions: A_PROCESS, A_SHADOW, A_TAP, A_MAILBOX, A_POSTWRITE, A_FAULTSET.

Conditional result: Use a violation/equivalence-class conclusion until a tested fault-containment boundary proves at least one relevant witness survives the specified corruption.

Source support: `state_shared`: [include/ecu_types.h:276](../../include/ecu_types.h#L276) (`<file-scope>`); `control_error`: [src/control.c:72](../../src/control.c#L72) (`control_step`); `legacy_offset`: [src/control.c:53](../../src/control.c#L53) (`control_step`); `commit`: [src/control.c:24](../../src/control.c#L24) (`control_commit_target`); `triplex_shared`: [scripts/run_clo_dsf_triplex.py:136](../../scripts/run_clo_dsf_triplex.py#L136) (`embedded C: diagnostic_acquire`); `triplex_preserve`: [scripts/run_clo_dsf_triplex.py:152](../../scripts/run_clo_dsf_triplex.py#L152) (`build`); `mailbox_publish`: [src/v7_3/digital_sensor_integrity.c:17](../../src/v7_3/digital_sensor_integrity.c#L17) (`di_publish`); `mailbox_verify`: [src/v7_3/digital_sensor_integrity.c:32](../../src/v7_3/digital_sensor_integrity.c#L32) (`di_verify`); `mailbox_bank`: [scripts/run_digital_integrity.py:19](../../scripts/run_digital_integrity.py#L19) (`embedded C: <file-scope>`)

### CASE_5: Delayed/replayed data and timestamp visibility

**Status: INFERRED; sound unconditional origin: UNKNOWN.**

In the inspected new communication path, source timestamp and age ARE copied to runtime observation and legacy replay serialization. Generated/reception/replay-active/drop bookkeeping is not wholesale exported. Therefore universal timestamp invisibility is false. Given trustworthy source metadata and a synchronous source/control ordering contract, old data can be identified before a generic freshness timeout; stale origin is still not uniquely delay/drop/replay. An interface that lacks those fields, or a restamped/external trace path, does not inherit this contract. Old final_observation CSV retains timestamps but omits newer source/shadow/reference additions.

Competing explanations: Delay versus replay of equal-age samples; Drop/hold/stale producer yielding same observed sequence; Authentic current constant reading versus replay without trustworthy metadata; Corrupted/restamped timestamp.

Available observations: E_TAP, E_DELIVERED, E_AGE, E_TIMING, E_TRANSPORT_ORACLE. Timing constraints: T_COMM, T_BASE. Trust assumptions: A_TAP, A_CLOCK, A_REPLAY, A_FAULTSET.

Conditional result: Conditional stale-data/provenance-order violation is supportable; sound unique communication mechanism or physical attack attribution is not established.

Source support: `comm_delay`: [src/sensor_delivery.c:27](../../src/sensor_delivery.c#L27) (`cross_layer_sensor_delivery`); `comm_drop`: [src/sensor_delivery.c:35](../../src/sensor_delivery.c#L35) (`cross_layer_sensor_delivery`); `comm_replay`: [src/sensor_delivery.c:38](../../src/sensor_delivery.c#L38) (`cross_layer_sensor_delivery`); `timestamp_publish`: [src/sensors.c:129](../../src/sensors.c#L129) (`sensors_step`); `obs_timestamp`: [src/runtime_observation.c:9](../../src/runtime_observation.c#L9) (`runtime_observation_capture`); `obs_age`: [src/runtime_observation.c:10](../../src/runtime_observation.c#L10) (`runtime_observation_capture`); `delivery_time`: [src/sensor_delivery.c:49](../../src/sensor_delivery.c#L49) (`cross_layer_sensor_delivery`); `serialized`: [src/v7_2/final_observation_io.c:12](../../src/v7_2/final_observation_io.c#L12) (`<file-scope fields table>`); `replay_zero`: [src/v7_2/final_observation_io.c:34](../../src/v7_2/final_observation_io.c#L34) (`final_observation_read`); `sensor_trace`: [src/sensors.c:109](../../src/sensors.c#L109) (`sensors_step`)

## Observational-equivalence formulation for later work

**INFERRED, not an implemented diagnostic:** for an explicitly chosen intact input
view V and observation horizon H, compare the actual ordered observations O_V(H),
including acquisition/publication time and validity. If two allowed histories with
different origins have identical O_V(H), a sound single-origin conclusion is not
available from that view. Returning UNKNOWN does not mean no anomaly exists, nor
that no augmented, genuinely independent interface could ever disambiguate it.
Sampling gaps, command saturation, absent excitation and shared corruption must be
part of the model, not silently removed from its evaluation denominator. No
probability of independence or lower bound on detection is inferred here.
