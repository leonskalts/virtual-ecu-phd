# Multi-rate observability development: rejected

## Final decision

Retain unchanged TRIPLEX. No multi-rate extension is promoted. No further detector development or new unseen campaign. The original frozen Triplex source, thresholds, classical DS, plant/controller, fault semantics and GUI remain unchanged. New providers exist only in the development harness and are not linked into the retained Triplex entry point.

New valid cohort2700 distinct configurations: TRAIN1200, CALIBRATION750, VALIDATION750 (600fault,150benign,120each origin). Exact validation executed once after rate/source/manifest lock. The previous91.75% result remains byte-preserved; it is development/reference for this attempted architecture, not its validation. No commit/push.

## Temporal design and selection

The physical scheduler remains100ms. Diagnostic50/25ms conversions use timestamped independent acquisition/ADC state, fixed20/25/30ms lag and existing noise/quantization/calibration. Within-tick physical interpolation is the retained sensor-model convention, not new detector access to hidden truth. Decisions still arrive on100ms ticks. Source A diagnostic shares the existing variation; B shares existing benign frontend events. Actual additional samples feed the unchanged numerical FAST contract with elapsed-time scaling, 500ms startup qualification and one-second edge-history duration. SLOW32s remains unchanged. Evidence is max-combined into one source; no independent DS votes per sample. Batch evidence clears every100ms, no300ms latch.

Old memory schedule averages1000ms with1100ms max gap. Extra500ms schedule alternates600/400ms; extra250ms alternates300/200ms on the unchanged100ms grid. Same seven-operation atomic write/read/restore; every execution asserts unchanged target register. No sub-100ms memory-fault semantics invented.

TRAIN+CAL selection: sensor50 gained15+14 faults but benign96/240+61/150; sensor25 gained24+19 but benign97/240+60/150. Neither qualified. Per preregistration,50ms was frozen as the lower-complexity negative-control fallback, not a recommended rate. Memory500 added12+7 clean detections;250 added14+10, with no added benign or wrong-origin runs versus A1 (CAL baseline itself had1/150).250ms selected. No thresholds fitted. Detailed100/50/25 subgroup detection and latency are in multirate_rate_comparison.csv (A1=100ms reference). Validation evaluates selected50/250 only; no post-validation25ms comparison or reselection.

## Untouched validation

A0 CURRENT499/600=83.17%; A1 TRIPLEX527/600=87.83%; A2 SENSOR539/600=89.83%; A3 MEMORY536/600=89.33%; A4 BOTH548/600=91.33%, Wilson95 88.81–93.33%. A4: memory116/120,timing120/120,communication120/120,sensor113/120,actuator79/120. Effective memory82/82,dormant34/38. A38/40,B36/40,AB39/40; independent A/B slow27/27,weak steps40/40,pulses33/40. Initially excited46/46; initially unexcited33/74; unexcited-throughout0/41.

A4 plant267/267,silent0 versus A1 265/267,silent2. Benign62/150=41.33% versus A1 0/150. Precision89.84%. First localization548/548 correct on detected faults; runtime localized155370/155615=99.8426%; wrong62runs/245samples, all on benign runs. UNKNOWN0 first-detection,650runtime samples (0.416%). High conditional localization accuracy must not obscure62 benign wrong-confident runs.

A4 median/P95 latency0/32412.5ms versus A1 0/32535ms. The marginal P95 difference is only122.5ms and includes different detected sets; no material latency-reduction claim. Per-subgroup latencies are provided.

A4 vs A1: both527,A1-only0,A4-only21,neither52; exact McNemar p=9.5367431640625e-7. Recovery: memory9,sensor12,actuator0; no losses;2 recovered plant-propagating cases. Sensor gains A4/B5/common3; by waveform step2/pulse10/other0 (these are alternate partitions, not additive categories). Memory gains effective0,dormant9,transient4/intermittent5/permanent0.

## Mechanism and miss causes

A1 sensor misses19:10 entirely between100ms control observations,7 single-observation,2 weak despite multiple observations,0topology,0other. Of the12 sensor recoveries,3 were between-sample,7 single-observation and2 weak-multiple. A1 memory misses13:all13 lacked an intersecting probe;0 insufficient-evidence,0 diagnostically-invisible-after-probe,0other. Nine recover under the faster schedule. These classifications use offline manifest windows and diagnostic timestamps only, never runtime fault labels.

The sensor gain is real temporal observability, but not clean fault discrimination. In TRAIN, all96 false S50 runs followed the same benign signed0.83C,100ms B-readout excursion, first alarm31000ms. Multiple acquired samples from one physical transient satisfy the inherited short-window qualification. Treating them as persistence does not make the event a fault or statistically independent evidence. The rejected architecture would require an additional justified benign-event distinction, which is outside this final attempt; no rescue tuning was performed.

Even perfect recovery of all memory/sensor misses could reach at most559/600=93.17% on this validation cohort while41 unexcited pump-performance faults remain unobservable. Thus the>=94% goal is also infeasible for this cohort under the permitted scope. Hard actuator cases were not removed or reweighted. This is a cohort-specific upper bound, not a population performance claim.

Memory-only is clean but gains9/600=1.5percentage points and reaches89.33%; it fails both>=94% and>=2point requirements. All extensions rejected. The combined statistically significant detection gain does not establish overall superiority given the large false-alarm regression.

## Overhead and invariance

Per120-second validation simulation, selected diagnostics add7201 sensor acquisitions and481 memory probes=3367 elementary diagnostic read/write operations. Retained schedule121probes=847operations; total602probes=4214operations (~4.98x), including the retained schedule needed for baseline behavior. Candidate maximum scheduled extra-probe gap300ms.750cases add5,400,750acquisitions and360,750probes. Counted provider state664bytes for three fast-pair histories,three diagnostic sensor models and one memory-diagnostic state; excludes harness,logging and small bookkeeping. Full simulation/observer storage is not an embedded RAM estimate.

Paired host benchmark:8 already-seen benign TRAIN cases,3alternating-order repetitions per mode. Baseline median63.910ms versus baseline+A4 72.017ms per120-second simulation: +12.69%. This includes diagnostic CSV instrumentation and collector I/O; no embedded WCET claim. Physical/control raw logs and baseline evidence traces are byte-identical for all24pairs. Diagnostic probe restoration asserts also passed throughout every cohort. No plant perturbation.

## Execution accounting

The valid scientific dataset has2700unique cases. Before outcomes were inspected: the first command was rejected by the original100ms timing validator; corrected memory/timing/communication windows preserve those semantics. One completed simulation then had an incomplete collector due to reading memory timestamps from the legacy observation CSV; switched accounting to the explicit metadata log. An initial1200TRAIN cohort was superseded after source inspection found missing benign A/B perturbation sharing in the diagnostic frontend; no outcome counts from it were inspected or used. Corrected TRAIN reran, then CAL and VALIDATION each ran once.48additional simulation executions form the host benchmark, not detection-rate evidence. There were3949 campaign/benchmark executions including superseded and collector work, excluding regression tests; none was unseen. These corrections are documented rather than presented as2700total executions.

All implementation and rate choices frozen before VALIDATION. No source edits after validation inspection. Full regression332tests, build, Python compile,diff check,48legacy,64RTL passed. Retained source/config/GUI, prior unseen artifacts and historical Hybrid/HETIA evidence unchanged.
