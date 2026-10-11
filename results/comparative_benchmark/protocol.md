# Comparative benchmark preregistration

Frozen HEAD a340ca5cf0473d7dc572f7cd63e44fbc25b175a7. No retained scientific file,
provider, control/plant/fault or GUI edit. Existing paired observer harness executes
CURRENT and TRIPLEX on one physical scenario. Read-only instrumentation exports the
six provider strengths, availability, and instantaneous origin-support subsets
before causal suppression. Full-state CURRENT equality with historical classical
source is still asserted every sample. Inference receives no truth/labels/future.

C1 exports existing CURRENT evidence; C2 exports final TRIPLEX evidence, with max
AB/AC/BC contributing ONE sensor provider. Sensor qualification uses the EXISTING
five-sample absolute-slew startup rule; independent qualified acquisition, forecast,
redundancy or delivered-sample inconsistency remains immediately usable. Other
provider availabilities are unchanged. No origin precedence, remembered origin or
Triplex ambiguity veto is given to conventional backends. Both input contracts
include provider temporal preprocessing (FAST, SLOW, forecast and active diagnostic),
so these are fusion comparisons, not comparisons against raw-sensor algorithms.

Backend contract: immutable monotone timestamps, six [0,1] strengths, six availability
flags, six instantaneous origin subsets. Missing strength is masked and its mask is
explicit. Actual available healthy zeros remain in normalized denominators.
Origin order MEMORY,TIMING,COMMUNICATION,SENSOR_CONTROL,ACTUATOR. Plant evidence is
uninformative about origin. Delivered sensor evidence without local acquisition
support means {COMMUNICATION,SENSOR_CONTROL}, not a forced singleton.

OR: existing .5 provider criterion, any available provider. Localize only one
unambiguous qualifying origin; otherwise UNKNOWN. No fusion temporal state.
Weighted Sum: sum(w*available*e)/sum(w*available), zero score if none available.
Predeclared families weights [1,1,1,1,1,1] or [2,2,2,1,2,1]; thresholds
.04,.06,.08,.10,.14,.18, inherited historical baseline grid. Global choices only.
Conventional localization uses dominant instantaneous contribution >=.55 of total,
margin>=.15 and singleton provenance; otherwise UNKNOWN. No causal/temporal rules.
Plain DS: m(ABNORMAL)=e,m(Theta)=1-e; unavailable providers vacuous. Classical
Dempster gives detection belief 1-product(1-e), alarm >=.5. Origin masses support
instantaneous provider subsets; classical normalized conjunctive combination,
pignistic top>=.55, margin>=.15, ignorance<=.5. Total conflict abstains. No temporal
fusion, causal suppression, remembered origin, architectural-specific veto or
special C handling inside DS. C2 contains C-derived evidence supplied externally.
Zero anomaly is ignorance, not evidence of health. No deliberate discount handicaps.
SVM: twelve features (six masked strengths plus six availability bits); no timestamp,
scenario identity, magnitude, injected label, origin or future in runtime features.
Predeclared family: linear C=.1, linear C=1, RBF C=1 gamma=scale; class_weight=balanced,
StandardScaler fitted TRAIN only, decision threshold zero. Detection only; localization
NOT PROVIDED. Existing isolated sklearn installation; no production dependency.
TRAIN samples up to eight evenly spaced active and eight inactive frames per run,
labels used solely in offline fit. All benign frames label0. Exact fault-active labels
include dormant/unexcited states; contradictory observations remain legitimate limits.

Reuse complete multi-rate development TRAIN1200/CALIBRATION750 manifests only;
replay them through frozen 100ms Triplex, never rejected multi-rate observers. No
previous validation/unseen outcomes used for fitting, grid, feature selection or
cohort design. Physical templates and historical manifests are allowed for exclusion.
Selection independently for C1/C2: minimum CAL benign alarm runs, then maximum macro
fault recall, then lower P95 latency, then candidate order. No optimization on hidden
plant effects or localization. No retuning after CAL. Validation is a test, not selection.

Fresh VALIDATION750=600fault+150benign,120/origin, five physical groups. After it,
seal method_freeze.json with model/code/data hashes. Generate ONE UNSEEN1500=
1200fault+300benign,240/origin, ten groups, seed formula scenario1733000011+173u,
B1793000021+179u,C1831000033+181u, u=10000+i. Validation u=i. Distinct profiles, seeds,
epochs/magnitudes; hard cells kept. A/B/AB80 each, ramp/step/pulse80 each unseen.
All memory bit/polarity/behavior templates and cold actuator contexts retained.
No result-driven subgroup changes. Historical manifests, nested archives, Git blobs
and scratch manifests audited; benchmark TRAIN/CAL/VALID also explicitly audited.
Lock unseen manifest, hash and seed before any unseen execution. Execute once; no
poor-result reruns. Document any execution/collector failure separately.

Metrics: existing post-onset rising alarm edge, benign any alarm, counterfactual plant
manifestation for offline scoring only; latency among detected cases, plus paired
latency among jointly detected cases. First-detection localized accuracy and coverage,
all-alarm samples including benign/pre-onset for wrong origin, UNKNOWN abstention.
SVM localization is NOT PROVIDED, not an accuracy of zero. Wilson95 and exact paired
McNemar (two-sided binomial discordance) descriptive for deterministic grouped designs,
not population-generalization guarantees. Report pre-onset alarms separately. No
single-metric ranking. Common missed cases do not by themselves prove no physical
information exists; distinguish evidence-zero and evidence-positive misses.

Raw CSVs deleted after each scenario's read-only replay. Training keeps only sampled
feature matrix temporarily; final model serialized with manifest and hash. No bulk
raw traces; zero representative traces planned. Retain compact per-case sufficient
statistics for paired audit and reconstruction, summaries and manuscript table.
Full regression once at end, binaries restored to initial bytes. Preserve all old
final result hashes, Hybrid/HETIA/legacy evidence and GUI. Never commit/push.
