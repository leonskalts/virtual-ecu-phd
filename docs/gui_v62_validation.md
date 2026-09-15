# Cross-Layer Safety v6.2 GUI consolidation validation

The v6.2 pass builds directly on the unstaged v6.1 GUI at commit `8cb44d9`.
No reset, checkout, restore, clean, stage, commit or push was performed. Preflight
recorded 17 existing changed/untracked files and saved a working-tree patch, file
copies and the unrelated user session under `/tmp/vecu_v62_preflight/`. Durable
baseline hashes/status are in `results/cross_layer_safety_v6_2/validation/`.
The baseline suite passed **139 tests**.

## Delivered UI

The sidebar now contains exactly ten entries:

| Group | Entries |
| --- | --- |
| HOME | Dashboard |
| EXPERIMENT | Run Experiment, Compare Results, Propagation Path, Cross-Layer Safety |
| RESEARCH | Research Analysis, RTL Security |
| REPORT | Exports, Final Validation |
| ADVANCED | Experiment Builder |

Research Analysis provides a compact three-card Overview and a shared internal
selector for Overview, Aggregate Analysis, Detector Study and Parameter Sweep.
It reuses the v6.1 navy page header, palette, typography and action styles. Existing
research widgets stay in their original main-workspace frames; Tk widgets are not
reparented. The overview is appended at notebook index 12. Historical indices
5/6/7 and IDs `batch`/`runtime_study`/`parameter_sweep` still open their original
implementations with the common Research Analysis header and sidebar highlight.
The last subview is remembered in the current session; normal saved tab indices
also continue to work. Selecting a research view never launches a study.

Aggregate Analysis retains the actual 47-run CSV, original calculations, findings,
interpretation, per-fault table, plot selector and comparison view. A scope banner
clarifies that this general viewer does not define final v5/v6 evidence. Detector
Study retains the loaded **5 scenarios / 90 runs / 6 detectors / 3 actions**,
predefined/custom sources, reload/report/output/figure controls, with separate
Detection performance and Intervention outcome sections. Parameter Sweep retains
its run/load/export controls, detailed tables, breakdown and figures. The loaded
quick sweep remains **38 variants / 266 paper-facing runs / 7 detectors**.

Both actual Dashboard **Start Guided Experiment** buttons now select Guided and
navigate to Cross-Layer Safety. Advanced parameter values, backend requests and
monitor settings remain intact. Open Research Workspace opens Research Analysis;
direct navigation and presentation mode preserve the Cross-Layer visual mode.
Cross-Layer only adds a compact Monitoring subsection; relevant fields and the
collapsed Advanced Safety Contract retain v6.1 behavior and values.

Final Validation has eight responsive metric cards backed by the existing loaded
StringVars. Formatting separates ratios, percentages and pre-plant detail without
recomputing statistics. The accepted values are:

| Metric | Loaded evidence |
| --- | --- |
| Timing holdout coverage | 558/558 (100.00%) |
| Timing coverage 95% CI | 99.32–100.00% |
| Legal timing alarms | 0/156 |
| Legal false-alarm 95% CI | 0.00–2.40% |
| Plant-propagating timing detection | 33/33; pre-plant 33/33 |
| Cross-layer detection | 394/540 (72.96%) |
| Detection given plant propagation | 188/216 (87.04%) |
| Silent plant propagation | 28/216 |

Combined timing observation, Observe only (research preset), all four original
actions and the existing limitations text remain available. Missing evidence
produces N/A cards and an informative status. An added footer states the limits
of simulation confidence bounds, fleet reliability, embedded WCET, certification
and generalized hazard prevention.

Compare Results now has Left Case, Right Case and Key Difference cards, plus a
collapsed Detailed Comparison Summary. Case names use the loaded result metadata.
The key fact uses an existing verdict line or recorded cross-layer maximum
coolant values; it does not invent a scientific ranking. Detailed verdicts and the
cross-layer/legacy interpretation caveat remain accessible. Figures, selectors,
propagation tables and export callbacks remain unchanged.

Parameter Sweep displays Best Coverage, Best Median Latency, Hybrid Coverage,
Hybrid Median Latency and Clean Alarms. All tied names remain visible. The loaded
coverage tie is Kalman filter / Hybrid Adaptive Kalman at 100%; the latency tie is
Threshold / Hybrid Adaptive Kalman at 0 ms. Hybrid fields remain 100.0%, 0.0 ms and
0/1 clean alarms. The visible note says: “Ties are preserved; no artificial ranking
is applied.” Detailed tables retain the original values and ordering.

The builder empty result panel reports its current single/multi-fault state,
actual staged event count, detector and action. Run Scenario and Compare vs
Baseline dispatch the original single/multi callbacks. Zero events offers Add
Event and a Guided link; one event still requires another event before a multi
run. New buttons participate in the existing execution-disable mechanism. Loaded
results replace the empty state.

