# 04 — Experimental protocol, cohorts and statistics

Evidence labels used throughout: **VERIFIED FROM SOURCE** (literal implemented behavior); **VERIFIED FROM EXPERIMENT ARTIFACT** (recorded outcomes/protocol); **DERIVED MATHEMATICALLY FROM VERIFIED SOURCE** (algebra or deterministic accounting, not a new experiment); **NOT RECOVERABLE / REQUIRES CONFIRMATION** (missing/limited evidence). Source paths are repository-relative unless explicitly absolute. Line numbers refer to the hashes in 07, not an assumed future HEAD.

## Cohort separation and exact identities

**VERIFIED FROM EXPERIMENT ARTIFACT.** Never add numerators across these tables as though they were one held-out study. Original run identifiers, partition counts, manifest SHA-256 and sampled parameter inventories are in `data/cohort_inventory.json`; exact manifests remain at the cited paths. All new comparisons reuse related simulator templates: zero exact configuration overlap does not imply statistical independence of physical mechanisms.

| Study | Manifest partition | Fault | Benign | Original run-ID interval |
|---|---|---:|---:|---|
| digital_integrity_development | CALIBRATION | 1200 | 1200 | di_3600 … di_5999 |
| digital_integrity_development | TRAIN | 2400 | 1200 | di_0000 … di_3599 |
| digital_integrity_development | VALIDATION | 1200 | 1200 | di_6000 … di_8399 |
| benign_alarm_development | CALIBRATION | 1200 | 1200 | ba_2400 … ba_4799 |
| benign_alarm_development | TRAIN | 1200 | 1200 | ba_0000 … ba_2399 |
| benign_alarm_development | VALIDATION | 1200 | 2400 | ba_4800 … ba_8399 |
| integrity_final_unseen | UNSEEN | 1200 | 600 | ifu_0000 … ifu_1799 |
| frozen_robustness | ROBUSTNESS | 1800 | 600 | rob_0000 … rob_2399 |
| ieee_multibaseline | SECONDARY | 1200 | 600 | ieee_0000 … ieee_1799 |
| ieee_origin_rf | SECONDARY | 1200 | 600 | orf_0000 … orf_1799 |

The digital-integrity TRAIN partition is **2,400 faults +1,200 benign**, not 1,200 faults. CAL/VALIDATION each have1,200 faults+1,200 benign. The prior SEEN90 panel is a targeted re-analysis of historical misses, not new validation. Benign-alarm development uses1,200 faults+1,200 benign in each TRAIN/CAL and1,200 faults+2,400 benign in validation.

**VERIFIED FROM SOURCE.** Primary seed sequences for row index i: 1801100003+313i,1903300007+317i,2007700011+331i. IEEE ten-method secondary:3010100003+401i,3110300007+409i,3210700011+419i. Origin-RF secondary:3310100003+421i,3410300007+431i,3510700011+433i. Seeds are distinct deterministic noise contexts, not random sampling from a field population. Full generator formulas (including inherited transformations and per-family settings) and literal preregistrations are cited below; inspect manifests rather than reconstructing configurations by seed alone.

## Fitting, calibration and frozen selections

**VERIFIED FROM SOURCE / VERIFIED FROM EXPERIMENT ARTIFACT.** Digital integrity compares A0, A1 (integrity), A2 (integrity plus final M2); original SVM-INT uses41 engineered features, StandardScaler and candidates linear C=.1/1 and RBF C=1. TRAIN samples at most eight evenly spaced frames for each binary class per run. Frame targets reflect active or prior99ms intervals. These are supervised labels, not runtime inputs. CAL selects the model by balanced detection/benign accuracy; frozen model is linear C=.1. Default margin>0 remains primary; CAL1 threshold −0.999752366177874 is a separate secondary operating point, not guaranteed to outperform default. No plant label is used as an inference feature.

G2 selection evaluates G0,G1,G2,G3,G4, with (count,threshold)=(0,0),(2,.5),(3,.5),(1,.75),(3,.75). Select on NEW TRAIN/CAL only: no plant/integrity loss, no wrong confident fault origin, ≤.25pp detection loss and CAL benign≤.5%; minimize CAL then TRAIN benign, then loss, then index. G2 retained; validation1124/1200 and0/2400 benign versus original1124/1200 and49/2400. This is not the earlier55/1200 cohort.

The ten-method study fits new methods on the authorized original digital-integrity TRAIN/CAL, verifies reconstructed native training parity, and locks before a new secondary cohort. OR/PlainDS are fixed; WS/EWMA/CUSUM/LR/RF are selected under ≤1% CAL benign as preregistered. Original A0 is an architecture ablation. Strength-only classical methods discard explicit integrity PASS and provenance; learned41-feature baselines also omit some upstream ledger/context fields relative to CLOVER. Consequently this is a **qualified system comparison**, not strict information equality or a theorem about DS versus ML. Binary methods do not gain invented localization. The frozen primary unseen is not replayed from incomplete summary data.

Origin-RF uses the later common67-field upstream packet and174 causal features:66 values/ages +66 finite masks +six strengths +six availability +six support masks +24 ten/fifty-frame mean/max features. No DS predictions, direct-origin memory, fault metadata or plant truth. TRAIN/CAL are authorized benign-alarm-development2400-case partitions; TRAIN has54,635 sampled frames. Four RF candidates: depth12/unlimited × minimum leaf4/16;200 trees. Retained depth12/leaf16, alarm 1−P(NORMAL)>.9155568509788313; conditional fault-class confidence≥.7, margin≥0, otherwise UNKNOWN. CAL requires zero benign and zero wrong confident first/runtime origins, then maximizes detection/localization with fixed tie order. Labels fit trees only on TRAIN; CAL labels select thresholds; test labels only score. Frozen SVM remains a41-feature binary reference, not a multiclass schema-matched challenger.

