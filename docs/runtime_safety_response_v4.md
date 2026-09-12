# V4 runtime safety policy and evaluation contract

V4 adds two separate opt-in mechanisms around the accepted simulator. It changes
no existing detector, diagnostic rule, thermal physics, fault semantics or RTL
payload. Existing detectors remain independently selectable. The candidate
studies hold Hybrid Adaptive Kalman and its `observe_only` action fixed.

## Detection and intervention

The timing monitor receives only the scheduler observation defined in
`runtime_timing_observability.md`. It reports alarms/severity and never writes
commands or safety state. `runtime_safety_policy_step` is a separate pure policy
over the allowlisted runtime snapshot and timing-monitor status. It cannot see
fault model, injected delay/age, ground truth, reference state or hazard outcomes.

Timing `observe_only` never requests protection. Timing `protective_action`
observes isolated single anomalies without acting; repeated violating periods
request existing precautionary cooling, and critical execution absence requests
existing limp-home. Both are existing safety modes, including their modeled
cooling and load effects. There is no direct plant mutation or invented actuator.

The communication policy adds **no detector**. In protective mode it requests
limp-home only when the existing detector alarm is active AND the already-published
sensor freshness status is failed. No additional delay/replay threshold is tuned.
An existing alarm alone or failed freshness alone is insufficient. This conjunction
does not identify a fault model; it is applicable to observed stale sensing under
any origin. The accepted timestamp-preserving replay protocol remains unchanged.

The safety layer applies the maximum of its current requested mode and the new
policy request, using its existing transition/actuator mechanisms. V4 evaluates
requests every 100 ms after existing detection. Existing diagnostic/safety work
retains its old schedule. When a policy changes state or final commands, actuator
feedback is refreshed; diagnostics refresh only if due at that timestamp. Diagnostic
logic itself is unchanged. When the policy stops requesting, existing safety
recovery hysteresis determines release; no new permanent action latch is added.

An action run can change later measurements, detector scores, diagnostics and
physics through legitimate closed-loop feedback. That is different from detector
retuning. Default runs and all observation-only ablations preserve every original
CSV field and detector waveform exactly.

## Logged attribution

V4 appends trusted timing fields, current timing alarm/severity, first timing
violation/alarm, existing raw detector first alarm, communication alarm conjunction,
separate timing/communication requests, first request, and first incremental policy
action. An incremental action changes applied state or command; an already-satisfied
request is still logged as a request but is not fabricated as a new action.
Request/action sample counts count scheduler observations, not independent episodes.
No new field silently replaces the existing detector's bookkeeping or v1 propagation
timestamps. Old fields/headers are byte-identical when v4 options are absent.

Analysis records the first mechanism as existing detector, timing safety monitor,
SIMULTANEOUS or NONE. Ties are not arbitrarily awarded to the new monitor. The
communication policy is not credited as a detector. Existing raw first-alarm time
and legacy differential detection remain separate; no-fault raw alarms are
counted in false-alarm metrics. Policy request, incremental response, differential
safe-state entry and containment are distinct endpoints.

## Matched evaluation

Run `python3 scripts/run_runtime_safety_studies.py`. It reads the two versioned
YAML configurations and writes only `results/cross_layer_safety_v4/` (or a separate
explicit output directory). Output overlap with v1/v2/v3 is rejected. Captured
configuration, commands, raw hashes, implementation hashes and original v3 run
IDs make the comparison reviewable.

Timing has 72 unique fault cases plus two no-fault profiles per mode. There are
36 cases per model, 24 per behavior and 36 per profile. Because a transient deadline
miss is exactly one skipped execution, extra unique injection times balance its
count against the two task-delay magnitudes. Consequently timing grids are not
identical between models for transient/permanent faults; this is an explicitly
limited between-model comparison. Five modes yield 370 simulator runs: disabled,
deadline-only observation, age/missed-execution observation, combined observation,
and combined protection. Every ablation/action comparison is paired on identical
fault parameters/profile. All previous 42 timing cases are included.

