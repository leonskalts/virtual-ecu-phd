# Final unseen CLO-DSF holdout — registered before outcomes

Registered UTC: 2026-09-18T14:36:08.985670+00:00. Baseline: a681528af4f9a6a8bebc9ade2c73276375a99e22.
PASS: 9494 frozen revision/dependency/artifact identities. No final holdout.
Frozen v7.3 manifest SHA256: 12f1d4253bc46608b6568ef95fc1d5821b829b829afdd21956d525fbddec8eaf.
No detector, baseline, fault semantics or scientific parameter may change.
No search, recalibration, early stopping, outcome-dependent sampling or retuning.
All 1,500 valid unique cases must run once; errors stop the campaign and remain
visible. A registered campaign refuses overwrite or silent restart.

## Design

1,200 faults (240 each MEMORY, TIMING, COMMUNICATION, SENSOR_CONTROL, ACTUATOR)
and 300 benign cases. Five new piecewise driving profiles; four onset bases
18700/43900/81700/96700 ms; ordinary durations 1400/7300 ms; 120000 ms runs.
Profile segments 0/21300/57900/92300/120000 use factors .66/1/.82/.94.
Seeds 101/137/179/223; deterministic injectors do not create independent random
replications. Every exact profile, magnitude, onset, duration, seed and polarity
is in final_holdout_manifest.csv, including full profile contents. Profiles are
materialized only in temporary work space. No historical file is overwritten.

All model/behavior groups are present. Non-communication models have 40 cases
per behavior; communication has 80/model, using hash-selected 27 transient,
27 intermittent, 26 permanent cases from a fixed 40-case grid. The hash selection
is completely determined before any outcomes. Benign offsets form a 4x5x3 grid
per base profile. Hardware intermittent windows are 700 on/1100 off; legacy
intermittent is two transients separated by 1100 ms. Drop interval is 11 updates.

New continuous magnitudes: pump .965/.81; sensor bias -3.5/6.5; intermittent
sensor 3.5/7.5; task delay 800/1300 ms; communication delay 300/600 ms;
drop counts 3/8; replay ages 600/1700 ms. Memory bits 0/4 necessarily reuse
members of the finite supported bit domain; stuck polarity varies. Fan-stuck
has no magnitude, and a transient deadline miss necessarily lasts one tick
(100 ms). Severity-equivalent permanent/deadline cases use distinct 1700 ms
onset offsets. Novelty is in exact complete configurations, not a claim of
new fault mechanisms or unseen values for every categorical parameter.

Overlap audit canonicalizes numeric profile contents (not filenames or CSV
formatting), model, behavior, onset and meaningful magnitude/duration. It
conservatively ignores seed/polarity and ignored permanent durations. Exact
overlap is zero within this cohort and against ALL Candidate 1, Candidate 2,
v7.2 (including its abandoned draft), and v7.3 TRAIN/VALIDATION configurations.
Every final command passed the unchanged C configuration validator without
simulation before registration. No favorable subsets may be dropped.

## Execution and frozen comparators

Execute the exact frozen virtual_ecu_v7_3 binary with revised.cfg, the frozen
Candidate 2 configuration and Weighted Sum choice 6. All observer states see
the same runtime observations in one physics execution and remain observe-only.
Report Simple OR, frozen Fair Weighted Sum, Plain DS, frozen v7.2, frozen v7.3,
Hybrid, and Timing Monitor restricted to timing and benign cases. The existing
binary also computes Candidate 2 internally; it is not an additional reported
holdout comparison. All old baselines use their ORIGINAL extraction. None gain
the revised actuator evidence. The old Hybrid inputs remain unchanged.
No ground truth, injected origin, activation flag or reference deviation enters
v7.3 inference. Evaluation onset and truth are used solely in post-hoc scoring.

## Fixed metrics and comparisons

Fault detection uses the frozen evaluator's first new post-onset alarm edge.
Any benign alarm is a false alarm. Report all fault cases, including no-effect
latent faults, in recall denominators. Precision is TP/(TP+benign false alarms).
Latency is first post-onset alarm minus onset among detections; misses are never
assigned zero latency. Median/P95 use the frozen linear quantile convention.
Plant propagation uses the unchanged accepted reference comparison after runtime.
Report plant-conditional coverage and silent plant cases; pre/same/post timestamps
are restricted to detected plant-propagating cases. Other detected faults with
no plant manifestation are separate, not misclassified as pre-plant alarms.

First-alarm localization coverage includes non-UNKNOWN outputs among detections;
accuracy is correct among those outputs, UNKNOWN is reported separately. Include
all five true origins, UNKNOWN and misses in the confusion table. Report wrong
localized steps throughout runtime and correctly localized-before-plant cases.
Wilson two-sided 95% intervals use z=1.959963984540054 for detection, each origin,
plant coverage, silent plant rate, benign alarm rate, precision, localization
coverage, conditional accuracy, UNKNOWN, wrong-origin rate and pre-plant/localized
before-plant proportions. Macro coverage is the unweighted origin mean; no false
binomial CI is attached to a macro mean. Correlated designed families limit
population interpretation of all nominal intervals.

Pair v7.3 with Weighted Sum and v7.2 by run ID: both/only-v7.3/only-comparator/neither.
For zero or fewer than ten discordant pairs, give counts only and no McNemar p.
For at least ten, report the exact two-sided conditional binomial McNemar tail
2*sum(binomial(n,k), k<=min(discordant directions))/2**n, capped at one.
Treat p as descriptive under an IID assumption, not proof across correlated
families. Empirical binary superiority on this fixed modeled holdout requires
positive net paired detections, no higher benign alarm count, and p<.05 when
the test is eligible. No claim of universal/DS-specific superiority follows.

