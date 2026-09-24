# Benign-only thermal response contract: rejected

CURRENT remains unchanged. One1080-case development experiment was completed:
240 benign characterization TRAIN profiles;480 fault TRAIN profiles; separate
VALIDATION of240 faults and120 benign profiles. No final unseen holdout ran.
The fitted contract was frozen before any fault execution or benign-validation
outcome. No fault data fitted coefficients, bounds, margins or persistence.

## Empirical contract and scientific boundary

The six-coefficient rate model uses
x=[1,load,speed/100,ambient/40,(pump_actual+fan_actual)/2,predicted_temperature/100].
Fitted coefficients are
[2.0412696051545454,7.623879808637384,-2.0324149525890625,
2.6196269988798897,-11.2294235777198,-6.903266380784726].

Only measured acquisition temperatures and allowlisted context from clean TRAIN
runs supplied the28,800 one-second difference targets. Ridge regularization0.1
on non-intercept coefficients was specified in the experiment script before fitting.
Pump/fan share one cooling index: this deliberately reduced model does not copy
or invert the thermal simulator. No hidden temperature, experiment heat parameter,
fault offset, reference observation, future runtime value or evaluation label
is read by the monitor. Offline fitting uses subsequent benign measured samples
as targets; runtime integration uses previous context and its own prediction.

Each20s window predicts forward from its measured initial temperature. It does
not estimate long-term slope from current measurements. This is a **conditional
relative-evolution contract**, not an independently verified absolute temperature
reference. Reanchoring means a pre-existing constant offset can remain invisible.
Outside characterized context ranges plus5% margin, the monitor abstains.

TRAIN free-running20s maximum errors: minimum0.482C, median1.418C, maximum4.592C.
The frozen conservative envelope is1.25*max_error+0.20C = **5.940323C**. This is an
empirical operating-domain bound, not a universal physical guarantee. Clean sensor
variation, workload/ambient changes and approximation error all contribute. A valid
violation requires five same-sign100ms samples; excess uses the existing2C evidence
normalization and max-merges into SENSOR_CONTROL evidence. Existing global thresholds
and causal precedence remain. Evidence decays through the existing temporal fusion
when consistency returns; finite windows do not accumulate indefinitely.

thermal_contract.cfg stores six coefficients, then bound/horizon_ms/persistence,
then four pairs of normalized context minima/maxima. The file is **frozen but
rejected/inactive**, retained for reproducibility; production CURRENT does not load it.
The campaign manifest records roles explicitly: only benign-characterization rows
were fit-eligible. Fault configurations are included for exact reproduction, not
as fitting data. characterization_summary.csv retains each clean TRAIN profile's
free-prediction error. No raw streams remain.

## Required ablation

All methods observe identical ECU streams. Shared base logic includes original
sensor range/slew and two-edge primitives, all other origins and causal precedence.
"Short-horizon only" means CURRENT with its300ms forecast and no new contract.
"Contract only" disables just the300ms forecast and adds the frozen contract.
"Combined" retains both. Labels in CSV: Pre-change CLO-DSF, Contract only,
Revised CLO-DSF, respectively. The latter is experimental, not the retained detector.

| Validation method | Detection /240 | Slow drift /36 | Silent plant | Benign /120 | Median/P95 ms |
|---|---:|---:|---:|---:|---:|
| A0 / short-horizon only |177|0|54|0|0/3120|
| Contract only |168|0|63|0|0/2565|
| Combined |177|0|54|0|0/3120|
| Fair Weighted Sum |184|18|40|60|100/6200|

Combined versus A0:177 both,0 combined-only,0 A0-only,63 neither. Contract-only loses
nine A0 detections. On fault TRAIN, A0 and combined both359/480 with101 silent plant
misses and0/72 slow drifts; contract-only340/480 with120 silent misses. Neither
partition demonstrates a drift benefit. No settings changed in response.

A0/combined per-origin detection: memory39/48, timing24/24, communication36/36,
sensor/control42/96, actuator36/36. Effective memory39/39; dormant alarms0/9.
Weak steps11/24; pulses19/24; plant-propagating156/210. Weighted Sum's18/36 alarms
in slow-drift cases must not be read as proof of drift attribution: it also alarms
on60/120 benign cases including legal calibration changes; no recalibration occurred.

## Localization and retention decision

A0 first localization177/177; runtime known-origin accuracy56,834/56,834;
UNKNOWN472/57,306 (0.824%). Combined first localization177/177 and the same56,834
correct localized samples, but UNKNOWN increases to1096/57,930 (1.892%). The
624 added UNKNOWN alarm samples occur in actuator cases. Causal precedence prevents
wrong confident SENSOR_CONTROL origins: wrong runs/samples remain0/0. Contract-only
UNKNOWN1096/57,079 (1.920%); it also loses nine detections from the300ms channel.
A lower contract-only P95 is not a latency improvement: its detected cohort is smaller.

The predeclared retention gate required at least25% slow-drift detection, fewer
silent plant misses, at most one benign alarm, no wrong origin and no lost A0
fault detections. It fails: **zero slow-drift gain and zero silent-miss reduction**.
No contract is installed. Specificity alone is insufficient to retain a useless
channel; extra UNKNOWN alarms are an additional drawback. The fitted bound is
wider than the tested drift magnitudes. Narrowing it based on faults would violate
benign-only calibration and was not attempted.

Strongest positive: a cleanly separated benign fit preserved specificity on120
unseen benign development profiles; the ablation confirms nine useful detections
from the existing300ms forecast. Strongest limitation: the conservative empirical
uncertainty masks the target drift, and no absolute independent thermal anchor was
created. This negative result is conditional on this simple model and characterized
domain, not a proof that every benign-trained observer must fail.

## Reproducibility and final state

The reproduction script contains the temporary C contract monitor, ablation build,
fit, deterministic design and scoring. Runtime copies existed only in temporary
storage; no candidate implementation tree was added. Reproduce from the recorded
manifest and baseline source hashes using the script's design/fit/build/command
functions; the main entry point is a one-pass CURRENT-results replacement workflow.
The fitted file/hash must be held fixed for fault replay. Production scientific
sources, GUI state, Hybrid/HETIA and historical evidence are unchanged.

Ready for one genuinely new holdout of unchanged CURRENT with its documented
slow-drift limit; no unseen evaluation occurred here. Full regression and preservation
proofs are in validation_record.md. No commit/push. Eight compressed traces retained.
