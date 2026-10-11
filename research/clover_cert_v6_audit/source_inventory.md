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

## Inspection scope and executable variants

The inspected chain is the real fixed-step ECU, its new and legacy injectors,
source/delivery and control/actuator producers, the observation boundary, full-state
legacy consumers, and selected optional revised/Triplex/multirate/integrity sources.
This is a bounded audit of these paths, not a complete verification of every
untracked development algorithm or every RTL generator. No simulator, build, GUI,
experiment runner, training script or historical regression was executed.

- **Base:** `src/*.c` is the Makefile source set. GNUmakefile additionally links
  historical v7 variants; availability of a v7_3 source file does not enable it.
- **Revised:** `clo_dsf_revised.mk` explicitly wraps sensor, fault-step and detector
  calls. The memory probe and optional redundant reference require this path and
  its run-time enable conditions. Base memory diagnostic state starts invalid.
- **Generated variants:** the inspected Python runners contain C templates and
  source substitutions/link commands. Anchors prove these template operations,
  not which binary was actually used by a past result. No generated build was run.
- **Stress:** simulated 1 ms service and 100 ms outer observation are distinct
  from the base dispatcher; the CLI rejects stress plus the new cross-layer fault.

`build_default`: [Makefile:6](../../Makefile#L6) (`<file-scope>`); `build_priority`: [GNUmakefile:2](../../GNUmakefile#L2) (`<file-scope>`); `build_revised`: [clo_dsf_revised.mk:6](../../clo_dsf_revised.mk#L6) (`<file-scope>`); `probe_call`: [src/v7_3/revised_runtime.c:45](../../src/v7_3/revised_runtime.c#L45) (`__wrap_cross_layer_fault_step`); `base_init_probe`: [src/control.c:30](../../src/control.c#L30) (`control_init`); `triplex_link`: [scripts/run_clo_dsf_triplex.py:178](../../scripts/run_clo_dsf_triplex.py#L178) (`build`); `mailbox_wrap`: [scripts/run_digital_integrity.py:65](../../scripts/run_digital_integrity.py#L65) (`build`); `stress_exclusive`: [src/main.c:307](../../src/main.c#L307) (`main`)

## Inspected source snapshot

| Relative file | Tracking at audit | SHA256 |
|---|---|---|
| `GNUmakefile` | tracked | `d889389ab8aed71c84ba9a2e55e012966f266a309aa745d69b092c6afd6b7fae` |
| `Makefile` | tracked | `febd61e4dd3e665fe5b533453ce931a1971ced79c11b3e60f4b1fe2b6a762a56` |
| `clo_dsf_revised.mk` | tracked | `ee8a550d6953c31de3ecde1ee755c136fd42c6de03f418924b30356b14c3ff3d` |
| `include/config.h` | tracked | `eb481dc6fe5bca46e1c4a4fef773be421933c33b43ca385c8c88f8e013e16aa7` |
| `include/ecu_types.h` | tracked | `9db75d0b7e0c98ec54783eb8bf9491c6b154f5afd2f3a0ae16360ad713066ce4` |
| `include/memory_diagnostic.h` | tracked | `7d66530fcbbcfaab612ad9f01a2fe57b3ad20da9cf9ce4216127fde6443e306c` |
| `scripts/run_clo_dsf_multirate.py` | pre-existing untracked | `a7a1cd13b5e45b4a49345a22a693be46cc6c27aa68bdb5b57d4a415d38e0d104` |
| `scripts/run_clo_dsf_triplex.py` | tracked | `b23677c9bd7b0e68df5781c0d678e10df5e58e057cbda7841147e641c429c566` |
| `scripts/run_digital_integrity.py` | pre-existing untracked | `63fa7f99fcd770e6e7be4666abaa4ab5a8a47d455a6b25d989929669c175a16f` |
| `src/actuators.c` | tracked | `5b1fcad84453fce451aa7d08cb23dc744fa2ff484c0fb22e0cfe72d234641ce3` |
| `src/control.c` | tracked | `f2ccfbdde47db2ef483b1b64f4b83c9e6a48e9ae0b4f6450666686814dc839f7` |
| `src/cross_layer_config.c` | tracked | `0ac07cf90296a041f82973ad754337c9c8ae9fc9f58dff6104e2a828dfe38457` |
| `src/cross_layer_fault.c` | tracked | `5e3a807d89598615aa93cc9c3849eb6f8c4a44b1f25c4e56d6672ff5deb8e01f` |
| `src/detection_algorithm.c` | tracked | `c4a024feb6eabc6d62bb6a4483d504cc39c3efa8fa64baf16c7c1fec13a7804d` |
| `src/diagnostics.c` | tracked | `e20a16a34c8b2238a89d3363c40c15794fca5c37b5b7854524e1cbb383e448e6` |
| `src/experiment.c` | tracked | `f6334c4fb6d71bd1fbfec067434722d9c38d4f6bb525fb10ea17cf1fffbaeadf` |
| `src/fault_injection.c` | tracked | `52553d6d5b3e5f1d461dd52cf19be14941481581f1eb4613710dd0cee207d992` |
| `src/main.c` | tracked | `ce81833c12f36aca454251121efc18b835b30fe99cf2e434afd7370ed977e032` |
| `src/memory_diagnostic.c` | tracked | `439130d0db764db2a80076d1fafb194e6bdbf442e6b005a489b3d52a64c7531f` |
| `src/memory_diagnostic_backend.c` | tracked | `a6d0ece226c89b8f9b5fa1d7809927ccad63eefbd2c50f02d5e608c565c8a5ed` |
| `src/propagation_monitor.c` | tracked | `1bf34f5ea6fa748844d8c3353fc13ce07d679574178e3b1f051861c684a920e3` |
| `src/redundant_temperature.c` | tracked | `176da3fafddaf219b0515492be7225c72e59498ef1d3c10a74e771669d42a6d1` |
| `src/runtime_observation.c` | tracked | `cae3370319989b38c52832293215d678444eedcf20dba9b93dc04f2444c323ea` |
| `src/runtime_timing_observation.c` | tracked | `5d6f4cbe3d097136ed7f5883057388e0ed4dc6b84aff28a051386c68c7d84ac0` |
| `src/safety_monitor.c` | tracked | `27412e114cd0cd22132b1a5b24e7a14e5c937df4ade5ac3f1b6029c6aec2fe4d` |
| `src/scheduler.c` | tracked | `80d924e069d55926f6f2485db853ce8de06744c55c0119b640510e7641ec30d9` |
| `src/scheduler_stress.c` | tracked | `b9e4ca5013a90c6b639dcebaf1921beec07def11e443576bf36ba852534f66b0` |
| `src/sensor_delivery.c` | tracked | `f3ea17440e15513808e77f3c8f41849da31f3504ea6441bca85b5c963e037d76` |
| `src/sensors.c` | tracked | `f19e601d68976a563a5edb031d76ca259689b32bef04958a81f6bd4a8947a352` |
| `src/thermal_plant.c` | tracked | `162cff8f8729f524716f96836f78f3ebd5ae6b61818a461c7ca152c5e53aa106` |
| `src/v7_2/final_observation_io.c` | tracked | `19446a5c5726dd650da092c634e8c7ade7f4101401ad152e73fae41afb3d9145` |
| `src/v7_3/clo_dsf_revised.c` | tracked | `349084500594ea62f9472ed3bac3a3b79aa09713960ba5aface5bee095820fb0` |
| `src/v7_3/diagnostic_temperature.c` | tracked | `b4cd951328299da10fa5b4c0a504e79f9cf8a252b861304e38e77546be4e7be9` |
| `src/v7_3/digital_sensor_integrity.c` | pre-existing untracked | `10c0c9edf054003470e0b06ebfb0d2503341f71dfe1042efa1cad7774b2b7949` |
| `src/v7_3/multirate_memory.c` | pre-existing untracked | `cae25c6bb4aea063af0a6930a4628532cb3eb943d2e4b723ca6daf74f0ca39d6` |
| `src/v7_3/revised_runtime.c` | tracked | `1febac2b4044a5ea67a16e53ab1acc71332b228f3add33365167761a25424d2f` |

## Exact implementation anchors

All line numbers are 1-based and refer to the SHA256 snapshot above. Embedded C
functions are explicitly marked; their containing Python source is not executed.

| ID | Relative path:line | Function/context | Exact source token | Verified operation |
|---|---|---|---|---|
| tick | include/config.h:4 | <file-scope> | `#define ECU_DT_MS 100U` | Base simulated integration tick. |
| sensor_period | include/config.h:9 | <file-scope> | `#define ECU_SENSOR_PERIOD_MS 100U` | Primary acquisition cadence. |
| control_period | include/config.h:11 | <file-scope> | `#define ECU_CONTROL_PERIOD_MS 100U` | Control release cadence. |
| actuator_period | include/config.h:12 | <file-scope> | `#define ECU_ACTUATOR_PERIOD_MS 100U` | Actuator cadence. |
| diag_period | include/config.h:16 | <file-scope> | `#define ECU_DIAGNOSTIC_PERIOD_MS 500U` | Diagnostic cadence; safety can call again at a due diagnostic boundary. |
| due | src/scheduler.c:20 | scheduler_task_due | `return (time_ms % period_ms) == 0U;` | Periodic dispatch criterion. |
| inject_first | src/scheduler.c:63 | scheduler_inputs | `cross_layer_fault_step(state);` | Fault handling precedes acquisition and control. |
| acquire | src/scheduler.c:65 | scheduler_inputs | `sensors_step(state);` | Acquisition call before control. |
| control_dispatch | src/scheduler.c:71 | scheduler_inputs | `cross_layer_control_execution(state))` | Execution admitted by timing fault gate. |
| control_call | src/scheduler.c:73 | scheduler_inputs | `control_step(state);` | Actual C control call between same-time recorder start/complete calls. |
| reaction | src/scheduler.c:98 | scheduler_reactions | `detection_algorithm_step(state);` | Detector runs after normal actuator/diagnostic/safety work; later safety actions may change commands. |
| runtime_capture | src/scheduler.c:107 | scheduler_reactions | `runtime_observation_capture(state, &observation);` | Runtime policy captures after detector and its safety request. |
| loop | src/scheduler.c:146 | scheduler_run | `state->time.time_ms += ECU_DT_MS` | Outer loop advances the simulation clock in 100 ms increments. |
| log | src/scheduler.c:168 | scheduler_run | `logger_write(state);` | Logging follows reaction/scoring and precedes plant integration. |
| plant_call | src/scheduler.c:170 | scheduler_run | `thermal_plant_step(state);` | Plant evolves after current tick observations. |
| reference_copy | src/scheduler.c:135 | scheduler_run | `reference = *state;` | Counterfactual is a separate local copied state. |
| reference_disable | src/scheduler.c:137 | scheduler_run | `reference.cross_layer_fault.enabled = false;` | Counterfactual new injector disabled. |
| stress_inner | src/scheduler.c:59 | scheduler_inputs | `boundary-ECU_DT_MS+1` | Optional stress services 1 ms substeps before current outer input update. |
| active_window | src/cross_layer_fault.c:65 | cross_layer_fault_step | `elapsed >= f->duration_ms` | Nonpermanent end is exclusive. |
| intermittent | src/cross_layer_fault.c:69 | cross_layer_fault_step | `elapsed % (f->intermittent_on_ms + f->intermittent_off_ms)` | Intermittent phase tested at scheduler calls. |
| memory_save | src/cross_layer_fault.c:82 | cross_layer_fault_step | `r->memory_original_value = state->control.target_register_c;` | Snapshot current register on each activation. |
| flip | src/cross_layer_fault.c:85 | cross_layer_fault_step | `state->control.target_register_c ^= (uint16_t)(1U << f->bit_index);` | Flip occurs once on active transition. |
| restore | src/cross_layer_fault.c:91 | cross_layer_fault_step | `if (r->memory_values_valid) state->control.target_register_c = r->memory_original_value;` | Restore snapshot on active-to-inactive transition. |
| stuck | src/cross_layer_fault.c:96 | cross_layer_fault_step | `state->control.target_register_c = f->stuck_polarity ?` | Active stuck bit forces the chosen bit each call. |
| commit | src/control.c:24 | control_commit_target | `state->control.target_shadow_c = target_c;` | Authorized commit writes target and shadow together. |
| consume | src/control.c:43 | control_step | `float effective_target_c = (float)state->control.target_register_c;` | Register consumed only when control executes. |
| legacy_offset | src/control.c:53 | control_step | `effective_target_c += state->faults.control_target_offset_c;` | Legacy calibration corruption modifies local effective target, not stored register. |
| cal_trace | src/control.c:60 | control_step | `(void)calibration_trace_get(` | Optional RTL trace replaces local target, not target_register_c assignment. |
| target_publish | src/control.c:68 | control_step | `state->control.active_control_target_c = effective_target_c;` | Executed target value is published. |
| control_error | src/control.c:72 | control_step | `temp_error = state->sensors.coolant_temp_meas_c - effective_target_c;` | Delivered sensor and target share downstream control expression. |
| pump_cmd | src/control.c:76 | control_step | `state->control.pump_command = clamp_unit(0.30f + (0.025f * temp_error) + load_term);` | Saturated command can mask distinct target/sensor changes. |
| release | src/cross_layer_fault.c:111 | cross_layer_control_execution | `runtime_timing_release(&state->timing_recorder, state->time.time_ms);` | Release recorded before timing gate. |
| delay_due | src/cross_layer_fault.c:134 | cross_layer_control_execution | `r->job_due_ms = now + (int)f->task_delay_ms;` | Delayed job retained for later scheduler call. |
| delay_complete | src/cross_layer_fault.c:122 | cross_layer_control_execution | `execute = now >= r->job_due_ms;` | Pending job really executes at a later allowed call. |
| discard | src/cross_layer_fault.c:121 | cross_layer_control_execution | `r->release_discarded = true;` | Releases discarded while one delayed job is pending, including completion boundary. |
| skip | src/cross_layer_fault.c:144 | cross_layer_control_execution | `runtime_timing_cancel_release(&state->timing_recorder, true);` | Deadline-miss injection cancels rather than executes a late job. |
| exec_missing | src/cross_layer_fault.c:46 | cross_layer_control_execution | `r->actual_execution_ms = -1;` | Skipped execution has no actual timestamp. |
| timing_start | src/runtime_timing_observation.c:47 | runtime_timing_start | `r->observation.actual_start_ms = (int)now;` | Recorder uses simulated caller clock, not host WCET. |
| timing_complete | src/runtime_timing_observation.c:54 | runtime_timing_complete | `o->actual_completion_ms = o->last_successful_execution_ms = (int)now;` | Normal start and completion have identical scheduler time. |
| timing_deadline | src/runtime_timing_observation.c:70 | runtime_timing_observe | `o->actual_completion_ms == (int)now && now > deadline` | Completion exactly at deadline is allowed. |
| stress_complete | src/scheduler_stress.c:30 | complete_job | `control_step(state);` | Stress computes real control at simulated job completion. |
| stress_queue | src/scheduler_stress.c:74 | scheduler_stress_tick | `.execution=overload ? c->overload_execution_ms : c->execution_ms` | Configured occupancy and finite queue, not measured processor duration. |
| stress_publish | src/scheduler_stress.c:101 | scheduler_stress_sample | `o->actual_completion_ms=s->count ? -1 : s->last_completion;` | Stress observation is sampled at outer tick; it can hide earlier completions while jobs remain. |
| stress_exclusive | src/main.c:307 | main | `state.scheduler_stress_config.enabled && state.cross_layer_fault.enabled` | CLI rejects stress/new-cross-layer-fault composition. |
| alignment | src/cross_layer_config.c:183 | cross_layer_validate | `if (f->start_ms % ECU_DT_MS` | New injector timestamps must align with tick. |
| delay_alignment | src/cross_layer_config.c:193 | cross_layer_validate | `f->task_delay_ms % ECU_DT_MS` | Task delay is positive and tick aligned. |
| replay_limit | src/cross_layer_config.c:195 | cross_layer_validate | `f->replay_age_ms > f->start_ms` | Replay history age is bounded and aligned. |
| mixed_reject | src/cross_layer_config.c:181 | cross_layer_validate | `Use baseline with new faults; mixed legacy/new injections are unsupported.` | Not all fault combinations are executable. |
| legacy_window | src/fault_injection.c:100 | fault_event_active | `return time_ms < end_ms;` | Legacy faults evaluated only on scheduler calls. |
| legacy_priority | src/fault_injection.c:159 | fault_injection_step | `apply_fault_event(state, &state->experiment.events[i], (int)i);` | First active event wins, then break. |
| legacy_config | src/experiment.c:287 | experiment_configure_custom_single_fault | `state->experiment.events[0].start_ms = start_ms;` | Custom legacy start retained; no tick alignment enforced here. |
| sensor_base | src/sensors.c:63 | sensors_step | `float coolant_meas = state->plant.coolant_temp_true_c;` | Primary front-end model starts from plant temperature. |
| sensor_bias | src/sensors.c:68 | sensors_step | `coolant_meas += state->faults.sensor_bias_c;` | Bias precedes source tap. |
| sensor_intermittent | src/sensors.c:13 | intermittent_sensor_error | `unsigned int phase = (time_ms / ECU_SENSOR_PERIOD_MS) % 6U;` | Legacy intermittent signal is a six-sample pattern, not continuous sub-tick pulse acquisition. |
| source_tap | src/sensors.c:84 | sensors_step | `state->sensors.coolant_source_c = coolant_meas;` | Tap includes primary front-end errors and precedes transport/trace replacement. |
| source_time | src/sensors.c:85 | sensors_step | `state->sensors.coolant_source_ms = state->time.time_ms;` | Tap timestamp written from common scheduler clock. |
| legacy_hold | src/sensors.c:103 | sensors_step | `coolant_meas = state->faults.stale_coolant_temp_c;` | Legacy stale transfer holds prior measurement. |
| sensor_trace | src/sensors.c:109 | sensors_step | `if (state->coolant_sensor_trace.enabled) {` | External sample replacement follows tap and legacy hold. |
| delivery_call | src/sensors.c:126 | sensors_step | `cross_layer_sensor_delivery(state, coolant_meas, &coolant_meas, &coolant_refreshed, &source_ms);` | Delivery input may already be transformed; generated is not necessarily pristine tap. |
| delivered_publish | src/sensors.c:127 | sensors_step | `state->sensors.coolant_temp_meas_c = coolant_meas;` | Delivered value exposed to control. |
| timestamp_publish | src/sensors.c:129 | sensors_step | `state->sensors.coolant_sensor_last_update_ms = source_ms;` | New communication branch preserves original source timestamp, not reception time. |
| age | src/sensors.c:33 | update_coolant_sensor_freshness | `state->time.time_ms - state->sensors.coolant_sensor_last_update_ms;` | Runtime age is derived from common clock and published timestamp. |
| history | src/sensor_delivery.c:13 | cross_layer_sensor_delivery | `r->history[slot] = generated;` | Communication history records supplied generated samples. |
| comm_delay | src/sensor_delivery.c:27 | cross_layer_sensor_delivery | `else sample_time = now-f->communication_delay_ms;` | After initial delay interval, choose historical timestamp. |
| comm_drop | src/sensor_delivery.c:35 | cross_layer_sensor_delivery | `r->update_delivered = !drop;` | Burst/pattern drop suppresses new delivery. |
| comm_replay | src/sensor_delivery.c:38 | cross_layer_sensor_delivery | `sample_time = now-f->replay_age_ms;` | Replay selects older history. |
| history_match | src/sensor_delivery.c:46 | cross_layer_sensor_delivery | `r->history_timestamps[source_slot] == sample_time` | Exact timestamp/history availability required for delivery. |
| delivery_time | src/sensor_delivery.c:49 | cross_layer_sensor_delivery | `r->delivered_ms = (int)now;` | Reception timestamp is in injector/runtime state; not all fields exported to runtime allowlist. |
| delivery_source | src/sensor_delivery.c:55 | cross_layer_sensor_delivery | `*source_ms = r->delivered_source_ms;` | Held or replayed provenance returned to sensor publisher. |
| obs_age | src/runtime_observation.c:10 | runtime_observation_capture | `.sample_age_ms = s->sensors.coolant_sensor_update_age_ms,` | Runtime interface publishes age. |
| obs_timestamp | src/runtime_observation.c:9 | runtime_observation_capture | `.sample_timestamp_ms = s->sensors.coolant_sensor_last_update_ms,` | Runtime interface publishes source timestamp. |
| obs_memory | src/runtime_observation.c:21 | runtime_observation_capture | `.target_register_c = s->control.target_register_c,` | Live register available without consuming it in control. |
| obs_source | src/runtime_observation.c:27 | runtime_observation_capture | `.source_c = s->sensors.coolant_source_c,` | Tap available in in-memory observation. |
| obs_timing | src/runtime_observation.c:38 | runtime_observation_capture | `.timing = s->timing_recorder.observation` | Timing recorder published to runtime interface. |
| obs_actuator | src/runtime_observation.c:13 | runtime_observation_capture | `.pump_actual = s->actuators.pump_actual,` | Model actuator realization exposed as feedback. |
| obs_diag | src/runtime_observation.c:15 | runtime_observation_capture | `.diagnostic_id = s->diagnostics.primary_dtc, .safety_state = s->safety.current_state,` | Publication does not remove diagnostic/safety oracle dependencies. |
| obs_reference | src/runtime_observation.c:33 | runtime_observation_capture | `.reference_c = s->temperature_reference.value_c,` | Optional reference model output exposed, validity must be checked. |
| truth | src/runtime_observation.c:47 | experiment_ground_truth_capture | `.coolant_true_c = s->plant.coolant_temp_true_c,` | Plant truth in separate experiment capture. |
| prop_truth | src/propagation_monitor.c:57 | propagation_monitor_step | `p->coolant_deviation_c = state->plant.coolant_temp_true_c - p->reference_coolant_c;` | Propagation derives from counterfactual truth. |
| diag_truth | src/diagnostics.c:151 | diagnostics_step | `float sensor_residual = state->sensors.coolant_temp_meas_c - state->plant.coolant_temp_true_c;` | Legacy rationality diagnostic reads oracle temperature. |
| diag_label | src/diagnostics.c:154 | diagnostics_step | `bool permanent_injected_fault = state->faults.active_behavior == FAULT_BEHAVIOR_PERMANENT;` | Diagnostic classification also consults injection metadata. |
| hybrid_truth | src/detection_algorithm.c:324 | hybrid_kalman_sensor_score | `state->plant.coolant_temp_true_c` | Hybrid sensor score directly uses oracle truth. |
| detector_truth | src/detection_algorithm.c:997 | detection_algorithm_step | `state->sensors.coolant_temp_meas_c - state->plant.coolant_temp_true_c` | Legacy detector residual is oracle-derived. |
| detector_onset | src/detection_algorithm.c:1006 | detection_algorithm_step | `state->time.time_ms < state->metrics.first_fault_start_ms;` | before_fault uses campaign onset metadata. |
| action_gate | src/detection_algorithm.c:1169 | detection_algorithm_step | `if (detector->alarm_active && !detector->detected && !before_fault) {` | Onset metadata gates first detection and subsequent action request block. |
| safety_truth | src/safety_monitor.c:31 | requested_state_from_diagnostics | `state->plant.coolant_temp_true_c >= ECU_SHUTDOWN_COOLANT_TEMP_C` | Legacy shutdown path reads truth. |
| pump_scale | src/actuators.c:90 | actuators_step | `pump_actual *= state->faults.pump_scale;` | Pump loss is multiplicative after command clamp. |
| pump_publish | src/actuators.c:114 | actuators_step | `state->actuators.pump_actual = pump_actual;` | Actual is assigned by same software model, no physical transducer here. |
| fan_stuck | src/actuators.c:22 | actuators_step | `fan_actual = 0.0f;` | Fan stuck-off suppresses realization. |
| fan_oracle | src/actuators.c:48 | update_fan_actuator_feedback | `state->faults.active_mode == FAULT_FAN_STUCK_OFF;` | Self-test feedback is synthesized from fault mode, including at zero command. |
| fan_trace | src/actuators.c:101 | actuators_step | `fan_actual_trace_get(` | Optional external RTL actuator value replaces model realization. |
| pump_thermal | src/thermal_plant.c:187 | thermal_plant_step | `pump_cooling = 7.5f * state->actuators.pump_actual;` | Only realized pump affects this cooling term. |
| plant_integrate | src/thermal_plant.c:198 | thermal_plant_step | `state->plant.coolant_temp_true_c += temp_delta * dt_s;` | Plant difference first observed after integration, at next outer observation. |
| state_shared | include/ecu_types.h:276 | <file-scope> | `typedef struct ecu_state {` | Plant, sensor, control, faults and monitors coexist in one C aggregate. |
| probe_read | src/memory_diagnostic.c:14 | memory_diagnostic_step | `uint16_t saved = read(ctx);` | Probe snapshots, writes test patterns and restores saved register. |
| probe_schedule | src/memory_diagnostic.c:11 | memory_diagnostic_step | `unsigned int interval=s->checks%10U ? MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS :` | Checks use phase-swept interval schedule. |
| probe_backend | src/memory_diagnostic_backend.c:21 | cross_layer_memory_write | `value = state->cross_layer_fault.stuck_polarity ?` | Virtual stuck device behavior encoded in diagnostic write callback. |
| probe_call | src/v7_3/revised_runtime.c:45 | __wrap_cross_layer_fault_step | `memory_diagnostic_step(&state->control.memory_diagnostic,state->time.time_ms,` | Optional revised wrapper probes after injector, before normal tasks. |
| revised_capture | src/v7_3/revised_runtime.c:178 | __wrap_detection_algorithm_step | `runtime_observation_t o;runtime_observation_capture(state,&o);` | Revised detector gets captured interface, not whole state. |
| reference_acquire | src/v7_3/revised_runtime.c:64 | reference_acquire | `redundant_temperature_sample(r,state->time.time_ms,state->plant.coolant_temp_true_c);` | Optional reference channel is another model fed by same plant truth. |
| reference_model | src/redundant_temperature.c:18 | redundant_temperature_sample | `float measured=physical_c+s->offset_c+noise;` | Reference has its own state/noise, but independence is not hardware proven. |
| revised_memory | src/v7_3/clo_dsf_revised.c:29 | clo_revised_extract | `o->target_register_c != o->target_shadow_c` | Register/shadow comparison can expose value-changing memory fault without command change. |
| revised_target | src/v7_3/clo_dsf_revised.c:31 | clo_revised_extract | `o->control_target_c != (float)o->target_shadow_c` | Active target/shadow comparison shares software provenance. |
| adc_sample | src/v7_3/diagnostic_temperature.c:12 | diagnostic_temperature_sample | `while(s->next_ms<=now){` | Optional phase-offset ADC model catches up scheduled sample timestamps. |
| adc_interpolate | src/v7_3/diagnostic_temperature.c:17 | diagnostic_temperature_sample | `double at_sample=s->previous_physical+w*(physical-s->previous_physical);` | Interpolated physical values use invocation endpoint. |
| adc_gain | src/v7_3/diagnostic_temperature.c:22 | diagnostic_temperature_sample | `double measured=((1+s->gain)*s->thermal_state+s->offset+noise)*(1+s->adc_reference_gain);` | Explicit simulated gain/offset/noise/ADC-reference path. |
| adc_publish | src/v7_3/diagnostic_temperature.c:24 | diagnostic_temperature_sample | `s->output.value_c=(float)(round(measured/s->quantum)*s->quantum);` | Only latest output remains after catch-up loop. |
| triplex_pulse | scripts/run_clo_dsf_triplex.py:124 | embedded C: inject_value | `now>=injection_start+injection_duration` | Generated adapter pulse gate only consulted at explicit sample calls. |
| triplex_shared | scripts/run_clo_dsf_triplex.py:136 | embedded C: diagnostic_acquire | `inject_value(&state->sensors.coolant_source_c,0,now);state->sensors.coolant_temp_meas_c=state->sensors.coolant_source_c;` | Primary source and delivered channels can be modified together. |
| triplex_preserve | scripts/run_clo_dsf_triplex.py:152 | build | `adapter=adapter.replace(' inject_value(&state->sensors.coolant_source_c,0,now)` | Generated build adds mask guard so non-sensor communication cases keep delivered data. |
| triplex_link | scripts/run_clo_dsf_triplex.py:178 | build | `'-Wl,--wrap=cross_layer_fault_step'` | Script links sensor/memory/detector wrappers into temporary comparison binary. |
| mr_loop | scripts/run_clo_dsf_multirate.py:46 | embedded C: mr_acquire | `for(unsigned at=mr_last_ms+period;at<=now;at+=period){` | 25/50 ms sub-acquisitions computed in a batch at outer invocation. |
| mr_interpolate | scripts/run_clo_dsf_multirate.py:49 | embedded C: mr_acquire | `float at_physical=mr_last_physical+(physical-mr_last_physical)` | Subsample plant input interpolated using current endpoint. |
| mr_inject | scripts/run_clo_dsf_multirate.py:55 | embedded C: mr_acquire | `inject_value(&sensor->output.value_c,member,sensor->output.sample_ms);` | Pulse applied to returned acquisition at sample timestamp. |
| mr_probe | src/v7_3/multirate_memory.c:5 | mr_memory_step | `unsigned interval=nominal==500?(s->checks%2?600:400):(s->checks%2?300:200);` | Nominal 500/250 probes actually alternate 600/400 or 300/200 ms. |
| mailbox_publish | src/v7_3/digital_sensor_integrity.c:17 | di_publish | `w->protected_record=p;w->valid=true;*r=p;` | Witness and envelope are ordinary software record assignments. |
| mailbox_verify | src/v7_3/digital_sensor_integrity.c:32 | di_verify | `if(ms!=p->ms\|\|r->sequence!=p->sequence\|\|r->ms!=p->ms)status\|=2;` | Checks timestamp and sequence against stored witness, not an independent clock. |
| mailbox_bank | scripts/run_digital_integrity.py:19 | embedded C: <file-scope> | `static di_bank_t di_banks[2],*di_producer;` | Optional protected-bank template is ordinary process storage, not hardware isolation. |
| mailbox_wrap | scripts/run_digital_integrity.py:65 | build | `s=s.replace(' __real_sensors_step(state);'` | Optional build instruments producer boundaries; not default ECU behavior. |
| serialized | src/v7_2/final_observation_io.c:12 | <file-scope fields table> | `FIELD(time_ms,UINT_FIELD),FIELD(coolant_measured_c,FLOAT_FIELD),FIELD(sample_timestamp_ms,UINT_FIELD)` | Replay allowlist includes timestamps but omits new shadow/tap/probe/reference additions. |
| replay_zero | src/v7_2/final_observation_io.c:34 | final_observation_read | `memset(o,0,sizeof(*o));` | Omitted fields become zero/invalid when reading this replay format. |
| build_default | Makefile:6 | <file-scope> | `SRC := $(wildcard src/*.c)` | Base build does not automatically compile v7_3 subdirectory. |
| build_priority | GNUmakefile:2 | <file-scope> | `include Makefile` | Default GNU make entry adds historical v7 variants. |
| build_revised | clo_dsf_revised.mk:6 | <file-scope> | `-Wl,--wrap=cross_layer_fault_step` | Separate revised build enables memory/sensor wrappers. |
| probe_max | include/memory_diagnostic.h:7 | <file-scope> | `#define MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS 1100U` | Probe schedule maximum interval constant. |
| probe_phase | include/memory_diagnostic.h:6 | <file-scope> | `#define MEMORY_DIAGNOSTIC_PHASE_STEP_MS 100U` | Wrap-around phase step. |
| log_period | include/config.h:18 | <file-scope> | `#define ECU_LOG_PERIOD_MS 100U` | Logger outer cadence. |
| safety_period | include/config.h:17 | <file-scope> | `#define ECU_SAFETY_PERIOD_MS 100U` | Safety outer cadence. |
| crc | src/v7_3/digital_sensor_integrity.c:10 | di_tag | `crc^=(v[i]>>(8*b))&255U;` | Unkeyed deterministic CRC arithmetic. |
| source_period_variant | scripts/run_clo_dsf_multirate.py:45 | embedded C: mr_acquire | `unsigned period=k?25:50;` | Optional two acquisition rates. |
| base_init_probe | src/control.c:30 | control_init | `state->control.memory_diagnostic = (memory_diagnostic_t){0};` | Base diagnostic fields start invalid. |
| operating_load | src/control.c:45 | control_step | `float load_term = 0.35f * state->plant.engine_load;` | Control directly reads simulated operating load. |
| operating_speed | src/control.c:46 | control_step | `float speed_term = state->plant.vehicle_speed_kph / 200.0f;` | Control reads simulated vehicle speed, not a separately verified acquisition. |
| operating_capture | src/runtime_observation.c:16 | runtime_observation_capture | `.detector_alarm = s->detection.alarm_active, .engine_load = s->plant.engine_load,` | Operating load is copied from plant state; adjacent fields copy modeled ambient and speed measurements. |
