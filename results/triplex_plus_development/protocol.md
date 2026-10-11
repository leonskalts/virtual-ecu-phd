# Triplex-Plus development protocol — preregistered

Retained Triplex commit a340ca5cf0473d7dc572f7cd63e44fbc25b175a7 remains unchanged.
Prior comparative unseen is development/reference knowledge only; no individual
historical case tuning. Protect its artifacts, all frozen scientific sources and GUI.
No unseen, commit or push. New lightweight separately ablatable providers only.

One new3150-case,21-physical-family campaign: TRAIN10families1500(1200fault/300benign),
CAL5families750(600/150), VALID6families900(720/180),144/origin in validation.
Every family retains24each MEMORY/TIMING/COMMUNICATION/SENSOR_CONTROL/ACTUATOR and
30benign. A/B/AB8each, rotating slow drift/weak step/pulse. Short50–900ms pulses,
off-grid fault starts, signed. Memory100–2300ms finite durations, varied100ms-valid
phases, dormant/effective and intermittent/permanent. All actuator templates and
cold contexts retained. Benign startup, load changes, target updates, independent
noise, ramps, signed legal100ms B excursions included. No composition change for gains.
All profiles/seeds/config identities audited against existing files, Git and archives.

M0 is the exact retained ~1000ms mean phase-sweeping schedule. M500 alternates400/600ms,
M250 alternates200/300ms on the unchanged100ms ECU scheduler. Each variant receives
ONLY its own status, not union with M0. Atomic saved-value/write0/read/write65535/
read/restore/read transaction:7operations, original backend/address, no injector
metadata. Assert register restoration every probe. Shared experiment executes all
observer schedules, but reports per-deployed-architecture counts and isolated host
cost. The controller/plant cannot run between the transaction's operations.

S0: A stays functional0,100,... B33,133,... C66,166,... each100ms. B uses the existing
redundant_temperature model; C uses the unchanged diagnostic_temperature model with
identical calibration/noise/lag parameters. A is NOT duplicated or resampled for the
candidate. Baseline observers have their own old-phase diagnostic state. New physical
samples use existing within-integration-step interpolation ONLY inside the sensor
model; runtime consumes acquired readouts chronologically and never uses A(now) to
align an earlier B/C sample. Decisions still occur at100ms detector ticks, never
report fictitious sub-tick detection latency. Functional control sees no new data.

Alignment: six actual readout timestamps/member, continuous100ms provenance. Theil–Sen median of the ten pairwise slopes
from five samples PRECEDING the newest acquisition (400ms span), qualified by
existing2.5C/s qualification. Causal projection age<=100ms. Extra uncertainty
u(a)=2.5a+1.5a^2 C, a in seconds. Six of ten slopes span>=.2s, so
existing +/- .1C sample uncertainty bounds median slope error by1C/s. Existing
3C/s^2 curvature over at most.5s slope age adds1.5C/s; future curvature adds1.5a^2.
For a pair use sign(delta)*max(0,abs(delta)-u_i-u_j), closest-to-agreement point.
Existing noise/quantization bounds and FAST/SLOW thresholds remain unchanged.
Invalid/gapped/high-slope/high-age histories yield ignorance. A pair may update only
when BOTH actual endpoint timestamps advanced, so a held100ms excursion never becomes
multiple persistence witnesses. Aggregate acquisition gaps are33/33/34ms; qualified
pair evidence is not guaranteed every33ms. No claim of equivalent33ms sampling of
an individual sensor. MAX pair evidence remains ONE correlated DS source.
Core candidate AB uses the conservatively aligned B value at the A epoch, while
extra AC/BC/AB pair evidence retains its true update epoch. Old core, DS rule, global
thresholds and causal localization are unchanged. Ambiguity uses interval-aware
pair disagreement with the existing.90C bound. No phase-specific fault threshold.

TRAIN/CAL all six physical ablations A0,M500,M250,S0,S500,S250 on identical runs.
Memory selection: slowest rate capturing>=95% of faster rate's paired gain on BOTH
TRAIN andCAL, provided benign<=1%,zero wrong-origin runs and no effective-memory,
timing or communication loss. Otherwise250 if eligible; if neither eligible, useM0.
Stagger extension eligible only if same safety gates pass both partitions, critical
origins do not regress, and it adds CAL detections over selected memory alone.
Prefer simpler architecture on ties. All four requested A0,A1,A2,A3 ablations still
reported on validation, including rejected diagnostic variants as negative controls;
only the preselected eligible architecture can be V2.

Fresh SVM receives same selected final qualified providers: six strengths,six
availability flags, six causal1s running means and six causal1s maxima. Missing
observations excluded from means. TRAIN labels permit fault/benign only; a label
covers a fault active now OR in the immediately preceding100ms delivery bin, to avoid
mislabeling delayed diagnostic batches. No runtime labels/times/scenario IDs/magnitude.
Up to8uniform samples/class/case, StandardScaler fitted TRAIN, class_weight=balanced.
Predefined family linearC=.1,linearC=1,RBF C=1 gamma=scale; threshold0. Select maximum
CAL run-level balanced accuracy, then recall, then lower complexity. No broad search.

Only if the selected A3/eligible architecture trails this fair SVM by>=3/600 CAL
faults, implement ONE OQ-SET stage. TRAIN-only per-provider empirical p(e|benign),
p(e|fault), Laplace smoothing1, fixed common bins [0,1e-6,.01,.025,.05,.1,.2,.35,.5,.75,1].
Unqualified observations provide no increment. Per-stream S=max(0,decay*S+LLR), cap32;
LLR clipped[-4,4]. Fixed CAL grid decay[.8,.95,.99], GLOBAL boundary[4,8,12]. Reject
settings exceeding1%benign or any confident wrong-origin run on either TRAIN/CAL.
Select highest CAL recall, then lower benign count, then lowest decay/boundary order.
Rescue affects detection only; if frozen core is not alarmed, origin UNKNOWN. Never
synthesize an origin or alter localization thresholds. Retain stage only if it adds
CAL detections without critical-origin losses. If selected, fresh final SVM also
receives the six normalized cumulative scores in addition to the24 causal features,
and its same three-model family is fitted on TRAIN, selected on CAL once. No iterative
rescue to win against the enhanced SVM. If gap condition is not met, no OQ-SET.

Freeze all provider source, selected rate, optional likelihood tables/decay/boundary,
SVM model, feature and manifest hashes before untouched VALIDATION. One validation,
no post-result redesign. Promote only raw detection>SVM, benign<=1%,plant>=99%,zero
wrong confident runs,no timing/comm/effective-memory regression. Desired+1pp not forced.
Report matched detections/McNemar, all subgroup gains/losses and component incremental
contributions. UNKNOWN is separate from wrong confident localization. Unexcited
pump-performance faults remain unobservable. Wilson/exact tests descriptive for the
deterministic grouped design. Same existing post-onset rising-edge scoring; report
late/non-specific credits honestly. One physical experiment per case for all ablations.

Raw run CSVs deleted after streaming. Temporary causal feature tapes permit fitting
and safe replay without re-running physics; remove them after final accounting.
No bulk traces in results. Keep compact summaries/manifests/locks/models and findings.
Overhead: transaction/readout counts, alignment state and isolated host timing using
TRAIN scenarios only, no hardware WCET claim. Candidate-focused qualification,
chronology, symmetry/independence tests before outcomes. If promoted, full regression
(build/compile/alltests/diff/48legacy/64RTL/Hybrid/HETIA/Triplex symmetry/C independence).
