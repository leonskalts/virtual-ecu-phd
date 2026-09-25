# Active diagnostic development: memory retained, no sensor anchor

CURRENT adds an active protected-memory diagnostic. A new1200-case campaign used
720 TRAIN cases (600 faults/120 benign; six families) and480 VALIDATION cases
(400 faults/80 benign; four other families). Parameters were fixed before TRAIN and
unchanged through VALIDATION. No final unseen holdout ran. No commit or push.

Validation detection is **362/400=90.5%**, versus340/400=85.0% for pre-change CURRENT.
Wilson95% interval87.23–93.00%: the90% target is met on this development-validation
cohort, not established as a population guarantee or unseen result. All22 gains are
previously dormant stuck-cell cases. No primary threshold or fusion/localization
rule was lowered, tuned or replaced. Weighted Sum is only an unchanged comparator.

## Active memory: a new measured storage contract

The passive shadow cannot identify a stuck cell whose value still equals the
intended value. The new checker tests the ability to change that same16-bit protected
target word: save/read, write0/read, write65535/read, restore saved/read. It runs once
per1000ms in an exclusive synchronous transaction between scheduled fault application
and normal control use. No control/sensor task runs during the transaction. The
trusted shadow and authorized calibration commit path are unchanged.

The generic memory_diagnostic module has only read/write callbacks and ordinary
readback comparisons. It contains no ECU state, faulty-bit identity, active-fault
flag, injection label or reference truth. The separate virtual storage backend
models a stuck cell rejecting an opposite write. That backend necessarily applies
the simulated cell fault, just as other device models apply faults to measurements;
its configuration is not passed to the checker or inference. This distinction is
central: the added diagnostic observes unsuccessful writes, not a fault-active
oracle or a repackaged passive checksum.

This is an explicit extension of the virtual storage-access model. Previously,
stuck bits were imposed at scheduler fault updates; diagnostic writes now exercise
the corresponding persistent stuck-cell constraint within the atomic transaction.
The original injector source/header and normal control/injection operations remain
unchanged. Results are conditional on the new storage contract, not evidence that
CRC alone can expose a value-correct stuck cell.

Restore uses the actual saved register word, never the expected shadow. A pre-existing
bit-flip therefore remains corrupted and is still detected by the original shadow
channel. Both polarities across all16 bits are exercised without knowing the faulty
bit. Legal calibration updates refresh the existing shadow through control_commit_target;
probes neither change that metadata nor manufacture stored/used corruption.

Fresh failed-check results join the existing MEMORY/ABNORMAL channel as direct
contract evidence. Validity expires after1000ms and the next successful probe clears
the diagnostic result. No additional independent DS source or propagation bonus is
added. The current causal-precedence and sensor-response logic are unchanged.

Six new tests cover all65536 clean16-bit values, all32 stuck-bit/polarity combinations,
recovery, cadence, legal updates, bit-flip preservation, stale/future evidence and
checker isolation. Eight representative TRAIN scenarios were compared against the
pre-change executable before and after final backend packaging: raw physics/control
logs and C summaries were byte-identical. Thus the tested probes do not leak test
patterns into normal controller behavior.

## Sensor anchor feasibility: no qualified window

No physically justified ambient anchor exists in the current operating model:
zero engine load retains a positive base heat source; zero speed selects hot idle,
not engine off; safety shutdown scales operating inputs but does not remove that
heat; startup has no certified ambient soak. No trusted runtime signal establishes
a bounded zero-net-heat equilibrium independent of the measured coolant trajectory.
Low load alone is insufficient, especially with continuing actuator and ambient
changes. The algebraic radiator model is not an independent measured reference.

No simulator-equation inversion, true coolant temperature, injected magnitude,
future sample or fitted generic thermal predictor was used. No benign anchor fit
was attempted because its prerequisite physical window is absent. Half the operating
families include a zero-load/zero-speed interval to exercise the proposed context;
all such intervals remain explicitly unqualified. Qualified-anchor cases0; all
slow-drift cases belong to the no-anchor stratum. A2 is exactly A0 and A3 exactly A1;
these are explicit aliases, not distinct implemented sensor algorithms.

## Validation and ablation

