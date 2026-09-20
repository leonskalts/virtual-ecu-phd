# Final CURRENT development pass

No runtime accumulation was selected. The eight prior isolated weak bias misses
have equal acquisition/consumption values. Constant bias cancels from successive
samples; excess slew occurs at onset and recovery, not throughout the bias.
Six cases have exactly two nonzero excess samples; two also contain small thermal
residuals around legal target updates. A diagnostic signed accumulator with the
existing .8 decay never exceeds .481. Recycling an old impulse would manufacture
persistence. This is a sensitivity limit of current trusted evidence and decision
rules, not proof of universal unobservability. No threshold or detector logic changed.
See weak_bias_inspection.csv and the pre-registered protocol for exact evidence.
Legacy nonzero-duration sensor events end at their configured duration, including
those labeled permanent. Existing fault semantics were preserved.

738 new simulations: 492 TRAIN, 246 VALIDATION (210 fault, 36 benign), disjoint
operating families. New profiles and seeds; no unseen holdout. Benign measurement
workloads test bounded alternating jitter and slow triangular variation alongside
legal calibration updates. The envelope does not establish general noise immunity.
The adapter uses existing measured values only and defaults to zero perturbation.
Pre-change and retained CURRENT detector source are identical; the historical
CSV method name Revised CLO-DSF does not imply a new detector revision.

| Origin | Pre-change detection | Retained detection | Correct/known first origins | Correct/known runtime origins | Runtime UNKNOWN/all |
|---|---:|---:|---:|---:|---:|
| MEMORY | 57/72 | 57/72 | 57/57 | 18237/18237 | 16/18253 |
| TIMING | 12/12 | 12/12 | 12/12 | 4364/4364 | 0/4364 |
| COMMUNICATION | 54/54 | 54/54 | 54/54 | 18392/18392 | 0/18392 |
| SENSOR_CONTROL | 40/48 | 40/48 | 40/40 | 4613/4613 | 0/4613 |
| ACTUATOR | 24/24 | 24/24 | 24/24 | 4566/4566 | 730/5296 |

Validation detection 187/210; isolated weak bias
0/8. Plant detection
161/169;
silent plant 8; benign alarms 0/36.
Median/P95 0.0/4610 ms.
Effective memory 57/57, effective
stuck bits 45/45, dormant alarms
0/15. Effective memory detects at
first integrity mismatch; activation-relative delay is not evidence-processing delay.

First localization 187/187, UNKNOWN 0.
Runtime localized accuracy 50172/50172;
UNKNOWN 746/50918; wrong samples/runs
0/0. Abstentions included in the denominator:
correct fraction 0.9853489924977414. Causal precedence preserved.

Pre-change detection 187/210, silent 8,
benign 0/36, median/P95
0.0/4610 ms.
Fair Weighted Sum detection 177/210, silent 9,
benign 18/36, median/P95
0.0/5000.0 ms. Its fixed target assumption can
alarm on authorized updates; no recalibration was performed.

No weak-bias improvement or reduction in silent plant misses is claimed. The remaining
misses are retained as a documented limit. Paired comparisons and descriptive Wilson
intervals are supplied; deterministic grouped cases are not independent population
replications. Latency-tail cases are tabulated separately. No ground truth enters
inference; post-hoc labels only score outcomes. Preservation and final regression
are recorded in validation_record.md. No commit, push or unseen validation.