## Offline outcomes, timing and statistical interpretation

**VERIFIED FROM SOURCE.** A synchronized healthy reference ECU uses the same legal workload, with injected faults disabled. Propagation monitor compares true coolant: plant manifestation first occurs when |T_fault−T_reference|≥.01°C after injection; command-effect tolerance is10⁻⁶. It operates in reporting/evaluation code. `runtime_observation_t`, provider functions and learned feature allowlists omit both trajectories and this label. Sensor producers legitimately see physical simulator state to simulate measurement, but detector functions receive measurements only.

Detection is the established **post-onset rising-edge** outcome, not merely any positive sample. First/global alarm and later localizations are separate. Latency is conditional on detection, calculated on sampled timestamps; zero is not instantaneous continuous-time detection. Runtime origin accuracy excludes UNKNOWN; first coverage is conditional on detection; run-origin labels apply across the run and are not generic active-frame ground truth. Precision=detected faults/(detected faults+benign alarm runs), so it depends on the constructed prevalence.

**DERIVED MATHEMATICALLY FROM VERIFIED SOURCE.** Wilson95 for k/n uses z=1.959963984540054:
\[
\frac{\hat p+z^2/(2n)\;\pm\;z\sqrt{\hat p(1-\hat p)/n+z^2/(4n^2)}}{1+z^2/n}.
\]
Paired binary counts are both/onlyA/onlyB/neither on the same case IDs. Exact McNemar uses a Binomial(b+c,.5) two-sided tail (clipped at1) on discordants; no discordance supplies no evidence of difference. Some original CSVs leave p blank; others record1—preserve those conventions. Ten-method study applies Holm adjustment across eight algorithm comparisons per endpoint; A0 ablation is separate. Repeated templates, deterministic seeds and within-run correlated samples invalidate an unqualified IID/field-risk reading. These CIs/tests are descriptive conditional simulator summaries; no sample count should be inflated to the millions of runtime frames for run-level accuracy.

## Six-condition robustness

**VERIFIED FROM EXPERIMENT ARTIFACT.** A400-template panel, selected with seed20261007 using proportional largest-remainder fault stratification, is repeated across six conditions with new per-case noise seeds:300fault+100benign/profile,60fault/origin. Fault parameters remain the same across conditions; context can naturally change actuator excitation. P0 nominal; P1 ambient−15/load×.55; P2 ambient+15/load×1.4 capped1; P3 elevated legal noise/quantization; P4 fixed Sensor-C phases1,21,41,61,81,99ms; P5 combined legal ambient/load, authorized calibration/offset, noise and fixed phase variation. Scheduler-jitter robustness was NOT evaluated because scheduler-stress and direct timing-fault paths are incompatible. P4/P5 must not be called scheduler jitter. Literal values and transforms appear in the copied protocol excerpt below.

## Resource studies

**VERIFIED FROM EXPERIMENT ARTIFACT.** Native timing and memory reuse origin-RF's2,161,800 stored frames/1800 cases; they are retrospective correctness/resource replays, **not new fault cohorts or extra unseen confirmations**. Full-frame exact parity precedes timings. Native timing is one pinned i7-14700 pass; native memory later uses separately linked host payloads and a provider-inclusive RF B. Timings/footprints cannot be interchanged across the two build layouts. See05.

## Literal preregistration and methodological qualifications

### digital_integrity_development

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/digital_integrity_development/protocol.md` — `file`, lines 1–11

# Protected digital acquisition witness — DEVELOPMENT ONLY

A0 retained Triplex. A1 same + protected digital producer records. A2 A1 + previously evaluated M2 phase-superset 40 probes/10s. No fusion/Triplex/threshold/causal-precedence changes. No unseen, commit, push, old evidence or GUI changes. This is a simulated isolated driver mailbox, not a claim that ordinary C static memory is hardware protected. Protect each acquisition result after its modeled conversion; store channel, exact value bits, monotone sequence, timestamp, CRC32 and independent full protected record. Verify delivered source before control, and B/C before observer use. Callback is at producer function return irrespective of faults, not in inject_value. No plant/model state, truth or injection metadata enters witness. Legal primary variation and reference calibration transform only the protected producer value via an authorized operation; delivered values remain unchanged. Do not authenticate arbitrary caller-modified data. Counterfactual ECU has separate bank; no mixing.

Integrity mismatch creates a 300ms diagnostic status, merged by MAX into existing sensor anomaly/origin evidence. Existing DS and temporal/localization logic unchanged. Three-channel bad mask exposed equally to SVM. Fixed parameters, no fault-specific tuning. Repeated checks of a bad published sample may renew status until next correct producer publication. No correction, control action, or physical perturbation from witness. Faults before protection remain authenticated; a consistent compromise of data AND isolated witness is not covered. CRC alone does not resist recomputation; the independent full protected record supplies that boundary. Canonical unit failure tests: value-only; old value+sequence replay; modified value+recomputed tag; witness bit upset; consistent data+witness modification; pre-protection error; legal transform. No coverage claim for unmodeled physical faults.

8400 new cases using existing original fault-space generator: TRAIN3600(2400fault/1200benign), CAL2400(1200/1200), VALID2400(1200/1200), 240 faults/origin in VALID. Change profiles/seeds/phases/nearby amplitudes, preserve subtype/domain balance including ABC common-mode and unexcited actuators. All historical manifests/embedded manifests must be audited including dynamic consensus. No outcome-dependent case selection. Prior90 misses are a separate SEEN diagnostic regression cohort, not part of new campaign or promotion metrics. Static sample-overlap classification is post-hoc accounting only. Preserve unchanged physical baseline alarm/origin series, original fault semantics and plant traces; verify A0 against an uninstrumented executable on representative cases before validation.

SVM-INT uses same cross-layer evidence, raw sensor/context features and integrity observables. TRAIN-only StandardScaler and linear SVC C=.1 or1, RBF C=1; <=8 frames/class/run. Select on CAL balanced run accuracy, then recall, then simpler order. Default threshold0; CAL<=1% point uses strict exceedance of ceil((n+1)*.99) benign run-max order statistic. Empirical target, not validation guarantee. Group partitions unchanged/disjoint; no validation tuning. Freeze code/protocol/manifest/model/threshold before any VALID run. All faults/benign accounted once.

Promotion: >=2 percentage points A2/A0, zero A0 fault detections lost, zero wrong confident fault origins, newly alarming benign runs due to integrity <=0.5pp, plant detection unchanged or better. Strong success A2 raw recall>SVM default; report failure honestly. Physical/pre-protection and data+witness common failure are boundary tests, not newly invented primary fault coupling. Full regression once if retained; always provider tests/build/compile/diff check. Keep compact summaries/configs/model/case metrics; no raw traces retained.


### benign_alarm_development

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/benign_alarm_development/protocol.md` — `file`, lines 1–15

