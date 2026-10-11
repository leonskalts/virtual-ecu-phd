# Reproducibility and preservation

Repository HEAD: `a340ca5cf0473d7dc572f7cd63e44fbc25b175a7`. The working tree includes pre-existing user changes and untracked research, so HEAD alone is not the input identity. `research_import.json` records hashes of all 44 v6/v7 artifacts read, including structured results, scripts, logs, inventories and the v7 binary. All 134 v6 anchors and 36 source hashes were rechecked. `workspace_baseline.json` records all 43,732 pre-existing files outside v8 and `.git`.

Run from repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 research/clover_cert_v8/run_validation.py
```

The runner verifies the fixed import, regenerates the bounded comparison and measured report, runs every new test and checks preservation. It writes only into v8. Do not replace its baseline or import hashes merely to make a changed checkout pass. The full preservation scan streams approximately 13.6 GB locally and may dominate runtime.

To rerun only individual stages:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 research/clover_cert_v8/compare_methods.py
PYTHONDONTWRITEBYTECODE=1 python3 research/clover_cert_v8/report_results.py
PYTHONDONTWRITEBYTECODE=1 python3 research/clover_cert_v8/test_reduction.py
```

Python standard library only. No dependency installation, production build, GUI launch or existing experiment runner is needed. The test suite imports v7's reference module read-only with bytecode disabled and never calls its output-generating entry point. It does not overwrite v6/v7 results or rerun the C harness.

`benchmark_environment.json` records Python/platform, measurement scope and tool limitations. This session found neither Python z3/sympy nor z3/cvc5 executables; B therefore uses exact finite propositional bit vectors rather than an SMT engine. No comparison with actual SMT solver performance is claimed.

## Bounds and measurements

- Real data: 67 executions per context, including healthy; two fixed-input component contexts; deadlines 100/200/400 ms; source acquisition every 100 ms.
- Menu: five field bundles, all subsets, capture every 100 or 200 ms; 64 contracts for each of six real cases.
- Synthetic: deterministic bit streams with origin-dependent common-domain overwrites; vary origins 4→8, domains 2→4, timestamps 3→6, bundles 5→8, and one combined case. These are not ECU observations or verified physical fault models.
- Seed: none; no random sampling. Numerical tolerance: zero; v7 binary32 hex values are compared without conversion or rounding.
- Objective: scalar reads + reduced finite Moore-checker states, unit weights. No compiled checker is measured.
- Runtime: three untraced samples and their median. Memory: one separate tracemalloc peak. This is Python allocation accounting above preloaded input, not total RSS/physical memory or WCET. All method-specific preprocessing is timed and counted.
- A/C oracle calls are explicit history compatibility checks; B uses no external solver. Zero solver calls means no solver was used, not a solved problem with no work.

## Expected validation

All four established-method implementations must return the same feasible set and per-contract costs, optimum value and optimum set for each case. Tests independently check exact clause equivalence, source support inclusion, all realized checker prefixes, UNKNOWN/sound origin answers, v7 decision agreement and invalid support examples. Formal proofs are in `proof_obligations.md`; successful tests alone are not those proofs.

`comparison_results.json` preserves every feasible cost and optimum; `comparison_metrics.csv` includes work/runtime/memory; `test_results.json` and `tests.log` record actual tests. `run_metadata.json` records the commands. `preservation_report.json` checks byte hashes, sizes, symlink targets, outside-v8 file set and HEAD; Git status snapshots give working-tree context.

The literature investigation is reproducible from the primary links and access notes in `prior_art_algorithm_matrix.md` and `bibliography_access.json`. It was a targeted algorithm collision check, not an exhaustive systematic review. Two requested journal full texts were not retrieved; their abstract-level information is kept distinct from inspected full papers/predecessors. No inaccessible algorithm was reconstructed from its abstract.
