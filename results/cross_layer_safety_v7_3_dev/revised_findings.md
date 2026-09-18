# CLO-DSF v7.3 findings — DEVELOPMENT ONLY

No final paper holdout was created or inspected. These are new development
TRAIN/VALIDATION cases, not final unseen generalization evidence.

## Miss audit and principled choice

Every historical v7.2 miss is classified: {'algorithm_limited': 78, 'misses': 114, 'observability_limited': 36, 'silent_plant': 36}. The 78 algorithm-limited
cases comprise 48 communication cases with visible 100/200 ms reception age
suppressed by the inherited 300 ms grace, and 30 actuator cases with a visible
tracking mismatch but insufficient scaled/temporally retained mass. All 36
silent plant misses are algorithm-limited (30 actuator, 6 communication).
The 36 observability-limited cases are latent stuck bits that agree with the
current stored target. Passive values cannot identify those dormant defects;
trusted active memory BIST would be needed. No checksum claim is made for a
bit whose observed value remains correct. Candidate 2 corroboration over all
its development cases: {'algorithm_limited': 87, 'misses': 117, 'observability_limited': 30, 'silent_plant': 26}.

The per-case CSV records comparator detections and exact supporting signal
ranges. No reference-run residual was supplied to inference. Classification is
an offline engineering diagnosis, not a theorem of universal observability.

One change replaces actuator residual severity scaling with an exact synchronous
command/response conformance check. The source model guarantees clamp(command)
before detector sampling. A one-representable-float envelope accepts numerical
neighbors; it is not a severity parameter fitted to faults. Replace the source,
do not duplicate it. Keep all other evidence, DS fusion, independent frames,
temporal retention, thresholds, origin gates and UNKNOWN behavior unchanged.
No additional trusted observable is introduced. The label-derived simulated
fan self-test is explicitly excluded. Historical Hybrid retains its own original
inputs; this revision gains nothing from that self-test.

## Registered campaign and selection

1,125 new unique configurations: 900 faulty, 225 benign. TRAIN: 735 (600 faulty,
135 benign); VALIDATION: 390 (300 faulty, 90 benign). Every validation origin
has 60 cases. Each model contributes one whole behavior group to validation,
chosen by a fixed hash; severity/profile/onset siblings never cross partitions.
All three behaviors occur across the campaign. Five new operating profiles,
multiple magnitudes/durations/onsets and recorded seeds are used. Seed labels
do not make these deterministic injectors independent stochastic replicates.
Zero physical overlap with Candidate 1, Candidate 2, v7.2 or its excluded draft.

A static duplicate-profile check caught clipped-speed duplicates during design,
before registration or any simulation; the speed base was corrected. All final
configurations passed the unchanged C validator before execution. No partial
simulation campaign, outcome-driven definition change or validation rerun occurred.

The algorithm, generator, split, fixed objective and dependencies were hashed
before TRAIN. No parameter search was necessary. All eight configuration values
are byte-identical to v7.2. A selection record with validation_seen=false was
written after TRAIN passed the predeclared contradiction checks and before any
VALIDATION simulation. Source identities were verified at that boundary.

## Same-cohort validation

| Method | Detected | Coverage | Silent plant | Benign alarms | Median/P95 ms | Correct origins | UNKNOWN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Revised CLO-DSF | 260/300 | 86.67% | 6 | 0/90 | 0.0/200.0 | 200 | 60 |
| Candidate 2 | 252/300 | 84.00% | 14 | 0/90 | 0.0/200.0 | 174 | 78 |
| v7.2 CLO-DSF | 252/300 | 84.00% | 14 | 0/90 | 0.0/200.0 | 192 | 60 |
| Plain DS | 230/300 | 76.67% | 34 | 0/90 | 0.0/200.0 | 170 | 60 |
| Simple OR | 244/300 | 81.33% | 22 | 0/90 | 0.0/200.0 | None | None |
| Weighted Sum | 251/300 | 83.67% | 15 | 0/90 | 0.0/200.0 | None | None |
| Hybrid | 155/300 | 51.67% | 67 | 0/90 | 0.0/1129.9999999999982 | None | None |
| Timing Monitor | 60/60 | 100.00% | 0 | 0/90 | 50.0/100.0 | None | None |