# Provenance-aware legacy sensor confirmation — development registration

Historical seen audit reconstructs all55 benign false-alarm runs and1200faults from DIGITAL INTEGRITY VALID. Require exact A2 alarm/localization metric parity. Audit only; not selection. Old evidence and scientific files, digital integrity, M2, physics/fault/controller, DS combinations and Triplex providers unchanged. Separate output confirmation gate; never correct samples or feed ground truth. No unseen, commit, push; preserve GUI.

The gate is eligible ONLY with all three protected records available, no current integrity violation, no latched integrity FAIL, no non-sensor evidence>0 (including plant), and no retained direct non-sensor origin. Missing integrity status is UNKNOWN, never PASS. Integrity FAIL and other-layer/provenance support always bypass. DS masses, combination, output scores and causal origins remain untouched. Final alarm alone requires sufficient consecutive100ms qualified sensor samples; suppressed alarm publishes UNKNOWN rather than an origin. Qualification uses runtime origin_local (trusted provider provenance); no label or case parameters. Duplicate timestamps do not advance; gaps or subthreshold samples reset. Confirmation can accumulate before a base alarm, but never create an alarm the base did not produce. Suppression never changes internal DS state or established causal provenance.

Five predefined choices only: G0 original; G1 two consecutive qualified samples>=.5; G2 three>=.5; G3 one>=.75; G4 three>=.75. .5 is existing confirmed evidence threshold; .75 is a predefined stronger sensor-only qualification. No additional grid/search after outcomes. No provider/DS/global threshold changes.

New group-wise TRAIN2400(1200fault/1200benign), CAL2400(1200/1200), VALID3600(1200fault/2400benign),240fault/origin each. Original fault subtypes/domains/behavior remain, with new profiles,seeds,activation phases,nearby magnitudes. Expanded benign variants retain legal calibration/reference offsets, independent noise/quantization, temperature/load/speed ramps and abrupt actuator transitions. Complete physical profiles and seeds disjoint across partitions and all historical CSV/Git/archive/embedded manifests. Old1255 audit excluded from this zero-overlap claim.

Select using NEW TRAIN/CAL only: no plant-detection losses, no integrity-fault losses, zero wrong confident FAULT origins, detection loss<=.0025 separately on TRAIN/CAL; CAL benign<=.005 required. Among eligible candidates minimize CAL benign runs, then TRAIN benign runs, then total detections lost, then smallest predefined index. Prefer zero; no validation feedback. Freeze selected config, sources, manifest, protocol and unchanged SVM before executing any VALID case. Evaluate original and selected refinement once; no validation candidate search. Evaluate frozen SVM-INT default and prior frozen CAL1 threshold with EXACT original41 features, no retraining/rescaling/recalibration. Preserve original A2 streams for fair SVM input.

Report both first and all-runtime fault localization, UNKNOWN, benign assigned origins separately, precision/latency and per-origin losses. Primary VALID hard gates: <=12/2400benign, no plant/integrity detection loss, no wrong fault origins, <=3/1200detection losses. Retain zero-benign/no-loss point if obtained; otherwise only best safe preregistered selected point meeting all gates. No statement of physical/pre-protection sensitivity preservation beyond modeled cohorts: original sensor faults are post-conversion and witness-covered when sampled; this gate can delay or miss PASS-only physical anomalies outside that space.

Compact manifest, audit, selection, summaries, compact case outcomes/frozen SVM reference and validation record; no bulk raw traces. Full regression once if retained: build, compile, tests, diff check,48legacy,64RTL, Hybrid/HETIA and old evidence hashes unchanged.


