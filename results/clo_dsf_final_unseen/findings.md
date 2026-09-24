# New final unseen validation — CURRENT at d040c341

One preregistered campaign completed: **1500 cases, 1200 faults and300 benign**;
240 faults per origin. CURRENT and all baselines remained unchanged. No selection,
recalibration, excluded failures or reruns. The rejected thermal contract was inactive.
Previous final-unseen data at this commit were treated as seen and incorporated into
the overlap audit before replacement. The old evidence remains recoverable from Git.

## Detection

| Origin | Detected | Wilson95% CI | Silent plant misses |
|---|---:|---:|---:|
| MEMORY |184/240 (76.67%)|70.92–81.57%|0|
| TIMING |240/240 (100%)|98.42–100%|0|
| COMMUNICATION |240/240 (100%)|98.42–100%|0|
| SENSOR_CONTROL |80/240 (33.33%)|27.67–39.52%|158|
| ACTUATOR |240/240 (100%)|98.42–100%|0|
| Overall |984/1200 (82.00%)|79.73–84.07%|158|

Macro detection82.00%. Effective memory184/184; dormant/no-effect stuck-bit alarms
0/56. The56 dormant cases had no control, actuator or plant effect; their inclusion
in overall recall is intentional. Every effective memory case alarmed at the first
register/shadow inconsistency (integrity-relative latency0ms). Scheduled-onset memory
P95 is7.455s because a stuck bit can remain dormant until a later legitimate update.
No alarm was forced merely because an injected stuck condition existed.

Slow drift **0/120**, positive0/60 and negative0/60; each of the7/19/47s rise-time
strata0/40. Weak steps25/60; pulses55/60. All120 slow drifts propagated silently,
plus35 weak steps and3 pulses. All240 communication cases detected, including short
windows and all delay/drop/replay types. Pump180/180 and fan60/60 detected.

Plant-propagating detection815/973 (83.76%, CI81.31–85.95%);158 silent misses.
Benign alarms0/300 (upper Wilson95 bound1.26%), including all150 legal-calibration
cases and all150 static-target cases. No pre-onset fault-run alarms. Precision100%
(CI99.61–100%); recall82%. Precision reflects the prescribed case mixture, not field
prevalence. Median/P95 latency0/485ms among984 detections;100ms tick sampling and
linear quantiles explain the interpolated485ms. Misses have no latency, rather than
zero. The lower aggregate P95 versus earlier development is a cohort effect, not a
new algorithm improvement. Maximum18.1s; subgroup latencies are retained separately.

Among815 detected plant-propagating runs:757 pre-plant,20 same-tick,38 post-plant;
169 other detections had no plant manifestation.757 were correctly localized before
plant manifestation. Ground truth and reference comparisons were used only offline.

## Localization

All984 first detections localized correctly: first coverage100%, accuracy100%,
UNKNOWN0. Across314512 alarm samples,311595 were localized and all311595 correct;
coverage99.073%, localized accuracy100%, UNKNOWN2917/314512 (0.927%). Correct fraction
of all alarm samples is99.073%, not100%. Wrong-origin runs/samples **0/0**.

Runtime UNKNOWN by true origin: memory50, timing0, communication11, sensor/control0,
actuator2856. All origins have100% accuracy among their localized samples. Actuator
runtime coverage97.227%; later downstream sensor evidence did not produce wrong
confident sensor/control origins. These results support causal-precedence behavior
on this cohort, not universal correctness. Missed faults are not counted as successful
localizations. Confusion and per-origin counts are in their summary CSVs.

## Frozen comparators and paired analysis

| Method | Detected | Silent plant | Benign alarms | Median/P95 ms |
|---|---:|---:|---:|---:|
| CURRENT CLO-DSF |984/1200|158|0/300|0/485|
| Fair Weighted Sum |943/1200|157|150/300|100/6500|
| Simple OR |903/1200|197|150/300|100/6600|
| Plain DS |886/1200|214|150/300|100/6700|
| Hybrid |849/1200|212|200/300|3700/7600|
| Timing Monitor, timing only |240/240|0|not evaluated|50/100|

