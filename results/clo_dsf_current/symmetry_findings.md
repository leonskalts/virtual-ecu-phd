# Final triplex symmetry audit and untouched validation

## Decision

Retain the unchanged A1 triplex candidate for freezing, after the required full regression passed (339 tests, build/compile/diff check,48 legacy,64 RTL, Hybrid/HETIA integrity). No detector fix was justified or applied. This is development validation, not an unseen holdout. The previous 361/400 (90.25%) result remains valid and unchanged. The new 437/480 (91.04%) result crosses the >=91% gate by only 0.04 percentage points; this change in percentage is a cohort difference, not evidence of an implementation improvement. Its Wilson interval spans the target.

## Implementation audit

Pairwise A/B permutation tests pass at every timestamp for nine synthetic scenarios, including asynchronous C projection and invalid acquisition. Signed residual reversal preserves FAST/SLOW strength and threshold-crossing timing; AC/BC state and cut labels exchange consistently. Full ECU invariance is not appropriate when exchanging primary control sensor A with diagnostic reference B: acquisition-to-consumption, forecast, startup qualification, noise/calibration and plant feedback have different physical roles. No unjustified implementation, ordering or numerical/scaling asymmetry was found. Sensor-member cuts are not confident faulty-member localization. See symmetry_audit.md for code paths and classifications.

Five historical memory misses were all non-effective stored-value cases with no active probe intersecting their half-open fault windows. No address, bookkeeping, indexing, stale-state or end-of-run defect was found. Seven existing memory diagnostic tests pass. No memory change, active-probe frequency change, latch, actuator telemetry, threshold adjustment or DS redesign occurred.

## Development verification

New TRAIN150 and CALIBRATION150 ran before freeze. A0/A1 detected102/107 of120 TRAIN faults and108/113 of120 CALIBRATION faults. Both methods had0/30 benign alarms and no wrong origins in each partition. A-only8/8 and B-only7/8 in each partition; AB3/8 to8/8. These verify the unchanged behavior, not a fitted correction. No parameter selection.

## New locked validation

600 new cases:480 faults,120 benign;96 each original origin. A/B/AB32 each, drift/step/pulse32 each. Four grouped operating families; cold/unexcited actuator templates remain. Manifest and scientific hashes frozen before execution; outcomes inspected only after completion. A0/A1 share physical observations. All cases retained, no reruns, no post-result adjustments.

A0:417/480=86.875%, Wilson83.56–89.61%. A1:437/480=91.0417%, Wilson88.15–93.28%. Memory90/96, timing96/96, communication96/96, sensor/control92/96, actuator63/96. Effective memory66/66; non-effective/dormant stuck states24/30 detected through the existing active diagnostic, not by fabricating a passive inconsistency. Remaining6 dormant states undetected.

A32/32; B28/32; AB32/32. Independent A/B slow drift21/21 (all domains slow32/32), weak steps32/32, pulses28/32. All four sensor misses remain B-only pulses. No A/B gain is claimed from this audit. Initially excited actuator43/43; initially unexcited20/53;33 unexcited throughout undetected.

Plant manifestation231 cases: A0 detected214, silent17; A1 detected231, silent0. A0 pre/same/post182/24/8; A1 182/31/18. Benign0/120 for both. Median/P95 A0 0/5.54s; A1 0/30.88s. Marginal latency distributions include different detected sets: additional slow detections increase A1 P95; no latency improvement claim.

First localization accuracy100% for both. A1 all437 detected cases localized correctly; runtime129139/129139 localized alarm samples correct,659/129798 UNKNOWN (0.508%), wrong runs/samples0/0. A0 runtime122388/122388 correct,659/123047 UNKNOWN (0.536%). Main-origin correctness does not resolve which member of a disagreeing pair is faulty.

Paired: both417, A0-only0, A1-only20, neither43; exact two-sided McNemar p=1.9073486328125e-6. All20 gains are AB common-mode; A-only0, B-only0, memory0, other0. No detections lost; timing/communication/effective-memory casewise preserved. All predeclared retention gates pass, without a symmetry correction. Wilson and McNemar statistics are descriptive for the deterministic grouped cohort, not a population-generalization guarantee.

## Limits and next step

Strongest result: common-mode32/32 and plant-conditioned231/231 with no false or wrong confident alarms. Strongest remaining limitations:33 unexcited actuator misses,6 non-effective/probe-unobserved memory states,4 B-only pulses; narrow overall gate margin and common-mode observability still depends on independent C. Retention here means eligibility to freeze the evaluated A1 harness; the production detector was not rewritten or integrated after seeing validation. Freeze exact evaluated sources/harness before any completely new unseen study. No unseen execution, commit or push in this task.