Communication uses all 48 existing delay/drop/replay cases plus both no-fault
profiles, each under observation and protection: 100 simulator runs. This includes
benign, non-propagating, plant-propagating and both previously hazardous cases.
The only communication-policy change is its opt-in action setting. One seed is
recorded; deterministic replication is not presented as statistical sampling.

For intervention analysis, consequence/eligibility is fixed from each matched
combined-observe timing run or observe-only communication run. This prevents an
action's own cooling deviation from manufacturing a safety-relevant denominator.
Both actual and no-action propagation/hazard timestamps remain available.
Before/after ordering uses the no-action boundary; SAME_TICK is distinct from BEFORE.
Absence of either endpoint is N/A, not a successful early intervention.

Exclusive intervention categories among incrementally acted-on runs:

| Category | Required observed evidence |
| --- | --- |
| FALSE_INTERVENTION | No injected fault in the paired benign run |
| UNNECESSARY_NO_DOWNSTREAM | Injected run has no actuator or plant effect without action |
| TRUE_PROTECTIVE_HAZARD_MITIGATED | Paired no-action hazard exists and action eliminates it or reduces its critical exposure |
| RESPONSE_TO_PROPAGATING_FAULT_BENEFIT_UNPROVEN | A real actuator/plant consequence exists but hazard mitigation is not demonstrated |
| NO_INTERVENTION | No incremental policy action |

"Unnecessary" is bounded by this horizon and the accepted propagation tolerances,
not a claim that such an event is always harmless. A separate field identifies
unnecessary transient interventions. False interventions use no-fault runs as
denominator; unnecessary interventions use no-action non-propagating injected
runs. A response to a tiny physical deviation is not automatically true protection.
The actual action may itself change cooling/derating substantially; future work
must quantify cost. Neither detection nor safe-state activation proves containment.

## Containment and FTTI

The accepted hazard/containment code is unchanged: sustained critical >=115 C for
1000 ms defines hazard; below warning 108 C for a 1000 ms stable final tail with
protection or resolved effects defines containment, provided no hazard occurred.
Later violations revoke earlier candidate containment. Fault recovery, hazard
avoidance and stable-tail containment are different outcomes.

V4 fixed-cohort containment uses that actual-run predicate only for cases whose
no-action actuator/plant manifestation makes containment relevant. The denominator
does not change between observation and action. The fixed-cohort FTTI field uses
the original injection-based 5000 ms experimental clock and includes the hold.
Missing evidence remains N/A. The v3 manifestation-based and legacy metrics also
remain in each detailed run record; their actual-run eligibility must not be
confused with the fixed intervention cohort. These are not OEM-certified FTTIs.

The observed communication policy can avoid hazards while still failing the
reference-resolution final-tail rule. Reports must retain that negative result,
not relax the contract until action looks beneficial. Longer post-recovery runs
and a separate action-cost study are preferable to retrospective threshold tuning.

## GUI and compatibility

Only Cross-Layer Safety is extended. Timing Monitor offers Disabled / Observe Only /
Protective Action; Communication Safety Response offers Observe Only / Protective
Action. New single runs use existing Hybrid in observe-only mode, with the runtime
policy controls selecting intervention explicitly. Load v4 Runtime Safety opens
seven outcome cards and views for validation, ablation and communication response.
Single-run unnecessary/false intervention classification is N/A without its matched
no-action run. V1/v2/v3 loaders remain available. GUI-generated single/study/campaign
artifacts now go into v4 subdirectories, preserving accepted evidence folders.

Runtime timing support assumes a trusted independent supervisor. Legacy sensor
truth, DTC metadata and modeled fan self-test limitations are unchanged and still
documented in `detector_observability_boundary.md`. Finite deterministic coverage
does not establish production safety, literature novelty or vehicle-level benefit.
