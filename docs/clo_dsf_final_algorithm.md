# CLO-DSF final pre-holdout algorithm

This document specifies the v7.2 simplification of Cross-Layer Observability-Aware Dempster-Shafer Fusion. It is a research runtime detector, not a claim of production readiness, functional-safety compliance, calibrated Bayesian uncertainty or embedded WCET. Its confirmation campaign is DEVELOPMENT CONFIRMATION, not final paper holdout.

## Motivation and development history

Candidate 1 coupled anomaly and origin reasoning in one frame, included a joint NORMAL absence source, and discounted origin evidence. Candidate 2 separated anomaly confirmation from selective origin estimation. On its new development-validation cohort it detected 262/300 cases, compared with Candidate 1's 162/300. A positive-only single-frame control matched the initial dual-frame ablation: removal of conflicting NORMAL evidence, rather than separation alone, accounts for that observed first-stage detection gain. Temporal fusion added ten detections. Origin discounting reduced accepted correct origins from 202 to 176 without removing any observed errors; propagation modulation showed no measured benefit. Calibrated Weighted Sum matched Candidate 2 binary coverage.

The final revision therefore retains positive anomaly evidence, structural origin subsets, independent temporal states and selective abstention. It removes additional origin reliability discounting and all propagation decision modulation. It does not introduce a new signal or tune a parameter. The complete Candidate 2 no-origin-discount validation result is reproduced before implementation; historical data are not represented as fresh confirmation.

## Runtime inputs and structural observability

The six evidence transforms are inherited unchanged from Candidate 2. The implementation reuses its frozen extraction and origin-map functions; no historical file is edited. The allowed snapshot includes measured temperature and freshness/timestamps, active control target, actuator commands and actuals, scheduler ledger, operating context and current time. Diagnostic IDs, safety-state labels and other detector outputs are ignored. Injector labels, bit index, true plant temperature, fault activation metadata, reference simulation deviations and evaluation propagation are excluded from inference.

| Channel | Strength e, clipped to [0,1] | Legitimate origin support |
|---|---|---|
| Timing | max(deadline exceeded, missed expected execution, late completion, (execution age−period−deadline)/period) | TIMING |
| Communication | 1 for freshness failure or backward received timestamp; otherwise (sample age−300)/300 | COMMUNICATION |
| Memory/control | abs(active target−92)/4 | MEMORY |
| Sensor/control | implausibility outside [−40,150], or (abs(measured change)−2.5×elapsed seconds)/2 | {COMMUNICATION, SENSOR_CONTROL} |
| Actuator | max(abs(fan command−actual)/.25, abs(pump command−actual)/.20) | ACTUATOR |
| Plant symptom | (measured temperature−108)/7 | Entire origin frame |

Unavailable/nonfinite evidence is vacuous. Future sample timestamps and missing timing periods use Candidate 2's existing availability checks. PLANT is not a fault origin. No absence of a particular channel is treated as positive proof of a competing origin. The word Observability-Aware remains justified by available sources, legitimate hypothesis subsets, broad support, ignorance and UNKNOWN abstention; it no longer means a numeric origin reliability factor.

## Independent frames and exact mass assignments

Let Theta_D={NORMAL,ABNORMAL} and Theta_L={MEMORY,TIMING,COMMUNICATION,SENSOR_CONTROL,ACTUATOR}. For available evidence e_i:

m_D,i({ABNORMAL})=e_i, m_D,i(Theta_D)=1−e_i.

m_L,i(S_i)=e_i, m_L,i(Theta_L)=1−e_i, except S_i=Theta_L gives a wholly vacuous mass.

Detection reliability r_D is the copied Candidate 2 value 1. Discounting a mass with reliability r multiplies every proper nonempty subset by r and sets m'(Theta)=1−r+r m(Theta). No origin reliability discount is applied. Healthy evidence contributes ignorance, not positive NORMAL mass. Consequently state NORMAL means no confirmation of abnormality, not belief establishing fault-free operation.

