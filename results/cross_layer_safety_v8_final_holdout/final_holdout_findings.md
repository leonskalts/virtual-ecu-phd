# Final unseen holdout findings

The frozen v7.3 binary/configuration was evaluated once on 1,500 preregistered,
previously unused configurations: 1,200 faults, 300 benign, 240 faults per origin.
Zero exact configuration overlap with Candidate 1/2, v7.2 or v7.3 development.
All registered cases completed; no scientific parameters, baselines, fault
semantics or sampling decisions changed after outcomes. Exact configuration
novelty is not independence from the shared simulator/fault-family assumptions.

## Detection and frozen baselines

| Method | Detected | Coverage | Silent plant | Benign alarms | Median/P95 ms |
|---|---:|---:|---:|---:|---:|
| Simple OR | 956/1200 | 79.67% | 176 | 0/300 | 0/300 |
| Weighted Sum | 1068/1200 | 89.00% | 66 | 0/300 | 0/200 |
| Plain DS | 942/1200 | 78.50% | 190 | 0/300 | 0/300 |
| v7.2 CLO-DSF | 1068/1200 | 89.00% | 66 | 0/300 | 0/300 |
| Revised CLO-DSF | 1137/1200 | 94.75% | 0 | 0/300 | 0/300 |
| Hybrid | 785/1200 | 65.42% | 210 | 0/300 | 0/2500 |
| Timing Monitor | 240/240 | 100.00% | 0 | 0/300 | 50/100 |

v7.3 coverage 1137/1200 = 94.75%; nominal
Wilson 95% CI 93.34%–95.88%. Macro detection 94.75%.
Recall 94.75%; precision 100.00%, interval 99.66%–100.00%.
Plant-propagating detection 852/852 =
100.00%, interval 99.55%–100.00%.
Silent plant 0/852, interval
0.00%–0.45%. Benign alarm interval 0.00%–1.26%.

Of detected plant-propagating cases: 768 pre-plant,
0 same-tick and 84 post-plant.
Another 285 detected faults had no plant
manifestation and are not classified as pre-plant. Pre-injection alarm runs:
0. Latency statistics exclude misses.

| Origin | Detection | Coverage | Wilson 95% | Localized | UNKNOWN | Wrong |
|---|---:|---:|---|---:|---:|---:|
| MEMORY | 180/240 | 75.00% | 69.16%–80.06% | 180 | 0 | 0 |
| TIMING | 240/240 | 100.00% | 98.42%–100.00% | 240 | 0 | 0 |
| COMMUNICATION | 240/240 | 100.00% | 98.42%–100.00% | 240 | 0 | 0 |
| SENSOR_CONTROL | 240/240 | 100.00% | 98.42%–100.00% | 0 | 240 | 0 |
| ACTUATOR | 237/240 | 98.75% | 96.39%–99.57% | 237 | 0 | 0 |

## Localization and UNKNOWN

Coverage 897/1137 = 78.89%,
interval 76.42%–81.16%. Accuracy conditional on localization
897/897 = 100.00%,
interval 99.57%–100.00%. UNKNOWN 240/1137 =
21.11%, interval 18.84%–23.58%.
Wrong non-UNKNOWN at first alarm: 0; wrong localized
runtime samples: 0. Correct localization
before plant manifestation: 533/852
plant-propagating faults. All origin confusion tables retain UNKNOWN and misses
separately. UNKNOWN is valid abstention, not a confident localization error.

## Paired comparison and inference limits

v7.3 versus Weighted Sum: both 1068, only v7.3 69,
only Weighted Sum 0, neither 63.
Exact McNemar p: 3.3881317890172014e-21; Descriptive exact conditional paired test; related configurations violate IID interpretation.
Silent plant comparison: 0 versus 66.
Benign alarms: 0 versus 0.
Median/P95: 0/300 versus
0/200 ms.

Binary advantage under the preregistered rule on THIS modeled holdout: True.
Do not generalize this to a population guarantee, physical hardware, or a unique
advantage of DS mathematics. Weighted Sum retained its frozen original evidence;
a pool augmented with the same actuator contract was not tested. Designed
families share profiles/mechanisms and are correlated; the nominal Wilson
intervals and IID-conditional McNemar p do not account for that dependence.

## Does the v7.3 gain generalize?

Beyond intermittent actuator cases versus v7.2: True.
Report the actual contributing subtypes below, not a blanket all-origin claim.

| Origin | Subtype | Behavior | Only v7.3 | Only v7.2 |
|---|---|---|---:|---:|
| MEMORY | bit_flip | transient | 0 | 0 |
| MEMORY | bit_flip | intermittent | 0 | 0 |
| MEMORY | bit_flip | permanent | 0 | 0 |
| MEMORY | stuck_bit | transient | 0 | 0 |
| MEMORY | stuck_bit | intermittent | 0 | 0 |
| MEMORY | stuck_bit | permanent | 0 | 0 |
| TIMING | deadline_miss | transient | 0 | 0 |
| TIMING | deadline_miss | intermittent | 0 | 0 |
| TIMING | deadline_miss | permanent | 0 | 0 |
| TIMING | task_delay | transient | 0 | 0 |
| TIMING | task_delay | intermittent | 0 | 0 |
| TIMING | task_delay | permanent | 0 | 0 |
| COMMUNICATION | delayed_update | transient | 0 | 0 |
| COMMUNICATION | delayed_update | intermittent | 0 | 0 |
| COMMUNICATION | delayed_update | permanent | 0 | 0 |
| COMMUNICATION | dropped_update | transient | 0 | 0 |
| COMMUNICATION | dropped_update | intermittent | 0 | 0 |
| COMMUNICATION | dropped_update | permanent | 0 | 0 |
| COMMUNICATION | replayed_sample | transient | 0 | 0 |
| COMMUNICATION | replayed_sample | intermittent | 0 | 0 |
| COMMUNICATION | replayed_sample | permanent | 0 | 0 |
| SENSOR_CONTROL | sensor_bias | transient | 0 | 0 |
| SENSOR_CONTROL | sensor_bias | intermittent | 0 | 0 |
| SENSOR_CONTROL | sensor_bias | permanent | 0 | 0 |
| SENSOR_CONTROL | sensor_interface_intermittent | transient | 0 | 0 |
| SENSOR_CONTROL | sensor_interface_intermittent | intermittent | 0 | 0 |
| SENSOR_CONTROL | sensor_interface_intermittent | permanent | 0 | 0 |
| ACTUATOR | fan_stuck_off | transient | 0 | 0 |
| ACTUATOR | fan_stuck_off | intermittent | 0 | 0 |
| ACTUATOR | fan_stuck_off | permanent | 0 | 0 |
| ACTUATOR | pump_degraded | transient | 23 | 0 |
| ACTUATOR | pump_degraded | intermittent | 23 | 0 |
| ACTUATOR | pump_degraded | permanent | 23 | 0 |

