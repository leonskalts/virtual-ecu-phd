# CLO-DSF Candidate 2: detection and localization as independent inference tasks

Candidate 1 and its development evidence remain scientifically frozen. Candidate 2 is an additive C11 experimental runtime detector. Neither is accepted final safety evidence. Candidate 2 uses the same six observed evidence strengths, cadence and static episode graph as Candidate 1, with separate detection and origin masses. No final holdout is defined here.

## Frames and exact storage representation

The detection frame is {NORMAL, ABNORMAL}. The origin frame is {MEMORY, TIMING, COMMUNICATION, SENSOR_CONTROL, ACTUATOR}; NORMAL and PLANT are not origin hypotheses. The unchanged generic DS core has 64 storage entries with universal mask 63. To reuse it without modifying Candidate 1, each logical frame is a partition of the six storage bits. Detection blocks are 1 and 62; origin blocks are 33, 2, 4, 8, 16. A logical subset is encoded by union of its blocks. These partitions preserve intersection, union and the universal set, so DS combination is exact on the embedded subalgebra.

The two bits in origin MEMORY block 33 are one logical atom, not two hypotheses. Candidate 2's pignistic transform counts five logical blocks, never raw storage bits. For logical origin h, BetP(h) = sum over subsets A containing h of m(A)/|A|, with |A| the number of logical origins. Vacuous origin evidence gives exactly 1/5 to each. Generic six-atom pignistic output is not used for either Candidate 2 frame. The binary decision uses belief, not pignistic score.

Two ds_mass_t objects occupy 1024 bytes. Their independent state and outputs are measured in candidate2_overhead.json. The fixed dense storage is an intentional compatibility tradeoff; it is not the minimal possible binary/five-origin representation.

## Runtime evidence and observability

All transformations are identical to Candidate 1 and equivalence-tested. clip denotes [0,1].

| Channel | Runtime transform | Origin support | Origin reliability class |
|---|---|---|---|
| Timing | max(deadline flag, missed execution, late completion, clip((execution age − period − deadline)/period)) | TIMING | Direct |
| Communication | freshness failure or backward received timestamp → 1; otherwise clip((sample age − 300)/300) | COMMUNICATION | Direct |
| Memory/control | clip(abs(active target − 92)/4) | MEMORY | Direct |
| Sensor/control | implausible measured value or clip((abs(measured change) − 2.5×elapsed seconds)/2) | {COMMUNICATION, SENSOR_CONTROL} | Indirect |
| Actuator | clip(max(abs(fan command − actual)/.25, abs(pump command − actual)/.20)) | ACTUATOR | Direct |
| Plant symptom | clip((measured temperature − 108)/7) | Entire origin frame (vacuous) | Indirect but uninformative for origin |

Future packet timestamps, invalid/nonfinite measurements and absent timing periods make affected channels unavailable. An unavailable channel contributes a vacuous mass and zero reliability. Unused diagnostic IDs, detector alarms and safety state in the shared observation struct are ignored. Fault labels, injected bit index, onset metadata, simulator temperature truth and reference trajectories are not detector inputs. Changing hidden labels or these unused fields does not change outputs.

Every available positive strength e contributes m_D(ABNORMAL)=e, m_D(Theta_D)=1−e. Healthy evidence is vacuous: it is absence of anomaly support, not evidence proving NORMAL. There is no joint NORMAL source. This intentionally differs from Candidate 1's conflicting absence source. The displayed NORMAL state means that confirmation thresholds are not met; it is not a claim of positive normality belief.

For localization, m_L(S)=e and m_L(Theta_L)=1−e, except S=Theta_L remains wholly vacuous. Consequently the measured plant symptom cannot assign an origin. Sensor-jump evidence explicitly supports a composite subset instead of a fabricated sensor-specific singleton.

## Discounting, fusion, state and outputs

Reliability discount maps every proper nonempty subset mass to r×m(A), and ignorance to 1−r+r×m(Theta). Detection and origin discounts are separate. Candidate 2 initially fixes anomaly reliability to 1 and origin direct/indirect reliabilities to .9/.6. The selected global configuration is in the development directory. Anomaly reliability .9 is tested separately. No origin reliability, propagation, localization score, margin or ignorance threshold feeds back into detection.

Within each frame, fold channels in timing, communication, memory/control, sensor/control, actuator, plant order using Dempster's normalized intersection rule. K is the sum of products whose intersections are empty. For K below 1−1e−12, divide nonempty intersections by 1−K; at total conflict the unchanged core returns flagged vacuous evidence. Log every pairwise K and its per-step maximum independently for both frames. High conflict is K≥.5. Temporal fusion discounts each frame's own previous state by lambda then combines it with the current frame; neither previous frame is used by the other.