## Scientific and compatibility checks

- **145 headless tests pass**: 139 baseline tests plus six formatting/navigation
  contracts. Existing tests still compare all 42 original v6 GUI command fixtures.
- **181 live Tk checks pass**, with 51 drawable screenshots. These exercise both
  Dashboard buttons, saved indices, research reentry, no automatic study execution,
  loaded/missing final cards, original version-specific v1–v6 loaders, aggregate,
  detector/sweep results, builder event changes/callbacks, comparisons, session
  serialization and actual snapshot/report/presentation exports.
- One representative Guided bit-flip run used the normal background worker.
  Its raw CSV matches the pre-v6.2 run byte for byte. Detection is 1, latency 0 ms,
  plant manifestation 1, hazard entry 0, safe state 0, containment 1, depth 5.
- **48 legacy cases** match raw and C-summary bytes against the compiled accepted
  C commit. **64 RTL cases** match historical raw/C-summary fields and comparison
  metrics, excluding relocated paths and allowing the already appended schema
  fields. HT1–HT4 behavior is unchanged.
- All **78 scientific source files** and **10,693 accepted evidence files** retain
  their hashes and file sets. This covers v1–v6, frozen v5, HETIA paper evidence and
  RTL evidence. Hybrid, safety policies, timing, FTTI, fault grids and CSV scientific
  schemas are unchanged. The unrelated session file is byte-for-byte preserved.
- The original GUI execution guard retains **398 identical protected definition
  hashes**. Only `_navigate_to_page` and `_set_active_nav` move from the former
  400-definition guard into its explicit presentation exceptions. Every retained
  hash is identical to v6.1. Incremental AST auditing additionally finds only four
  main-GUI presentation/navigation methods changed; all 505 other main-GUI methods
  and functions are unchanged from v6.1. Cross-Layer execution/loading methods and
  Final Validation load/report/reproducibility callbacks are unchanged.
- `final_evidence.artifact_manifest` only adds new GUI resources to newly generated
  inventories; accepted manifests and evidence locks are not rewritten.
- `make`, Python compilation and `git diff --check` pass. No dependency was added.

## Desktop review

Live Tk widget invocation and screenshot inspection were performed on WSLg at
**1366×768**, **1920×1080**, and **2560×1440**; actual window dimensions match the
requests. Every main page was visited at all three sizes. Changed pages were also
captured in Presentation Mode. Card text bounds are checked programmatically;
Final Validation fonts remain prominent, internal navigation stays visible, and
scientific values remain available. The builder's empty state was captured after
scrolling into view at each size.

The review caught and fixed a late-bound comparison-grid closure, the global Tk
font overriding metric styles, and resize feedback from hidden notebook pages.
Metric layout now waits for a mapped viewport and ignores redundant width events.

Reproduce the checks with:

```bash
make
python3 -m py_compile scripts/virtual_ecu_gui.py python/virtual_ecu/*.py
python3 -m unittest discover -s tests
python3 tests/gui_v62_desktop_checks.py
python3 scripts/run_cross_layer_reproducibility_package.py --analysis-only --output-dir results/cross_layer_safety_v6_2/final_validation
python3 scripts/run_cross_layer_reproducibility_package.py --quick-check --output-dir results/cross_layer_safety_v6_2/final_validation
git diff --check
```

The desktop test requires a display and the existing local accepted/v6.1 example
results. It redirects session/history/export writes and its Guided execution into
v6.2 output locations. Normal GUI scratch/reproducibility destinations remain the
v6.1 defaults to preserve existing behavior. Scientific hash, incremental AST,
regression and desktop reports are in `results/cross_layer_safety_v6_2/validation/`.
The v6.2 analysis/check copy is separate from every accepted evidence directory.

## Files and remaining limits

Incremental edits: `.gitignore`, the user guide, `scripts/virtual_ecu_gui.py`,
`cross_layer_gui.py`, `final_validation_gui.py`, `gui_design.py`, `gui_workflows.py`,
`gui_execution_lock.json`, `final_evidence.py`, and `tests/test_gui_ux.py`.
New files: `research_analysis_gui.py`, `tests/test_gui_v62.py`,
`tests/gui_v62_desktop_checks.py`, and this validation record. Earlier v6.1 files
remain present, including the command fixture, original desktop checks and report.

Large scientific tables intentionally retain horizontal scrolling. Longer pages,
including Final Validation's footer and the stacked laptop builder, require
vertical scrolling. Research view persistence uses the existing tab index schema;
no separate persistent subview history was introduced. Native Tk rendering and
fonts can differ outside the reviewed Linux/WSLg environment. Accepted evidence
is local and ignored by Git, so a source-only checkout cannot reproduce evidence
loads without that dataset.

Another major GUI redesign is **not needed** for the current research/demo scope.
The next useful feedback should come from actual professor/researcher use. All
work remains unstaged; no commit or push was made.
