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

The Dashboard offers Guided Experiment, Research / Validation, and Advanced
Experiment Builder. The sidebar groups experimentation, research, reporting and
advanced work. Existing saved page indices and internal page IDs remain compatible.
Final Validation is a separate page under REPORT.

The v6.2 sidebar has HOME (Dashboard), EXPERIMENT (Run Experiment, Compare Results,
Propagation Path, Cross-Layer Safety), RESEARCH (Research Analysis, RTL Security),
REPORT (Exports, Final Validation), and ADVANCED (Experiment Builder).

## Which workflow should I use?

| Workflow | Use it for |
| --- | --- |
| Guided Cross-Layer Experiment | One memory, timing, communication, sensor/control or actuator fault. Start here. |
| Run Experiment / Compare Results | Predefined comparison stories or saved left/right CSV results. |
| Propagation Path | Inspect fault origin, ECU effects, actuation and plant outcome. |
| Research Analysis → Aggregate Analysis | Aggregate campaigns and per-fault findings. |
| Research Analysis → Detector Study | Runtime detector/action comparisons; detection and intervention are shown separately. |
| Research Analysis → Parameter Sweep | Fault-severity and detector sensitivity; tied metrics remain ties. |
| RTL Security | HT1–HT4 hardware Trojan studies and their loaded trigger/payload metadata. |
| Advanced Experiment Builder | Staged, multi-fault or custom scenarios, presets and timelines. |
| Final Validation | Frozen v5/v6 research evidence and reproducibility controls. |
| Exports | Snapshot, full comparison report or presentation bundle. |

## Research Analysis

Research Analysis opens an Overview with three optional research utilities:

1. **Aggregate Analysis** summarizes many completed campaign runs, including
   per-fault averages, detection trends and thermal/safe-state outcomes. This general
   viewer does not define the final frozen v5/v6 validation evidence.
2. **Detector Study** compares detection algorithms and intervention actions.
   Detection performance and intervention outcome remain separate sections.
3. **Parameter Sweep** evaluates sensitivity to fault severity, duration and
   activation timing. Its summary cards use loaded values and name every tied
   detector; detailed detector and parameter tables remain below.

The internal selectors keep all three tools in the main workspace. Switching views
never runs a study. Returning through the sidebar remembers the last view during
this session; Overview remains available in the selector bar. Old `batch`,
`runtime_study`, and `parameter_sweep` IDs and saved notebook indices still open
these views. Existing loaders, result folders and study commands are unchanged.

For a first experiment, use **Dashboard → Start Guided Experiment**. For final paper
evidence, use **Final Validation**. For **HT1–HT4**, use the independent **RTL Security**
page. Research Analysis is not a mandatory step in a single experiment.

## A first guided experiment

1. On Dashboard, select either **Start Guided Experiment** button. It always opens
   Cross-Layer Safety with Guided selected, retaining all Advanced values.
2. Keep **Memory → bit_flip → transient** for the existing example, or choose a
   supported layer/model/behavior. The form shows only relevant parameters.
3. Select **Run Experiment**. The existing background worker keeps the interface
   responsive. Scroll to Experiment results to inspect the summary, interpretation,
   visual path and exact propagation timestamps.
4. For comparison, open **Run Experiment**, load the generated raw CSV at left and
   a reference CSV at right, then use **Compare Results** and **Propagation Path**.
5. Select **Exports**. Last Export records the actual successful destination in this
   session; unavailable exports remain disabled.

**Guided / Advanced are visual modes.** Switching modes preserves every configured
value and does not change the backend command. Advanced exposes seed and the safety
contract alongside all model-relevant fields. Intermittent ON/OFF appears only for
intermittent faults. Permanent duration is hidden, retaining the existing value.
A transient deadline miss retains the original single 100 ms tick rule. The legacy
sensor and actuator models offer only their supported transient/permanent behavior.
Stuck-at-0/1 uses **stuck_bit** with polarity 0/1, not a new fault model.

The Advanced Safety Contract starts collapsed in Guided. Its original values are
FTTI 5000 ms, warning 108 °C, critical 115 °C, maximum critical exposure 1000 ms.
Both independent response selectors remain visible in the compact **Monitoring** subsection. Hover or keyboard-focus an
annotated field for technical help. No visual mode resets an advanced value; check
your values before running a controlled study.

Before loading a run, the results area offers Run Example, Load V5 Validation and
Load Latest Results. **Run Example executes the currently configured example**;
it does not silently replace your configuration. Load Latest opens the last local
v6.1 single run. New single runs overwrite that scratch run; copy it before running
another case if you need to retain both. Studies and campaigns retain their own
subdirectories under `results/cross_layer_safety_v6_1/runtime/`.