The positive-only binary frame has zero conflict by construction: every informative focal set is ABNORMAL. If e_i are available detection-discounted strengths, current support is q=1−product(1−e_i), and temporal support obeys b_t=1−(1−q_t)(1−lambda×b_(t−1)). Its plausibility is 1 and ignorance is 1−b_t. Thus this binary DS component is mathematically a noisy-OR style accumulator; it is not novel DS mathematics or a calibrated probability. Missing/healthy steps decay previous support through lambda. The explicit separate frame gives a clean independence contract and traceable uncertainty, not evidence that DS universally outperforms simpler pooling.

Detection reads only Bel_D(ABNORMAL). Below suspect threshold → NORMAL; at/above suspect → SUSPECT until the configured consecutive confirmation count reaches its limit, then CONFIRMED. Reset count below confirmation threshold and recover immediately to the appropriate state. Duplicate or backward timestamps do not change either detector state. The expected scheduler cadence is 100 ms; retention is per update, not elapsed-time normalized.

Localization requires CONFIRMED and all three global conditions: largest origin BetP reaches threshold, its margin over second reaches threshold, and origin ignorance is at most the limit. Otherwise output UNKNOWN. Anomaly state remains CONFIRMED when origin is UNKNOWN. Origin belief and plausibility describe the leading singleton even when abstaining; estimated_origin and localization_valid indicate whether it was accepted. Scores are not Bayesian probabilities. Alarm/localization timestamps record first-ever runtime events; evaluator event timestamps separately require a new post-onset alarm edge.

## Propagation and temporal dependence

Reuse the exact Candidate 1 graph: timing, communication and memory/control each point to sensor/control, actuator and plant; sensor/control points to actuator and plant; actuator points to plant. A channel episode is active at strength≥.5. An edge supports its upstream channel only when both episodes remain active, upstream onset is strictly before downstream onset, neither is future, and upstream age is within the configured window. Same-tick, reversed, incomplete and expired paths cannot help. The upstream origin reliability is multiplied once by (1+bonus), capped at 1. This does not create a new independent mass or improve anomaly evidence.

The campaign predeclares that propagation is retained only for measurable TRAIN localization benefit without additional wrong origins at the selected operating point. Otherwise bonus zero is the primary configuration. The .1 variant remains an explicitly optional ablation. No novelty claim rests on a propagation feature with no observed value.

Repeated sensor measurements and cross-layer symptoms are correlated. DS independence assumptions are not established; temporal discounting limits retention but does not prove independence or calibration. Empirical conflict/ignorance and selective accuracy are reported with this limitation.

## Sensor/control identifiability

Under this evidence map, a measured slew can be caused by a corrupted sensor value or a corrupted/stale communication stream. The exact same runtime observations can have different hidden fault labels. A deterministic runtime detector must emit the same output for both. No independent trusted temperature, trusted packet provenance, or known injector label is present. Healthy freshness does not prove sensor origin; absence of positive communication evidence is not positive sensor evidence. Consequently sensor-only composite evidence yields tied COMMUNICATION/SENSOR_CONTROL scores and UNKNOWN.

This proves a limitation for observationally equivalent cases and for this map, not universal impossibility of identifying sensor faults from every conceivable richer runtime model. Future independent measurements could change identifiability, but adding truth-derived sensor support here would invalidate the comparison. Existing freshness evidence can sometimes disambiguate toward COMMUNICATION.

## Controlled comparisons and development discipline

The new YAML and preregistered selection_protocol.md define 1140 unique configurations, grouped TRAIN/VALIDATION, eight detection configurations, six global localization readouts and matched propagation on/off states. Weighted Sum gets twelve transparent TRAIN settings. Architecture, search and hierarchy precede validation. All comparisons run online on identical observations, with no feedback into physics. Timing Monitor is reported only on timing and benign cases. Hybrid remains an existing specialized comparator, not a six-feature fusion method.

B0 Plain DS retains Candidate 1's single frame and joint NORMAL evidence; B1 removes the NORMAL absence source and separates frames. To avoid attributing both changes to frame separation alone, the supplemental single-frame positive baseline removes only the absence source. B2 adds origin reliability; B3 adds propagation; B4 adds temporal retention. A separate detection-reliability ablation prevents origin discounting from masquerading as anomaly discounting. TRAIN ablations are at the declared starting configuration; validation ablations share the selected detection/readout parameters. Search states supply selected TRAIN scores. TRAIN runtime sidecars show the declared initial configuration, not the subsequently selected one; validation sidecars are the selected candidate.