### integrity_final_unseen

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/integrity_final_unseen/protocol.md` — `file`, lines 1–13

# Final frozen refined-A2 unseen protocol

Freeze the retained benign_alarm_development G2 (three consecutive100ms qualified sensor observations >=0.5), unchanged digital integrity, M2 probes, Triplex, causal origins and DS mathematics. Missing/failed integrity and independent cross-layer/provenance support bypass confirmation exactly as retained. A0 is the original retained Triplex without integrity/M2. Frozen SVM-INT retains its41runtime features, scaler, linear C=.1 model, default threshold0 and previous CAL1 threshold; default is primary, CAL1 secondary. No training or selection.

One cohort,1200faults(240/origin) +600benign. Use the existing original fault-space generator's ten validation-family templates solely as parameter templates, without reading their outcomes; assign all-new profiles,seeds,activation times and sensor magnitudes/drift rates. Keep all120fault cells/family and the first60of120benign cells/family, giving two complete cycles of30benign archetypes. Fixed transformations are in the locked runner. Preserve dormant/transient memory, weak steps, short50ms pulses, AB/ABCpost-conversion corruption, initially-unexcited pump degradation, legal offsets and authorized updates. Independent benign noise/variation and load/thermal/speed profiles remain legal. No subgroup/outcome-based balancing to meet targets.

Audit every historical CSV/Git manifest/archive/profile and embedded JSON/spec manifest, including digital-integrity and benign-alarm TRAIN/CAL/VALID. Require zero configuration AND operating-profile overlap; this stricter independent profile check prevents administrative-ID changes from masquerading as novelty. New seeds must also be disjoint. This is unseen configuration-level evaluation inside the existing simulator fault space, not new physical fault semantics or independent field data.

Record all scientific sources/configs/models and previous artifacts before outcomes; hash newly generated native adapter/executable, complete manifest/seeds, protocol, runner and selection. Build once before lock. Register execution-start marker before physical runs; refuse repeat execution. Exactly one physical run/configuration; evaluate A0, refined A2 and frozen SVM on the same runtime stream. Do not execute alternative G1/G3/G4 choices or select SVM points on outcomes. The original-A2 internal alarm is available only as part of the unchanged refinement computation, not a new selectable comparator.

Stream/process and discard raw run traces. Post-hoc labels may categorize effective/dormant memory, active actuator excitation and misses, never enter inference. Common-mode post-conversion data corruption with intact witness must not be conflated with physical/common-witness failure. Unsampled/no-effect events remain in the denominator. Detection and latency retain the existing alarm-edge scoring. Report fault detection and Wilson95%, per-origin,benign,precision,plant/silent,latency,integrity-observed detection; A2 first/runtime localization/UNKNOWN and wrongfaultorigins. Exact two-sided McNemar A2/A0 and A2/SVM for faults and benign; p=1 when no discordance. CIs/tests are descriptive for deterministic grouped cases.

No rerun/tuning/redesign after outcomes. Full regression once afterward:358existing tests, build,Pythoncompile,diffcheck,48legacy,64RTL; preserve GUI/Hybrid/HETIA/historical evidence and verify all hashes. No commit/push. Retain summaries,manifest,audit,freeze/provenance and compact sufficient statistics only; no bulk traces.


### frozen_robustness

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/frozen_robustness/protocol.md` — `file`, lines 1–26

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


### ieee_multibaseline

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/ieee_multibaseline/protocol.md` — `file`, lines 1–41

# Locked IEEE secondary multi-baseline comparison

Publication name: CLOVER-ECU = exactly the retained final refined A2. No source identifiers, final records, executable or model are changed. Primary final unseen and frozen robustness remain separate frozen evidence.

## Replay eligibility and design
The final unseen retained per-case sufficient statistics do not contain the framewise provider values, raw runtime inputs and temporal feature histories required by new decision methods. Fair replay from those summaries is not possible. Do not regenerate primary outcomes. Instead execute ONE new deterministic secondary cohort, 1,200 faults (240 each Memory, Timing, Communication, Sensor/Control, Actuator) and 600 benign.

Reuse the final protocol's subtype allocations, durations, magnitudes and activation times WITHOUT removing weak, common-mode, dormant, unsampled or unexcited cases. Change operating profile ambient by 0.157 + i*0.0000029 C and speed by 0.379 + i*0.0000059 kph, and replace independent seeds with 3010100003+i*401, 3110300007+i*409, 3210700011+i*419. These fixed perturbations define new configurations rather than a new fault space. No claim of independent fault families. Audit historical CSVs/archives/Git manifests and embedded JSON manifests including primary unseen, robustness and all TRAIN/CAL/VALID records. Freeze the entire manifest before any simulations. Stop on overlap. No evaluation-case rerun or post-outcome selection.

## Observability and trust
Reuse the exact final native executable and original frozen SVM-INT/scaler/default margin>0. Verify final recorded hashes before registration, then all scientific/executable/model hashes before/after execution and regression. GUI, Hybrid/HETIA, final and historical results remain byte-identical.

Every primary backend has access to the same frozen evidence architecture: six runtime provider strengths/availability (timing, communication, memory, sensor/control including Triplex + digital integrity, actuator and plant-response evidence), M2 diagnostics, and 41 runtime features of the original SVM-INT feature extractor. Provider strengths contain the frozen preprocessing, not injected origin, fault labels, plant-truth values or A2 alarm outputs. Plant-response evidence means observable runtime response, not offline propagation labels. Six-stream methods intentionally compress available observables; this is equal provider availability, NOT identical feature representations or a comparison from raw sensors. Integrity is already incorporated in the sensor provider and must not be counted as a second independent DS source. Original Triplex A0 is an architecture ablation, not an equal-observability baseline.

## Authorized fitting and operating-point selection
Reconstruct ONLY the exact original digital_integrity_development TRAIN (3,600 runs) and CALIBRATION (2,400 runs) configurations with the unchanged final executable. No development validation/final/robustness labels select parameters. All original training features precede the unchanged G2 decision gate. For supervised training use identical original SVM frame labels and at-most-eight evenly spaced frames/class/run. These labels are fitting targets only; never inference inputs. TRAIN feature standardization belongs inside supervised pipelines.

Candidate families fixed before TRAIN:
- Threshold OR: reuse available provider >=0.5 and existing unambiguous origin rule, unchanged.
- Plain DS: reuse simple-support combination Bel(A)=1-product(1-e), >=0.5, existing DS origin rule, unchanged. Shared-source dependence limits a probabilistic interpretation.
- Weighted Sum: reuse existing weight vectors (1,1,1,1,1,1) and (2,2,2,1,2,1), normalized over available channels; thresholds 0.04,0.06,0.08,0.10,0.14,0.18. Existing instantaneous contributor localization. New decision uses strict score>threshold to match calibrated strict comparisons; disclose this boundary convention.
- EWMA: z_t=alpha*e_t+(1-alpha)*z_(t-1), zero initial state per channel; alarm on max-channel z > h. alpha in {0.1,0.3,0.6}; h in {0.1,0.25,0.5}.
- CUSUM: S_t=max(0,S_(t-1)+e_t-k), zero initial state per channel; alarm on max-channel S > h. k in {0.05,0.15}, h in {0.25,0.5,1,2}. No Gaussian residual, change-size or average-run-length assertion. State naturally recovers when increments become negative; no alarm-triggered reset.
- EWMA/CUSUM unavailable inputs are zero; no invented evidence; reset only between runs. Sample-domain updates match the frozen 100-ms consumer cadence. They accumulate nonnegative anomaly evidence, not signed raw residuals.
- Logistic Regression: StandardScaler plus balanced L2 logistic regression, C={0.1,1,10}, max_iter=2000, random_state=20261008.
- Random Forest: 100 trees, depth {8,unbounded}, leaf minimum {2,8}, sqrt feature sampling, balanced classes, random_state=20261008, one CPU worker.
- Frozen SVM-INT: exact stored model/scaler/default threshold 0, no fitting/selection.
- Original Triplex A0 and CLOVER-ECU: exact native recorded decisions, including G2 for CLOVER only; no modifications.

For LR/RF candidate thresholds include default (margin0/probability0.5) and smallest strict threshold at CAL benign run-maxima giving empirical 0%,0.5%,1% false-alarm runs. Thresholds and model choice may use CAL only. For each selected WS/EWMA/CUSUM/LR/RF family: require <=12/1200 CAL benign alarm runs where feasible; then maximize fault-run post-onset edge detection, minimize benign, break ties lexically by candidate then ascending threshold. If no eligible point, select minimum benign then maximum detection and explicitly report calibration gate failure. Retain ALL calibration results. Do not apply this calibration to frozen OR, DS, SVM or CLOVER. Lock selected parameters/models before secondary execution.

## Execution and reporting
One physical simulation per secondary case; score all ten methods on identical runtime streams. No retained raw traces. Temporary TRAIN data reduced to fitted models; CAL score tapes deleted after locking; per-case evaluation metrics retained compactly. No final unseen rerun.

Report detection count/rate/Wilson95, per-origin, benign alarms, precision, propagation-conditioned detection/silent misses, median/P95 latency and integrity-observable coverage. Use existing rising-edge detection definition, including pre-onset alarm limitations. Conditional latency and localization denominators must be explicit. LR/RF/EWMA/CUSUM/SVM are binary: localization N/A. Existing OR/WS/DS origin rules are evaluated honestly, not retrofitted with CLOVER causal localization.

Paired CLOVER vs each comparator: both/only CLOVER/only comparator/neither for fault detection and benign alarms, exact two-sided McNemar (p=1 if no discordance), joint-detection faster/equal/slower latency. Report raw and Holm-adjusted p-values over eight equal-observability comparisons separately for detection and benign endpoints. A0 is a separately labeled architecture comparison. Correlated simulator families limit independence/field-risk interpretation. No superiority from unpaired counts or from lower false alarms alone.

Runtime overhead: measure one-pass Python backend CPU time per frame over secondary cases, excluding common features/providers, simulator, logging and metric computation. DS includes its origin calculation. Unchanged native final adapter does not isolate final-A2 core time; mark native A0/A2 overhead not comparably measured. No WCET, embedded throughput, energy or cross-language speed claim.

After reporting, run full unit tests, build, Python compile, diff check and existing48legacy/64RTL checks once. Restore build products, verify all initial preserved hashes. Do not commit/push.


### ieee_origin_rf

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/ieee_origin_rf/protocol.md` — `file`, lines 1–37