Loaded historical values remain **N/A** when unavailable. A reached propagation
stage is supported by a recorded timestamp. N/A can mean unavailable or not reached;
it is not silently converted to “no”. Safe-state application alone does not prove
containment. The results interpretation repeats observed values without inferring
missing hazard or safety outcomes.

Compare Results shows Left Case, Right Case and Key Difference cards. The key
fact comes from the existing verdict or recorded cross-layer temperatures;
**Detailed Comparison Summary** retains the longer evidence and verdict. Missing
cases remain N/A. The original figure selector, plots and propagation tables stay
available below.

The Advanced Experiment Builder's result area shows the current single/multi-fault
configuration, staged event count, detector and action before execution. Run Scenario
and Compare vs Baseline use the existing callbacks. With no staged events it offers
Add Event and a Guided link; at least two events are still required for a multi-fault
run. Loaded results replace this empty state.

Final Validation presents eight cards using the loaded v6 fields, plus the current
recommended timing monitor and default safety policy. Confidence intervals and
scientific limitations remain visible. Missing evidence produces N/A cards.
It retains Load Final Validation, Open Final Report, Run Quick
Reproducibility Check and Regenerate Analysis. It loads accepted v6 by default;
new checks and analysis copies go to `results/cross_layer_safety_v6_1/final_validation/`.
The frozen evidence remains in its original folders. If a generated copy becomes
stale after a source edit, regenerate analysis before running Quick Check again.

Presentation Mode increases table/body readability and reduces optional helper text;
it does not change fault parameters, detector settings, scientific data or commands.
Wide scientific tables retain their horizontal scrollbars. On laptop windows,
paired propagation diagrams and the advanced builder/inspector stack vertically.

The final research recommendation is combined timing observation and no new policy
action by default. Legacy CLI and single-run GUI controls retain their original
monitor-disabled default; select Observe Only explicitly when testing that research
configuration. Existing legacy safety/diagnostics are still active.

## One timing fault, with explicit observation settings

```bash
mkdir -p results/cross_layer_safety_v6_1/runtime
./virtual_ecu results/cross_layer_safety_v6_1/runtime/example.csv baseline \
  --cross-layer-fault task_delay --fault-layer timing --fault-target control_task \
  --fault-behavior transient --fault-start-ms 45000 --fault-duration-ms 1000 \
  --task-delay-ms 300 --seed 42 --hazard-monitor on \
  --timing-monitor observe_only --timing-evidence combined \
  --communication-safety-response observe_only \
  --detector hybrid_adaptive_kalman --detector-action observe_only
```

The CSV and companion C summary are generated under v6.1 runtime. Load the raw CSV
with Cross-Layer Safety → Load Results. Do not substitute unsupported durations or
behaviors for legacy models: for example, a transient deadline miss is one tick.

## Campaign and historical analysis

A small existing five-case study is useful for exploring the interface:

```bash
python3 scripts/run_cross_layer_safety_study.py \
  --output-dir results/cross_layer_safety_v6_1/runtime/five_case_study
```

To execute the accepted v2 campaign configuration in a new directory:

```bash
python3 scripts/run_cross_layer_campaign.py studies/cross_layer_vts_candidate_v1.yaml \
  --output-dir results/cross_layer_safety_v6_1/runtime/campaign
```

Reanalyze the accepted v2 inputs with their existing v3 semantics:

```bash
python3 scripts/analyze_cross_layer_safety.py \
  --input results/cross_layer_safety_v2 \
  --output results/cross_layer_safety_v6_1/runtime/v3_analysis
```

Explicit destinations keep old evidence immutable. Existing legacy scripts retain
their historical default output directories, so use the v6 orchestrator or an
explicit new output path when reproducing a study.

## Final reproducibility and paper evidence

```bash
python3 scripts/run_cross_layer_reproducibility_package.py --quick-check \
  --output-dir results/cross_layer_safety_v6_1/final_validation
python3 scripts/run_cross_layer_reproducibility_package.py --analysis-only \
  --output-dir results/cross_layer_safety_v6_1/final_validation
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

## GUI regression checks

```bash
python3 -m unittest discover -s tests
python3 tests/gui_v61_desktop_checks.py
```

The opt-in desktop check needs an X11/WSLg graphical session and the existing Pillow
installation for screenshots. It exercises normal background workers, redirects
history/session/export writes, checks v1–v6 loaders, and captures every page at
1366×768, 1920×1080 and 2560×1440. It saves its report and screenshots under
`results/cross_layer_safety_v6_1/validation/`. The standard suite stays headless.

The v6.1 command fixtures were captured from the unmodified v6 GUI at `8cb44d9`.
They cover 42 model/behavior/default-or-advanced combinations. An additional AST
integrity check protects 400 original GUI command, loader, export and analysis
functions while allowing the documented presentation methods to change. The
original scientific source/evidence lock is unchanged.
