# Virtual ECU cross-layer platform user guide

This is a C research thermal/control ECU prototype with modular fault injection,
runtime observation, detectors, timing supervision, safety response and CSV evidence.
It supports experiments and paper preparation. It is not a certified ECU or a
validated digital twin of a specified vehicle.

Run commands from the repository root. Use the existing Python environment with
PyYAML and Matplotlib; GUI use requires Tk and a graphical display. GCC and make
build the C core. RTL reproduction additionally uses the existing Verilog toolchain.
V6 introduces no new dependency. Local evidence folders are intentionally ignored by
Git: a source checkout alone does not contain the accepted research dataset.

## Build and launch

```bash
make
python3 scripts/virtual_ecu_gui.py
```

The application retains its existing pages. In Cross-Layer Safety, use the original
single-run/campaign controls or version-specific loaders. The compact Research
Summary / Final Validation panel has Load Final Validation, Open Final Report,
Run Quick Reproducibility Check and Regenerate Analysis. Background work leaves the
GUI responsive. A missing package shows N/A and regeneration guidance.

The final research recommendation is combined timing observation and no new policy
action by default. Legacy CLI and single-run GUI controls retain their original
monitor-disabled default; select Observe Only explicitly when testing that research
configuration. Existing legacy safety/diagnostics are still active.

## One timing fault, with explicit observation settings

```bash
mkdir -p results/cross_layer_safety_v6/runtime
./virtual_ecu results/cross_layer_safety_v6/runtime/example.csv baseline \
  --cross-layer-fault task_delay --fault-layer timing --fault-target control_task \
  --fault-behavior transient --fault-start-ms 45000 --fault-duration-ms 1000 \
  --task-delay-ms 300 --seed 42 --hazard-monitor on \
  --timing-monitor observe_only --timing-evidence combined \
  --communication-safety-response observe_only \
  --detector hybrid_adaptive_kalman --detector-action observe_only
```

The CSV and companion C summary are generated under v6 runtime. Load the raw CSV
with Cross-Layer Safety → Load Results. Do not substitute unsupported durations or
behaviors for legacy models: for example, a transient deadline miss is one tick.

## Campaign and historical analysis

A small existing five-case study is useful for exploring the interface:

```bash
python3 scripts/run_cross_layer_safety_study.py \
  --output-dir results/cross_layer_safety_v6/runtime/five_case_study
```

To execute the accepted v2 campaign configuration in a new directory:

```bash
python3 scripts/run_cross_layer_campaign.py studies/cross_layer_vts_candidate_v1.yaml \
  --output-dir results/cross_layer_safety_v6/runtime/campaign
```

Reanalyze the accepted v2 inputs with their existing v3 semantics:

```bash
python3 scripts/analyze_cross_layer_safety.py \
  --input results/cross_layer_safety_v2 \
  --output results/cross_layer_safety_v6/runtime/v3_analysis
```

Explicit destinations keep old evidence immutable. Existing legacy scripts retain
their historical default output directories, so use the v6 orchestrator or an
explicit new output path when reproducing a study.

## Final reproducibility and paper evidence

```bash
python3 scripts/run_cross_layer_reproducibility_package.py --quick-check
python3 scripts/run_cross_layer_reproducibility_package.py --analysis-only
```

No mode argument also selects quick-check. Quick-check builds, runs the full test
suite, replays eight representative accepted configurations, verifies source/evidence
locks, and checks artifact/claim references. It creates a missing local final package.
If an existing generated artifact is stale, the check fails; regenerate analysis
rather than silently blessing stale content. A changed *accepted* input is rejected
by both modes and must be restored from the accepted evidence distribution.

Analysis-only reads frozen evidence, regenerates five table sources in CSV/Markdown/
LaTeX form, four curated figures, claim/audit/story/outline documents and a local
final report. It indexes existing raw files in place. It does not rerun the simulator,
collect a new host benchmark or overwrite an accepted package. Unchanged evidence
and software produce byte-identical final analysis artifacts; transient check logs
and machine-specific runtime outputs are excluded from that comparison.

For the complete selected timing, communication, cross-layer, recovery and matched
validation workflows, plus legacy/RTL checks:

```bash
python3 scripts/run_cross_layer_reproducibility_package.py --full
```

FULL warns that it executes many simulations. It reproduces the accepted v5 design
in `results/cross_layer_safety_v6/full_reproduction/v5`, verifies raw hashes and
scientific metrics, and regenerates the v6 analysis. It also compares 48 legacy
configurations against C built from the accepted Git commit and runs 64 RTL cases.
No new matrix is created. Keep the accepted Git history available for this baseline
build. Host overhead remains the accepted v5 measurement, since another noisy
collection is not evidence of better performance.

Use `--output-dir` to choose a separate package directory. Output overlap with
accepted evidence, including symlink aliases and parent directories, is rejected.
Accepted source/configuration/artifact hashes are in the tracked study evidence lock;
large generated result folders need not be tracked. Missing accepted files require
restoring the research evidence package before these checks can pass.

## Result versions and interpretation

| Version | Role and loader |
| --- | --- |
| Legacy CSV | Original simulator logs; load through existing application or Cross-Layer Load Results; unavailable new fields stay N/A |
| v1 | Cross-layer framework and five-case demonstration; Load Results |
| v2 | Configured campaigns and hazard/FTTI instrumentation; Load Campaign Results |
| v3 | Consequence-conditioned observability analysis; Load v3 Analysis |
| v4 | Timing observation and response development studies; Load v4 Runtime Safety |
| v5 | Frozen holdout, legal/overload stress, paired policies, recovery, matched temporal and host overhead evidence; Load V5 Validation |
| v6 | Final configuration, claim traceability, curated paper artifacts and reproducibility; Load Final Validation |

The accepted directories remain `results/cross_layer_safety_v1` through `v5`.
V6 reports are under `results/cross_layer_safety_v6`; tables and figures use
`paper_tables/` and `paper_figures/`. `manifests/artifact_manifest.csv` records paths,
row counts, sizes and hashes. `paper_artifact_traceability.csv` records source columns,
filters and claim IDs. New GUI experiments use `v6/runtime/`. Verification records
and GUI operation logs use `v6/validation/`.

Seeds matter only where a mechanism actually uses randomness. Legal scheduler jitter
uses deterministic seeded variation. A changed seed on a deterministic fault is not
an independent replicate. Repeated runs verify reproducibility and do not enlarge
statistical denominators. Policy/ablation comparisons remain paired; shared temporal
comparison traces are counted once in unique-run summaries.

Runtime observations feed the timing monitor and policy. Evaluation truth and paired
fault-free references establish injection, propagation, hazard and containment.
Legacy residual detectors and diagnostic bookkeeping still have simulation truth
or scenario dependencies; see the [boundary document](detector_observability_boundary.md).
An alarm is not containment, a safety request is not detection, a plant deviation is
not necessarily a hazard, and an absent endpoint is not numeric zero.

The platform does not establish fleet reliability, zero population false-positive
probability, universal hazard prevention, embedded WCET, certified ISO 26262 compliance,
full digital-twin fidelity or causal fault-class superiority. Stronger claims require
the [independent validation roadmap](independent_validation_roadmap.md).
