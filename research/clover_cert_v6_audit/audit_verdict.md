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

## Audit verdict

**Source-grounded foundation obtained; unconditional origin attribution remains
UNKNOWN in the five requested critical cases.** Conditional state/provenance
violations may be identifiable under narrower, verified future contracts. This is
not a novel algorithm, an origin-certificate implementation or an IEEE Transactions
readiness result. No novelty literature claim is made.

The most consequential implementation findings are:

1. The current runtime interface has live register/shadow and acquisition-tap
   fields; dormant-to-plant does not automatically mean dormant-to-monitor.
   Optional probe write failures provide a different observation from passive
   register equality. Their enabled build and integrity assumptions matter.
2. A non-latching pulse missed by every available acquisition is not observable
   merely because its configured start/end is present in an experiment manifest.
3. Pump degradation at zero command has no response difference in this model;
   no independently verified pump-health witness was established. Fan feedback
   is partly produced from injected fault metadata and cannot fill this gap.
4. Source, delivered, target, shadow, feedback and optional CRC witnesses coexist
   in software. Source/delivered shared modification is explicit in an optional
   adapter. Independence and resistance to coherent corruption remain unverified.
5. New communication source timestamps and age really are runtime-published.
   Reception/history/replay-cause bookkeeping is not wholesale runtime evidence.
   Timestamp availability can reveal staleness without proving its unique origin.
6. Some legacy diagnostics, detectors and safety paths use live plant truth or
   fault metadata. An apparently runtime-only output can therefore carry oracle
   dependencies. Observation allowlisting alone does not sanitize its producer.
7. Optional 25/50 ms acquisitions are batched, endpoint-interpolated model events;
   their timestamp is not an established online publication or reaction bound.

## Suitable subsequent mathematical models

