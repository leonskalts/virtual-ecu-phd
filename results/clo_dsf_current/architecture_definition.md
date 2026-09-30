# Final triplex temporal-consensus refinement protocol

One fresh2400-case development campaign.16 distinct physical families,150 each:
TRAIN8families1200cases;CALIBRATION4families600;VALIDATION4families600. Per family
20faults EACH MEMORY,TIMING,COMMUNICATION,SENSOR_CONTROL,ACTUATOR in ORIGINAL space,
20additional sensor-domain faults involving C,30benign. VALIDATION original400faults
(80each origin),expanded480faults,120benign. A/B/AB original sensor cells7/7/6;
expanded adds C8,ABC4,AC4,BC4. All original actuator cells sampled across prior24
including fan and pump, all behavior modes and initially unexcited cases. Faults
are not removed to improve percentages. Cases/families/seeds/profiles new and disjoint.
Prior validation is development knowledge, never reused as this validation.

A0=frozen CURRENT; A1=previous triplex; A2=A1+ONE consensus latch. Sensor C physical
model and parameter ranges unchanged; no new sensors,plant model,ML,excitation,fusion
rule or global threshold changes. A0 and A1 observer core/provider code unchanged.
Every variant observes the same physical simulation. State equivalence A0/frozen
classical asserted every sample. Historical miss audit uses TRAIN/CALIBRATION only.

Latch uses three causal acquisition increments (A,B fresh and C<=100ms old,each
successive acquisition100ms apart). C RAW increments avoid projection overshoot.
Startup must satisfy the existing5-acquisition A qualification and triplex C gate.
For candidate member i and peers j,k, innovations x=delta_i-delta_j,y=delta_i-delta_k
must have same sign and both exceed existing FAST envelope .40+1.2*.1=.52C; peers'
increment difference must be<=existing .40C floor. Strength=min(1,max(0,
(min(abs(x),abs(y))-.52)/2)), reusing existing2C evidence scale. All parameters fixed
before new outcomes. No extra independent DS vote: MAX with existing triplex sensor
strength feeds ONE sensor channel. Single-versus-pair member ambiguity remains.

Hold peak corroborated strength until seed_time+300ms inclusive (four100ms samples),
reusing existing FAST horizon. Same-cut recovery edges can raise the peak but NEVER
renew expiry; competing cuts do not accumulate. Expire to zero; existing classical
DS temporal mass decays normally. Invalid input clears the latch. No artificial
fault-origin labels or physical truth. This can only recover sufficiently strong
short evidence; brief legal deviations may be indistinguishable and must be tested.

Benign workload includes cold startup,independent sensor noise,legal target changes,
load/speed/ambient variation,natural actuator transitions and temporary A/B/C
sensor disagreement. Added impulses use A .30C, B/C .35 or .90C,100/300ms signed
excursions. Original benign perturbations are disabled for these cells to avoid
unintended overlapping sensor impulses; physical ramps/noise/target changes remain.
A+B common-mode and original independent drifts,weak steps,short pulses and shifted
activation phases retained. Original and expanded populations reported separately.

No fit/search on new TRAIN/CALIBRATION; audit only. Freeze all scientific hashes
before benign VALIDATION. Run120 benign validation cases FIRST. Gate requires
A2 alarm-run rate<=1%,wrong confident origins0,no additional cold-start alarm runs
relative to A1. If gate fails reject latch and STOP: do not execute ANY480 fault
validation cases, do not modify latch or try a replacement. Report unavailable
validation metrics honestly. Only after a passing gate run fault validation once.

If fault validation is reached: original-space>=91%,benign<=1%,zero wrong confident
origins,plant-propagating>=95%,timing/communication/effective-memory no regression,
ABcommon>=90%. Retain A2 only on clean incremental gain and all gates. If A1 meets
gates and A2 offers no clean gain retain A1; otherwise CURRENT. Expanded-space
recall is reported but is NOT the headline retention criterion. No post-validation
changes or fallback trial after a failed benign gate. No unseen,commit,push.

All thresholds,masses,causal logic and C physical model remain fixed. Offline truth
only for classifications/metrics. Detection uses post-onset rising edges; all-runtime
localization includes benign/pre-onset samples. Exact paired counts and Wilson
intervals are descriptive for this grouped deterministic design. Max8compressed
traces,plan zero. Raw run files removed immediately; historical current artifacts
preserved in a compact results-only archive. Manifest and lock are retained for
reproducibility, not duplicate source trees.

Registered UTC:2026-09-29T13:56:40.759900+00:00
Manifest SHA256:d619cbd26d76f3bcb450741a575bc5144f6e1bd6841ab91995963470fe9edf8e