# IEEE origin-aware RF: preregistered secondary comparison

CLOVER-ECU remains the exact final refined A2 algorithm. Frozen SVM-INT/scaler/default margin0 is unchanged. The ten-method study remains a qualified system comparison; this study does not retrospectively relabel it strict equality.

## Common input contract, fixed before data execution

`input_schema.json` lists every exported upstream field and every prohibited field. Capture the exact `runtime_observation_t z` passed to final M2/CLOVER, independent C readout, Triplex provider strength/ambiguity/qualification/aligned value, qualified/local sensor evidence, and integrity availability/status/held FAIL. Also expose the frozen six provider strengths, availability and provider support sets. This is the same sensing/protection architecture and full trusted upstream interface, including explicit provenance missing from the old41 representation. No current/previous CLOVER alarm, predicted origin, belief, direct-origin episode state, diagnostic ID, safety state, injection specification or offline plant truth enters RF. Diagnostic-ID/safety/alarm fields in the generic struct are unused by the frozen core and intentionally excluded. Provider support sets are architectural mappings, not estimated fault origins.

RF receives all logged upstream fields except absolute elapsed time. Timestamp fields are deterministically encoded as age relative to current runtime time (negative invalid sentinels retained); add finite masks. This avoids absolute campaign-clock learning while preserving freshness/order information. Append six masked strengths, six availability bits and six support masks; append causal ten-frame and fifty-frame strength means/maxima. No fitted transform, global sequence counter derived from a case index, future window or outcome label. Real scheduler release/execution counters remain trusted runtime inputs. Algorithm-specific temporal state is not copied from CLOVER. Native provider engineering is shared; this is not a raw-sensor-only ML benchmark.

A logging-only adapter is built in /tmp by three insertions into the recorded adapter: function declaration, pre-fusion call for architecture6, and pure CSV writer. Link all frozen detector/provider objects unchanged. Do not rebuild/redesign any frozen core. Before fitting, compare original versus instrumented executable on24 predetermined authorized TRAIN cases (four per origin including NORMAL, evenly spread within each class). Require exact native metrics, physical/runtime hashes and all original evidence/audit/SVM-feature streams. Stop on failure; never repair a detector using secondary outcomes.

## Training, calibration and one challenger

