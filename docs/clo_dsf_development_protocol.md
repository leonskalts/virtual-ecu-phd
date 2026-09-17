# CLO-DSF development protocol (registered before execution)

This is development/tuning evidence, never a final independent holdout. Existing
v1–v6 results informed architecture and semantic contracts. No future holdout is
created or inspected here. The new design is in `studies/clo_dsf_development_v1.yaml`.

There are 720 faulty configurations (144 per origin) and 192 distinct benign
profiles, 912 primary simulations. The same C scheduler also advances the accepted
fault-free reference for each monitored simulation (912 internal reference runs).
All detectors run observe-only on identical runtime trajectories. Fault model,
behavior and origin define split groups; severity, onset, duration and profile
variants never cross a group's split. Benign profiles group by operating template (two train, two validation templates under the ceil rule; 96 runs each).
The seed determines group ranking, not independent stochastic replication.
Explicit bits make the memory seeds operationally irrelevant; no duplicate-seed
replicates are counted. Transient deadline misses retain the required one tick and use distinct onset offsets (0/1000/2000 ms), since they have no severity parameter.
Fan-off magnitudes have no meaning: duration varies for finite behaviors, and
onset offsets vary for permanent behavior. These variants share a split group. Legacy intermittent cohorts use two existing custom_multi transient events separated by a 1000 ms recovery gap, because the legacy CLI accepts only transient/permanent behavior. The sensor-interface model also has its own frozen intermittent waveform.

The eight candidates are the Cartesian product of conflict rule {Yager, Dempster},
retention {0.8, 0.9}, confirmation threshold {0.65, 0.75}. All other parameters and
evidence transformations are fixed before execution. Index bits respectively
select Dempster, 0.9 and 0.75. All candidates execute online in C on TRAIN only.
The selection criterion is the exact lexicographic ordering in the YAML, with
candidate index as final deterministic tie-break. TRAIN must have zero benign
false-alarm runs for the candidate to be eligible for freezing. Only after selecting
and recording a configuration may VALIDATION run. No parameter or algorithm change
is allowed in response to validation outcomes; correctness fixes invalidate and
require a transparently recorded new development execution.

Detection is a new alarm episode at/after injection, within simulation end; an
already-active pre-injection alarm is not credited. Pre-injection alarm samples
are reported separately. All injected configurations, including masked stuck bits
and no observable effect, remain in coverage denominators. Conditioning uses the
accepted reference-based control/actuator-command/plant manifestation timestamps,
only in the evaluator. Silent plant propagation = plant manifested AND no credited
alarm. Plant coverage does not imply alarm before plant; report that separately.
Benign FP is any alarm during a benign run. Precision is detected faulty runs /
(detected faulty runs + benign alarm runs). Latency excludes misses; p95 uses
linear interpolation. Confidence intervals are not claimed for deterministic cases.

Localization at alarm uses the first credited alarm's estimate, including UNKNOWN;
accuracy denominator includes ALL credited alarms. Also report first later valid
localization, localized precision, and first localization strictly before plant.
Macro localization averages origin-specific accuracies among origins with alarms;
empty origin denominators stay N/A. Confusion rows include all faulty runs; misses
and UNKNOWN alarm estimates both enter UNKNOWN, with miss counts also separate.
No-alarm methods and non-localizing baselines retain UNKNOWN, not fabricated
origins. Timing Monitor has coverage only on TIMING; other origins are N/A.
Legacy detector comparisons inherit their existing simulator-truth access, and
are not proof of equivalent production observability.

Per-run ignorance and conflict are means over all runtime samples. Conflict is the
maximum step K in each timestep; the evidence sidecar also records every fusion
step K. A high-conflict run contains at least one K >= 0.5. Report distribution
quantiles separately for benign/faulty runs. A0 is standard Dempster without
extensions; A1 adds discounting and uses the selected conflict rule; A2 adds
propagation; A3 adds temporal fusion. Consequently A0→A1 changes two components
if Yager is selected; the TRAIN paired candidate comparison isolates rule choice
at equal retention/threshold. No causal claim should conflate those changes.

A freeze is justified only with zero TRAIN benign alarms, validation macro coverage
at least 0.50, localized precision at least 0.70, and passing isolation/regression.
This gate warrants further independent evaluation, not superiority or safety
qualification. False alarms, UNKNOWNs, poor layer coverage and negative ablations
must remain visible. Never alter the gate after seeing results.
