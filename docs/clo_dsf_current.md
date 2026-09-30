# Final retained CURRENT CLO-DSF

Development is closed. The implementation is `src/v7_3/clo_dsf_revised.c`,
`include/clo_dsf_revised.h`, and the existing runtime adapter. Configuration remains
`results/cross_layer_safety_v7_3_dev/revised.cfg`. Global confirmation threshold
0.5, persistence1, temporal discount0.8 and localization thresholds are unchanged.

Retained runtime evidence:

- Trusted calibration shadow and acquisition-to-consumption consistency.
- Atomic protected-memory save/challenge/read/restore diagnostic with deterministic
  phase sweeping: nine1100ms gaps followed by100ms, average1Hz, maximum1100ms.
  Probe freshness follows the existing maximum interval. The diagnostic consumes
  readback/status/timestamps, never injected labels. Effective stored-value
  corruption and dormant/value-consistent stuck cells are reported separately.
- Independent redundant coolant sensor, long-horizon signed disagreement and
  short-horizon FAST disagreement with bounded same-sign integration. The
  existing300ms local trajectory forecast is retained. A redundant pair does not
  identify which member is faulty; common-mode drift can remain plausible.
- Runtime command/actual actuator consistency. No active excitation, added health
  telemetry or pre-mission BIST. Zero command may conceal authority degradation.
- Causal-precedence localization. Later downstream sensor evidence cannot rewrite
  an established direct origin. Ambiguous origins remain UNKNOWN.
- Startup qualification: absolute slew requires five contiguous in-envelope
  acquisitions for origin evidence. Anomaly history alone from unqualified slew
  cannot confirm without independently qualified evidence. Direct memory,
  communication, timing, actuator and independent sensor evidence remain usable.

No hidden plant truth, fault labels or counterfactual reference feeds inference.
Counterfactual propagation metrics are post-hoc evaluation only. Memory accesses
have no measured hardware WCET in this simulator; results are not certification.

Rejected mechanisms remain absent: supervised residual ML, one-class ML,
control-action contracts, radiator reference, multi-node thermal model, active
actuator excitation, pre-mission actuator BIST and passive actuator-health
extensions. The final supervised trial improved detection331/396 to366/396 but
introduced17/108 benign alarms, failing both its95% recall and1% benign gates.
Its compact rejection record is development evidence, not the retained detector.

`results/clo_dsf_current/` keeps required historical identities, development
manifests and compact summaries. All earlier campaigns, including previous
`clo_dsf_final_unseen` contents, are seen development evidence. The final new
holdout must record the freeze commit, lock its manifest/protocol before outcomes,
execute each case once and report all faults including latent/unobservable cases.
No further selection, tuning or reruns for poor performance are permitted.

## Subsequent conflict-aware development (no replacement retained)

The9f993587 freeze and its separately preserved holdout evidence remain historical
classical baseline/reference evidence. A new2100-case TRAIN/CALIBRATION/VALIDATION
campaign tested Dempster,Yager,Dubois-Prade and sequential binary PCR6,without
changing providers or thresholds. All scored319/360validation faults,0/90benign
alarms and0wrong confident origins. None reaches95%; no replacement is retained.

Anomaly masses contain only ABNORMAL and ignorance,so detection conflict is
identically zero. Standard conflict redistribution cannot improve those masses.
The selectable C layer defaults to classical Dempster; alternative state selections
are available for reproducibility but are not enabled in the production adapter.
No CLO-DSF+ or new mathematics is claimed. Full335tests,build/compile/diff,48legacy
and64RTL pass; baseline behavior matches frozen source across2522100sample steps.
See the preserved previous_fusion_development.tar.gz in results/clo_dsf_current/ for that audit and its findings. No new unseen
holdout was run. Modified detector code is not committed or pushed.

## Binary-frame development result (rejected)

The subsequent2400-case grouped binary NORMAL/ABNORMAL/ignorance study produced
meaningful conflict but failed the95% retention gate:417/480 validation detections
versus413/480 classical,0/120 benign alarms,0wrong confident origins. Four gains
(three weak steps,one pulse), no losses; exact McNemar p0.125. Plant misses14versus16.
First-alarm origin coverage fell to363/417; the unchanged localizer correctly leaves
new early detections UNKNOWN. Dempster,Yager,PCR6 detected the same validation set.
The binary module is experimental and unlinked; CURRENT remains classical. No
new unseen or commit/push. See results/clo_dsf_current_history.tar.gz for this rejected binary development result and its selection record.

## Triplex observability development (not retained)

The2400-case grouped third-coolant-chain study recovered all32/32 validation AB
common-mode cases (22 additional) and all170/170 original-space plant-propagating
cases. No benign alarms or wrong confident origins. Original-space343/384 (89.32%)
and expanded-space415/480 (86.46%) fail the95% retention gate. Global ABC slow drift
remains0/8; all33 never-excited actuators remain missed. No actuator telemetry was
justified. CURRENT stays classical; sensor/model/provider modules are experimental
and unlinked. Historical CURRENT artifacts are preserved in
results/clo_dsf_current_history.tar.gz. See results/clo_dsf_current/findings.md for
the new development evidence, fairness denominators, limits and regression record.

## Final triplex latch refinement (stopped at benign gate)

The fixed300ms consensus latch gained one pulse in TRAIN and one in CALIBRATION,
but failed the separate benign validation gate:1/120 alarms,one wrong confident
SENSOR_CONTROL sample and one added alarm in a cold-start workload. CURRENT and
triplex-only both had0/120. The480 planned fault-validation cases were not run.
CURRENT remains retained; neither triplex nor latch was promoted. No unseen,commit
or push. See results/clo_dsf_current/findings.md; prior triplex findings are preserved
in results/clo_dsf_triplex_development_history.tar.gz.

## Final retained Triplex freeze

The retained architecture is A1 Triplex from the symmetry audit (437/480). See results/clo_dsf_current/triplex_freeze_record.md for exact build/evaluation entry points and cleanup equivalence. Rejected latch and alternative fusion experiments are not part of the retained executable. The idle pump-performance observability boundary remains unchanged.
