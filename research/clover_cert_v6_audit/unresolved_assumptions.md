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

## Explicit assumptions

### A_PROCESS — UNVERIFIED

Hardware isolation, memory protection and independent power/clock domains are not established by structs or comments.

Evidence: `state_shared`: [include/ecu_types.h:276](../../include/ecu_types.h#L276) (`<file-scope>`); `mailbox_bank`: [scripts/run_digital_integrity.py:19](../../scripts/run_digital_integrity.py#L19) (`embedded C: <file-scope>`)

Required resolution/action: Independent protection mechanism and fault-containment evidence.

### A_SHADOW — UNVERIFIED

Target shadow, legal writes and probe code/callback results remain honest when target storage is faulty. Common corruption can defeat agreement.

Evidence: `commit`: [src/control.c:24](../../src/control.c#L24) (`control_commit_target`); `probe_backend`: [src/memory_diagnostic_backend.c:21](../../src/memory_diagnostic_backend.c#L21) (`cross_layer_memory_write`); `revised_memory`: [src/v7_3/clo_dsf_revised.c:29](../../src/v7_3/clo_dsf_revised.c#L29) (`clo_revised_extract`)

Required resolution/action: Concrete protected storage, writer authorization and common-cause fault coverage.

### A_CLOCK — UNVERIFIED

Common simulated timestamps correspond to a trustworthy deployed clock and bounded monitoring delay.

Evidence: `loop`: [src/scheduler.c:146](../../src/scheduler.c#L146) (`scheduler_run`); `timing_start`: [src/runtime_timing_observation.c:47](../../src/runtime_timing_observation.c#L47) (`runtime_timing_start`); `timing_complete`: [src/runtime_timing_observation.c:54](../../src/runtime_timing_observation.c#L54) (`runtime_timing_complete`)

Required resolution/action: Clock provenance, WCET, scheduling and dropped-record contracts.

### A_TAP — UNVERIFIED

Acquisition tap and timestamp remain unmodified by faults affecting delivered/control values.

Evidence: `source_tap`: [src/sensors.c:84](../../src/sensors.c#L84) (`sensors_step`); `triplex_shared`: [scripts/run_clo_dsf_triplex.py:136](../../scripts/run_clo_dsf_triplex.py#L136) (`embedded C: diagnostic_acquire`)

Required resolution/action: Producer/consumer integrity boundary and explicitly scoped write-fault domains.

### A_PUMP — UNVERIFIED

A physical pump-health or flow/current witness independent of the command/realization model exists.

Evidence: `pump_scale`: [src/actuators.c:90](../../src/actuators.c#L90) (`actuators_step`); `pump_publish`: [src/actuators.c:114](../../src/actuators.c#L114) (`actuators_step`)

Required resolution/action: Actual separately acquired pump-feedback interface, validity, timing and failure model.

### A_SENSOR — UNVERIFIED

Optional redundant ADC channels are physically independent and their common-cause behavior is bounded.

Evidence: `reference_acquire`: [src/v7_3/revised_runtime.c:64](../../src/v7_3/revised_runtime.c#L64) (`reference_acquire`); `adc_gain`: [src/v7_3/diagnostic_temperature.c:22](../../src/v7_3/diagnostic_temperature.c#L22) (`diagnostic_temperature_sample`)

Required resolution/action: Hardware acquisition design and common-cause measurements; shared simulated plant is not that evidence.

### A_MAILBOX — UNVERIFIED

Protected CRC witness storage is inaccessible to the corruption that affects values, metadata or verifier.

Evidence: `mailbox_publish`: [src/v7_3/digital_sensor_integrity.c:17](../../src/v7_3/digital_sensor_integrity.c#L17) (`di_publish`); `mailbox_verify`: [src/v7_3/digital_sensor_integrity.c:32](../../src/v7_3/digital_sensor_integrity.c#L32) (`di_verify`); `mailbox_bank`: [scripts/run_digital_integrity.py:19](../../scripts/run_digital_integrity.py#L19) (`embedded C: <file-scope>`)

Required resolution/action: Enforced storage/access protection; CRC by itself is not authenticated provenance.

### A_BUILD — UNVERIFIED

A named binary or historical result is linked with the exact optional wrappers audited here.

Evidence: `build_default`: [Makefile:6](../../Makefile#L6) (`<file-scope>`); `build_revised`: [clo_dsf_revised.mk:6](../../clo_dsf_revised.mk#L6) (`<file-scope>`); `triplex_link`: [scripts/run_clo_dsf_triplex.py:178](../../scripts/run_clo_dsf_triplex.py#L178) (`build`); `mailbox_wrap`: [scripts/run_digital_integrity.py:65](../../scripts/run_digital_integrity.py#L65) (`build`)

Required resolution/action: Binary/source/config/link provenance per evaluated run; no build or experiment run in this audit.

### A_FAULTSET — UNVERIFIED

The competing-origin set is closed, single-fault and matches the allowed injector combinations.

Evidence: `mixed_reject`: [src/cross_layer_config.c:181](../../src/cross_layer_config.c#L181) (`cross_layer_validate`); `legacy_priority`: [src/fault_injection.c:159](../../src/fault_injection.c#L159) (`fault_injection_step`); `stress_exclusive`: [src/main.c:307](../../src/main.c#L307) (`main`)

Required resolution/action: Explicit admissible adversary/fault specification and indistinguishability checks.

### A_ORACLE — VERIFIED

Some currently published legacy outputs are oracle-derived and cannot serve as independent runtime evidence for a future sound checker.

Evidence: `diag_truth`: [src/diagnostics.c:151](../../src/diagnostics.c#L151) (`diagnostics_step`); `hybrid_truth`: [src/detection_algorithm.c:324](../../src/detection_algorithm.c#L324) (`hybrid_kalman_sensor_score`); `fan_oracle`: [src/actuators.c:48](../../src/actuators.c#L48) (`update_fan_actuator_feedback`); `safety_truth`: [src/safety_monitor.c:31](../../src/safety_monitor.c#L31) (`requested_state_from_diagnostics`); `action_gate`: [src/detection_algorithm.c:1169](../../src/detection_algorithm.c#L1169) (`detection_algorithm_step`)

Required resolution/action: Require a taint-aware input contract before reusing these outputs.

### A_REPLAY — VERIFIED

Existing final_observation serialization is narrower than the in-memory observation struct; omitted additions read as zero.

Evidence: `serialized`: [src/v7_2/final_observation_io.c:12](../../src/v7_2/final_observation_io.c#L12) (`<file-scope fields table>`); `replay_zero`: [src/v7_2/final_observation_io.c:34](../../src/v7_2/final_observation_io.c#L34) (`final_observation_read`); `obs_memory`: [src/runtime_observation.c:21](../../src/runtime_observation.c#L21) (`runtime_observation_capture`); `obs_source`: [src/runtime_observation.c:27](../../src/runtime_observation.c#L27) (`runtime_observation_capture`); `obs_reference`: [src/runtime_observation.c:33](../../src/runtime_observation.c#L33) (`runtime_observation_capture`)

Required resolution/action: Select an audited complete input view; do not infer absent tap/shadow/reference values.

### A_SUBTICK — UNVERIFIED

A 25/50 ms modeled acquisition timestamp proves data was available to a checker at that instant.

Evidence: `mr_loop`: [scripts/run_clo_dsf_multirate.py:46](../../scripts/run_clo_dsf_multirate.py#L46) (`embedded C: mr_acquire`); `mr_interpolate`: [scripts/run_clo_dsf_multirate.py:49](../../scripts/run_clo_dsf_multirate.py#L49) (`embedded C: mr_acquire`); `adc_interpolate`: [src/v7_3/diagnostic_temperature.c:17](../../src/v7_3/diagnostic_temperature.c#L17) (`diagnostic_temperature_sample`)

Required resolution/action: Release/publication timestamps and an online scheduler; inspected template batches observations at the outer tick.

### A_POSTWRITE — UNVERIFIED

Arbitrary post-control corruption of both downstream values and upstream witnesses is faithfully represented by an existing general injector.

Evidence: `legacy_offset`: [src/control.c:53](../../src/control.c#L53) (`control_step`); `triplex_shared`: [scripts/run_clo_dsf_triplex.py:136](../../scripts/run_clo_dsf_triplex.py#L136) (`embedded C: diagnostic_acquire`); `state_shared`: [include/ecu_types.h:276](../../include/ecu_types.h#L276) (`<file-scope>`)

Required resolution/action: Define a testable write-fault model separately; this audit implements no new injection.

## Open modeling obligations

- Select a concrete input view and executable variant. Source templates, base
  live capture, revised capture and replay serialization are not interchangeable.
- Define acquisition versus publication versus consumption versus alert time,
  including base tick, stress substep and batched optional ADC cases.
- Specify legitimate writer behavior, corruption scope, persistence and recovery.
  Restoration to a saved activation value may overwrite an intervening legal
  update; a target/shadow discrepancy alone need not identify physical bit physics.
- Establish a threat/fault model for shared address-space corruption. Distinct
  struct members, independent RNG seeds and a CRC are not protection boundaries.
- Keep raw labels, fault activation, paired counterfactuals and oracle-derived
  baseline signals outside claimed independent runtime evidence.
- Prove or measure any physical sensor/actuator/clock trust or latency assumptions;
  simulation source inspection cannot supply them.
- Separate anomaly detection, evidence availability, mechanism identification and
  physical-origin attribution. A stale timestamp or register mismatch establishes
  at most a qualified contract violation under the selected trusted view.
- Reconstruct source/config/link provenance before interpreting historical results
  from generated adapters. Existing results were neither regenerated nor re-scored.
- This bounded inspection does not prove absence of all alternative code paths or
  physical side channels. No uninspected capability is assumed absent globally.

## Machine-reported unresolved findings

`validation_report.json` is authoritative for the executed validator result.
A structurally valid manifest can and here does retain unresolved findings.
The report contains per-record findings for unverified assumptions/domain isolation,
known oracle-derived or unavailable evidence, unverified deployment timing and
absence of unconditional per-path timing bounds. These are not 41 independent
experimental failures; several refer to the same unresolved protection obligation.
The optional `--strict-unresolved` mode returns exit 2 for this distinction.
