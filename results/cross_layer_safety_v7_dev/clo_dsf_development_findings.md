# CLO-DSF development findings

DEVELOPMENT RESULTS — NOT FINAL HOLDOUT. No final safety, universality, WCET,
ISO 26262 or Bayesian probability claim is supported. Dempster–Shafer itself and
Yager's rule are established methods, not claimed contributions.

1. **Macro coverage versus simple baselines:** CLO-DSF 63.33%;
   OR 81.67%; Weighted Sum 0.00%;
   Plain DS 65.00%. The table reports actual results;
   richer outputs alone do not establish improved detection.
2. **Observability contribution:** A0 coverage 65.00%,
   A1 56.67%; localization accuracy
   87.18% → 100.00%.
   If Yager is selected, this comparison also changes conflict handling and does
   not isolate discounting alone. TRAIN paired candidate results compare rules.
3. **Propagation contribution:** A1 → A2 coverage
   56.67% → 56.67%;
   supported in 2 validation runs. No guarantee of benefit.
4. **Temporal contribution:** A2 → full coverage
   56.67% → 63.33%; latency medians
   100.0 → 100.0 ms.
5. **Difficult layers:** see the complete per-origin denominators in
   clo_dsf_layer_summary.csv. Sensor/control lacks independent true-temperature
   evidence, mild communication faults can remain fresh, masked memory writes
   can have no effect, and fan-off can be hidden by low commanded duty.
6. **Silent plant propagation:** 56 / 166 plant-manifesting faults.
7. **Benign false alarms:** 0 / 96; pre-injection
   alarms on faulty runs: 0. Benign conditions are diverse
   deterministic profiles, not an estimated operational distribution.
8. **Localization:** 89.47% of all detected runs correct at first
   alarm; macro 80.00%; localized-only precision
   100.00%. Later localization does not repair first-alarm errors.
9. **Confused origin pairs:** {}. See full matrix including misses.
10. **UNKNOWN:** 10.53% of credited alarms. Abstention prevents forced
    predictions; no counterfactual number of 'correct UNKNOWNs' is identifiable
    without specifying a forced classifier. UNKNOWNs are not scored as correct origins.
11. **Hybrid:** coverage 49.17%, macro 49.17%,
    benign alarms 0; uses frozen legacy evidence,
    including simulator-truth-dependent residuals. This is not an equal-observability comparison.
12. **Timing Monitor:** 48 / 48
    timing cases; other injected layers are N/A. It retains its specialized contract.
13. **Value beyond OR:** explicit ignorance/conflict, conservative localization,
    runtime evidence provenance and temporal persistence. Compare coverage/latency/FP
    directly; interpretability does not prove alarm superiority.
14. **Largest alarm-coverage ablation change:**
    ('observability/rule', -0.08333333333333337).
    Signed effects, ignorance and conflict remain in clo_dsf_ablation.csv.
15. **Promising for independent validation:** YES; final isolation/regression checks passed.
    TRAIN selected candidate 1; validation never selects or retunes it.
    A freeze is permission to test an unchanged candidate on unseen data, not a claim of superiority.

Full counts: validation 336 runs, 240 faults, 96 benign.
Coverage 63.33%; plant-conditional coverage 66.27%;
precision 100.00%; recall 63.33%; median/p95 latency
100.0/344.99999999999886 ms. Mean ignorance 0.162708,
mean max-step conflict 0.004407; 152 high-conflict runs.

A0–A3 use exactly the same validation trajectories and global decision rules;
localization is a readout and cannot change alarms. The single-fault frame cannot
represent simultaneous independent origins as conjunctions of truths: subsets
express uncertainty over alternatives. Channel and time dependence remain a
scientific limitation despite reliability discounts and finite retention.

## Interpretation of negative results

The OR baseline detects 196/240 (81.67%), versus CLO-DSF's 152/240 (63.33%):
CLO-DSF does **not** improve alarm coverage beyond OR. Plain DS detects 156/240,
also higher than full CLO-DSF. Weighted Sum's equal 1/6 weights and 0.5 threshold
require several concurrently strong channels; its 0/240 is an uncalibrated,
strict pooling baseline, not evidence that weighted fusion generally fails.

Discounting decreases coverage by 8.33 percentage points (65.00% to 56.67%).
Its higher conditional localization accuracy partly reflects abstention and
removal of difficult alarm cases, not demonstrated new origin information.
Propagation changes no binary decisions in this validation cohort. Temporal
fusion recovers 16 detections (+6.67 points) but introduces many high-conflict
steps against historical evidence. Its improved coverage does not establish
statistical independence or calibrated confidence.

The full detector localizes 136 alarms correctly and abstains on 16; all 16
sensor/control alarms are UNKNOWN. There are no wrong non-UNKNOWN estimates in
this development cohort, but the ambiguous channel mapping precludes a clear
sensor/control diagnosis. Memory coverage is 24/48, communication and sensor/control
16/48 each, timing and actuator 48/48 each. The candidate's 56 silent plant cases
are a material limitation. Only 20 correct localizations precede plant manifestation.

The continuation gate is met for testing explainability, abstention and broader
coverage than the unchanged Hybrid (118/240), not for claiming superior alarm
coverage or demonstrating the proposed propagation contribution. A new independent
holdout may validly falsify this candidate. No further parameter change is justified
from these development-validation results within this task.

A post-study semantic audit found 16 redundant TRAIN executions from permanent
single-model deadline settings that ignore severity/duration. There are 896 distinct
physical configurations among the 912 configured simulations. All repeats remain
within one split group; none appears in VALIDATION. De-duplicated TRAIN sensitivity
selects the same candidate and gives the same 58.75% macro coverage for CLO-DSF.
See physical_equivalence_audit.json and deduplicated_sensitivity.csv. Repeats are
not independent evidence and were not used to compute statistical intervals.
