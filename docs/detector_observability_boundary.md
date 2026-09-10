# Runtime observations and experiment ground truth

V2 defines an explicit boundary for the **new** infrastructure. This is not a
claim that the accepted legacy detectors already satisfy production-ECU signal
purity. Their behavior is preserved; no new detector or detector retuning is
part of v2.

`include/runtime_observation.h` defines only `runtime_observation_t` and its
capture interface. It does not include the ground-truth header. A future
runtime monitor should accept this allowlisted snapshot, not `ecu_state_t`.

`include/experiment_ground_truth.h` separately defines
`experiment_ground_truth_t`: descriptor, injection-active truth, actual and
reference true coolant, reference observations, and propagation truth.
`hazard_model_step` is explicitly an **evaluation** consumer of both snapshots.
It cannot command the controller or safety monitor. No reference pointer or
hazard outcome is passed to a runtime detector.

| Signal | Runtime observable | Detector accessible | Evaluation only | Legacy exception | Reason |
| --- | --- | --- | --- | --- | --- |
| Delivered coolant measurement | yes | yes | no | none | Actual ECU-facing sensor value |
| Delivered packet acquisition timestamp/age | yes in this protocol | yes | no | none | Packet carries timestamp; freshness is observable |
| Replay source timestamp/history index | no as injector provenance | no through new API | yes | none | Dedicated replay metadata is not an input; historical packet timestamp remains observable |
| Newly generated, undelivered sample | no | no through new API | yes | none | Has not reached the ECU |
| Control target register / active calibration | yes | yes | no | none | Mutable ECU-owned control state |
| Pump/fan commands and actual feedback | yes | yes | no | Existing simulated health feedback models | Controller requests and modeled driver/rotation/current feedback |
| Last actual control execution time | yes | available to future snapshot monitors | no | Existing detectors do not consume it | Scheduling instrumentation available to the ECU |
| Diagnostic ID / protective mode | yes | yes | no | Legacy DTC classification uses injection metadata | Published ECU status is observable; provenance of old logic is a limitation |
| Runtime detector alarm | yes | output, not new injected evidence | no | Legacy bookkeeping gates described below | Used by reporting without label-based alarm improvements |
| Engine load, measured ambient/speed | modeled runtime context | yes | no | Context source is simulator environment | Existing operating context retained |
| Actual true coolant temperature | no independent production sensor assumed | not in new snapshot | yes | Existing C/Python sensor residual detectors use it | Simulator-only residual reference is not production observability |
| Fault-free reference trajectory/commands | no | no | yes | none introduced | Counterfactual evaluation simulation |
| Fault ID, layer, model, behavior | no | no through new API | yes | Legacy diagnostics use mode/behavior | Injection/orchestration/reporting metadata |
| Fault active flag, start, duration, ON/OFF | no | no through new API | yes | Legacy detector bookkeeping uses campaign start | Never new decision inputs |
| Saved original/corrupted register value | injected provenance: no | no | yes | Nominal/active calibration itself is observable | Separate actual ECU state from injection history |
| Propagation timestamps/path/depth | no | no | yes | none | Reference comparisons and outcome analysis |
| Hazard/critical exposure/FTTI/containment | experimental truth: no | no | yes | Safety already uses true coolant for shutdown | Evaluated after runtime decisions; not fed back |
| Scenario identity / experiment label / seed | no | no | yes | Legacy thermal prediction reads phase/environment | No new classification based on labels |

## Retained legacy exceptions

- `src/detection_algorithm.c` and its accepted Python equivalent use true plant
  coolant in residual evidence. Thermal predictions use scenario phase and
  configured environmental terms.
- C detector alarm-score/threshold logic is untouched. The existing detected,
  first-detection, false-positive, and action bookkeeping uses legacy campaign
  existence/start. These fields are not reinterpreted as cross-layer truth.
- `src/diagnostics.c` uses injected mode/behavior for permanent DTC classification.
- `src/safety_monitor.c` uses true coolant for shutdown evaluation.
- Legacy actuator self-test feedback has an explicit simulator fault model.

These are documented exceptions, not an excuse to add similar dependencies.
Moving/removing them requires a separately validated migration because it may
change HETIA results or safety reactions. The new campaign uses the existing
alarm waveform plus experiment-only reference comparison for attribution.
A detector miss is retained as a miss.

## Validation and future interfaces

The tests mutate injection ID/timing/active flags, propagation, hazard state, and
true coolant while holding ECU-facing signals fixed; the runtime snapshot stays
unchanged. Existing tests also verify that fault ID/seed changes do not alter
alarm outputs and that detector/diagnostics/safety source files contain no new
cross-layer or propagation references. Saved legacy and RTL runs compare every
previous CSV value, not just aggregate coverage.

The boundary is a type/API contract for new code, not a capability sandbox:
legacy `ecu_state_t` still exposes internal fields to old functions. A future
new detector must accept only `const runtime_observation_t *` plus its own
state. Fault injection and hazard evaluation must never populate an additional
runtime field with labels, reference deltas, or future outcomes.
