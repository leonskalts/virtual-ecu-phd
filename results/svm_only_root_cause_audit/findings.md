# SVM-only root-cause audit

## Scope and integrity

This is a post-hoc audit of the already-seen Triplex-Plus validation, not a new validation or an unseen run. HEAD `a340ca5cf0473d7dc572f7cd63e44fbc25b175a7`. No source, detector, model, threshold, or existing result changed. GUI bytes preserved. The 40 previously seen runs were reconstructed with a read-only temporary logger because their full traces had been deleted; physical-output SHA256, CURRENT trace SHA256, M250 detection and first-alarm metrics, and frozen SVM alarm timing/sample counts reproduced exactly. Two logger passes were needed to add primitive signal provenance. No model was retrained. TRAIN/CALIBRATION replay reconstructed all 2,250 existing configurations for each fixed emulation, with original output hashes and M250 decisions checked. Prior result and scientific-file locks passed before and after.

## Cases and mechanism

All 17 are SENSOR_CONTROL: 8 steps (2 A, 6 AB), 9 pulses (6 A, 3 AB), all +0.49 C. A=primary, B=reference, AB=both; C remains independent, so AB is not a three-member common-mode fault. Eight steps are permanent; nine pulses are transient (six 150 ms, three 50 ms). Memory/timing/communication/actuator, dormant memory, B-only, excited/unexcited actuator, other: zero. Ten propagated to the plant. Source acquisition phase is recorded per case, not used for inference. SVM alarms 15–99 ms after activation, at the first positive qualified evidence sample.

At first SVM detection, primary acquisition changes by 0.454–0.541 C per 100 ms. The local 2.5 C/s contract produces weak positive slew evidence. Current A/B forecast, FAST and SLOW contributions are zero there. The only positive qualified provider is sensor/control; no cross-layer concurrence or source-order signature is present. A sensor-only logical origin subset (8) exists, but the first origin BetP is only 0.282–0.317 and ignorance 0.854–0.898. It is not a confident localization. The actual core maximum anomaly belief is 0.137–0.361, leaving 0.139–0.363 to the unchanged 0.5 confirmation threshold; this is not a blocked persistence counter. `case_audit.csv` gives each case's duration, phase, margins, maxima, distances and provenance.

## Exact model attribution

The selected SVM is LINEAR, not nonlinear. For these cases, other positive evidence sources are zero. Its decision function reduces (rounding only here) to:

`margin = -1.000449 + 15.650295*s + 4.720079*mean_1s(s) + 1.384091*max_1s(s) + 0.000850*available_sensor`.

Mean/max are causal summaries of the SAME source, not independent corroboration. `feature_attribution.csv` contains all 24 exact standardized contributions and contributions relative to a zero-valued input at first alarm. Summed standardized contributions plus intercept were checked against decision_function. Attribution describes the fitted model, not causation.

Removing mean/max contributions at the first positive decision leaves all 17 fault margins positive. Therefore their advantage does not require temporal interactions, cross-layer evidence, or a nonlinear classifier. Seven of 23 benign first decisions do need the SVM history contributions. No positive SVM frame in these 40 runs has zero current sensor evidence.

## Fault/benign pattern overlap

The same sensor-current + sensor-mean + sensor-max feature pattern occurs in 17/17 faults and 23/23 benign alarms. Primary pattern groups: P1=0, P2=17, P3=0, P4=0 among faults; an aggressive sensitivity operating point is a secondary interpretation of every P2 case, not another disjoint case count. Raw maximum sensor strengths overlap: faults 0.102–0.281, benign 0.063–0.169. No threshold is selected from these ranges.

Fault evidence lasts 2–3 consecutive frames. Eighteen benign runs have only isolated positive evidence; five also contain stretches of five positive frames. All benign SVM-positive stretches last one frame; faults last 2–3. This is a hypothesis-generating temporal distinction, not demonstrated validation performance for a new rule. The fixed rule below was NOT scored on validation. The 23 false-positive runs are concentrated in validation profile families 18–20, so profile/noise dependence and limited independence also constrain inference.

## One proposed principle and development-only risk test

Qualified same-provider recurrence: two adjacent 100 ms frames with positive, available evidence in the same originating provider (any of timing, communication, memory, sensor/control, actuator). Zero retains its existing meaning; no new amplitude threshold. Two is the minimum repeated observation, fixed before replay. Exclude plant-only support. Union with M250 alarms; rescue-only origin UNKNOWN. This is an OFFLINE hypothesis test, not a detector change. Its prereplay specification is `recurrence_protocol.md`.

- TRAIN: +24 faults; 15/300 benign; wrong localized samples 0; UNKNOWN rescue origins.
- CALIBRATION: +10 faults; 5/150 benign; wrong localized samples 0; UNKNOWN rescue origins.

Historical qualified leaky likelihood accumulation provides supporting sensitivity evidence. The already locked TRAIN likelihood table, decay 0.8 and predeclared boundaries 4 and 12 were independently replayed; no fitting or selection occurred. Results exactly matched the saved pre-validation grid:

- Boundary 4.0: TRAIN: +24 faults; 81/300 benign; wrong localized samples 0; UNKNOWN rescue origins.
- Boundary 12.0: TRAIN: +0 faults; 0/300 benign; wrong localized samples 0; UNKNOWN rescue origins.
- Boundary 4.0: CALIBRATION: +10 faults; 29/150 benign; wrong localized samples 0; UNKNOWN rescue origins.
- Boundary 12.0: CALIBRATION: +0 faults; 0/150 benign; wrong localized samples 0; UNKNOWN rescue origins.

The full archived nine-setting grid remains in the unchanged Triplex-Plus results. Every gain-bearing setting in that grid exceeds 1% benign on at least one development partition; the sole setting that meets both benign gates adds no faults. The new recurrence test must be judged by its reported benign rates, not its gains alone. These finite tests do not prove that every conceivable deterministic rule would fail.

## Recoverability and recommendation

R1=0, R2=17, R3=0, R4=0, R5=0. R2 means a supported sensitivity/false-alarm tradeoff within the tested rule families; it does not prove all possible deterministic rules would fail. The recurrence rule adds 24 TRAIN and 10 CALIBRATION detections, but causes 15/300 (5%) and 5/150 (3.33%) benign alarms. It fails the 1% benign-risk criterion on both partitions. No low-risk principle was established. There is no evidence that CLO omits these observables: it already fuses the same sensor evidence, at a more conservative decision operating point. Do not initiate another detector-development pass from this audit.

Classifications in `temporal_patterns.csv` are operational assessments within the tested evidence/rule families, not impossibility theorems. No nonlinear requirement is supported by a linear decision function. No fault detection is attributed to a pre-onset alarm or unrelated source. Do not derive case-specific amplitude, sign, duration or profile rules from these 17 cases. Preserve the retained detector unless an independent scientific reason supports new work; report the SVM accuracy/false-alarm operating points together.

No source changes. No commit/push. No unseen run.
