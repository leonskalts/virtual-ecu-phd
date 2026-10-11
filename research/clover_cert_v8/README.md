# CLOVER-CERT v8 — algorithmic novelty challenge

**Verdict: NO-GO.** The investigated temporal-provenance pruning rule reduces to a conservative cone-of-influence bound and standard critical-pair observation clauses. No distinct method D is claimed or implemented. Start with [novelty_verdict.md](novelty_verdict.md).

| Required artifact | Purpose |
|---|---|
| [prior_art_algorithm_matrix.md](prior_art_algorithm_matrix.md) | All six requested works, mathematical collisions and full-text limitations |
| [formal_problem_v8.md](formal_problem_v8.md) | Exact finite input, requirements, runtime boundary and common cost objective |
| [candidate_algorithm.md](candidate_algorithm.md) | Precise falsifiable mechanism and explicit reduction to known transformations |
| [proof_obligations.md](proof_obligations.md) | Soundness, completeness conditions, invalidity cases and proof limits |
| [baseline_comparison.md](baseline_comparison.md) | Actual exact results, work counts, runtime/memory and labeled synthetic scaling |
| [reproducibility.md](reproducibility.md) | Commands, bounds, tooling, measurements and preservation |
| [novelty_verdict.md](novelty_verdict.md) | Exact decision and journal-algorithm maturity assessment |
| README.md | Entry point and full artifact inventory |

Reproduce using the standard library only:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 research/clover_cert_v8/run_validation.py
```

The prototype exists because the support rule is precise and falsifiable, even though it is not novel. It compares established A/B/C methods and a C+COI ablation on the same bounded problem. B is a finite Boolean backend; no SMT solver is installed. No production code is imported or altered. The v7 reference is imported read-only for an independent decision check, with bytecode disabled.

Supporting artifacts:

- `compare_methods.py`, `test_reduction.py`: finite comparison and independent tests.
- `report_results.py`, `run_validation.py`: measured report generation and preservation runner.
- `comparison_results.json`, `comparison_metrics.csv`, `comparison_summary.json`: exact feasible/optimum sets, counts and measurements.
- `benchmark_environment.json`, `benchmark.log`, `run_metadata.json`, `run.log`: environment, commands and execution logs.
- `tests.log`, `test_results.json`: actual test results.
- `bibliography_access.json`: primary sources and access scope, including unavailable journal texts.
- `research_import.json`: all 44 v6/v7 artifact hashes, rechecked anchors and 41 unchanged unresolved findings.
- `workspace_baseline.json`, `preservation_report.json`, `git_status_before.txt`, `git_status_after.txt`: preservation evidence for 43,732 pre-existing files and unchanged HEAD.

All outputs reside in this directory. No production C/Python, GUI, scheduler, detector, injector, v6/v7 artifact, HETIA result, historical experiment or Git history is changed. All positives remain finite-model conditional results; there is no physical certificate or publication-novelty claim.
