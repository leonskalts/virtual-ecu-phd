# Cross-Layer Safety v6.1 GUI/UX validation

Baseline: `8cb44d9` (main/origin/main at preflight).
Scientific behavior modified: **No**.
Accepted scientific outputs modified: **No**.
No commit, staging or push was performed.

## Implementation

| Area | Result |
| --- | --- |
| Navigation | HOME, EXPERIMENT, RESEARCH, REPORT and ADVANCED groups. Existing page IDs and ordering retained; Final Validation appended. |
| Dashboard | New-user guided action, research workspace choice and advanced workflow; existing comparison/export/research/builder cards retained. |
| Cross-Layer configuration | Guided default and Advanced visual modes; five supported layers; only supported models and behaviors; model-specific fields; intermittent ON/OFF only when relevant; permanent duration hidden. |
| Safety contract | Collapsed in Guided, accessible by expansion or Advanced. Existing FTTI, hazard thresholds and exposure defaults retained. Independent monitoring selectors remain available. |
| Cross-Layer results | Empty-state actions, compact result cards, strictly evidence-based interpretation, reached/N/A propagation summary and exact timestamp table. |
| Help | Fifteen technical concepts, with hover/focus tooltips and inline workflow guidance. |
| Run Experiment | Existing three steps, campaigns, left/right loading, execution, metrics, context and exports retained. |
| Compare Results | Loaded pair summary, explicit recorded cross-layer fault metadata, wider selector and wrapped helper text. Plot data unchanged. |
| Propagation Path | Distinct FAULT ORIGIN / MAIN OUTCOME labels. Paired five-stage diagrams stack on narrower windows. |
| Batch Analysis | Runs/classes/models, fastest detection, highest temperature, most severe recorded final safe state, and existing detailed findings/tables/plots. |
| Detector Study | Detection performance and intervention outcome separated in the summary; original scenario/detector/action matrix retained. |
| Parameter Sweep | Best coverage and median latency identify all tied detectors. Hybrid and six paper-facing baselines remain visible; tables retain original values. |
| RTL Security | Selected target metadata and recorded outcome above the existing viewer. Trigger/payload prose comes from the accepted taxonomy CSV. P/DET/DTC legend retained near the timeline. |
| Exports | Descriptions for snapshot/report/presentation bundle; Last Export reflects the actual successful destination in the current session. |
| Advanced Experiment Builder | Guided-workflow link, empty result inspector, original single/multi-fault controls, presets, timelines and result-placement actions retained. |
| Final Validation | Separate REPORT page with all ten existing summary fields and four controls. Accepted v6 loads by default; new regeneration/check artifacts go to v6.1. |
| Design system | Shared navy/blue palette, typography, spacing, dimensions, semantic buttons, section/summary/status helpers, tooltips and responsive wrapping. |
| Presentation mode | Visual font/density adjustment, preserving scientific parameters and commands. |

Blue denotes navigation/load/inspect; green denotes execution/generation/export;
gray denotes neutral/open/save; red denotes destructive actions. Amber remains a
status/accent color. Labels accompany status colors. Status banners use Ready,
Running, Completed, Loaded, No Results, Warning and Error; running feedback is
indeterminate and uses the original worker architecture.

## Scientific boundary and compatibility

- All **42** stored command cases captured from the original v6 GUI match the new
  adapter, covering seven models, three behaviors and default/advanced settings.
- **400** original GUI command, loading, export and analysis definitions retain
  their AST hashes. Documented presentation methods may change. The original
  accepted source/evidence lock itself remains untouched.
- The final-evidence verifier permits the main GUI presentation integration while
  retaining the execution-definition guard and every scientific source/evidence
  check. Newly generated inventories include the new GUI dependencies.
- **78** preflight scientific source/configuration files and **10,693** accepted
  evidence files match their hashes. Accepted file sets also match for v1–v6,
  HETIA and RTL. This includes the frozen v5 hashes.
- All **48** legacy configurations reproduced byte-identical raw/C summaries
  against the compiled accepted C tree. All **64** RTL cases reproduced identical
  historical raw/C-summary fields and comparison metrics, apart from relocated
  paths; the already-existing appended columns remain permitted.
- Hybrid Adaptive Kalman, fault semantics, timing rules, simulator physics,
  thresholds, FTTI, containment definitions, campaigns and scientific CSV schemas
  are unchanged.
