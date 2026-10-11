# Triplex-Plus development: no promotion

The retained frozen Triplex is unchanged. The preselected memory-only candidate
improves detection but **does not exceed the fair SVM**, and plant-conditioned
coverage remains below99%. Retain **TRIPLEX**; no new unseen comparison is warranted
for this candidate. No commit/push or unseen execution occurred.

## New data and locked selection

3150 new configurations: TRAIN1500(1200fault/300benign), CAL750(600/150), VALID900
(720/180),144 validation faults per origin. Distinct physical-group partitions;
zero configuration/profile/seed overlap with956 audited historical sources. Manifest
SHA256 `1390fe890eb80ceb1e8d0fb07a47775cd7cf6838d0c976cf4655048a04018323`.
Previous unseen results were preserved and used only as aggregate development context.
There was no individual historical-case tuning. Protocol, generation and all final
method/model hashes were sealed before validation. Confidence intervals and exact
paired tests are descriptive for this deterministic grouped design.

M500 replaces the observer's old schedule with alternating600/400ms gaps. M250 uses
300/200ms gaps. Neither unions old and new failures. Same address, original atomic
save/write/read/restore/read transaction; no control interleaving, fault-label-aware
address choice or continuous scan. All restoration assertions passed.

TRAIN: retained1055/1200; M5001065; M2501074. CAL: retained522/600; M500529; M250533.
All had zero benign alarms and zero wrong origins. The predeclared95%-of-faster-gain
rule selected250ms;500ms did not capture most of the gain.

Staggered sensing kept A0,100,...; B33,133,...; C66,166,...ms, using unchanged physical
sensor models and exactly100ms nominal acquisition per member. A was never resampled
or changed for control. Timestamp histories were processed in order; future A samples
were not used for earlier B/C alignment. Robust causal slope projection and an
uncertainty interval were applied; only new samples from BOTH endpoints could count
as another pair persistence witness. The same frozen FAST/SLOW and DS thresholds were
used. Aggregate acquisition gaps33/33/34ms do **not** make any individual sensor a
33ms sensor, nor guarantee a qualified pair decision every33ms.

A synthetic pre-campaign test caught endpoint-slope contamination by an abrupt offset.
Before any campaign outcome, the estimate became a median of pairwise slopes and the
uncertainty was widened to account for noise and history age; registration.json
records this correction. No alignment change followed TRAIN/CAL/VALID outcomes.

Stagger alone lost12 TRAIN and4 CAL detections, with no benign alarms or wrong origins.
Thus it was rejected for V2, not rescued by narrowing its uncertainty envelope.
The best eligible physical candidate was M250 with retained sensor acquisition.

## OQ-SET feasibility and fair SVM

The fresh SVM received the same selected M250 runtime observability: six qualified
strengths, six availability bits, six causal1s means and six causal1s maxima. TRAIN
only supplied labels and normalization. LinearC=.1,linearC=1,RBF C=1 formed the full
predefined family; CAL balanced accuracy selected linearC=.1 at decision threshold0.
Training used20613 frames, class_weight=balanced; no scenario/magnitude/origin/future
features. CAL SVM543/600 with19/150 benign alarms versus M250533/600 with0/150.
This ten-case gap triggered OQ-SET under the predeclared rule.

OQ-SET was implemented in C with TRAIN-only per-provider histograms, Laplace1
smoothing, clipped log-likelihood increments and bounded leaky cumulative scores.
Only its global decay/boundary grid used CAL. It never assigned origins: rescue-only
alarms had UNKNOWN unless the unchanged CLO detector itself supplied an alarm origin.

The only grid point passing both TRAIN and CAL benign gates was decay.8,boundary12;
it added **no CAL detections** and was rejected. Boundary4 reached543/600 on CAL but
caused29/150 benign alarms; other gain-bearing settings also failed safety gates.
Boundary8 at decay.8 had0 CAL benign alarms but8/300 on TRAIN and no CAL gain, so was
not accepted by overlooking TRAIN failure. No validation data was used for rescue.
Histogram increments do not model serial dependence; the leaky test has an empirical
benign gate, not a formal independent-sample false-positive guarantee. Full likelihood
tables and every grid result are retained. There was no iterative
search or new mechanism after this negative result. Final SVM therefore has24 features;
it would have received cumulative scores too had OQ-SET been selected.

## Untouched validation

V0=retained Triplex; V1=fair SVM using M250 observability; V2=preselected M250-only
Triplex-Plus. Rejected stagger ablations were also evaluated on these same cases.

| Method | Detection | Wilson95 | Benign | Plant detection | Silent plant | Precision | Median/P95 |
|---|---|---|---|---|---:|---|---|
| Retained Triplex | 639/720 (88.75%) | 86.23–90.86% | 0/180 | 395/405 (97.53%) | 10 | 100% | 0/32.706s |
| Fair SVM | 669/720 (92.92%) | 90.81–94.57% | 23/180 (12.78%) | 405/405 (100%) | 0 | 96.68% | 0/28.861s |
| Triplex-Plus | 652/720 (90.56%) | 88.20–92.48% | 0/180 | 395/405 (97.53%) | 10 | 100% | 0/32.657s |