Subgroups are predeclared by origin/model/behavior (and severity in a companion
table). Generalization beyond intermittent actuator faults means a positive
net gain over v7.2 outside ACTUATOR/intermittent; report exact contributing
subtypes, not a blanket cross-origin improvement. Show all actuator subtypes,
communication, memory, timing and sensor/control. Test whether stuck-bit runs
whose nominal target remains unchanged still evade detection; do not remove
them from overall coverage. Report unexcited actuator misses honestly.

## Post-hoc identifiability and artifacts

After each C runtime finishes, hash the complete allowed-observation stream and
complete six-channel evidence/availability stream using exact serialized values,
and inspect the trace for scoring consistency. Group these signatures and join
origin labels ONLY after all runtime executions. No signature or post-hoc label
is fed back into any detector. Full raw-history equivalence and feature-history
equivalence are different claims. No tolerance-based grouping is invented.

Temporary raw, summary, evidence and observation CSVs are discarded after offline
summaries/signatures and SHA256 identities are recorded. Retain compact per-run
metrics, exact commands with a reproducible temporary-workspace token, profile
manifest, input/output signatures, subgroup/identifiability tables and a few
paper figures. The listed top-level artifacts are the only output files.

After evaluation verify every frozen v7.3 hash again, build/compile, run all tests,
48 legacy cases and 64 RTL cases in temporary directories, and verify original
tracked files/session plus Hybrid/HETIA identities. No commit/push.

Methods: [NIST Wilson intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm),
[paired McNemar definition](https://www.stat.ethz.ch/R-manual/R-devel/library/stats/html/mcnemar.test.html),
[exact paired binomial calculation](https://pdixon.stat.iastate.edu/stat511/notes/part%202b.pdf).

## Pre-outcome source and design identities

```json
{
  "python/virtual_ecu/clo_dsf_holdout.py": "25ebafd477f27f1df4a997017931e06df8483a5d134b791e1d35b2198a2c3294",
  "python/virtual_ecu/clo_dsf_holdout_reporting.py": "587b20d69958c7cf01685e1967f94d520f2198375fe27e14c81691fd9bdd8c16",
  "results/cross_layer_safety_v8_final_holdout/configuration_overlap_audit.csv": "f02e5393d01f0dd3d25cd45c704f7211fc1828b28c43784f295f46d2c7ecac68",
  "results/cross_layer_safety_v8_final_holdout/final_holdout_manifest.csv": "883efd805752747cabd795452b758aa8b274ea472c317ba52e7c8361bd4a97c8",
  "scripts/run_clo_dsf_final_holdout.py": "343c48024d52e3f0bdda2ce04a6b800f1bd496d280da29630058adde14613102",
  "scripts/validate_clo_dsf_final_holdout.py": "cea15f198d40614b2b3971969a8964337a982ed7a0d96d2dce2a03dd87452a90",
  "tests/test_clo_dsf_holdout.py": "e3c46035b422d210cb3e83853bcad5b331d1aba961a91253f85dd62b9699ea97"
}
```

## Pre-outcome serialization amendment

2026-09-18T14:38:32.984785+00:00 UTC. The first process stopped in profile loading before any simulation (zero completed cases). JSON key order had been used as positional CSV column order. Only materialization now uses the C reader's required seven-column order. The public C profile loader and coverage validator now check every command before execution. All manifest values, profile semantics, seeds, case selection, metrics, decision rules, detector and baseline identities remain unchanged. The original source/protocol contents and hashes are preserved in paper_tables/pre_outcome_registration_history.csv. The erroneous input attempt is not represented as an observed simulation. This explicit pre-outcome amendment authorizes one execution of the same 1500 configurations, with no substitution or tuning.

Updated pre-outcome identities:
```json
{
  "python/virtual_ecu/clo_dsf_holdout.py": "e3900214dbbeb2df5bfcf8e033e0798515321398f0adca4bf5fff1c9f86a8d69",
  "python/virtual_ecu/clo_dsf_holdout_reporting.py": "587b20d69958c7cf01685e1967f94d520f2198375fe27e14c81691fd9bdd8c16",
  "results/cross_layer_safety_v8_final_holdout/configuration_overlap_audit.csv": "f02e5393d01f0dd3d25cd45c704f7211fc1828b28c43784f295f46d2c7ecac68",
  "results/cross_layer_safety_v8_final_holdout/final_holdout_manifest.csv": "883efd805752747cabd795452b758aa8b274ea472c317ba52e7c8361bd4a97c8",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/pre_outcome_registration_history.csv": "af69e95d6d37392828b7f5cd74bddd86380734110cc3bc5b0031feeafe95a0a6",
  "scripts/run_clo_dsf_final_holdout.py": "2c32ce0ae453896500dc644b67a9af330b487e858e6b02cbf6c084527e8505a0",
  "scripts/validate_clo_dsf_final_holdout.py": "66cdf58a14b3b435437633f35d3d7b66fab5034dff87fc4c4675f00cc13ea403",
  "tests/holdout_configuration_check.c": "d152c979bbfeb69f880d6a39a6dbcd651e7d6197fae2d54ea8808c7ce97a9867",
  "tests/test_clo_dsf_holdout.py": "f07045688399f1395aab3b4a7f9a3026c5a6f0b35d68afc90c3b12928674d491"
}
```
