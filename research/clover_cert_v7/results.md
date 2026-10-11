# CLOVER-CERT v7 measured results

These are finite component-model results. Model traces and actual isolated C-component observations are separate artifacts. No full closed-loop or deployed ECU result is claimed.

Analyzed **10 distinct fault-origin pairs** in **240 context/policy/deadline checks**. Each context has 66 fault realizations plus one healthy realization. Independent world choices are exhaustively crossed; no random seeds or sampling were used.

There are **62 conditionally disjoint pair checks** and **178 overlapping pair checks**. Saved 24 replayable ambiguity-history representatives, plus a counterexample for each overlapping pair check. These counts include different deadlines/views of the same executions and are not independent trials.

## Frontier at 400 ms

| Context | View | Executions | Histories | Unique-origin histories | Ambiguous histories | UNKNOWN executions | Earliest unique (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| zero_command | values_100 | 67 | 9 | 8 | 1 | 57 | 100 |
| zero_command | timestamp_100 | 67 | 13 | 12 | 1 | 45 | 100 |
| zero_command | full_100 | 67 | 25 | 24 | 1 | 19 | 100 |
| zero_command | full_200 | 67 | 8 | 7 | 1 | 34 | 200 |
| positive_command | values_100 | 67 | 25 | 24 | 1 | 33 | 100 |
| positive_command | timestamp_100 | 67 | 29 | 28 | 1 | 21 | 100 |
| positive_command | full_100 | 67 | 33 | 32 | 1 | 11 | 100 |
| positive_command | full_200 | 67 | 10 | 9 | 1 | 28 | 200 |

Full 100/200/400 ms frontier: `diagnosability_frontier.csv`. Each row includes its assumption IDs, observation count, scalar field-read cost and unminimized history-trie node count. Costs are operation/storage proxies, not host WCET or optimized automaton sizes. Each positive history and its earliest singleton time is in `conditional_positive_histories.json`.

UNKNOWN is counted per compatible history and per realization separately. A singleton history identifies the origin only within this finite model. No frequency distribution over executions is justified; no count is reported as diagnostic coverage.

## Concrete ambiguity and conditional separation

At constant 60 C/load zero, world A forces already-zero register bit 0 to zero during [100,200) ms; world B scales the pump by 0.5 during [100,200) ms. Both acquire/deliver 60 C, retain target/shadow 92, execute at every tick, and issue/realize pump 0 throughout. Full selected observations at 0,100,200,300,400 ms coincide exactly. Both are implemented paths; neither is a fabricated witness. Healthy and a missed legacy sensor window also share this history. A sound checker returns UNKNOWN.

At 92 C/load zero with full_100 and deadline 400 ms, timing versus actuator origins are conditionally separable over all independently selected finite realizations: timing retains an earlier control_execution_ms at a skipped/delayed tick, whereas pump degradation does not prevent execution. A pump gap at positive command is also observed in the isolated component model. These are not independently verified physical feedback contracts.

Replay at age 100 ms leaves constant measured values unchanged; source timestamp/age separates these communication realizations from fresh healthy/latent-memory histories under intact metadata. Delay/drop/replay mechanisms can still be identical to each other: replay-age-100, first-drop and delay-100 over [100,200) all retain the t=0 sample at t=100 and recover at t=200. Mechanism attribution is not claimed.

## Validation and limits

The independent C harness invokes unchanged fault, sensor, delivery, timing, control, actuator and capture modules. All **134 executions / 670 rows** matched Python predictions exactly, with **zero discrepancies**. The harness omits thermal evolution and safety/detector reactions; passing this comparison does not validate those omitted paths. Build command, compiler, binary/source hashes and each run command are recorded in `ecu_comparison.json` and `actual_component_observations.json`.

Run `test_reference_oracle.py` for exhaustive soundness, independent scan/index agreement, full pair cross-product checks, counterexample replay, policy/time monotonicity, one-bit numerical sensitivity, physical-path boundary cases and imported-anchor checks. Actual test outcome is in `test_results.json` / `tests.log`.

All 41 v6 findings are retained verbatim in `v6_import_verification.json` and `two_world_model.json`. No physical certificate and no PROVEN_SEPARABLE_WITH_VERIFIED_CONTRACTS result is emitted. The novelty gate is **NO-GO** for a novelty claim; this implementation is an exhaustive reference baseline.

Preservation status is independently recorded in `preservation_report.json`. No pre-existing file is rewritten by the runner.
