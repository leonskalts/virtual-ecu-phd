# Final triplex refinement: rejected at benign validation gate

**Retained CURRENT. STOP rule enforced: no fault-validation simulations executed.**
No post-validation parameter changes, replacement trial, unseen run, commit or push.

## Historical miss audit (TRAIN/CALIBRATION only)

The preceding triplex campaign had97 original-space misses in TRAIN/CALIBRATION:

| Class | Description | Count |
|---|---|---:|
| A | Weak step | 1 |
| B | Short pulse | 6 |
| C | Independent stuck sensor with single-versus-pair attribution ambiguity | 3 |
| D | Memory/probe-limited | 19 |
| E | Unexcited actuator/no passive evidence | 68 |
| F | Other | 0 |

Ten historical sensor cases were replayed solely to audit runtime increments; none
came from the previous validation partition. Seven step/pulse cases had a positive
corroborated innovation (continuous strengths .0285–.2940), despite little/no retained
old FAST/SLOW evidence. The three stuck cases had gradual/topology evidence but no
qualifying abrupt consensus. Every miss and its evidence assessment is recorded in
prior_miss_audit.csv. D/E were not targeted; no new memory or actuator mechanism.
These10 reference replays are separate from the new campaign execution count.

## One fixed refinement

The latch requires qualified A/B/C acquisitions and a pairwise innovation cut:
two incident residual changes share a sign and exceed the existing .52C FAST envelope,
while the remaining pair's increment difference stays within the existing .40C floor.
Strength is excess divided by the existing2C scale, clipped to[0,1]. C raw acquisition
increments avoid extrapolation overshoot in the latch; its physical sensor model and
the original A1 triplex provider are unchanged. No sensor member is assumed healthy.

Hold the peak for300ms inclusive (four100ms observations). Recovery edges may raise
the peak but cannot renew expiry; competing cuts cannot add votes. Invalid data clears
the hold; expiry removes it and the unchanged DS memory decays normally. MAX with
existing triplex evidence supplies one sensor channel, without changing global
thresholds,source fusion or causal localization. No injected labels/plant truth enter
runtime inference. All parameters fixed before the fresh campaign; no search.

## Registered versus executed campaign

Registered2400 simulations:TRAIN1200,CALIBRATION600,VALIDATION600. Original-space
validation was balanced80faults each for MEMORY,TIMING,COMMUNICATION,SENSOR_CONTROL,
ACTUATOR (400 total), with80expanded sensor-C/correlated faults and120benign. Distinct
physical families never cross partitions. Old hard actuator cases,fan and pump,
weak sensor manifestations and sensor-C faults were retained; none removed to raise
percentages. Full deterministic manifest and scientific lock are preserved.

Executed:1200 TRAIN +600 CALIBRATION +120 benign VALIDATION =1920 new simulations.
The remaining480 fault-validation cases were NOT executed, exactly as the failed-gate
STOP rule required. No fault-validation performance,Wilson interval,paired counts,
>=91% result,or>=95% plant result can be reported. Development metrics below are NOT
substitutes for validation. Prior validation was not reused as new validation.

## Benign VALIDATION gate

| Observer | Benign alarms | Wrong-origin runs/samples | Added cold-workload alarms vs A1 |
|---|---:|---:|---:|
| A0 CURRENT | 0/120 | 0/0 | 0 |
| A1 TRIPLEX | 0/120 | 0/0 | 0 |
| A2 TRIPLEX+LATCH | 1/120 (0.833%) | 1/1 | 1 |

**FAIL.** The <=1% alarm-run criterion passes, but zero wrong confident origins and
no cold-start-workload regression both fail. The false alarm happened later in a
cold-start mission, not during the initial startup qualification interval. This is
an empirical gate, not a population false-alarm guarantee.

Failure case:latch_2099 (held-out physical family13), benign_cold workload, one legal
+0.9C diagnostic-C disagreement lasting100ms starting34900ms. C acquired it at34978ms.
At35000ms the consensus strength was0.22038578; recovery at35100ms raised the held peak
to0.22999977 without extending expiry. At35200/35300ms fresh innovation was ZERO,
but the latch continued emitting0.22999977. A1 triplex strength stayed ZERO throughout.
A2 raised a single confident SENSOR_CONTROL alarm at35300ms; A0/A1 never alarmed.
The unmodified DS recurrence approximately e+(1-e)*0.8*previous_mass amplified
repeated held evidence across the four samples. Thus a legal single-sensor excursion
and recovery can produce the same two-edge topology as a faulty pulse. Topological
corroboration does not make those repeated samples independent evidence.

