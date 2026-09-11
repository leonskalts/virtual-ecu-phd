# Cross-layer safety v3 scientific contract

Baseline: 97f18ce, including v1 9299c04 and v2 e89c27b. V3 is a Python analysis
layer over accepted C telemetry. No detector, threshold, fault model, thermal
physics, safety decision or HETIA result is changed. No new runtime monitor is
implemented. All original metrics and both accepted evidence directories remain
unchanged. Generated results follow the existing ignored-results convention.

Run `python3 scripts/analyze_cross_layer_safety.py`. Inputs default to
`results/cross_layer_safety_v2/`; outputs go to `results/cross_layer_safety_v3/`.
Input/output overlap and writes into accepted v1/v2 directories are rejected.
The package includes source SHA-256 hashes and self-contained per-run, grouped,
miss, observability, timing, severity and parameter tables, reports and six figures.
The narrative interpretation targets the accepted 182-run candidate study;
it is not a generic inference engine for arbitrary studies.

## Hazard audit and state machine

This is an experimental cooling-system hazard contract. It is not ISO 26262
certification, an OEM hazard analysis or a calibrated field safety requirement.
All candidate runs use the same warning 108 C, critical 115 C, maximum consecutive
critical exposure 1000 ms, recovery hold 1000 ms and injection budget 5000 ms.
No threshold is selected by fault type, profile or outcome.

The accepted C implementation in `src/hazard_model.c` compares **true** coolant
against thresholds. Warning includes critical (`T >= 108`); critical is `T >= 115`.
At a new critical sample, start a consecutive-critical clock. At each observation,
hazard is active only if critical remains true AND elapsed time from this entry
is at least 1000 ms. Exactly 1000 ms qualifies. A departure below 115 immediately
exits hazard and resets the consecutive clock. Warning need not have cleared.
First hazard entry and first hazard exit are retained, even through re-entry.
`hazard_entered` is latched; `hazard_active` is current. Hazard exit is not containment.

V3 states, ordered by current condition:

| State | Exact condition |
| --- | --- |
| HAZARD_SUSTAINED | Critical, uninterrupted critical elapsed time >= allowance |
| CRITICAL_TRANSIENT | Critical, elapsed time < allowance |
| WARNING | Warning but not critical |
| RECOVERED | Below warning after any previously observed warning/critical excursion |
| NORMAL | Below warning and no observed warning/critical excursion yet |

From any state, entering critical starts/reuses the critical clock. Falling below
critical goes to WARNING if still at/above warning, otherwise RECOVERED. Renewed
warming moves RECOVERED to WARNING/CRITICAL_TRANSIENT. RECOVERED is a thermal
history state; it does not assert fault recovery, protective response or containment.
No reset to NORMAL is made during one run. With an allowance of zero, the first
critical sample immediately enters HAZARD_SUSTAINED.

Exposure sums **completed** observation intervals using the previous critical
sample (left endpoint). The sample at simulation end has no fabricated following
interval. A final critical sample can therefore be transient; a final sustained
sample leaves an open hazard with N/A exit. Exposure includes the interval ending
at the first noncritical sample, while consecutive duration resets there. Thus
cumulative exposure reaching 1000 ms on an exit tick alone does not imply sustained
hazard: critical must still be true at that tick. This discrete convention is
preserved and tested. Tick resolution is 100 ms, not continuous event localization.

V3 reconstructs states from authoritative C warning/critical flags and verifies
hazard active, exposure and consecutive duration at every sample. Rounded 2-decimal
temperature fields are not used to re-decide a threshold crossing. Transition CSVs
include all runs, including baselines. Preexisting hazard at or before injection
is not fault-associated: the injection-tick plant sample predates the new physical
effect. Association after injection is still not proof of exclusive causation;
the accepted study has no baseline hazard. V3 severity uses observed post-injection
critical state with plant propagation, not injected model identity.

## Manifestation and multiple clocks

Authoritative C propagation timestamps are computed against a fault-free reference
with unrounded runtime values. Do not recreate them from rounded commands.

- First internal manifestation: `propagation_internal_ms`, including actual register
  corruption, scheduling corruption recorded by the fault path, or measurement/
  timestamp corruption. Injection alone does not qualify; a matching stuck bit is
  a constraint with no effect.