Full subtype rates and severity-level paired counts are retained in paper_tables.
The v7.3 change affects only actuator conformance. Its validity rests on the
simulator's synchronous noiseless clamp(command) response. A physical actuator
requires trustworthy feedback plus a validated error/dynamics envelope; the
one-ULP rule is not a hardware tolerance. Historical Hybrid retains its original
feedback inputs, including the simulator's label-derived fan self-test; that
signal is not supplied to revised CLO-DSF.

## Post-hoc identifiability and latent memory faults

Analysis was performed offline after runtime, never fed into inference.
Mixed-origin complete allowed-observation-history groups: 1.
Mixed-origin complete extracted-evidence-history groups: 2.
Group members and exact signatures are retained; complete observation equivalence
and representation-induced equivalence are distinct. No rounded similarity
criterion or alleged universal identifiability theorem is introduced.

Stuck-bit runs whose runtime target remained exactly nominal: 60.
Detected among these: 0; plant-propagating among them:
0. These test the same dormant-defect pattern as
the 36 historical observability-limited v7.2 cases, under new configurations.
A stuck-at bit agreeing with the current value produces no passive value error;
trusted active memory testing, not an unchanged-value checksum, would be needed.
No no-effect faults were excluded from detection denominators.

## Manuscript use and integrity

These are final unseen configuration holdout results for this virtual-ECU model.
They support bounded claims about measured detection, selective localization and
the specific actuator evidence contract. Additional origin output is implemented
capability beyond the evaluated binary Weighted Sum, not proof that weighted
pooling cannot be extended to localize. Preserve conditional accuracy alongside
coverage and report silent plant misses and abstentions. No production,
compliance, embedded WCET, calibration or physical transfer claim is justified.

Frozen identities were verified before design/execution and after all runtime
cases. Final regression and preservation results are in validation_record.md.
The protocol, exact manifest, per-run results, commands and artifact hashes allow
reproduction without duplicate raw logs. Nothing was tuned after holdout.

Method references: [NIST Wilson intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm),
[paired McNemar definition](https://www.stat.ethz.ch/R-manual/R-devel/library/stats/html/mcnemar.test.html),
[exact paired binomial calculation](https://pdixon.stat.iastate.edu/stat511/notes/part%202b.pdf).

## Final review and explicit limitations

The strongest positive finding is 69 additional correctly localized pump faults
with no paired detection losses against either frozen comparator, and 66 fewer
silent plant misses. There are 23 extra detections in each of transient,
intermittent and permanent pump degradation, so the gain extends beyond the
intermittent development family. No incremental detection gain was observed
for fan-stuck, memory, timing, communication or sensor/control faults.

The strongest negative finding is the remaining observability/localization
boundary: all 60 latent stuck-bit cases are undetected, all 240 sensor/control
alarms abstain on origin, and three unexcited pump cases remain undetected.
Weighted Sum also retains better P95 latency (200 versus 300 ms). All extra
coverage comes from the actuator evidence contract, not demonstrated superiority
of DS over another fusion rule given the same enhanced evidence.

Communication coverage of 240/240 applies to the registered new magnitudes;
the delay levels here are 300/600 ms. It does not resolve the known shorter
100/200 ms freshness blind spots from development. Zero silent plant misses
on this holdout must not erase those historical counterexamples.

Identifiability details: one complete-observation collision group contains
12 latent memory cases and three unexcited actuator cases. The same group also
collides in extracted evidence. A second evidence group contains latent MEMORY
and benign runs, rather than two distinct faulty origins. Thus the reported two
mixed evidence groups comprise one cross-fault-origin group and one fault/benign
group. These are exact finite-stream observations, not a universal impossibility
claim for every fault or operating condition.

A disclosed input-serialization correction preceded every completed simulation.
The first attempted process rejected malformed profile column order before the
scheduler ran. Zero outcomes existed. The original registration/source contents
were archived; the unchanged manifest was revalidated using the public C profile
loader, and an explicit pre-outcome amendment fixed only positional CSV writing.
All 1500 completed simulations then ran once. See the protocol amendment and
validation record; no detector, threshold, sampling selection or outcome was
changed to obtain these results.

Temporary paths appear in original raw/summary metadata, so their retained byte
hashes attest to the completed run but should not be expected to match replay at
a different temporary path. Observation, evidence and online metric identities
are path-independent; all profile contents, commands and frozen dependencies are
retained to reproduce scientific results. No raw traces were kept redundantly.
