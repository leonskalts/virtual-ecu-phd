# CLO-DSF v7.3 development specification

This is new DEVELOPMENT research, not final paper holdout. Historical candidates,
source, manifests and evidence remain immutable. Baseline: 30e4853.

## Historical miss analysis and one chosen change

The exhaustive audit classifies v7.2's 114 misses as 78 algorithm-limited
(48 communication and 30 actuator) and 36 observability-limited latent memory
stuck-at cases. The latter agree with the current stored target, causing no
value change; passive target/plant signals cannot reveal the dormant defect.
A trusted memory BIST could, whereas a checksum of the unchanged value cannot.
Candidate 2's 117 development misses corroborate these categories (87/30).
Each missed case and each comparator's outcome is retained in the root-cause CSV.

Communication timestamp age already exposes late/missing periodic delivery, but
the old 300 ms grace maps 100/200 ms anomalies to zero. This is a separately
possible contract improvement, deliberately NOT combined with this revision.
All 36 v7.2 silent plant misses are algorithm-limited: 30 actuator, 6 communication.

Actuator command/actual differences already expose all 30 actuator misses.
The .20/.25 scaling suppresses weak evidence; b=q+(1-q)*.8*b has equilibrium
q/(.2+.8*q), below .5 for q<1/6. Accumulation cannot resolve that saturation.

Choose ONE change: replace actuator strength with a synchronous command/response
contract violation indicator. This targets the largest silent-plant category
without new sensors, fitted thresholds, weights or a parameter search.

## Exact contract and boundaries

In the unchanged actuators_step, each healthy realized output equals
clamp(command,0,1). scheduler_reactions executes that update (again after safety)
before detector sampling every 100 ms. This is a specification of this virtual
ECU, not a statistical fit to the old or new data. The detector reads only the
already allowed command and actual fields. Accept the expected float and its
two adjacent representable float values (one ULP in either direction); outside
that interval is a witnessed contract violation. Use nextafterf, not a chosen
real-valued fault-severity threshold. At off-actuator-cadence samples or any
nonfinite command/response, actuator evidence is unavailable/vacuous.

Replacement e_act is 1 for a witnessed violation, 0 otherwise. Existing DS maps
therefore assign ABNORMAL and ACTUATOR simple support, or ignorance. This is
a logical contract evidence encoding, not a calibrated probability. It replaces
the original actuator source; it is never added as a duplicate correlated source.
All other channels, both independent frames, combination order, temporal .8,
UNKNOWN gates and eight configuration values remain precisely v7.2. No origin
discount or propagation decision bonus is introduced. No A2 supporting change.

The source includes the frozen inference body with only its extractor replaced.
The adapter runs frozen v7.2 and all original baselines on original evidence;
the revised evidence does NOT silently strengthen OR/Weighted Sum/Plain DS.
The Weighted Sum remains choice 6 selected on Candidate 2 TRAIN.

Do not consume the existing fan self-test: its simulator implementation directly
reads the active fault label, so it is not an independently justified observable.
Hybrid remains unchanged, including its historical inputs. On hardware this
conformance rule requires trustworthy synchronized response feedback and a
validated actuator dynamics/error envelope; one-ULP tolerance is not a deployable
physical sensor tolerance. Plant propagation is evaluation-only reference truth.

## Selection and validation discipline

No parameter search: one structurally justified candidate, all eight parameters
copied byte-for-byte from v7.2. A deterministic model/behavior group-wise split
is registered before any run. TRAIN checks implementation and scientific
plausibility; VALIDATION is unopened until the source/config/protocol identities
and no-search selection record are locked. Abort if TRAIN contradicts the
contract; do not rescue it with validation-driven edits.

Before inspecting validation, freeze eligibility is defined as a material
reduction in silent plant misses or correct selective-origin improvement,
without additional benign alarms or wrong confident origins versus v7.2,
with no detection losses and complete isolation/preservation/regression checks.
Reject an unhelpful component. Keep detection/latency/coverage/accuracy tradeoffs
visible and report paired Weighted Sum outcomes without baseline recalibration.
All related deterministic configurations are designed cases, not independent
random replications or population-safety proof. No final unseen holdout is made.
