# V5 predeclared validation protocol

V4 is development evidence; da126cb is the accepted baseline. No monitor or policy
rule will be selected or retuned using v5 outcomes. Frozen combined observation is
the primary configuration. Three predeclared action policies and three fixed
ablations are comparisons; recommendations after validation are not a new validated
configuration. Source/profile/design hashes precede holdout execution.

Three new 180 s operating profiles, injection times 17.3/77.3/137.3 s, unseen delay
magnitudes/durations and intermittent patterns are specified in
`studies/cross_layer_v5_holdout.yaml`. None of these complete profile/parameter
combinations occurred in v4. Existing models, detectors and thermal equations are
unchanged. The profiles include moderate and high demands, urban/highway transitions,
and final recovery demand. They are designed scenarios, not sampled vehicle data.

Primary timing design: 714 distinct configured cases: 156 legal workloads,
450 direct timing injections and 108 temporary overload workloads. Ten deterministic
seeds vary each jitter pattern; zero-jitter/exact-deadline patterns have only one
seed to avoid fake replicates. Legal workloads include normal, small/medium jitter,
near-deadline variation and exactly-at-deadline completion. Each violating condition
is assessed from actual event outcomes, not its configured stress label. Fifty-four
balanced direct-fault strata also receive both action policies: 822 timing simulations.
All 714 no-action traces are replayed through three frozen C ablations. These are
paired computations on the same simulations, not 2,142 independent experiments.

Communication: 108 unique injections balanced across three existing models, three
behaviors, four magnitudes and three profiles. Early/middle/late occurrences rotate
by a fixed Latin-style index, yielding balanced time counts without a full Cartesian
explosion. Three benign profiles and three policies yield 333 simulations. Policies
are exactly paired on configuration. Deterministic faults are never replicated under
meaningless new seed values.

Cross-layer: 540 injections (10 models x2 behaviors x3 variants x3 times x3 profiles)
plus three benign profiles. Fault magnitudes and durations vary; fan-stuck variants
vary duration, not a fictitious severity parameter. Broad-layer severity is not
physically matched, so origin comparisons are descriptive, not controlled causal
rankings. Existing sensor and actuator models retain their original semantics.

Matched temporal study: same target register, bit, injection time and profile;
transient bit flip compared with each polarity of permanent/intermittent stuck bit.
The 27 transient runs are shared across polarity comparisons; 108 stuck runs give
135 unique simulations and 54 matched triples. No duplicate flips are counted as
new independent observations. Permanent exposure has no finite fault duration;
transient flip is one write, intermittent stuck is repeated constraint. This is
an operational temporal comparison, not equal-energy disturbance or superiority.

Recovery analysis is separate development-case follow-up, not unseen holdout:
all five v4 protected communication containment failures plus the first timing case in
each model/behavior stratum are rerun with a common extended end of 360 s. Fixed
5/15/30/60 s horizons follow recovery, alarm and action where observable. The original
horizon and extended final status are also retained. Permanent cases have no recovery
anchor. Horizons beyond the recorded end are N/A, never presumed successful.
Profiles hold their final configured demand beyond their final segment. The original
containment predicate remains unchanged; prior hazard permanently prevents success.

Intervention burden uses completed sample intervals: actual safe-state duration,
limp-home duration, precautionary-cooling duration, policy-request duration and
incremental activation count. Paired excess safe-state duration subtracts no-action
state duration and can be negative. Normalized request burden is requested-time /
observed-time. This is not monetary, energy, comfort, or vehicle-level cost.
Unnecessary means no actuator/plant consequence in the paired no-action trajectory;
false means action in a legal/no-fault case. Propagating nonhazardous responses have
unproven benefit. Actual action and counterfactual ordering are separate.

Rates use explicit eligible denominators and Wilson 95% intervals. N/A has no numeric
zero substitute. The matrix is deterministic and not an IID population sample:
Wilson bounds are descriptive binomial reference intervals under an independence
model, not fleet reliability or proof of statistically independent replications.
Seeds share profiles; model/profile grouping and paired case counts remain explicit.
Small/empty hazard denominators cannot establish broad prevention probability.
Latency median and 95th percentile have units ms and endpoint sample counts; they
are not percentages. Timing coverage uses observed contract violations, not injection
count. Pre-plant is strict '<'; equality is same tick and separately reported.

The alternate overload scheduler is not relabeled as injected fault. Its plant
manifestation is evaluated from the full-precision paired plant deviation. Legacy
fault-containment/FTTI fields for non-injection workloads remain N/A. Absolute hazard
flags are still recorded; attribution is evaluated against the matched legal workload
and the workload-start boundary. This limitation is explicit in final scope tables.

Host overhead uses repeated matched simulator invocations, interleaved order, equal
logging and the same profile/horizon. State sizes and compiler object sections are
reported directly. Process/I/O/simulation overhead is not embedded timing or WCET.
All old evidence and detector/plant/RTL source hashes are regression checked.

The existing [detector observability boundary](detector_observability_boundary.md)
remains in force. Legacy detector residuals use true plant state; diagnostic
classification and bookkeeping retain scenario information, and the old shutdown
path uses true coolant temperature. The new timing monitor and graded policy do
not directly consume fault identity, reference trajectories or future hazards.
The communication policy still depends on legacy alarm evidence. Runtime-only
inputs to these new modules do not establish production-signal isolation of the
entire platform.

Pre-evaluation design correction: transient deadline miss lasts exactly 100 ms under accepted semantics. Additional 0/400/3600 ms occurrence offsets replace invalid multi-tick transient durations. No monitor/policy rule changed. See contracts/design_correction.md; final runs restart from the corrected frozen design.

Wilson method reference: [NIST confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Legacy sensor/actuator behavior correction: the accepted custom CLI supports transient/permanent only. Their second behavior is permanent; fan permanent variants use 0/400/1800 ms occurrence offsets because fault duration is immaterial. This preserves old semantics and unique deterministic conditions. Cross-layer deadline transient variants also use these occurrence offsets with a 100 ms duration.

Unnecessary intervention duration is max(0, action safe-state duration minus matched no-action safe-state duration) for an unnecessary intervention. A separate unnecessary_requested_duration_ms records request time; it does not include release hysteresis.

GUI inspection remains confined to Cross-Layer Safety. Load V5 Validation provides
seven views. Existing v1/v2/v3/v4 loaders remain available. New GUI single/study/
campaign outputs use v5 subdirectories to avoid altering accepted v4 evidence.

Overhead measurement refinement: the v4 `disabled` alarm mode still performs contract
bookkeeping. To measure monitor computation rather than just its alarm branch,
the disabled measurement build replaces only the monitor object with no-op functions.
The production frozen object supplies the enabled build. Both use identical CLI
arguments, telemetry collection and nominal CSV bytes, which are asserted equal.
This special build is never used in holdout validation. The linked text-size delta
is therefore separately available from the whole-v5-versus-v4 binary delta.