- **P_MEMORY — INFERRED candidate:** Discrete register-value, consumption and optional probe traces; distinguish latent device defect from observed state mismatch. Prerequisites: A_SHADOW, A_BUILD. Source: `flip`: [src/cross_layer_fault.c:85](../../src/cross_layer_fault.c#L85) (`cross_layer_fault_step`); `stuck`: [src/cross_layer_fault.c:96](../../src/cross_layer_fault.c#L96) (`cross_layer_fault_step`); `restore`: [src/cross_layer_fault.c:91](../../src/cross_layer_fault.c#L91) (`cross_layer_fault_step`); `consume`: [src/control.c:43](../../src/control.c#L43) (`control_step`); `probe_backend`: [src/memory_diagnostic_backend.c:21](../../src/memory_diagnostic_backend.c#L21) (`cross_layer_memory_write`)
- **P_TIMING — INFERRED candidate:** Release/admission/cancel/start/complete automata with separate base and stress semantics. Prerequisites: A_CLOCK, A_BUILD. Source: `release`: [src/cross_layer_fault.c:111](../../src/cross_layer_fault.c#L111) (`cross_layer_control_execution`); `skip`: [src/cross_layer_fault.c:144](../../src/cross_layer_fault.c#L144) (`cross_layer_control_execution`); `delay_due`: [src/cross_layer_fault.c:134](../../src/cross_layer_fault.c#L134) (`cross_layer_control_execution`); `delay_complete`: [src/cross_layer_fault.c:122](../../src/cross_layer_fault.c#L122) (`cross_layer_control_execution`); `timing_deadline`: [src/runtime_timing_observation.c:70](../../src/runtime_timing_observation.c#L70) (`runtime_timing_observe`)
- **P_TRANSPORT — INFERRED candidate:** Generated/delivered sample provenance and observational equivalence classes, conditional on timestamp integrity. Prerequisites: A_TAP, A_CLOCK. Source: `history`: [src/sensor_delivery.c:13](../../src/sensor_delivery.c#L13) (`cross_layer_sensor_delivery`); `comm_delay`: [src/sensor_delivery.c:27](../../src/sensor_delivery.c#L27) (`cross_layer_sensor_delivery`); `comm_drop`: [src/sensor_delivery.c:35](../../src/sensor_delivery.c#L35) (`cross_layer_sensor_delivery`); `comm_replay`: [src/sensor_delivery.c:38](../../src/sensor_delivery.c#L38) (`cross_layer_sensor_delivery`); `obs_timestamp`: [src/runtime_observation.c:9](../../src/runtime_observation.c#L9) (`runtime_observation_capture`)
- **P_SAMPLING — INFERRED candidate:** Acquisition-time versus publication-time traces with unobservable intervals and optional batched acquisition. Prerequisites: A_SENSOR, A_SUBTICK. Source: `sensor_period`: [include/config.h:9](../../include/config.h#L9) (`<file-scope>`); `adc_sample`: [src/v7_3/diagnostic_temperature.c:12](../../src/v7_3/diagnostic_temperature.c#L12) (`diagnostic_temperature_sample`); `mr_loop`: [scripts/run_clo_dsf_multirate.py:46](../../scripts/run_clo_dsf_multirate.py#L46) (`embedded C: mr_acquire`)
- **P_ACTUATOR — INFERRED candidate:** Excitation-conditioned model observability; include healthy/degraded zero-command equivalence. Prerequisites: A_PUMP. Source: `pump_scale`: [src/actuators.c:90](../../src/actuators.c#L90) (`actuators_step`); `pump_thermal`: [src/thermal_plant.c:187](../../src/thermal_plant.c#L187) (`thermal_plant_step`)
- **P_SHARED — INFERRED candidate:** Common-cause provenance graphs and abstention for jointly compromised evidence; no independence assumed from field names. Prerequisites: A_PROCESS, A_MAILBOX, A_POSTWRITE. Source: `state_shared`: [include/ecu_types.h:276](../../include/ecu_types.h#L276) (`<file-scope>`); `triplex_shared`: [scripts/run_clo_dsf_triplex.py:136](../../scripts/run_clo_dsf_triplex.py#L136) (`embedded C: diagnostic_acquire`); `mailbox_publish`: [src/v7_3/digital_sensor_integrity.c:17](../../src/v7_3/digital_sensor_integrity.c#L17) (`di_publish`)

The next research step is a formal evidence/observation contract and admissible
fault-domain model, with explicit UNKNOWN regions and publication-time semantics.
It is not justified to implement a new synthesis algorithm by silently treating
these missing contracts as true. No algorithm or experiment was added by this audit.

## Executed validation

The standard-library validator checks structure, unique IDs/reference consistency,
source-file existence and SHA256, exact 1-based line/token anchors, explicit
visibility, trust-domain assumptions and unverified timing. It does not mechanically
prove all prose deductions or protection mechanisms. The accompanying mutation
self-tests exercise malformed structure, missing sources, line/token errors,
visibility/domain omissions, unsupported timing and oracle promotion.

See `validation_report.json` for actual counts and full unresolved findings, and
`unresolved_assumptions.md` for all thirteen explicit assumption records. The audit
also performs a full outside-audit byte/symlink/file-set comparison against the
preflight workspace snapshot. Production code, GUI, experiments, historical/frozen
outputs and user changes are not repaired or overwritten if that comparison fails.

No build or historical test suite was run because those can write outside the
permitted audit directory. The checks execute only the new audit validator and its
in-memory negative tests. The entire Git history remains untouched.

### Recorded validation result

Executed `python3 research/clover_cert_v6_audit/validate_manifest.py --self-test --check-preservation`.
The result is **STRUCTURALLY_VALID_WITH_UNRESOLVED_FINDINGS**: zero structural/source
errors, 134 exact anchors across 36 source files, 19 fault-origin paths, 17 evidence
classes, 20 typed provenance edges, 12 timing records and five critical cases. All
21 validator self-tests passed. The 41 unresolved findings remain explicitly listed
in `validation_report.json`; they are qualifications, not 41 independent experimental
failures or evidence of successful origin attribution.

The preservation check passed for all 43,688 pre-existing files (13,570,258,677 bytes
in the baseline), with no changed, missing or added files outside this audit directory.
Git HEAD remains `a340ca5cf0473d7dc572f7cd63e44fbc25b175a7`. Existing user changes,
production code, GUI, frozen HETIA results, paper artifacts and experiments were preserved.
