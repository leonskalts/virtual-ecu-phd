# Final unseen CURRENT CLO-DSF validation

Tested commit: `145794476b51e8d75fbe3043fa0672e136aaa1e9`.
One execution of 1,500 new cases: 1,200 faults (240/origin), 300 benign.
Zero exact configuration overlap. Protocol, manifest, scientific hashes and tracked
campaign overlap audit were recorded before execution. A supplemental inventory
of ignored older result files was checked after registration: also zero overlap.
No outcome-driven changes, detector edits, calibration, commit or push.

## Detection

CLO-DSF: **1,047/1,200 (87.25%)**, Wilson95 **85.24–89.02%**.
Macro detection: **87.25%**. Precision **100%**, recall **87.25%**.
Benign alarms **0/300** (Wilson95 upper bound about1.26%). No pre-onset alarm runs.

| Origin | Detection | Interpretation |
|---|---:|---|
| Memory |177/240|177/177 effective; 0/63 dormant alarms|
| Timing |240/240|Deadline and task-delay cases|
| Communication |240/240|81 delays, 81 drops, 78 replays|
| Sensor/control |150/240|90 remaining sensitivity misses|
| Actuator |240/240|180 pump degradation and 60 fan-off cases|

Effective memory includes **117/117 effective stuck bits and60/60 flips**.
All detect at the first register-shadow mismatch. Dormant conditions produce no
invented alarm. Weighted Sum alarms in18/63 dormant cases; these are not evidence
that it observes an actual memory inconsistency. Its fixed target assumption also
alarms on all150 benign legal-update cases (0/150 static-target benign alarms).

Weak isolated sensor biases: **40/80**; including intermittent bias: **60/120**.
All +/-1.05 C biases miss; all +/-1.30 C biases detect. Sensor pulses: **90/120**;
all30 amplitude .35 C pulses miss, whereas .65/2.3/6.7 C cases detect. These are
post-hoc subgroup descriptions, not new thresholds. Known weak-bias limitations
remain, with no attempted fix. Overall sensor/control improvement does **not**
generalize as a broad detection advantage: Weighted Sum detects209/240 versus150/240,
although its alarms are confounded by authorized calibration changes. CURRENT-only
sensor detections number11; this does not overcome70 Weighted-Sum-only cases.

Plant-propagating detection **874/964 (90.66%)**; silent plant misses **90**, all
sensor/control (60 biases,30 pulses). Of detected plant cases, **841 pre /31 same /
2 post** manifestation. Weighted Sum has **83** silent plant misses: seven fewer.
The153 total CURRENT misses comprise63 dormant memory cases and90 sensor cases.

Median/P95 activation-relative latency **0/300ms** versus Weighted Sum
**0/11,275ms**. This is a cohort-dependent percentile, not a detector modification.
Memory P95 remains10,820ms, with every effective mismatch detected in0ms from
observability; long waits are for legal updates to expose initially dormant bits.
Exact tail cases are retained. Among938 jointly detected faults, CURRENT is faster
in211, equal in710, slower in17.

## Localization

First-detection coverage **1,047/1,047 (100%)** and accuracy **1,047/1,047 (100%)**;
first UNKNOWN0. Runtime coverage **369,298/372,740 (99.08%)**; accuracy among localized
samples **369,298/369,298 (100%)**. UNKNOWN **3,442/372,740 (0.923%)**; wrong-origin
runs/samples **0/0**. Correct over all alarm samples, including UNKNOWN, is99.08%.
Every origin has100% accuracy among localized samples. UNKNOWN samples: memory65,
timing0, communication3, sensor0, actuator3374. Localization precedes plant
manifestation in841 detected cases. Causal precedence generalized without confident
origin drift; abstention remains visible. Confusion/coverage summaries include
UNKNOWN and use explicit run versus sample denominators.

## Baselines and paired interpretation

| Method | Detection /1200 | Silent plant | Benign alarms /300 |
|---|---:|---:|---:|
| CURRENT CLO-DSF |1047|90|0|
| Fair Weighted Sum |1026|83|150|
| Simple OR |957|152|150|
| Plain DS |910|199|150|
| Hybrid |913|142|200|

Timing Monitor detects240/240 timing cases only; no all-origin claim is made.
All baselines retain committed settings and original evidence extractors; the
CURRENT detector has additional runtime observables. This comparison is not an
ablation isolating fusion mathematics. Legal updates and benign sensor variation
are deliberate stressors; historical baseline calibration was not changed.

Paired CURRENT versus Weighted Sum: **both938 / only CURRENT109 / only Weighted
Sum88 / neither65**. Exact two-sided McNemar **p=0.153995**,197 discordances.
No statistically supported overall binary detection superiority. Subgroup tests
in the CSV are exploratory, unadjusted; do not infer population superiority from
deterministic correlated cases. Wilson intervals likewise describe this case set.
Run-level precision and alarm endpoints do not prove causal attribution of each
baseline alarm. Runtime sample intervals are not independent-sample evidence.

Communication and effective-memory capabilities generalized; causal localization
generalized; broad sensor/control detection improvement did not. The strongest
positive is full communication/effective-memory detection with zero benign alarms
and zero wrong confident origins. The strongest limitation is90 silent sensor
propagations, including the known isolated-bias sensitivity limit. Weighted Sum
has fewer silent plant misses despite its much higher benign alarm rate.

Scientific hashes, GUI preservation and full regression are recorded in
validation_record.md. Results are suitable for manuscript evidence with these
limitations and without a detection-superiority claim. Eight compressed traces;
no bulk raw run data retained.