- Legacy raw CSV and v1/v2 summaries loaded successfully; v3/v4/v5 panels and the
  v6 final summary loaded through their original version-specific APIs. Unavailable
  historical containment remained N/A. Presets, recent-history APIs, saved page
  indices, session serialization and comparison/export APIs remain compatible.
- The user's existing session edit was preserved. Its selected page changed
  externally during preflight (before implementation and GUI testing); that newer
  selection was not overwritten. Every desktop run verified byte-identical session
  contents before and after its own checks.

## Representative GUI experiments

All three used the normal GUI background worker, 45,000 ms injection, 100 ms
transient duration, seed 42, and the original monitor-disabled/observe-only defaults.
The table reports loaded evidence, without attributing detection to an unrecorded
mechanism.

| Fault | Detected | Detection latency | Plant manifestation | Hazard | Safe state | Containment | Depth |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Memory / bit_flip | Yes | 0 ms | Yes | No | No | Yes | 5 |
| Timing / task_delay | No | N/A | No | No | No | Yes | 4 |
| Communication / replayed_sample | Yes | 0 ms | No | No | No | Yes | 4 |

Raw traces, selected values and command requests are retained under
`results/cross_layer_safety_v6_1/validation/gui_runs/` and `desktop_checks.json`.
Containment and safe-state values are separate experimental fields; the table does
not assert certification or a new safety result.

## Validation record

- Preflight: **114** tests passed.
- Final complete suite: **139** tests passed, including the original tests.
- Live GUI: **120** assertions, including dynamic fields/modes, historical loading,
  state preservation, three runs, comparison metadata, all three exports and page
  navigation at all requested sizes.
- `make`, compilation of the main GUI and all package Python modules, and
  `git diff --check`: passed.
- Quick reproducibility: build/tests, **8** deterministic accepted replays, frozen
  checks, artifact inventory and claim references passed in the new v6.1 directory.
- All twelve pages captured at actual **1366×768**, **1920×1080**, **2560×1440**.
  Screenshots were visually inspected, including lower plots/tables, Guided,
  Advanced, results, presentation mode and a tooltip. Additional plain-Tk fallback
  and detailed-view checks covered ten pages each with no callback errors.
- Desktop interaction was scripted; screenshot inspection was visual. This was not
  a separate first-time-user usability study.

Generated records are under `results/cross_layer_safety_v6_1/validation/`:
`preflight_sha256.json`, `frozen_verification.json`, `final_tests.log`,
`desktop_checks.json`, `legacy/verification.json`, `rtl/verification.json`,
`tk_only_checks.json`, `detail_checks.json`, screenshots and exports.
The separate final-validation copy contains its own quick-check and analysis logs.

## Files and reusable components

Changed: `.gitignore`, `scripts/virtual_ecu_gui.py`,
`python/virtual_ecu/cross_layer_gui.py`, `final_validation_gui.py`,
`final_evidence.py`, and `docs/cross_layer_platform_user_guide.md`.

New: `python/virtual_ecu/gui_design.py` (tokens/components),
`cross_layer_ui.py` (visibility/command adapter), `gui_workflows.py` (summary and
responsive layout), `gui_execution.py` plus `gui_execution_lock.json` (integrity),
`tests/test_gui_ux.py`, `tests/gui_v61_desktop_checks.py`,
`tests/gui_window_capture.py`, `tests/fixtures/gui_v6_commands.json`, and this report.
`presets/gui_session_state.json` remains a pre-existing user modification.

## Known UI limitations and recommendation

Wide scientific tables still require horizontal scrolling or column resizing;
long research pages require vertical scrolling. Plain Tk uses native square
controls while CustomTkinter provides rounded surfaces. Some existing export success
dialogs remain. The legacy comparison plots retain stored campaign labels, and their
legacy propagation table classifies campaign events; instrumented cross-layer
propagation must be inspected on Cross-Layer Safety. The new pair summary explicitly
identifies the recorded cross-layer fault and this boundary. Single-run output is
scratch space and is replaced on the next run; the guide explains how to retain it.

The GUI is suitable for a guided first experiment, research demonstrations,
professor presentations and paper-evidence inspection with the accepted local
datasets installed. Presentation Mode and the separate Final Validation page are
appropriate starting points for a research presentation. No new scientific claims
or retuning were introduced. All changes are left unstaged.
