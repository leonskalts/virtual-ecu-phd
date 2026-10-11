# Final comparative unseen findings

Frozen commit: `a340ca5cf0473d7dc572f7cd63e44fbc25b175a7`.
One locked unseen campaign: **1500 cases, 1200 faults, 300 benign**, 240 faults per
origin. Manifest SHA256:
`06669c8b8358bc8120085e9a3af53a3a67479f7cc2214bc64262056d85377452`.
Zero overlap with 953 audited historical sources and the benchmark TRAIN/CAL/VALID
identities. No method changes after CAL selection; no outcome-triggered reruns.

The headline result is a trade-off, not universal detection superiority. On the
same final observability, Triplex, OR and Plain DS detect the **same 1089/1200 cases
(90.75%, Wilson95 88.98–92.26%)**, all with **0/300 benign alarms**. Triplex supplies
reliable runtime origin localization and lower P95 latency. The selected SVM detects
more cases but has substantially worse benign behavior and provides no localization.

## Method comparisons

Complete C1/C2 metrics and manuscript trade-offs are in `manuscript_table.md`.
All algorithms inherit the frozen evidence-provider engineering. C2 supplies the
same C-derived sensor evidence to every applicable method; no separate correlated
C vote or hidden sensor truth is used. These are fusion/backend comparisons, not
raw-sensor algorithms against a privileged engineered detector.

| Comparison | CURRENT/TRIPLEX | OR | Plain DS | Weighted Sum | SVM |
|---|---:|---:|---:|---:|---:|
| C1 detection /1200 | 1051 | 1022 | 1022 | 888 | 1090 |
| C2 detection /1200 | 1089 | 1089 | 1089 | 888 | 1118 |
| C1 benign /300 | 0 | 0 | 0 | 0 | 46 |
| C2 benign /300 | 0 | 0 | 0 | 0 | 49 |

C2 Triplex plant-propagating detection is **716/730 (98.08%)**, silent misses14;
OR/DS are identical. Weighted Sum detects584/730, silent146. SVM detects730/730,
silent0, but alarms on49/300 benign runs (16.33%). Run-level precision is100% for
Triplex/OR/DS/WS and95.80% for C2 SVM. Zero observed false alarms is not a guarantee
of zero population false-positive probability.

Triplex median/P95 latency **0/33.72s** versus OR/DS **0/43.58s**. Among their1089
jointly detected cases, Triplex is earlier on80, tied on1009, never later. The P95
reduction is9.86s. SVM is earlier than Triplex on158 joint detections and tied on931;
its median/P95 is0/29.815s. Weighted Sum's0/0.4s reflects its different detected-case
subset; on888 shared detections it is tied with Triplex. Latency percentiles across
different detection sets are not a standalone speed ranking.

Triplex first-detection localization:1089/1089 correct,100% coverage. All-runtime
localized samples329665/329665 correct, **zero wrong runs/samples**; UNKNOWN2044 of
331709 alarm samples (0.6162%). OR and Plain DS first detections are also100% correct,
but later have **82 wrong samples across33 runs** (32 actuator,1 communication).
Their runtime localized accuracy is99.9735%. OR UNKNOWN26/309826; DS10/309826.
CURRENT also has zero wrong origins. Weighted Sum has zero wrong origins among its
narrower detected subset. SVM localization is **NOT PROVIDED**, not an accuracy of0.
No method had a pre-onset alarm in the fault runs in this unseen campaign.

Triplex plant timing:584 pre-plant,78 same-tick,54 post-plant detections,14 misses.
These categories refer only to cases with a manifested counterfactual plant effect.

## Exact paired results (C2)

| Comparator | Both | Comparator only | Triplex only | Neither | Exact McNemar p |
|---|---:|---:|---:|---:|---:|
| OR | 1089 | 0 | 0 | 111 | Not applicable: no discordance |
| Weighted Sum | 888 | 0 | 201 | 111 | 6.2230e-61 |
| Plain DS | 1089 | 0 | 0 | 111 | Not applicable: no discordance |
| SVM | 1089 | 29 | 0 | 82 | 3.7253e-9 |

Benign Triplex/SVM pairing: both0, SVM-only49, Triplex-only0, neither251;
exact p3.5527e-15. Other C2 benign pairs have no discordance. Tests and Wilson
intervals are descriptive for a deterministic grouped design; no population
sampling or multiplicity-adjusted superiority claim is implied.

## Scientific interpretation