Use exactly `benign_alarm_development` TRAIN2400 and CAL2400 (each1200fault+1200benign), the cohorts used to select the retained CLOVER confirmation rule. Original development VALID, primary unseen, robustness and the ten-method secondary outcomes are excluded from fitting/selection. Origin classes: NORMAL, MEMORY, TIMING, COMMUNICATION, SENSOR_CONTROL, ACTUATOR.

TRAIN targets: injected origin while the fault is active now or at the immediately preceding99ms, otherwise NORMAL, matching the established short sampled-effect labeling convention. Use up to16 evenly spaced frames per present class/run, balanced class weights. Labeling is supervision only; no fault time, model name or origin is passed to inference. Dormant/unobservable active faults remain in the training target rather than being removed by plant truth. CAL class labels evaluate/select operating points but never fit trees. Unseen labels are offline scoring only.

One RF family, four predefined hyperparameter candidates:200 trees, max_depth {12,None}, min_samples_leaf {4,16}, max_features=sqrt, class_weight=balanced, random_state20261009, n_jobs1. No subsequent grid expansion. All six classes must be present. No independent ML-assisted CLOVER or candidate detector copy.

Alarm score =1-P(NORMAL); strict score>threshold. For each candidate choose the maximum CAL benign-run score as threshold: empirical zero CAL benign runs, matching the retained CLOVER zero-benign operating point on this SAME cohort (and tighter than its hard0.5% gate). If this sacrifices recall, report it; do not relax after outcomes.

Given an alarm, normalize the five fault-class probabilities by total fault probability. Publish the top fault origin only if conditional maximum>=confidence and top-minus-second>=margin; otherwise UNKNOWN. UNKNOWN never suppresses the binary alarm. Confidence candidates {0.5,0.7,0.85,0.95,0.99,1,1.000001}; margins {0,0.1,0.2}. The last confidence is an explicit abstain-all fallback, not hidden successful localization. Require zero CAL first-alarm and runtime wrong confident origins on fault runs. Select jointly among candidates/thresholds: maximize detected CAL fault runs, then correct first-localized cases, then localized runtime samples, then fixed candidate order, lower confidence and lower margin. Preserve all candidate results, including abstention and detection losses. This is a strict empirical risk constraint, not a probability guarantee.

## Locked new secondary cohort

Exactly1800 cases:1200faults,240/origin;600diverse benign. Retain the primary final protocol's subtype/behavior/activation/duration/magnitude allocation, including dormant/transient memory, weak/short/common-mode sensor corruption and unexcited actuators. New profile perturbations relative to final design: ambient +0.269+i*0.0000033 C; speed +0.457+i*0.0000061 kph. Seeds3310100003+i*421,3410300007+i*431,3510700011+i*433. These are new configurations, not new independent fault mechanisms. Audit all current/Git/archived/embedded historical manifests, explicitly including ieee_multibaseline. Freeze manifest and protocol before parity/TRAIN; freeze selected model/thresholds before SECONDARY. Execute one physical simulation per secondary case and all three methods on its streams. No rerun or post-result tuning.

## Endpoints and evidence retention

Report binary fault detection using existing post-onset rising-edge convention, Wilson95CI, per-origin detection, benign alarm runs, precision, plant-propagating detection/silent misses, conditional median/P95 latency. Report first-alarm localization (origin AT first post-onset alarm, not a later successful localization): coverage, conditional accuracy, wrong and UNKNOWN. Report runtime localized accuracy, wrong runs/samples, UNKNOWN on all alarm samples, preserving the existing run-origin scoring convention even during post-fault alarm recovery. Separate benign-origin assignments.

Compare localization both on each method's own detected fault cases and on the common detected set; UNKNOWN remains in coverage denominators and is not removed to fabricate perfect accuracy. Report six true run classes versus NORMAL/no detection, five origins and UNKNOWN for first-case confusion; report alarm-sample confusion by run origin separately. These are not an active-frame multiclass accuracy score. Binary SVM has no localization. Use exact paired McNemar for CLOVER vs RF (primary) and frozen SVM (reference), fault and benign endpoints, with exact counts and joint-detection latency. Paired first-origin-correct counts on common detections are a separate localization endpoint. Grouped simulator statistics are descriptive; no equivalence/superiority theorem.

Retain one compact compressed archive of lossless upstream packets and shared provider values, plus separately named RF probabilities/CLOVER outputs/SVM margins; labels stay in the manifest, not RF inputs. Transpose numeric arrays for compression. This curated runtime-boundary evidence permits later causal replay; delete bulk simulator/plant traces each run. Keep model/schema/locks, provenance and summaries. Never use output arrays as future feature inputs. Do not retain TRAIN/CAL bulk tapes after selection; retain exact manifests/hashes, fitting record and calibration grid.

Run full tests/build/compile/diff check,48legacy,64RTL once at end; preserve old files, scientific objects, frozen models/results, Hybrid/HETIA and GUI. No commit/push.


