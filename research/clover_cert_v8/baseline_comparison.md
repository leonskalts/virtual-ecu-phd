# Fair finite algorithm comparison

All methods use identical v7 executions, menus, deadlines, target singleton/UNKNOWN decisions and joint objective. Six real component cases (two contexts × three deadlines) each enumerate 64 contracts. Six explicitly synthetic scaling cases are separate; no synthetic row is ECU evidence.

## Implemented methods

- **A_pairs:** direct exhaustive history-pair compatibility for every contract, followed by the shared compact checker generator.
- **B_boolean:** exact positive-clause formulation; compile required-pair differences once per period, remove subsumed clauses and evaluate all assignments as a bit-vector truth table. This is a generic finite Boolean baseline, not an SMT/BDD implementation. Z3 and cvc5 are unavailable; no extra dependency was installed.
- **C_cuts:** conventional critical-pair clause learning. A failed explicit check adds its exact separating clause. Contracts violating learned clauses are rejected before another explicit check. All remaining feasible contracts get the same checker/cost computation.
- **C_coi_cuts:** C with the conservative source-provenance support prefilter. This is a known cone-of-influence relaxation, not a distinct proposed method D.
- **D:** NOT IMPLEMENTED because the candidate rule reduced to existing transformations.

The comparison does not benchmark the published authors’ software. In particular, these Python implementations are not NuSMV, Kang’s joint diagnoser, Li’s cyclic-model algorithm, a Büchi-game solver or R2U2. They test the bounded reduction and cost preservation, not state-of-the-art performance superiority.

For real cases, the CSV domains=5 denotes five logical origin-mutation groups used by the support map, not five independent or protected physical domains. All fields still share the unresolved process boundary. Only the synthetic domain-count axis denotes the explicit correlated-overwrite partition defined by that synthetic generator.

## Exact results on source-backed cases

| Case | Feasible contracts / 64 | Optimum read+state cost | Optimum contracts (period:bundle mask) |
|---|---:|---:|---|
| zero_command_100 | 3 | 29 | 100:15, 100:30 |
| zero_command_200 | 3 | 47 | 100:15, 100:30 |
| zero_command_400 | 3 | 83 | 100:15, 100:30 |
| positive_command_100 | 4 | 22 | 100:11 |
| positive_command_200 | 4 | 38 | 100:11 |
| positive_command_400 | 4 | 70 | 100:11 |

All four implementations return exactly the same full feasible sets, per-contract costs, optimum values and complete optimum sets on all 12 cases. The independent tests also compare exact clauses, decisions and all checker prefixes. No UNKNOWN is converted into an unsupported specific origin.

## Measured runtime, memory and work at 400 ms

| Context / method | Median ms | Python peak bytes | Candidate nodes | Pair tests | Preprocessing pair visits | Boolean tests | Explicit oracle calls | Solver calls | Checker builds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| zero_command_400/A_pairs | 36.077 | 173426 | 64 | 287296 | 0 | 0 | 64 | 0 | 3 |
| zero_command_400/B_boolean | 25.917 | 132306 | 64 | 0 | 4936 | 224 | 0 | 0 | 3 |
| zero_command_400/C_cuts | 5.620 | 142394 | 64 | 35912 | 0 | 87 | 8 | 0 | 3 |
| zero_command_400/C_coi_cuts | 18.390 | 133518 | 64 | 31423 | 4936 | 199 | 7 | 0 | 3 |
| positive_command_400/A_pairs | 33.949 | 226993 | 64 | 287296 | 0 | 0 | 64 | 0 | 4 |
| positive_command_400/B_boolean | 30.039 | 187225 | 64 | 0 | 5880 | 192 | 0 | 0 | 4 |
| positive_command_400/C_cuts | 6.651 | 197361 | 64 | 44890 | 0 | 101 | 10 | 0 | 4 |
| positive_command_400/C_coi_cuts | 20.453 | 197157 | 64 | 31423 | 5880 | 101 | 7 | 0 | 4 |

Each runtime is the median of three untraced perf_counter_ns runs, including target construction, method preprocessing, contract checks and feasible checker generation. Input JSON loading is outside the timer. Memory is a separate tracemalloc run measuring peak Python allocations after inputs are loaded; it is not RSS, a total system-memory bound or deployed checker RAM. Fixed method order and microbenchmark scale limit timing conclusions.

“Candidate nodes” counts complete assignments visited, not internal solver or transition-system states. “Pair tests” counts explicit history equality tests; “preprocessing pair visits” separately counts support/difference-set extraction. Boolean tests are clause/assignment or membership evaluations. Solver calls are zero; explicit reference-oracle calls are not mislabeled as SMT calls. No compiled checker, executable-size measurement, hardware-memory measurement or WCET evidence is produced.

## Synthetic one-axis scaling

| Synthetic case | Origins | Domains | Timestamps | Bundles | Contracts | A ms | B ms | C ms | C+COI ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| synthetic_base | 4 | 2 | 3 | 5 | 64 | 1.379 | 0.807 | 0.959 | 0.961 |
| synthetic_origins_8 | 8 | 2 | 3 | 5 | 64 | 2.995 | 2.040 | 1.874 | 1.787 |
| synthetic_domains_4 | 4 | 4 | 3 | 5 | 64 | 1.517 | 0.962 | 1.246 | 1.221 |
| synthetic_timestamps_6 | 4 | 2 | 6 | 5 | 64 | 2.642 | 1.945 | 2.471 | 2.650 |
| synthetic_observations_8 | 4 | 2 | 3 | 8 | 512 | 12.960 | 6.854 | 9.732 | 9.997 |
| synthetic_joint | 8 | 4 | 6 | 8 | 512 | 54.587 | 36.742 | 54.386 | 54.829 |

Synthetic generation is deterministic: each origin has two realizations; after t=0 one realization sets all fields in its origin-selected common domain to zero, while the other retains generated bits. This tests correlated evidence changes, not physical attacks. Domain count, origins, time points and candidate fields vary from a disclosed base fixture. The support filter uses the universal safe bound on synthetic data, because there is no source-backed ECU graph for it. These tiny cases are functional scaling probes, not asymptotic lower-bound families.

## Mechanism challenge result

The source support prefilter is slower than conventional exact-clause learning on **6 of 6 real cases** in this run, despite rejecting some candidates before explicit pair checking. Its preprocessing cost is included. No measured advantage over C is established by fewer oracle calls alone.

The main mathematical finding is independent of these timings: support pruning is a relaxation of ordinary critical-pair clauses. Even a favorable timing would not make that rule distinct. The finite implementation confirms the reduction rather than demonstrating a new synthesis method.

The common objective is preserved by using the identical minimized finite-prefix checker for each feasible contract. This does not prove an optimal physical monitor or the best possible diagnosis algorithm; it optimizes the specified menu and fixed completed-prefix behavior only. All v6/v7 assumptions remain unresolved.
