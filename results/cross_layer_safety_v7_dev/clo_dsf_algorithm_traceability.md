# Algorithm and evidence traceability

All claims here are DEVELOPMENT, not independent holdout results.

| Requirement / output | Implementation / evidence |
|---|---|
| DS mass algebra, belief/plausibility/BetP, discount, Dempster/Yager | `include/ds_evidence.h`, `src/v7/ds_evidence.c`; hand examples in `tests/clo_dsf_unit.c` |
| Runtime channels and monotonic mass assignment | `src/v7/clo_dsf.c:extract`, `clo_evidence_mass`; detailed equations in `docs/clo_dsf_algorithm.md` |
| Architectural observability (not injected origin) | `src/v7/clo_observability.c`; direct/indirect/unavailable unit tests |
| Propagation episodes / allowed graph / bounded adjustment | `clo_propagation_edges`, `propagation`; forward/incomplete/reversed/future tests; transition mask and reliability columns |
| Temporal persistence and recovery | `clo_dsf_step`; transient/persistent/intermittent/recovery/long-benign tests |
| Runtime integration without frozen source changes | `GNUmakefile`, `src/v7/clo_runtime.c`; original scheduler detector call wrapped at link time |
| Ground-truth isolation | transitive allowlist test; hidden-label invariance using two ECU states and identical observable signals; ignored legacy DTC/alarm fields |
| Evaluation truth / scoring separation | adapter `score_step` only uses evaluation start; Python evaluator reads accepted reference-based manifestations; no score feeds detector |
| Episode-based detection and first-alarm localization | metrics/*.csv; exact definitions registered before selection in protocol |
| Grouped 576/336 split / 912 configs | studies YAML; `development_split_manifest.csv`; seed and group column; design integrity tests |
| Eight TRAIN-only global candidates | `clo_dsf_parameter_search.csv`, `selection_record.json`; validation mode excludes candidate bank |
| Primary results and denominators | `clo_dsf_dev_runs.csv`, `clo_dsf_dev_summary.csv`, layer/localization/uncertainty CSVs |
| All baseline and ablation outcomes | `clo_dsf_baseline_comparison.csv`, `clo_dsf_ablation.csv`; same trajectories, no tuning after validation |
| Runtime evidence, no labels | traces/*.clo_dsf.csv.gz; original CSV bytes with deterministic gzip headers |
| Confusion matrix including UNKNOWN/misses | `clo_dsf_origin_confusion.csv`; row label is evaluation-only |
| Representative traces selected without favorable-outcome filtering | first validation run ID per origin; `traces/representative_cases_evaluation_only.csv` |
| Every executed command and original experiment traces | commands/*.json; raw/*.csv.gz; generated profiles/*.csv |
| GUI additive experimental access | `clo_dsf_gui.py`, Cross-Layer Advanced selector, Research Analysis / Detector Study panel; sidecar allowlist |
| Host cost and memory | `clo_dsf_overhead.json`, `scripts/benchmark_clo_dsf.py`; no embedded WCET |
| Frozen scientific regression | `scientific_regression.json`, validation/legacy, validation/rtl, validation/quick_runs |
| Failed pre-selection execution disclosed | `development_attempt_1.log`, `execution_corrections.md`; no algorithm/parameter change |

TRAIN candidate results selected online in C are authoritative for selected TRAIN
CLO-DSF metrics. TRAIN sidecar archives record the initial candidate 0 (Yager);
VALIDATION sidecars and all six publication trace examples record selected candidate
1 (Dempster). These are not interchangeable. No TRAIN sidecar is relabeled to
pretend it used the selected rule. The run CSV includes all eight actual TRAIN
candidate outputs; initial A1/A2 TRAIN comparisons also use the initial rule.
The requested A0–A3 ablation is exclusively on VALIDATION using the selected rule.