Timing Monitor's denominator is timing-only (plus benign for false alarms).
All frozen baselines retain original evidence/parameters; Weighted Sum remains
Candidate 2 TRAIN choice 6. Its evidence does not inherit the new actuator rule.
There is no comparison against a separately enhanced Weighted Sum, and no claim
that DS uniquely enables a contract checker. A generic pool could incorporate
the same evidence; that is a different, untested baseline.

Revised macro detection: 86.67%. Plant-propagating detection:
198/204
(97.06%). Silent plant cases:
6. Localization coverage 76.92%,
accuracy when localized 100.00%, UNKNOWN
60 (23.08%), wrong non-UNKNOWN first origins
0, wrong localized runtime samples
0. Coverage and conditional accuracy must
always be reported together. Benign counts do not establish population safety.

| Origin | Detection | Localization coverage | Accuracy when localized | UNKNOWN | Wrong |
|---|---:|---:|---:|---:|---:|
| MEMORY | 46/60 | 100.00% | 100.00% | 0 | 0 |
| TIMING | 60/60 | 100.00% | 100.00% | 0 | 0 |
| COMMUNICATION | 40/60 | 100.00% | 100.00% | 0 | 0 |
| SENSOR_CONTROL | 60/60 | 0.00% | N/A | 60 | 0 |
| ACTUATOR | 54/60 | 100.00% | 100.00% | 0 | 0 |

Paired against Weighted Sum: {'comparator': 'Weighted Sum', 'both_detect': 251, 'only_revised': 9, 'only_comparator': 0, 'neither': 40}.
Paired against v7.2: {'comparator': 'v7.2 CLO-DSF', 'both_detect': 252, 'only_revised': 8, 'only_comparator': 0, 'neither': 40}.
No population-significance claim: designed families are correlated.

## Minimum ablation and interpretation

A0 is frozen v7.2. A1 changes only the actuator source. There is no A2 or hidden
supporting change. Detection changes from 252 to 260;
silent plant cases from 14 to 6; benign alarms
from 0 to 0; correct origins
from 192 to 200; UNKNOWN
from 60 to 60. Median/P95 latency changes from
0.0/200.0 to 0.0/200.0 ms.

Gained-case families (origin/model/behavior/magnitude): {('ACTUATOR', 'pump_degraded', 'intermittent', 0.98): 8}.
All eight gains over v7.2 are weak intermittent pump degradations; they span
four operating profiles and two onsets, but are a related deterministic family,
not eight independent demonstrations of broad generalization. Remaining misses
by origin: {'MEMORY': 14, 'COMMUNICATION': 20, 'ACTUATOR': 6}. Remaining silent-plant families: {('COMMUNICATION', 'delayed_update'): 6}.
The six remaining actuator misses have no witnessed response violation; a
degraded pump commanded at zero throughout both injected intervals cannot be
exposed by passive command tracking alone. Archived observations confirm zero
pump command and zero response gap in all six of these cases.

Scientific freeze eligibility under the registered rule: True.
Final freeze is gated on the separate final regression/preservation record.

Strongest positive: the new contract evidence tests whether discarded weak
actuator residuals explain missed plant propagation, with an isolated A0/A1
comparison and no numerical tuning.
Strongest limitation: this is an instantaneous, noiseless virtual actuator
contract. Physical hardware needs trusted response feedback and a justified
error/dynamics envelope; this one-ULP bound cannot be exported as a physical
sensor tolerance. Unchanged communication freshness blind spots, dormant memory
faults and sensor/control origin ambiguity remain. Improvement over frozen
Weighted Sum would establish the value of added evidence, not DS superiority.

Runtime isolation tests mutate injector fields, true plant state, propagation
truth, and diagnosis/safety/detector labels while keeping allowed inputs fixed.
Historical hashes, full final regression and manifests are recorded separately.
Exact allowlisted runtime observations and compact online metrics are retained;
commands plus raw/summary/trace hashes permit reproducibility without retaining
duplicate large raw logs or screenshots. No GUI changes or performance claims.