The reference uses the unchanged DS core's 64-entry storage. Detection blocks are 1 and 62; the five logical origin blocks are 33,2,4,8,16. Disjoint partitions cover mask 63 and preserve intersections/unions exactly. MEMORY block 33 counts as ONE logical origin. Pignistic scores use logical five-origin cardinality, never the six storage bits. Both masses are 512 bytes in the reference; storage compatibility is not a minimal-memory claim.

## Dempster combination and temporal fusion

For two masses a,b, conflict K=sum_{A intersection B=empty} a(A)b(B). For nonempty C, normalized Dempster mass is

(a ⊕ b)(C) = sum_{A intersection B=C} a(A)b(B)/(1−K).

The existing core computes the nonempty sum and normalizes it, with a flagged vacuous fallback when 1−K≤1e−12 or normalization fails. All per-stage conflicts and fallback flags remain visible. Fold channels in timing, communication, memory/control, sensor/control, actuator, plant order. Each frame then combines its current evidence with its own prior mass discounted by lambda=.8:

m_D,t = current_D,t ⊕ discount(m_D,t−1,lambda)
m_L,t = current_L,t ⊕ discount(m_L,t−1,lambda).

Neither prior frame is used by the other. Retention is per 100 ms scheduler sample; duplicate/backward times are ignored. Missing/healthy evidence lets prior support decay. Repeated measurements are correlated, so DS independence/calibration is not asserted.

All informative binary focal sets are ABNORMAL, so detection conflict is zero by construction. Its current support is q=1−product_i(1−r_D e_i), with temporal b_t=1−(1−q_t)(1−lambda b_t−1). This is mathematically a noisy-OR style accumulator. Detection plausibility is one and ignorance is 1−b_t. This identity is an explanation, not permission to silently reorder floating-point operations or claim new DS mathematics.

## State machine and selective origin decision

Read exact parameters from the selected Candidate 2 configuration: suspect=.35, confirmed=.5, persistence=1, lambda=.8, r_D=1, origin score=.55, margin=.15, maximum origin ignorance=.5. The final runtime CFG contains only retained decision parameters. Provenance records original lexical values and the source SHA-256. There is no v7.2 search.

The consecutive confirmation counter increments at/above confirmed threshold and resets below it. When persistence is met, output CONFIRMED; otherwise choose SUSPECT or NORMAL from the suspect threshold. On recovery, alarm clears; first-ever alarm/localization timestamps remain historical records. Evaluation-specific onset windows never enter the core.

For origin h, BetP(h)=sum_{A containing h} m_L(A)/|A|, where |A| counts logical origins. Let h* be the leading score and margin the largest minus second-largest score. Localize only if CONFIRMED, score≥.55, margin≥.15 and m_L(Theta_L)≤.5. Otherwise estimated_origin=UNKNOWN. Scores, belief and plausibility are not Bayesian probabilities. CONFIRMED + UNKNOWN is a valid output, particularly for sensor/communication ambiguity and broad plant symptoms.

## Propagation is diagnostic only

After inference, a separate diagnostic function can update the inherited evidence-episode graph. Both source episodes must remain active at strength≥.5, with strict forward onset order and a 3000 ms window. The graph is timing/communication/memory→sensor/actuator/plant; sensor→actuator/plant; actuator→plant. This function accepts only the evidence-history object, time and diagnostic window. It cannot access either mass or output/state-machine object. Its bitmask is logged as observed_evidence_path and displayed as diagnostic only. The legacy-compatible propagation_support output stays false: no decision support is claimed.

## Paper-ready pseudocode

