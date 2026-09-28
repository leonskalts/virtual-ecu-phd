# FINAL unseen protocol: retained CURRENT only

Development is closed. No rejected provider/model is linked or loaded. Use the
recorded Git commit and its exact virtual_ecu_v7_3 binary; frozen cfg and Weighted
Sum choice6 unchanged. No algorithm selection, tuning or case replacement.

1500 cases,1200 faults/300 benign,240 each MEMORY/TIMING/COMMUNICATION/
SENSOR_CONTROL/ACTUATOR. Ten fixed families; each24 per origin/30benign.
The design is deterministic from master seed982451653 (explicit affine primary
and reference seed schedules, no random manifest selection). All parameters and
physical profiles are in campaign_manifest.csv. Every120s mission has100ms cadence.

Sensor per family:4primary slow,4reference slow,4common-mode slow,6weak steps,
6pulses. New drift times[14900,35300,58700,76900]ms and common-mode[21100,47900]ms;
new signed magnitudes, both sensor members,100/200ms or permanent weak steps,
200/700ms or persistent pulses. No common-mode exception from denominator.
Memory keeps valid stuck bits/polarities/bit-flip semantics and all three behaviors;
new activation phases and[500,900,1700,2700]ms finite windows; intermittent
on/off[600/1400,900/1600,1200/1800]ms. Effective/dormant categories are post-hoc
register-shadow consistency; dormant probes may detect a value-consistent cell.
Actuators include pump scales[.989,.971,.937,.873,.769,.619],fan stuck off, all
three behaviors,one quarter predefined cold low-load profiles. Actual initial
command at first active observation determines initially-excited/unexcited;
throughout-window excitation also reported separately. No-excitation is not an
exclusion. Timing/communication include finite[900,3100,7900,14900]ms disturbances
and valid transient deadline misses. Discrete fault types/bits can recur.
Benign per family six cold cases and24 varied profiles, normal command transitions,
legal calibration updates, bounded independent noise and brief disagreement.

New profiles differ from all recovered historical profiles. Historical registry
preserves32k+ profile identities/34k+ configuration identities from working files,
all Git manifest/profile blobs and surviving overwritten scratch manifests/audits,
including TRAIN/CALIBRATION/VALIDATION and prior holdouts. Audit disjoint complete
physical profiles, which prove zero exact configuration overlap despite older
inconsistent hash schemas. No claim covers irrecoverable unrecorded experiments.

Write/hash manifest,protocol,audit,scientific files,seed and commit before execution.
Run every case exactly once; checkpoint summaries before postprocessing. Abort and
record genuine collector/software errors separately, never rerun or replace cases.
Poor metrics are valid final results. No bulk traces; zero representative traces
selected. Temporary run files are deleted after scoring.

Evaluate CURRENT, frozen Fair Weighted Sum,Simple OR,Plain DS,v7.2 CLO-DSF,Hybrid
on identical observations. Timing Monitor only on TIMING. Counterfactual hidden
plant data is used only by unchanged offline propagation scoring, never inference.
Detection is any post-onset alarm, including after clearance; report pre-onset
alarms separately. Benign alarm is any alarm during the whole mission. Latency
is activation-to-first-post-onset alarm, median/P95 among detections. Run-level
precision is detected fault runs/(detected fault runs+benign alarm runs).
Plant manifestation threshold/semantics unchanged. First-detection accuracy among
localized detections and all-runtime accuracy among localized alarm samples are
separate; UNKNOWN/coverage include all alarms, including benign/pre-onset samples.
Wilson95 intervals are descriptive case-level intervals for grouped deterministic
cases, not independent population sampling guarantees. Exact two-sided McNemar is
the binomial discordance test; no superiority claim from marginal percentages alone.

Report overall detection,consequence-conditioned detection,benign alarms,
localization reliability and latent/unobservable categories separately. Do not
substitute one metric for another or make certification claims. Full pre-freeze
regression must pass before commit/push and this lock. Verify all scientific hashes
and GUI after execution. Results reference that exact pushed freeze commit.
