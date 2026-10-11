# Frozen operating-condition robustness preregistration

Six profiles,400cases each:300faults(60each Memory,Timing,Communication,Sensor/control,Actuator)+100benign. Total1800fault/600benign. Select one400-template panel by seeded(20261007), proportional largest-remainder stratification from the final generator's specifications, without using outcomes. Fault strata:model/behavior/domain/kind; benign strata:workload. Reuse identical fault model,magnitude,start,duration,temporal behavior,domain and ramp/probe-related configuration across conditions. Generate fresh profiles and three new independent sensor seeds per case. No fault parameter adjusted to improve coverage. Context-induced excitation/propagation changes are the object of the study, not fault-semantic changes.

All profiles receive the same formula for tiny unique ambient/speed offsets(.113+i*.0000037 C and .217+i*.0000071 km/h) and new seeds. P0 retains the nominal final operating templates, including their existing legal context variation. Explicit operating transforms:

| Profile | Registered conditions |
|---|---|
| P0 nominal/reference | Original template ambient/load, noise and phase plus the common identity offsets/new seeds |
| P1 low ambient/load | Ambient minus15 C; load times.55 |
| P2 high ambient/load | Ambient plus15 C; load times1.4, capped at1 |
| P3 elevated legal noise/quantization | Primary alternating amplitude.08 C plus triangle.04 C/19300ms; reference noise.08 C; C noise.04 C; C quantum.05 C |
| P4 fixed acquisition-phase variation | C phase1,21,41,61,81,99ms, cyclic by the fixed panel index; each case's phase is constant |
| P5 combined legal stress | Five profile segments: ambient offsets[-10,8,-4,14,0] C; load factors[.7,1.25,.85,1.4,1], capped at1; P3 noise; P4 phases; authorized target updates(35700ms,103 C),(72700ms,92 C); legal B offsets alternating sign with magnitudes[.2,.32,.5] C and durations[100,1100,2300,5100]ms cyclic by panel index |

Use only existing CLI/provider options. Existing parser/producer-authorized transformations define legal context, not a claim that the detector tolerates every combination. Do not lower thresholds if these conditions yield alarms. Preserve fault injection and scheduler paths. Scheduler-jitter robustness is NOT evaluated:main.c rejects scheduler workload stress with direct cross-layer faults, and scheduler.c substitutes the scheduler-stress path for timing injection. User explicitly approved fixed acquisition-phase variation instead. Do NOT describe phase variation as scheduler jitter. Sensor periods remain100ms; phase is supported Sensor C phase, not changing timing-task releases or adding within-run jitter.

Before any case: verify final frozen hashes and prior artifacts; audit all historical CSV/Git/archive/profile and embedded JSON/spec identities, including latest development/final cohorts. Require zero exact configuration/profile overlap. Lock this protocol, entire2400manifest/seeds, harness and source/config/model hashes. Reuse the exact final-unseen executable by hash; do not rebuild or edit detectors. A2 is final G2 confirmation + integrity + M2 + retained Triplex/DS/causal localization. SVM-INT is the same41-feature model/scaler and default threshold0 used as primary in the final unseen. Same runtime streams and original observables for both. No fitting, recalibration or profile-dependent policy.

Run each physical case once; refuse rerun after execution-start marker. All six profiles run regardless of observed detection or false alarms. If an execution fails, preserve the partial record and do not rerun it. No outcome-driven parameter changes. Raw traces processed/deleted; retain compact sufficient statistics for misses and alarm-edge accounting. Post-hoc labels never enter either detector.

Report each profile and pooled: detection/Wilson95, per-origin,benign,precision,plant/silent,median/P95 latency,integrity-observable detection; A2 first/runtime localization,wrongfaultorigins,UNKNOWN; SVM localization unavailable. Paired A2/SVM counts and exact McNemar where discordant. Worst detection/benign/plant profiles; absolute percentage-point and latency differences from final unseen. Descriptive comparisons only:case composition differs from final unseen, and matched templates have independent noise seeds across profiles.

Miss taxonomy: preserve structural idle-actuator, uncaptured-pulse and dormant-memory/probe categories only when runtime sufficient statistics support them. Separately flag alarm-edge-scoring misses (post-onset alarm present but no new edge), integrity-discrepancy/no-alarm decision failures, and unresolved sensitivity. Nonzero evidence alone does not prove healthy-set distinguishability or a classifier-only limitation. Inspect any new category post-hoc without rerunning or tuning.

Afterward verify hashes and run one full regression(build,compile,tests,diff,48legacy,64RTL), restore built artifacts, preserve GUI/Hybrid/HETIA and all old results. No commit/push.