CLO versus Weighted Sum: **851 both,133 only CLO,92 only Weighted Sum,124 neither**.
225 discordances; exact two-sided conditional McNemar **p=0.0075227959921351124**.
CLO has a3.42percentage-point binary detection advantage in this designed cohort;
the paired result supports that limited statement. It does not establish universal
superiority or a plant-propagation advantage: CLO has158 silent plant misses versus
157. Among973 plant-propagating cases,78 were missed by both,80 only by CLO and79
only by Weighted Sum;736 were detected by both. The net binary advantage comes from
communication(+62) and actuator(+47), offset by memory(-10) and sensor/control(-58).

On851 jointly detected cases CLO is faster200, tied635, slower16; median paired
latency difference0ms. Separate detector P95 values involve different detected
cohorts and should not alone be interpreted as a paired speed improvement.
Paired benign alarms: neither150, Weighted Sum only150, CLO only0, both0.

Weighted Sum's60/120 slow-drift alarms all occur in the60 legal-calibration workload
cases; it alarms in0/60 static-target slow drifts, but also150/150 benign legal-update
cases. This association confounds causal attribution: its higher slow-case binary
coverage is not evidence that it reliably identifies slow drift. All configured
baselines and thresholds were retained; this specificity weakness was not repaired.

## Post-hoc identifiability and scope of generalization

Slow-drift analysis began only after all runtime executions.70/120 cases had no
positive sensor-channel evidence after onset;50 first acquired positive evidence
after plant manifestation. Maximum sensor evidence per run ranged0..0.176956;
none reached an alarm. The common-mode acquisition/consumption bias preserves their
consistency, while gradually changing measurements can be absorbed by the short
forecast's measured slope and uncertainty allowance. Existing runtime evidence and
frozen logic therefore do not distinguish these slow cases adequately. This is a
measured limitation of this implementation/domain, not proof that every possible
observer must fail or that every gradual bias is physically unobservable.

Memory shadow and communication behavior generalized fully to the effective/tested
cases. Causal localization generalized with zero wrong origins. Sensor-response
behavior generalized **partially** to steps/pulses (80/120), not to slow drift or all
weak steps. No ablated implementation was run: this holdout does not independently
estimate the incremental causal contribution of the300ms channel versus other
sensor primitives. Do not describe broad sensor/control robustness as established.

Strongest positive:184/184 effective memory and240/240 each timing, communication,
actuator with zero benign alarms and zero wrong origins. Strongest limitation:
all120 slow biases silently reach the plant, plus38 missed step/pulse effects.
The frozen CURRENT implementation is ready for manuscript evidence with these
limitations and the full denominators. No further tuning followed this holdout.

## Integrity and evidence limits

Baseline commit was verified before creation. Scientific hashes were recorded before
design; exact commands, protocol and overlap audit preceded execution. Audit contains
943 historical identity sources and8588 distinct physical profiles, including Git
history, surviving overwritten local manifests, and the previous committed unseen
manifest. All1500 new full physical profiles are distinct and disjoint from that set:
**zero exact configuration overlap**. Built-in/no-custom-profile campaigns also cannot
match these explicit new profiles. Novel profiles are not independent random draws;
Wilson intervals and exact McNemar are descriptive under their usual independence
assumptions. Runtime sample intervals are particularly correlated.

All245 scientific files, GUI bytes, Hybrid/HETIA, CURRENT development results and
historical evidence outside the authorized output directory remain unchanged. Full
regression passed:308 tests, build, Python compile, diff check,48 legacy and64 RTL.
The two rebuilt historical reference executables were restored to their verified
initial bytes. CSV CRLF-to-LF publication normalization changed no parsed field;
registered and publication manifest hashes are both documented in validation_record.
Only compact summaries, commands, tables and eight preselected compressed traces
remain. No bulk raw data, algorithm copies, commit or push.