- First control manifestation: v2 includes target/command deviation **or** changed
  last-execution time. A timing-only control stage is not numerical output change.
- First plant manifestation: `propagation_plant_ms`, absolute true coolant difference
  from reference >= 0.01 C. Cooling and warming differences both count.
- First safety-relevant manifestation: earliest recorded **final applied** actuator
  command difference, actuator realization difference, or plant manifestation.
  Applied commands/feedback use v2's 1e-6 reporting tolerance. This is a conservative
  cooling-path proxy, not evidence of imminent hazard. It includes protective
  command differences and very small effects. Without any such timestamp, report
  N/A. Internal-only/received-data-only/execution-metadata-only deviations do not
  start this clock. A future calibrated safety-impact boundary requires new study
  contracts, not retroactive threshold tuning.

V3 reports injection → detection/containment, internal → detection, safety-relevant
manifestation → detection/containment, plant → detection/containment, and remaining
time from alarm to a **strictly future observed** hazard. Missing endpoints are
N/A. Detection offsets are signed: an alarm before plant manifestation has a
negative plant-to-detection value. Zero means the same observed tick. The retained
injection-to-containment field uses the v2 confirmation timestamp; see its success
flag, because a recorded eventual recovery after a hazard is not successful
containment. New manifestation/plant-to-containment clocks require hardened success.

`injection_based_experimental_ftti` is exactly the old `ftti_met` with its old
eligibility. The analyzer independently recomputes and checks it.
`manifestation_based_experimental_ftti` uses the new origin and hardened containment
eligibility. Both include the 1000 ms hold in the confirmation endpoint. A hazard
makes failure; confirmed stable containment at or before the deadline is success;
absence after an elapsed deadline is failure; an unexpired horizon is N/A.

Sensitivity uses global 1000/2000/5000/10000 ms budgets without rerunning or changing
any fault or alarm. The main injection and manifestation rates have different
denominators. `ftti_sensitivity_matched_cohort.csv` holds the hardened cohort fixed
to separate clock changes from cohort selection. Neither metric is certified FTTI.

## Containment, protection and recovery

The retained v2 stable predicate is below warning AND (protective mode active OR
effects resolved). Resolved requires injection inactive, true/measured temperature
within 0.01 C of reference, target/command/feedback within 1e-6, and equal sample and
execution timestamps. Stable must hold for 1000 ms. Any later violation revokes the
candidate/confirmation; only a stable final tail yields success. Any prior hazard
forces failure. It can count passive recovery, not just commanded intervention.
It can count a temperature moving down as well as up; it is not an optimal response
contract. Thermal profile changes can revoke prior confirmation. An active permanent
fault can be contained by protection; fault inactivity is not universally required.

V3 preserves this predicate and endpoint, labels its value `legacy_v2_containment`,
and restricts hardened eligibility to actual applied actuator or plant propagation.
No such propagation gives N/A and NO_CONTAINMENT_REQUIRED, even if v2 called it a
success. Preexisting hazards and baselines also have N/A, for different reasons.
No new confirmation timestamp is invented. An impossible confirmation preceding
the new origin is UNRESOLVED_CONTAINMENT rather than a fabricated zero latency.

Exclusive containment classification priority: NOT_APPLICABLE;
NO_CONTAINMENT_REQUIRED; FAILED_CONTAINMENT_HAZARD; successful
CONTAINED_BEFORE_PLANT or CONTAINED_AFTER_PLANT_BEFORE_HAZARD; unresolved evidence;
PROTECTIVE_RESPONSE_ACTIVE (still uncontained); DETECTED_NOT_CONTAINED;
FAULT_RECOVERED (still uncontained); UNCONTAINED_AT_END.
"Before plant" also includes no plant stage within the horizon and does not prove
the response prevented it. Fault recovery, any recovery window, current protective
state and differential safe-state entry remain **separate** fields. An intermittent
OFF window is not necessarily final fault recovery. Protective mode is not success.
An uncontained final state is an observed-horizon failure, not a claim it never recovers.

## Silent and safety severity

All v2 differential detector misses remain misses. Alarm attribution is an active
alarm while the matched fault-free reference has no active alarm. Raw alarm waveform
presence is also reported, so an attribution miss is distinguishable from no alarm.