### Qualification: results/ieee_multibaseline/observability_scope.md

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/ieee_multibaseline/observability_scope.md` — `file`, lines 1–12

# Pre-evaluation observability qualification

This clarification is made before any secondary outcomes. It does not change any parameter, method, selection rule, input, cohort or execution.

There are two backend strata, not a claim of identical sufficient information for all algorithms:

1. **Full-runtime-input comparison:** CLOVER-ECU and frozen SVM-INT, Logistic Regression and Random Forest share the runtime sensing/integrity architecture. All three learned methods have the identical original 41-feature interface, including explicit integrity availability, status and held FAIL. CLOVER additionally maintains its documented runtime temporal/provenance state; this is part of its method, not injected metadata.
2. **Provider-strength comparison:** Threshold OR, Weighted Sum, Plain DS, EWMA and CUSUM use the frozen six-channel evidence interface. It includes digital integrity FAIL through the sensor provider and M2 through memory. However this reduction does **not** preserve every raw feature or explicit PASS/provenance field. These methods are legitimate classical algorithms on common provider evidence, but their comparison with CLOVER does not isolate decision mathematics under an identical sufficient feature representation. In particular benign-alarm differences may reflect discarded provenance, not an inherently inferior algorithm.

Original A0 remains a third, architectural-ablation stratum. No method is deprived of an entire sensing architecture in the backend comparisons, but "equal observability" must be qualified by the representation actually consumed. Do not call the strength-only comparisons strict full-information equality. Do not invent status-to-mass mapping or inject CLOVER's confirmation rule merely to increase comparator fairness on paper. No unseen outcome informs this qualification.

The preregistered Holm correction over eight backend comparisons is conservative regardless of this interpretation; it does not establish representation equivalence. Read any shorthand "equal-observability" in generated tables/protocol statistical labels subject to this qualification. For the strongest full-runtime comparison, use LR/RF/frozen SVM versus CLOVER. Negative findings and all classical outcomes remain reported.

### Qualification: results/ieee_origin_rf/methodology.md

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/ieee_origin_rf/methodology.md` — `file`, lines 1–15

# Interpretation and replay boundaries

CLOVER-ECU is still frozen refined A2. The final primary unseen, robustness and ten-method secondary studies are not overwritten, pooled or relabeled. This is a new origin-aware secondary challenger, selected only on authorized TRAIN/CAL.

The common input schema closes the previous audit's missing-input gaps: full acquisition/delivery timestamps and validity, memory shadow/probe status, scheduler event ledger, actual actuator responses, ambient/control context, independent-C readout and explicit integrity status. Both methods share the unchanged provider engineering. RF also receives pre-fusion provider support/qualification; these are runtime evidence, not CLOVER's predicted fault class. It never receives DS masses, final alarms, direct-origin memory, injected labels or offline propagation as input. The frozen SVM remains a binary41-feature reference, not a new multiclass or full-schema challenger.

RF uses174 features derived from67 packet fields and shared provider streams. Absolute timestamps become ages and absolute elapsed time is not a feature. This does not eliminate all context correlations: legitimate scheduler counters, thermal values and workloads can still correlate with scenario construction. The two methods have different temporal representations and learning/decision rules. Access to the same upstream information does not establish equal model capacity or field generalization. In particular, an RF positive on an unexcited fault does not by itself establish a new health observable.

The empirical CAL targets are zero benign alarm runs and zero wrong confident origins, with UNKNOWN permitted. These match the retained CLOVER's observed CAL outcomes on the same cohort, not a population-risk guarantee. No requirement to force high localization coverage or a detection target is imposed. An abstain-all origin operating point remains reportable as such.

Origin labels fit trees only on TRAIN. CAL labels are used only for the preregistered parameter/threshold selection; secondary labels only for scoring. The active/previous99ms frame target is a sampled-effect labeling convention. Dormant/unobservable faults are not removed using plant truth, and post-fault lingering evidence may not align with active-frame targets. First/runtime localization metrics therefore explicitly retain the prior run-origin diagnostic convention; they are not generic per-frame active-fault classification accuracy.

`runtime_evidence.tar.gz` contains one NumPy member per secondary run. The allowed input arrays are `upstream`, `strength`, `available`, `origin_support`; `svm_features` is the unchanged reference representation. Arrays `rf_probability`, `clover_alarm`, `clover_origin`, `svm_margin` are **outputs**, stored separately within the member for auditing. They MUST NOT become feature inputs. Numeric input arrays are transposed for compression, retain float64 precision, and share the packet timestamp axis. Ground-truth labels reside only in the manifest/case scoring files. No bulk simulator/plant trace is retained.

Future replay on these now-seen cases is retrospective evidence, not another unseen evaluation. The selected model/schema/thresholds, exact instrumented adapter and linked original object hashes, instrumentation parity records, manifest/overlap audit and calibration grid document provenance. No physical tamper resistance or additional sensor architecture is claimed.

## Exact offline propagation implementation


### Exact source: propagation_monitor_step

**VERIFIED FROM SOURCE.** `src/propagation_monitor.c` — `propagation_monitor_step`, lines 51–79

```text
  51: void propagation_monitor_step(ecu_state_t *state, const ecu_state_t *reference)
  52: {
  53:     propagation_monitor_t *p = &state->propagation;
  54:     unsigned int now = state->time.time_ms;
  55:     if (!p->enabled) return;
  56:     p->reference_coolant_c = reference->plant.coolant_temp_true_c;
  57:     p->coolant_deviation_c = state->plant.coolant_temp_true_c - p->reference_coolant_c;
  58:     if (p->injection_ms < 0) return;
  59:     /* These are FINAL applied commands and realizations, after safety overrides. */
  60:     first_seen(&p->actuator_command_ms, now, commands_differ(state, reference));
  61:     first_seen(&p->actuator_realization_ms, now,
  62:         fabsf(state->actuators.pump_actual - reference->actuators.pump_actual) > COMMAND_EPSILON ||
  63:         fabsf(state->actuators.fan_actual - reference->actuators.fan_actual) > COMMAND_EPSILON);
  64:     /* The plant stored at t is the result of the preceding integration step. */
  65:     first_seen(&p->plant_ms, now, fabsf(p->coolant_deviation_c) >= PLANT_MANIFESTATION_C);
  66:     first_seen(&p->detector_ms, now, state->detection.alarm_active && !reference->detection.alarm_active);
  67:     first_seen(&p->safety_response_ms, now,
  68:         state->safety.requested_state > reference->safety.requested_state);
  69:     first_seen(&p->safe_state_ms, now,
  70:         state->safety.current_state > reference->safety.current_state &&
  71:         state->safety.max_cooling_active);
  72:     /* Integrate only completed intervals using the previous observed sample. */
  73:     if (p->last_observation_ms >= 0 && p->previous_unsafe) {
  74:         p->unsafe_exposure_time_ms += now - (unsigned int)p->last_observation_ms;
  75:     }
  76:     p->previous_unsafe = state->plant.coolant_temp_true_c >= ECU_CRITICAL_COOLANT_TEMP_C;
  77:     p->unsafe_state_entered = p->unsafe_state_entered || p->previous_unsafe;
  78:     p->last_observation_ms = (int)now;
  79: }
```