```text
Input: allowed runtime observation x_t, previous independent masses D and L
If timestamp is not strictly newer: return previous output
Extract the six inherited evidence strengths and availability flags
For each channel i:
    construct positive anomaly mass on ABNORMAL, remainder on ignorance
    apply the frozen detection reliability (zero if unavailable)
    construct origin support on legitimate subset S_i, remainder ignorance
    if S_i is the whole origin frame: keep origin mass vacuous
    apply NO additional origin reliability discount
Fold current anomaly masses with Dempster's rule, recording K and fallback
Fold current origin masses independently, recording K and fallback
D <- current_D combined with discount(previous_D, .8)
L <- current_L combined with discount(previous_L, .8)
Update NORMAL/SUSPECT/CONFIRMED using only Bel_D(ABNORMAL)
Compute five-logical-origin BetP scores, leading margin and origin ignorance
If CONFIRMED and score/margin/ignorance gates pass: emit leading origin
Else: emit UNKNOWN
Record first alarm and first accepted localization timestamps
Optionally update observed episode-path diagnostics AFTER inference
Never use that path to modify masses, scores, thresholds or decisions
```

## Comparators, confirmation and identifiability

The fixed confirmation cohort contains 900 unique configurations, 720 fault and 180 benign, with four new operating profiles and all five origin layers. Its physical signatures have no exact overlap with any Candidate 1/2 train/validation setting. All methods share each simulation's observations: frozen Candidate 1/2, no-origin-discount Candidate 2, final reference, temporal-zero ablation, matched Plain DS, OR, previously calibrated Weighted Sum, unchanged Hybrid and timing-only Timing Monitor. No recalibration is allowed. Per-run paired outcomes, conditional effects, localization coverage and accuracy, UNKNOWN, confidence/ignorance distributions and nominal Wilson intervals are reported. The designed cohort is not IID population safety evidence.

Weighted Sum computes a calibrated scalar anomaly score and supplies no implemented selective origin estimate or DS ignorance/conflict readout. CLO-DSF's possible added capability must be measured as meaningful localization with abstention, not assumed binary superiority. Timing Monitor uses specialized scheduler semantics and is assessed only on timing and benign cases, never assigned all-origin capability.

Post-hoc identifiability groups use exact whole allowed-observation streams, exact complete evidence streams and separately first-alarm snapshots. Truth labels are joined only after hashing. Whole-history equality across origins proves ambiguity for that stream; feature-stream equality proves ambiguity for the inherited representation. Snapshot coincidences alone do not prove that a stateful detector cannot distinguish histories. The sensor evidence's composite subset supplies a structural reason to abstain; empirical collision counts and their actual origins must be reported without inventing sensor collisions.

## Complexity, implementation and preservation

A generic frame of n atoms has up to 2^n mass entries and naïve dense pairwise combination O(4^n); sequential fusion of k channels is O(k4^n), memory O(2^n). Actual logical frames have n=2 and n=5: four and 32 possible entries, with few reachable focal sets. The reference embeds both in 64 entries to reuse the frozen mathematical core. It skips zero outer/inner mass products but scans dense storage for validation and normalization. Six channels plus one temporal fold run per frame. Five-origin pignistic readout visits 31 logical subsets.

No optimization is attempted until confirmation supports a mathematical freeze. Any optimized implementation must preserve the frozen mass assignments, fold order, temporal behavior, all decisions and timestamps; reference and optimized implementations are replayed over every archived confirmation observation. Both are retained. No approximation, threshold adjustment or new evidence is permitted. Measurements report persistent state separately from comparison-bank executable BSS and exclude stack/stdio from state counts. Host runtime includes process and instrumentation costs, not embedded WCET.

Historical Makefile, GNUmakefile, GUI launcher and candidate files are hashed and remain unchanged. Build with `make -f clo_dsf_final.mk`; launch the additive GUI with `python3 scripts/virtual_ecu_final_gui.py` once the frozen final view is available. The legacy entry points still work. The ordinary `make` and existing complete tests remain valid. Both candidates' historical evidence and the user's session are byte-preserved. No commit/push or final holdout is created by this task.