Four C-disagreement trace windows were selected by cell identity BEFORE validation;
latch_2099_benign.csv.gz contains the failure. All four are retained as compact
runtime-only witnesses. No raw bulk logs. The benign CSV's origin_at_alarm column
is the fault-evaluation post-onset statistic and is UNKNOWN for this benign case;
the all-runtime origin counts and trace explicitly show the wrong confident origin16
(SENSOR_CONTROL). No fault-localization accuracy should be inferred from benign rows.

## Development outcomes (not fault validation)

| Phase | Observer | Original detection | Expanded detection | Benign alarms |
|---|---|---:|---:|---:|
| TRAIN | A0 | 706/800 | 777/960 | 1/240 |
| TRAIN | A1 | 735/800 | 873/960 | 10/240 |
| TRAIN | A2 | 736/800 | 874/960 | 12/240 |
| CALIBRATION | A0 | 356/400 | 391/480 | 0/120 |
| CALIBRATION | A1 | 370/400 | 435/480 | 0/120 |
| CALIBRATION | A2 | 371/400 | 436/480 | 2/120 |

Original-space A2 vs A1 TRAIN:both735,A1-only0,A2-only1,neither64.
CALIBRATION:both370,A1-only0,A2-only1,neither29. Each additional detection was one
pulse; neither had plant propagation. No gains in weak steps,common-mode,memory or
other families. No lost detections. Each phase's exact McNemar p=1. The two small
development gains came with additional benign alarms, and did not justify promotion.
All per-origin/subgroup,safety,latency and localization development metrics are in
validation_summary.csv and subgroup_summary.csv with explicit phase labels.
Zero fault cases in BENIGN_VALIDATION paired rows means NOT EVALUATED, not a null
finding on the planned fault cohort.

## Decision

Retained:CURRENT. The latch is rejected and remains unlinked experimental code for
reproducibility. Triplex-only is not promoted either: its fresh fault validation was
not reached, and the predeclared STOP rule prohibits continuing with a fallback.
Original-space>=91%:NOT EVALUATED. Plant-propagating>=95%:NOT EVALUATED.
Benign rate<=1%:YES. Localization/no-cold-regression gate:NO.
Ready to freeze this refinement for a new unseen:NO.

Strongest limitation of this attempt: short legal sensor disagreement can have the
same triplex innovation topology as a short fault; bounded holding can still convert
it into a confident false alarm. Passive unexcited actuators and global common-mode
remain architectural limits; this experiment does not revise those conclusions.

## Integrity and checks

The C physical sensor,previous triplex provider,CURRENT core,global cfg,Hybrid/HETIA,
legacy source/results and GUI bytes are unchanged. Frozen CURRENT state equivalence
was asserted at every new campaign sample (2,305,920 observations), plus the10
historical TRAIN/CALIBRATION sensor replays. Historical results are preserved.

Focused latch unit test passed:two-edge topology,one-pair rejection,300ms expiry,
nonrenewing recovery,common thermal motion,small alternating noise and qualification
reset. Harness/CURRENT build,Python compile and diff check passed before the benign
gate. Full tests/48legacy/64RTL were NOT rerun: the extension was not retained and
execution stopped at the mandated gate. Do not claim the previous phase's full
regression as a new full regression. Runtime binary bytes were preserved/restored
to their task-start versions after build checking.

HEAD:`1bc6b12d970acc702dea62ad2507f5709a5254cc`. Protected unchanged files:21255. Previous CURRENT artifacts archived byte-identically:7.

Archive:`results/clo_dsf_triplex_development_history.tar.gz`; earlier histories remain intact.

Protocol registration UTC:2026-09-29T13:56:40.759900+00:00. Lock UTC:2026-09-29T14:00:05.306870+00:00. Benign validation start UTC:2026-09-29T14:00:06.078902+00:00.

Scientific hashes unchanged after lock; no algorithm or parameter edits after benign validation.