For offline TRAIN localization readouts that differ from the online bank, later-localization timestamps cannot be reconstructed from first-alarm statistics. The selected .55/.15 readout matches the bank exactly, so its actual later timestamps are retained (documented in reporting_adjustments.json). Validation executes the frozen readout and records actual later localization. Confusion tables keep missed detections separate from detected UNKNOWN. Results include coverage and wrong-localization rates beside selective accuracy. Per-run uncertainty distributions are descriptive, not independent sample confidence intervals.

## Additive integration and reproducibility

`virtual_ecu_v7_1` uses a linker wrapper around the accepted detection callback. Candidate 1 source, configuration, executable path and artifacts remain untouched. The original Makefile only includes the separate Candidate 2 fragment; the Candidate 1 GNUmakefile hash is unchanged. Existing GUI method bodies remain unchanged; one top-level installer extends classes with a separate Candidate 2 module. Hybrid remains default. Runtime panels use explicit field allowlists and never display evaluation truth.

Run `make`, `python3 scripts/run_clo_dsf_candidate2_development.py` once in a fresh development directory, and the Candidate 2 tests. The runner refuses to overwrite a preregistered/executed campaign. Ordinary runtime use requires the selected complete configuration, for example:

```
./virtual_ecu_v7_1 /tmp/candidate2.csv baseline --detector clo_dsf_candidate2 --detector-action observe_only --c2-config results/cross_layer_safety_v7_1_dev/selected_config.cfg
```

The study records full raw logs, runtime traces, per-method metrics, commands, audit, search and selection hashes. Executable BSS includes comparison banks and is not a deployment-state estimate. Host overhead includes process and logging effects and is never an embedded WCET claim. Candidate 2 can only be frozen as a second development candidate after the documented comparison and regression checks; this never replaces Candidate 1 or constitutes final paper validation.

## Paper-ready pseudocode

```text
Input: allowed runtime observation x_t; previous masses D_prev, L_prev;
       observed episode onsets; fixed global configuration c
If timestamp is duplicate or backward: return previous output unchanged
For each of the six channels i:
    e_i, available_i <- runtime_transform_i(x_t, previous observation)
Update observed episode onsets and strict forward graph edges
For each channel i:
    D_i <- positive support e_i on ABNORMAL, remainder on Theta_D
    L_i <- support e_i on allowed origin subset S_i, remainder on Theta_L
           (if S_i = Theta_L, L_i is vacuous)
    rD_i <- global detection reliability if available, otherwise zero
    rL_i <- direct/indirect origin reliability if available, otherwise zero
    If a valid forward edge supports i and propagation bonus is enabled:
        rL_i <- min(1, rL_i * (1 + bonus))
    Discount D_i by rD_i; discount L_i by rL_i
D_current <- ordered Dempster fold of D_i; record detection conflicts
L_current <- ordered Dempster fold of L_i; record localization conflicts
D_t <- D_current combined with discount(D_prev, lambda)
L_t <- L_current combined with discount(L_prev, lambda)
         [temporal stage omitted in the corresponding ablation]
score <- Bel_D_t(ABNORMAL)
Update consecutive-confirmation counter using only score
state <- CONFIRMED if persistence met; else SUSPECT/NORMAL from score
p <- logical five-origin pignistic transform of L_t
h <- deterministic leading origin; margin <- largest p - second largest p
If state = CONFIRMED and p[h] >= threshold and margin >= minimum_margin
   and L_t(Theta_L) <= maximum_ignorance:
    estimated_origin <- h
Else:
    estimated_origin <- UNKNOWN
Store D_t, L_t and runtime history; emit separate frame outputs
```

Candidate 1's historical development findings motivated the revision: origin discounting and NORMAL conflict could suppress alarms, sensor/control remained ambiguous, propagation produced no measured coverage gain, and the old Weighted Sum threshold was uncalibrated. The new study tests these explanations with a calibrated baseline and an extra single-frame positive control. Its actual findings, including the decision not to freeze the selected Candidate 2 configuration, are in `results/cross_layer_safety_v7_1_dev/candidate2_findings.md`.

Likely host cost sources are the frozen dense DS combination loops, two temporal/frame folds instead of one, logical pignistic subset iteration and detailed CSV formatting. No aggressive optimization or algorithm retuning was performed after validation. A sparse or smaller frame representation is a separate future engineering experiment, not an unmeasured WCET improvement claimed here.