| Method | Detected /400 | Silent plant | Benign /80 | Median/P95 ms |
|---|---:|---:|---:|---:|
| A0 CURRENT |340|37|0|0/400|
| A1 active memory |362|37|0|0/500|
| A2 anchor unavailable, identical to A0 |340|37|0|0/400|
| A3 combined, identical to A1 |362|37|0|0/500|
| Frozen Fair Weighted Sum |310|56|40|100/9600|

A3 per origin: MEMORY80/80, TIMING80/80, COMMUNICATION80/80, SENSOR_CONTROL42/80,
ACTUATOR80/80. Memory effective stuck bits42/42, all effective memory58/58, dormant
stuck bits22/22, legal-update benign alarms0/40. Effective/dormant categorization is
post-hoc from restored register/shadow contents, not from temporary test patterns.
A0 versus A3:340 both,0 A0-only,22 A3-only,38 neither; no lost detections.

Slow drift0/32; qualified anchor unavailable (0-case denominator); without anchor0/32.
Weak steps19/24, pulses23/24. Every sensor binary outcome equals A0. Plant-propagating
detection282/319 (88.40%);37 silent misses remain:32 slow drifts and5 weak steps.
The one missed pulse has no plant manifestation. All added dormant-memory detections
are diagnostic integrity findings before stored/used-value corruption, not recovered
silent plant effects. Do not claim improved plant safety coverage from those22 gains.

First localization362/362 correct and localized. Runtime122963/122963 localized alarm
samples correct; UNKNOWN1116/124079 (0.8994%), coverage99.1006%; wrong runs/samples0/0.
The number of UNKNOWN samples is unchanged from A0; the rate falls because added
memory alarms enlarge the denominator. No wrong confident origins were introduced.

TRAIN supports, rather than substitutes for, validation: A0=483/600; A1/A3=518/600,
with35 added dormant detections, no benign/wrong-origin alarms and unchanged sensor
outcomes. Neither partition was used to tune the checking period or thresholds.

## Latency and overhead

Dormant-memory detection latency from scheduled onset: median450ms/P951700ms;
maximum1700ms. Alarm occurs on the same tick as the first failed probe for all22
cases. Across all64 stuck-bit cases, first failed-probe latency median450ms,
P951785ms,max2900ms. Intermittent active windows can fall between periodic probes;
a one-second period does not imply every intermittent fault is found within one second.
Existing effective-memory shadow detection can precede the first probe.

The persistent state is16 bytes per ECU. Each probe requires four reads and three
writes; polling is once per100ms scheduler tick, actual probes every1000ms. A120s
inclusive run has121 probes (including both endpoints),847 protected-word accesses.
There is no extra dependency or heap allocation. Simulation models the transaction
as atomic with zero elapsed scheduler time; real hardware CPU time/WCET, interrupt
exclusion and restore-failure handling have not been established. Timing-regression
success is not a claim that the diagnostic is free on a physical ECU.

Aggregate P95 rises400 to500ms because A3 includes newly detected latent cases;
no A0 detection is lost. This comparison is across different detection cohorts.
The diagnostic period and overhead budget were not selected to reach90%.

## Final implementation and evidence

Memory retention gate passes: validation detection/dormant coverage improve; no lost
A0 detections or added benign alarms; full effective-memory/timing/communication/
actuator coverage; no wrong origins; plant coverage does not regress. Sensor mechanism
not retained because no qualified anchor exists. Current short-horizon sensor-response
code and all primary thresholds/causal-precedence behavior remain unchanged.

The simulation callback bodies were moved verbatim into their own module after the
campaign completed and before validation outcomes were inspected, restoring the
historical injector files. This was packaging only; function-body hash and final
reproduction hashes are recorded. Final production build omits the temporary A0
comparison object. All source/configuration choices are reproducible from the saved
manifest, baseline commit and run_clo_dsf_active_diagnostic.py; reconstruct baseline.c
from the task-start commit in temporary storage for its A0 observer. No candidate or
frozen implementation tree exists.

Full regression passed:314 tests, build, Python compile, diff check,48 legacy and64
RTL cases. Hybrid/HETIA and historical evidence outside CURRENT are unchanged; GUI
session bytes preserved. Eight compressed validation traces; no bulk raw data.
Ready for one new unseen holdout of the retained active-memory implementation,
explicitly conditional on the virtual storage contract. Strongest remaining limitation:
slow/common-mode sensor drift has no qualified independent anchor (0/32 here).