Paired V2/SVM: both652, SVM-only17, V2-only0, neither51. Exact McNemar p=1.5258789e-5.
V2 raw-detection margin **-2.36 percentage points**. SVM is earlier on93 shared
cases and tied on559. Its greater sensitivity has a substantial benign cost, but
that trade-off does not mean V2 has higher raw detection.

Triplex-Plus first-detection localization652/652 correct,100% coverage. Runtime
localized accuracy191373/191373=100%; wrong runs/samples0/0. UNKNOWN1075/192448 alarm
samples (0.559%). SVM localization is NOT PROVIDED. No localization framework or
threshold was altered. Retained Triplex also has zero wrong origins.

| V2 subgroup | Detection |
|---|---:|
| Memory | 142/144 |
| Timing | 144/144 |
| Communication | 144/144 |
| Sensor/control | 112/144 |
| Actuator | 110/144 |
| Effective memory | 97/97 |
| Dormant memory | 45/47 |
| Independent slow drift | 32/32 |
| Weak steps | 36/48 |
| Pulses | 28/48 |
| AB common-mode | 37/48 |
| Initially excited actuator | 72/72 |
| Initially unexcited actuator | 38/72 |
| Unexcited throughout | 0/34 |

Initially unexcited and unexcited throughout are different denominators. The latter
pump-performance cases have zero command throughout the fault and remain an explicit
physical observability boundary. No command pulses, new health bit or reinterpretation
was introduced.

## Ablations and gain accounting

| Requested role | Implementation | Validation detection | Benign | Wrong-origin runs |
|---|---|---:|---:|---:|
| A0 | retained Triplex | 639/720 | 0/180 | 0 |
| A1 | memory250 | 652/720 | 0/180 | 0 |
| A2 | stagger only | 628/720 | 0/180 | 0 |
| A3 | memory250 + stagger | 641/720 | 0/180 | 0 |
| Additional memory-rate ablation | memory500 | 647/720 | 0/180 | 0 |
| Additional combined-rate ablation | memory500 + stagger | 636/720 | 0/180 | 0 |

Selected V2 adds13 detections, loses0: **all13 are dormant memory**. Memory other0;
A-only0,B-only0,AB0; weak steps0,pulses0,other sensor0; timing0,communication0,actuator0.
Component contributions: memory+13, stagger0(not selected), sequential0(not selected).
These are incremental contributions for the selected candidate; they do not conceal
the negative stagger ablation. Stagger alone adds0 and loses11 validation detections:
A steps3,AB steps2,AB pulses2,B steps2,B pulses1,A pulses1. Conservative alignment
preserves benign safety but removes useful weak-disagreement evidence. No post-hoc
threshold tightening or fault-phase change was attempted to recover those losses.

## Overhead and scope

Per120s run, M0 has121probes/847operations; M500241/1687; M250481/3367. Candidate
increase is**2520 memory operations**, approximately21additional operations/s. Same
16-byte diagnostic state; no additional persistent memory-diagnostic state is needed
for replacing the schedule. Parallel experimental observers are not deployment state.

The rejected stagger architecture acquired A1201/B1200/C1200 times versus retained
A1201/B1201/C1200: same10Hz/member, one startup B conversion difference. Staggered
provider state13208B versus8656B retained: +4552B, including timestamp histories and
an additional pair state. OQ-SET's rejected runtime score state is48B, with480B LLR
lookup and fixed edges/global parameters. No new sensor rate was adopted by V2.

48 host executions on eight predetermined TRAIN benign cases, three repetitions,
alternating pair order: median baseline64.679ms, candidate71.409ms; median paired
increase10.89%. All paired physical-output and CURRENT-trace hashes matched. This is
an instrumented paired-observer experiment including the extra candidate observer,
CSV export and collection, **not a deployed runtime overhead or hardware WCET claim**.

## Decision and integrity

Benign/localization gate PASS; timing,communication,effective-memory capabilities
preserved. Raw-detection superiority FAIL; plant>=99% FAIL. **Do not promote.** The
strongest positive is clean recovery of13dormant-memory cases; the strongest negative
is that neither staggered acquisition nor the bounded likelihood stage closes the
sensitivity gap while preserving the benign requirement. This result concerns the
specified models and conservative contracts, not all possible sequential detectors.

339tests, full build, Python compile,diff check,48legacy,64RTL,Triplex symmetry and
sensor-C independence passed. All historical/frozen scientific and GUI hashes,
previous comparative results and37244protected historical files are unchanged.
No candidate linked into the retained production detector. No commit, push or unseen.
Temporary runtime feature tapes were used only for causal replay, then removed after
reporting. Compact manifests, models, sufficient statistics, locks and findings remain.
