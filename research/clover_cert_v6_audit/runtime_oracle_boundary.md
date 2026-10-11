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

## The boundary is about producers, not column names

A published field is not automatically independent or trustworthy. All principal
state objects share `ecu_state_t` and the same process/clock. The named domains in
the manifest are **logical dependency groups**, not verified isolation boundaries.
The base detector accepts a whole ECU state; a future checker must not treat that
signature as an admissible runtime contract. Even `runtime_observation_t` contains
legacy outputs whose producers read oracle information.

`state_shared`: [include/ecu_types.h:276](../../include/ecu_types.h#L276) (`<file-scope>`); `revised_capture`: [src/v7_3/revised_runtime.c:178](../../src/v7_3/revised_runtime.c#L178) (`__wrap_detection_algorithm_step`); `obs_diag`: [src/runtime_observation.c:15](../../src/runtime_observation.c#L15) (`runtime_observation_capture`); `diag_truth`: [src/diagnostics.c:151](../../src/diagnostics.c#L151) (`diagnostics_step`); `detector_truth`: [src/detection_algorithm.c:997](../../src/detection_algorithm.c#L997) (`detection_algorithm_step`)

## Evidence availability

| Evidence | Visibility | Exact availability and qualification | Anchors |
|---|---|---|---|
| `E_TRUTH` — plant.coolant_temp_true_c, reference.plant.coolant_temp_true_c, propagation.* | GROUND_TRUTH_ONLY | Simulator/paired evaluation truth; not an admissible future runtime witness. Legacy readers of live plant truth exist. | `truth`, `prop_truth`, `reference_copy` |
| `E_FAULT` — cross_layer_fault.*, faults.active_mode, faults.active_behavior, cross_layer_runtime.active, memory_original_value, memory_corrupted_value, replay_active, update_dropped, configured_task_delay_ms | GROUND_TRUTH_ONLY | Injector labels/configuration and scoring metadata, even when raw CSV logs them. Legacy fan/diagnostic/onset readers are exceptions, not an admissible input precedent. | `flip`, `fan_oracle`, `diag_label`, `detector_onset`, `comm_drop` |
| `E_TAP` — source_c, source_previous_c, source_ms, source_previous_ms, source_valid, source_previous_valid | RUNTIME_PUBLISHED_MODEL | In-memory runtime_observation_capture; tap is after front-end faults, before transport/trace. Optional generated adapters may change it. Not in old final_observation serialization. | `source_tap`, `source_time`, `obs_source`, `serialized` |
| `E_DELIVERED` — coolant_measured_c | RUNTIME_PUBLISHED_MODEL | Primary ECU-facing coolant after hold/trace/delivery, used by control. | `delivered_publish`, `control_error` |
| `E_AGE` — sample_timestamp_ms, sample_age_ms, sample_freshness_ok, sample_expected_period_ms | RUNTIME_PUBLISHED_MODEL | Explicitly available in runtime capture and old final_observation CSV. New communication path publishes source time; legacy trace branch instead reports current refresh time. Integrity is not authenticated. | `timestamp_publish`, `age`, `obs_age`, `obs_timestamp`, `serialized`, `sensor_trace` |
| `E_TRANSPORT_ORACLE` — cross_layer_runtime.history, history_timestamps, generated_ms, delivered_ms, replay_source_ms, update_generated, update_delivered, total_drops | GROUND_TRUTH_ONLY | Injector/history bookkeeping not wholesale copied to runtime interface. A derived source timestamp is deliberately published as E_AGE. | `history`, `delivery_time`, `delivery_source`, `comm_replay` |
| `E_MEMORY` — target_register_c, target_shadow_c, target_shadow_valid, control_target_c | RUNTIME_PUBLISHED_MODEL | Live register/shadow and executed target are in-memory observations; shadow/register additions omitted by old replay serializer. | `obs_memory`, `commit`, `target_publish`, `revised_memory`, `serialized` |
| `E_PROBE` — memory_check_ms, memory_check_valid, memory_check_failed | RUNTIME_OPTIONAL_MODEL | Only when optional revised wrapper is enabled with live log_file; base initialization leaves diagnostic invalid. Callback device model enforces stuck polarity. Not proof of deployed BIST. | `probe_call`, `probe_read`, `probe_backend`, `base_init_probe` |
| `E_TIMING` — timing.current_release_ms, timing.job_release_ms, timing.actual_start_ms, timing.actual_completion_ms, timing.last_successful_execution_ms, timing.execution_age_ms, timing.release_sequence, timing.execution_sequence, timing.cancelled_release_count, timing.job_outstanding, timing.missed_expected_execution, timing.deadline_exceeded, control_execution_ms | RUNTIME_PUBLISHED_MODEL | Recorder observed by runtime capture. Source of timestamps is simulated scheduler; stress publishes a sampled snapshot rather than a full queue/event history. | `release`, `timing_start`, `timing_complete`, `obs_timing`, `stress_publish` |
| `E_COMMAND` — pump_command, fan_command | RUNTIME_PUBLISHED_MODEL | Executed control output; capture phase matters because safety may override and re-realize it. Legacy safety/action provenance can depend on oracle inputs. | `pump_cmd`, `control_error`, `reaction`, `runtime_capture`, `action_gate` |
| `E_ACTUAL` — pump_actual, fan_actual | RUNTIME_PUBLISHED_MODEL | Direct software realization of command and scale/stuck/trace; no independently sampled physical response shown. | `pump_scale`, `pump_publish`, `obs_actuator`, `fan_trace` |
| `E_FAN_HEALTH` — fan_driver_feedback_ok, fan_rotation_feedback_ok, fan_current_feedback_ok, fan_actuator_health_score | RUNTIME_PUBLISHED_ORACLE_DERIVED | Published in actuator state, used directly by full-state baseline detectors; not part of runtime_observation_t. self_test_gap reads fan fault label, including zero command. | `fan_oracle`, `fan_stuck` |
| `E_LEGACY_OUTPUT` — diagnostic_id, safety_state, detector_alarm | RUNTIME_PUBLISHED_ORACLE_DERIVED | Base/legacy variants may depend on plant truth and injected behavior. Alternate wrapper outputs require separate provenance, not blanket taint removal. | `obs_diag`, `diag_truth`, `diag_label`, `hybrid_truth`, `detector_truth`, `safety_truth`, `action_gate` |
| `E_REFERENCE` — reference_c, reference_ms, reference_enabled, reference_valid, reference_failed, diagnostic_c.output.* | RUNTIME_OPTIONAL_MODEL | Reference B only initialized on revised option; diagnostic C only in generated optional builds. Own state/noise/gain, shared simulated physical input. | `obs_reference`, `reference_acquire`, `reference_model`, `adc_gain`, `triplex_link` |
| `E_DIGITAL` — di_witness_t.protected_record, di_record_t.sequence, di_record_t.ms, di_record_t.tag, di_verify status | RUNTIME_OPTIONAL_MODEL | Optional generated producer/checker. Software CRC consistency requires witness protection; same-process storage is not proof of isolation. | `mailbox_publish`, `mailbox_verify`, `mailbox_bank`, `mailbox_wrap`, `crc` |
| `E_PUMP_HEALTH` — independent physical pump flow/current/speed/health witness | UNVERIFIED_RUNTIME | Not established by inspected pump path. Fan fault-label feedback cannot substitute for pump evidence. | `pump_scale`, `pump_publish`, `fan_oracle` |

## Confirmed oracle dependencies

**VERIFIED:** legacy sensor rationality subtracts `plant.coolant_temp_true_c` from
the delivered value. Legacy threshold/EWMA/CUSUM residuals and the Hybrid sensor
score also use live plant truth. Diagnostic permanent classification reads injected
fault behavior. `before_fault` reads campaign onset metadata: it affects scoring
and gates the first-detection/action-request block, not merely offline reporting.
The safety shutdown branch reads plant truth. These existing behaviors are recorded
without altering or retuning them.

`diag_truth`: [src/diagnostics.c:151](../../src/diagnostics.c#L151) (`diagnostics_step`); `diag_label`: [src/diagnostics.c:154](../../src/diagnostics.c#L154) (`diagnostics_step`); `hybrid_truth`: [src/detection_algorithm.c:324](../../src/detection_algorithm.c#L324) (`hybrid_kalman_sensor_score`); `detector_truth`: [src/detection_algorithm.c:997](../../src/detection_algorithm.c#L997) (`detection_algorithm_step`); `detector_onset`: [src/detection_algorithm.c:1006](../../src/detection_algorithm.c#L1006) (`detection_algorithm_step`); `action_gate`: [src/detection_algorithm.c:1169](../../src/detection_algorithm.c#L1169) (`detection_algorithm_step`); `safety_truth`: [src/safety_monitor.c:31](../../src/safety_monitor.c#L31) (`requested_state_from_diagnostics`)

**VERIFIED:** the fan driver/current/rotation “self-test” is derived from the
injected fan-stuck mode. It is a simulator-produced runtime field, not independently
verified hardware-health feedback. No corresponding independent pump-health
measurement is established by the inspected pump implementation.

`fan_oracle`: [src/actuators.c:48](../../src/actuators.c#L48) (`update_fan_actuator_feedback`); `pump_publish`: [src/actuators.c:114](../../src/actuators.c#L114) (`actuators_step`); `pump_scale`: [src/actuators.c:90](../../src/actuators.c#L90) (`actuators_step`)

**VERIFIED:** the paired fault-free ECU and propagation differences are evaluation
instrumentation. Separate reference state does not create an independent deployed
sensor. A regular simulated sensor must of course be driven by modeled physical
state; that alone is not a prohibited oracle feature. The important distinction is
between consuming its modeled measured output and giving inference direct pristine
truth, injection labels, or counterfactual differences. Optional B/C channels have
separate modeled state/noise/gain but share physical truth and process resources;
hardware independence and common-cause limits remain UNVERIFIED.

`reference_copy`: [src/scheduler.c:135](../../src/scheduler.c#L135) (`scheduler_run`); `reference_disable`: [src/scheduler.c:137](../../src/scheduler.c#L137) (`scheduler_run`); `truth`: [src/runtime_observation.c:47](../../src/runtime_observation.c#L47) (`experiment_ground_truth_capture`); `prop_truth`: [src/propagation_monitor.c:57](../../src/propagation_monitor.c#L57) (`propagation_monitor_step`); `reference_acquire`: [src/v7_3/revised_runtime.c:64](../../src/v7_3/revised_runtime.c#L64) (`reference_acquire`); `reference_model`: [src/redundant_temperature.c:18](../../src/redundant_temperature.c#L18) (`redundant_temperature_sample`); `adc_gain`: [src/v7_3/diagnostic_temperature.c:22](../../src/v7_3/diagnostic_temperature.c#L22) (`diagnostic_temperature_sample`)

## Timestamp and serializer distinction

**VERIFIED:** the new communication path publishes the historical source timestamp
into `coolant_sensor_last_update_ms`; `runtime_observation_capture` copies this to
`sample_timestamp_ms` and also copies age. These fields are in the old final
observation serializer. Thus “all replay/delay timestamps are simulator-only” is
incorrect for this implementation. Injector generation/reception times, replay flags,
drop causes and history buffers are not wholesale exposed by that interface.

The external sensor-trace path is different: it marks its sample refreshed at the
current scheduled read. That read time does not authenticate the original physical
acquisition represented by a trace value. Do not transfer the new communication
provenance contract to every historical/RTL input route.

The in-memory struct also contains shadow, acquisition tap, probe and reference
additions that the older explicit serializer omits. `final_observation_read` zeroes
the struct before reading its allowlist. Availability in live capture therefore
does not establish availability in a saved/replayed observation CSV.

`timestamp_publish`: [src/sensors.c:129](../../src/sensors.c#L129) (`sensors_step`); `obs_timestamp`: [src/runtime_observation.c:9](../../src/runtime_observation.c#L9) (`runtime_observation_capture`); `obs_age`: [src/runtime_observation.c:10](../../src/runtime_observation.c#L10) (`runtime_observation_capture`); `delivery_time`: [src/sensor_delivery.c:49](../../src/sensor_delivery.c#L49) (`cross_layer_sensor_delivery`); `serialized`: [src/v7_2/final_observation_io.c:12](../../src/v7_2/final_observation_io.c#L12) (`<file-scope fields table>`); `replay_zero`: [src/v7_2/final_observation_io.c:34](../../src/v7_2/final_observation_io.c#L34) (`final_observation_read`); `sensor_trace`: [src/sensors.c:109](../../src/sensors.c#L109) (`sensors_step`)

## Shared corruption and integrity

**VERIFIED:** authorized target commits write both register and shadow; normal
capture copies them from the same aggregate. The optional Triplex producer can
modify the acquisition tap and delivered primary value together. Its generated
build adds a mask guard, so this assignment does not indiscriminately overwrite
communication-only cases. Agreement of two such fields is not two independent votes.

**VERIFIED:** digital-integrity code publishes value bits, channel, sequence, time
and an unkeyed CRC into ordinary records. The optional bank is process-static
storage. CRC equality checks are implemented; enforced isolation, authenticated
producers and trusted verifier execution are UNVERIFIED. Coherent corruption or
legal-transform misuse can preserve agreement. No MPU/MMU/HSM boundary is inferred
from the name `protected_record` or the comment “trusted acquisition tap.”

`commit`: [src/control.c:24](../../src/control.c#L24) (`control_commit_target`); `obs_memory`: [src/runtime_observation.c:21](../../src/runtime_observation.c#L21) (`runtime_observation_capture`); `triplex_shared`: [scripts/run_clo_dsf_triplex.py:136](../../scripts/run_clo_dsf_triplex.py#L136) (`embedded C: diagnostic_acquire`); `triplex_preserve`: [scripts/run_clo_dsf_triplex.py:152](../../scripts/run_clo_dsf_triplex.py#L152) (`build`); `mailbox_publish`: [src/v7_3/digital_sensor_integrity.c:17](../../src/v7_3/digital_sensor_integrity.c#L17) (`di_publish`); `mailbox_verify`: [src/v7_3/digital_sensor_integrity.c:32](../../src/v7_3/digital_sensor_integrity.c#L32) (`di_verify`); `crc`: [src/v7_3/digital_sensor_integrity.c:10](../../src/v7_3/digital_sensor_integrity.c#L10) (`di_tag`); `mailbox_bank`: [scripts/run_digital_integrity.py:19](../../scripts/run_digital_integrity.py#L19) (`embedded C: <file-scope>`)

## Admissible next-step contract (not implemented)

Model the exact producer, writer set, acquisition time, publication time, validity
and corruption domain of each chosen input. Qualify model-derived actuator response,
clock fields and optional sensor/probe channels explicitly. Exclude raw fault labels,
true/counterfactual temperature, propagation truth and oracle-derived legacy alarms
from evidence asserted to be independent. A different choice is possible only with
an explicit oracle-aided evaluation label, never silently. Derived fields and
repeated observations sharing a compromised producer cannot gain independence by
being serialized into separate columns. Missing or compromised provenance means
UNKNOWN, rather than a fabricated origin.

## Operating context and typed dependencies

`E_OPERATING` covers `engine_load`, `ambient_c` and `vehicle_speed_kph`.
Control directly uses simulated plant load/speed; capture copies plant load and
modeled sensor ambient/speed. These are model context, not independently verified
physical measurements. Their data dependencies must be retained in the control
provenance map (`operating_load`, `operating_speed`, `operating_capture` anchors).

The manifest's twenty `provenance_edges` explicitly distinguish physical input to
a measurement model, operating-context model input, conditional transport
publication, ordinary dataflow and oracle input to published legacy logic. A
sensor model's use of plant truth at its physical-input boundary must not be
confused with a detector directly subtracting pristine plant truth. Conversely,
calling a legacy DTC a runtime field does not erase its direct oracle inputs.
These typed edges describe inspected dependencies, not a new inference algorithm.