| Silent class | Observed consequence and alarm condition |
| --- | --- |
| SC0 | Internal corruption, no sensing/control/actuator/plant effect, no alarm |
| SC1 | Sensing or control visible, no actuator/plant effect, no alarm |
| SC2 | Actuator and/or plant propagation, no defined hazard, no alarm |
| SC3 | Defined hazard without an alarm strictly before its entry, including late alarms |

These are exclusive by highest consequence. Received corrupted value/age is visible
sensing evidence, so communication internal-stage-only cases enter SC1, not SC0.
No effective corruption is NO_EFFECT; alarmed non-SC3 cases are DETECTED. Unavailable
instrumentation is UNAVAILABLE, never zero. SC3 is not always a subset of legacy
silent corruption because it permits late alarms. This campaign happens to retain
81 total SC cases. Latent SC0 and hazardous SC3 counts are zero; do not fabricate
examples in the evidence. Unit tests use synthetic contracts clearly separate from
campaign outputs.

Run severity is exclusive: S0_NO_EFFECT, S1_INTERNAL_ONLY, S2_ECU_VISIBLE,
S3_ACTUATOR_OR_PLANT, S4_CRITICAL_TRANSIENT (post-injection critical with plant
propagation but no sustained hazard), S5_SUSTAINED_HAZARD. Baselines N/A. This never
uses v2 maximum stage 6 as severity: stage 6 may represent recovery or safety response.

Timing categories A–E mean no downstream, control only, actuator, plant, hazard.
The 21 control-only timing cases have changed execution metadata and unchanged
applied actuator/plant outputs; a separate `timing_metadata_only` flag makes this
explicit. Reached-control counts include them; numerical output changes must not
be inferred from the v2 control timestamp alone.

## Evidence limits and observability

Per-run miss reasons are established conditions, not guessed inner detector causes.
Below 0.900 combined score prevents the existing Hybrid confirmation path; no alarm
also establishes that a direct fast branch did not fire. Why individual support
branches failed cannot be reconstructed from unlogged components. Timing reasons
identify absent consumption of scheduler evidence and separately retain the scores.
No speculative short-duration/persistence explanation replaces UNRESOLVED.

Availability and measured coverage are separate matrices. Snapshot age/target/
feedback/last execution are legitimate modeled runtime signals. Independent plant
truth, reference deltas, injector drop/replay provenance and fault labels are not.
Existing legacy truth/metadata exceptions remain documented and unchanged.
Other detectors not exercised in this campaign are N/A, not missed. DTC coverage
means a nonzero primary DTC different from the matched baseline; it is not root-cause
classification. Safety-response coverage describes protection, not detection.

Conditional metric denominators are explicit at overall/layer/model/behavior/profile
levels. Silent plant/hazard rates condition on their respective consequences;
separate incidence rates use all eligible injected runs. Missing evidence is excluded.
Stages overlap; only explicitly exclusive severity/outcome bins are stacked in figures.
Stages are not nested: the six fan faults have actuator/plant evidence but no C
internal-stage timestamp, while 12 matching stuck constraints have no effect.
Thus internal-conditional coverage uses 162 runs, not all 168 effective faults.
Physical-deviation extrema include signed minimum/maximum as well as absolute
maximum, so extra cooling is distinguishable from excess heating. The 0.01 C
plant threshold is a reporting tolerance, not a damage threshold.
The two profiles and unequal deterministic grids provide descriptive evidence, not
statistical replication or matched causal comparisons. A claimed new paper's
literature novelty, field applicability and calibrated thermal/FTTI thresholds need
additional work.

## GUI and validation

The existing Cross-Layer Safety page adds Load v3 Analysis, eight denominator-labeled
cards and one compact table selector. It reads generated results only. Old v1/v2
loading and experiment controls remain available. The analysis area opens on demand.

Tests cover hazard transitions and endpoints, clock signs/N/A/censoring, SC0–SC3,
severity, containment eligibility/failure, conditional denominators, observability,
deterministic miss reasoning and old CSV readers. Regression reruns go to `/tmp`,
never the accepted evidence folders. Validation records belong in the v3 package.