1. **Does Triplex improve detection against simple fusion?** Compared with the
   selected Weighted Sum operating point, yes (+201). Against OR/Plain DS with the
   same final providers, no: detection sets are exactly equal. Do not claim binary
   superiority over conventional DS or OR from this result.
2. **Does a detection improvement remain with equal Triplex observability?** Not
   against OR/DS. The retained advantage is combined temporal/localization behavior:
   earlier80 detections and avoidance of82 later wrong-origin samples.
3. **Who trades benign performance for raw coverage?** SVM:1118/1200 versus1089,
   with49/300 benign alarms versus0. Both C1 and C2 SVM have higher raw detection
   than Triplex, but substantially worse benign behavior. The SVM threshold was
   not adjusted after calibration, validation or unseen.
4. **Who provides reliable localization?** CURRENT and Triplex remain correct
   throughout all alarm samples, with explicit abstention. Weighted Sum is also
   correct for its narrower set. OR/DS initial origins are correct but some later
   downstream sensor evidence produces wrong origins. SVM makes no origin claim.
5. **Architecture versus fusion contribution:** CURRENT→Triplex adds38 detections,
   loses0, paired p7.2760e-12. Of these,37 are AB common-mode and1 a B step; plant
   detection rises679→716. With fixed OR or DS, adding C yields67 detections. At
   fixed final observability, Triplex's count gain over those methods is0. At C1,
   CURRENT exceeds OR/DS by29. These contrasts are not an additive decomposition:
   added observability changes which residuals temporal fusion can exploit. C1/C2
   WS/SVM were independently calibrated, although both selected the same settings.
6. **Classes missed by all:**82 cases:50 unexcited pump degradations,21 dormant
   stuck-bit cases,5 weak B steps and6 weak B pulses. Idle pump performance faults
   have no modeled response at zero command, so lack of excitation is a genuine
   model observability limit. Dormant short/intermittent faults lack effective stored
   corruption and a qualifying diagnostic alarm in their execution windows. Sensor
   misses are an observed provider/sensitivity limit, not proof that no independent
   physical information could exist. See `all_method_misses.csv` for every case.

## Hard subgroups and qualifications

Triplex: MEMORY218/240; TIMING240/240; COMMUNICATION240/240; SENSOR_CONTROL201/240;
ACTUATOR190/240. Effective memory164/164; dormant memory54/76. Active diagnostic
alarms on dormant states are separated from actual stored-value corruption.
Independent slow drift53/53 (A27/27,B26/26); AB common-mode66/80; weak steps61/80;
pulses60/80. Initially excited actuators142/142; initially unexcited48/98;
unexcited throughout0/50. Hard cases were not removed to improve coverage.

The conservative, preregistered CAL criterion selected WS weights[2,2,2,1,2,1] and
threshold.14 to avoid benign alarms. With all six channels available, a standalone
sensor channel contributes at most.1; this operating point detects0/240 sensor
faults. This is a transparent limitation of the **selected global WS operating
point**, not evidence that weighted sums intrinsically cannot detect sensors. All
available measured zeros remain observations; unavailable inputs are excluded.
Full alternative CAL results remain available. No alternative was chosen using
validation or unseen results.

One of SVM's29 additional run-level detections requires care:
`benchmark_unseen_0750` is a dormant transient memory fault active29200–29800ms.
Its SVM alarm is at72800ms, concurrent with the first sensor residual and long after
the memory episode; no stored-value corruption or plant effect occurs. The existing
post-onset run metric credits it, but it is **not evidence of improved memory
observability**. The other28 additional credits are sensor cases. This accounting
caveat is retained rather than silently changing the registered metric after results.

Cohorts are restricted to the predefined simulator, original A/B/AB sensor fault
space, finite120s horizon and frozen provider engineering. C-only/global ABC faults
are not part of this primary benchmark. SVM results do not characterize all possible
SVM features or decision thresholds. Calibration prioritized benign behavior over
recall; no method was subsequently rescued. Strongest Triplex evidence is its
zero-benign, reliable-runtime-localization combination, not maximal binary recall.

## Integrity and completion

337 tests, full build, Python compile, diff check,48 legacy and64 RTL passed.
All221 frozen scientific/GUI hashes, method-freeze hashes, prior final unseen
artifacts and37244 historical/protected files (including Hybrid/HETIA) are unchanged.
Tracked build binaries were restored after regression. No commit/push; GUI preserved
and never staged. All4200 planned simulations completed once, no collector failures
or reruns. One common physical execution per case supplied all applicable backends.
No bulk raw traces or screenshots retained; zero compressed representative traces.