Source/selection/identity audit: `scripts/run_integrity_final_unseen.py` — `file`, lines 1–159.

Source/selection/identity audit: `scripts/run_frozen_robustness.py` — `file`, lines 1–133.

Source/selection/identity audit: `scripts/run_ieee_multibaseline.py` — `file`, lines 1–242.

Source/selection/identity audit: `scripts/run_origin_rf.py` — `file`, lines 1–212.

Source/selection/identity audit: `scripts/run_digital_integrity.py` — `file`, lines 1–170.

Source/selection/identity audit: `scripts/run_benign_alarm.py` — `file`, lines 1–169.

Source/selection/identity audit: `python/virtual_ecu/ieee_baselines.py` — `file`, lines 1–45.

Source/selection/identity audit: `python/virtual_ecu/origin_rf.py` — `file`, lines 1–60.

Source/selection/identity audit: `scripts/report_comparative_benchmark.py` — `file`, lines 1–88.

## Retained Triplex lineage (historical, not final A2 tests)

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/clo_dsf_current/triplex_only_findings.md` — `file`, lines 1–13

# Final triplex-only validation: promotion rejected

All 480 previously locked fault-validation cases completed once, A0/A1 only, with identical physical observations. The completed 120 benign cases were reused. Outcomes were inspected only after completion. No scientific source, thresholds, sensor model, fusion, localization, locked manifest or GUI bytes changed. A2 remains permanently rejected and was neither linked nor evaluated. No unseen holdout, commit or push.

Original space: A0 347/400 (86.75%, Wilson 83.08–89.73%); A1 361/400 (90.25%, Wilson 86.95–92.79%). Expanded space: A0 383/480 (79.79%, Wilson 75.97–83.14%); A1 426/480 (88.75%, Wilson 85.61–91.27%). The primary >=91% gate fails: three further original detections would have been required. No automatic promotion at >90%.

Original paired comparison: both347, A0-only0, A1-only14, neither39; exact two-sided McNemar p=0.0001220703125. All fourteen gains are AB common-mode; weak-step/pulse subgroup gains overlap this category and are not independent additional gains. No original detections lost. Expanded: both383, A0-only0, A1-only43, neither54; p=2.2737367544323206e-13.

AB common-mode improves 10/24 to24/24. Original plant-propagating detection improves170/180 to180/180, silent misses10 to0. Expanded plant detection185/204 to195/204, silent misses19 to9. Both methods have0/120 benign alarms, zero wrong confident origins, and100% first and localized-runtime accuracy. UNKNOWN runtime samples653 for each method, from existing uncertainty semantics. Timing80/80, communication80/80 and effective memory54/54 unchanged.

Limitations: original actuator detection50/80, including33/33 initially excited and17/47 initially unexcited; memory75/80; sensor76/80. Global ABC remains4/16, C-only29/32. Original P95 latency increases29.9s to34.6s when additional detections are included; this does not demonstrate latency improvement. Expanded P95 increases39.6s to42s.

No further refinement. A1 is not promoted; CURRENT A0 remains retained. Not ready to freeze triplex for a new unseen holdout. Full regression was conditional on passing retention and was therefore not run. Detailed original/expanded metrics and subgroup denominators are in triplex_only_summary.csv and triplex_only_subgroups.csv. Per-case sufficient statistics are retained without raw trajectories. Previous development and rejected-latch artifacts remain untouched.

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/clo_dsf_current/symmetry_findings.md` — `file`, lines 1–33

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

**VERIFIED FROM EXPERIMENT ARTIFACT.** `results/clo_dsf_current/triplex_freeze_record.md` — `file`, lines 1–13

# Triplex freeze record

Retained implementation is the exact validated A0/A1 comparison harness in scripts/run_clo_dsf_triplex.py, independent C model, triplex consistency provider and classical revised core. A1 is the evaluated Triplex; virtual_ecu_v7_3 alone is the CURRENT baseline, not the Triplex entry point. The unseen entry point is scripts/run_clo_dsf_triplex_final_unseen.py. Do not silently substitute the baseline executable for A1.

Rejected experimental selectors removed by restoring the original classical core/header, without changing classical behavior. Independent C/provider files unchanged. A shared physical-template utility was extracted unchanged (2400specifications equal). Rejected latch/binary/alternative-fusion source and experiment scripts/tests removed from the working tree; historical negative results retained. No detector development or fitted parameters.

Freeze regression:330 tests PASS, including Triplex symmetry and C independence; forced build, Python compile,git diff --check PASS;48legacy and64RTL PASS; Hybrid/HETIA historical evidence unchanged.150 previously seen TRAIN simulations replayed solely as cleanup equivalence: all A0/A1 sufficient-statistic rows exactly equal before/after cleanup. Not a new validation or unseen study.

All previously deleted historical/frozen result records restored, including historical manifest and identity registry. No result deletion staged. GUI preset byte-preserved and excluded from staging. Existing current-directory negative-study findings remain historical; symmetry_findings.md identifies the retained91.04% candidate.

Idle pump-performance degradation is unobservable in the modeled architecture until actuator excitation occurs.

Commit and push the freeze before generating primary/secondary unseen manifests. New evaluation will use the recorded full SHA and freeze hashes. Never rerun for performance or tune after outcomes.
