# Tractable-miss refinement findings

Retain the phase-sweeping memory schedule and bounded FAST residual integral. Do not change actuator logic. This is DEVELOPMENT evidence, not an unseen holdout or manuscript generalization claim. Baseline commit: e8126d9f3da261a210f1d16c83d4af57245036e2.

## Root causes before implementation

All 60 relevant previously seen misses were replayed individually and their runtime trace hashes matched the original traces. See root_cause_summary.csv for sensor chain, direction, magnitude, duration, phase and runtime evidence per case.

- Memory: A/B/C/D = 5/0/0/0. The fixed one-second probe aliases with 800 ms active / 1200 ms inactive bursts. No active-window probe occurred; this is classified primarily as scheduling (A), with inactive probes as its consequence. Each run contained 121 valid probes, full zero/all-one coverage and successful restoration. No end truncation or incomplete pattern coverage.
- Actuator: A/B/C/D = 0/0/0/13. Command and actual agree throughout the interval; inactive pump commands provide no passive degradation evidence and there is no plant propagation. No justified persistence or confidence increase exists. A2 is explicitly the unchanged A0 control.
- Weak steps: A/B/C/D/E/F = 3/17/0/0/2/0. Many 0.49 C, 100 ms excursions lack enough samples; two reference steps start an anchor but fail the widening second-sample envelope.
- Pulses: A/B/C/D/E/F = 7/13/0/0/0/0. Weak 0.39 C pulses fall below the edge bound or end before sufficient repeated edges.

## Retained mechanisms

Memory probes visit ten phases: nine 1100 ms intervals followed by 100 ms. Mean interval remains 1000 ms, maximum 1100 ms at the existing 100 ms invocation cadence. Seven memory accesses per probe, unchanged average overhead. Unit checks cover every 100 ms onset phase of the tested 600/1400 ms burst cycle over ten seconds. The atomic save, zero/write/read, all-one/write/read and restore/read sequence is unchanged. Atomicity assumes the existing synchronous single-thread execution without a concurrent calibration write. This schedule breaks the tested alias; it does not guarantee arbitrary transients shorter than the maximum gap or every possible adversarial period. Fresh failed-probe evidence now lasts the maximum interval.

FAST adds a same-sign residual integral inside the existing 300 ms anchor. With r_i the disagreement relative to the anchor and h_i elapsed seconds, require at least two same-sign samples, each |r_i| > 0.40 C, and sum |r_i| > sum (0.40 + 1.2 h_i). Recovery, sign reversal, gaps and anchor expiry reset accumulation. These are the existing noise and slew bounds; global threshold, existing onset/edge rules and SLOW sensitivity remain unchanged. Max-merge into the same sensor feature avoids double-counting. No sensor member is presumed faulty. No injection labels or hidden plant state enter the detector.

## Strict campaign and ablations

1560 simulations: TRAIN 936 (816 faults, 120 benign), VALIDATION 624 (544 faults, 80 benign). Six/four disjoint operating families; new deterministic profiles and seeds. All parameters fixed before TRAIN and locked unchanged before VALIDATION. No outcome-driven adjustment. Each simulation provides the same physical trajectory for every ablation; independent old/new restored probe transactions supply each observer its own diagnostic timestamps. Eight baseline/current production replay checks produced byte-identical plant/control outputs.

| Validation method | Detected / 544 | Silent plant | Benign / 80 |
|---|---:|---:|---:|
| A0 current | 514 | 11 | 0 |
| A1 memory only | 526 | 11 | 0 |
| A2 actuator unchanged | 514 | 11 | 0 |
| A3 FAST only | 518 | 9 | 0 |
| A4 combined | 530 | 9 | 0 |

Memory adds 12 detections, FAST adds 4, actuator adds 0. No A0 detections lost. TRAIN gains were +14 memory and +18 FAST; validation gains are independently positive. Timing, communication, slow drift and common-mode outcomes remain unchanged case-by-case. All ablations have zero wrong confident origins.

A4 overall: 530/544 = 97.43%; Wilson 95% interval 95.73–98.46%. These are descriptive case-level intervals, not an independence claim for grouped profiles.

| Origin | Detection |
|---|---:|
| MEMORY | 80/80 |
| TIMING | 80/80 |
| COMMUNICATION | 80/80 |
| SENSOR_CONTROL | 210/224 |
| ACTUATOR | 80/80 |

Effective memory 48/48; dormant stuck faults 32/32 (A0 20/32); phase misses 0; legal calibration update alarms 0/40. Dormant here means no ordinary stored-value corruption: active probing legitimately exposes a write/read inconsistency. This is distinct from an alarm without any diagnostic evidence.

Actuator transient/intermittent/permanent: 27/27, 27/27, 26/26. Weak degradation: 36/36. New validation command/response misses: 0. These results do not resolve the 13 historical unexcited-pump observability misses.

Weak steps 64/64 (primary 32/32, reference 32/32; positive and negative 32/32 each). Pulses 42/48 (primary 22/24, reference 20/24). All registered pulses are positive; negative pulse generalization is not established. Sensor totals primary 102/104, reference 108/112 (including reference dropouts), positive 122/132, negative 88/92. Common-mode 0/8, unchanged. Independent slow drift 96/96: primary and reference 48/48 each.

Plant-propagating detection 333/342; silent plant 9 (8 common-mode plus 1 pulse), down from 11. Benign alarms 0/80. Median/P95 100/42855 ms versus A0 100/42900 ms: no material P95 improvement; retained SLOW evidence still determines the long tail.

First-detection localization 530/530 correct and localized. Runtime localized accuracy 182672/182672; wrong-origin runs/samples 0/0. Runtime UNKNOWN 1052/183724 = 0.5726%; coverage 99.4274%. UNKNOWN samples are excluded from accuracy among localized samples.

## Limits and readiness

Fourteen validation misses remain: eight common-mode faults and six pulses. Common-mode lacks an independent reference. The new campaign uses 200 ms steps and 500 ms finite pulses; success does not establish recovery of the historical 100 ms weak impulses, which remain confounded with benign impulses. A known previously seen isolated benign impulse alarm in the unchanged FAST path was not claimed fixed; zero alarms applies to this campaign. No detection capability regressed in the registered validation, but the maximum memory interval increases from 1000 to 1100 ms and may delay individual detections. Ready for one genuinely new unseen holdout with these limitations declared; none run here.

## Verification and storage

327 tests, build, Python compile, git diff --check, 48 legacy and 64 RTL cases PASS. Frozen scientific/config/manifest hashes unchanged throughout outcomes. Hybrid/HETIA and historical evidence match task-start hashes; GUI state preserved byte-for-byte. No commit or push. Eight compressed representative traces; raw campaign data deleted after processing.

The campaign script records the exact design and comparison adapter. Its scratch inputs can be reconstructed at /tmp/clo-tractable: baseline.c from the baseline commit's src/v7_3/clo_dsf_revised.c, memory.c from src/memory_diagnostic.c, plus root_cause_summary.csv copied from this result and classification_complete marker after checking the recorded classification. The script refuses accidental overwrite of an existing tractable campaign. Do not rerun it as an unseen evaluation.
