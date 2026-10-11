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
