# Presentation Assets Guide

This guide defines a small curated set of thesis/demo assets to keep ready before a professor meeting, lab demo, or presentation dry run.

## Official Presentation Cases

Treat these as the primary official demo cases:

1. `Baseline vs Fan Hot Stress`
2. `Baseline vs Stale Sensor Data Hot Stress`
3. `Baseline vs Calibration Memory Corruption`
4. `Multi-Fault Sequence vs Baseline` as an optional advanced case

These cases give a compact, balanced set across:

- `actuation-path faults`
- `timing/communication faults`
- `computation/memory faults`
- staged multi-fault propagation

## Most Important Folders

Keep these folders ready and easy to find:

- `results/gui_presentation_bundles/`
- `results/gui_snapshots/`
- `results/gui_comparison_reports/`
- `results/batch/paper_quick/`
- `results/paper/`

## Best Tabs To Capture

Strongest screenshot tabs:

- `Comparison Summary`
- `Comparison Figures`
- `Fault Path`
- `Batch Results` when an aggregate-study screenshot is needed

Strongest figure views:

- `Coolant Temperature Comparison`
- `Safe-State Comparison`
- `Cross-Layer Propagation Timeline`

## Most Useful Export Outputs

Prioritize these exports:

- `Export Presentation Bundle`
- `Export Snapshot`
- `Export Full Report`

Use them this way:

- `Presentation Bundle` for the cleanest professor-facing handoff
- `Snapshot` for compact summary material
- `Full Report` for supporting figures and comparison detail

## Case-By-Case Recommendations

### Baseline vs Fan Hot Stress

Best used for:

- first live demo
- strongest single comparison
- actuation-path and safety-escalation explanation

What to export:

- presentation bundle
- snapshot

Best screenshots:

- `Comparison Summary`
- `Safe-State Comparison`
- `Cross-Layer Propagation Timeline`
- `Fault Path`

Strongest tabs:

- `Comparison Summary`
- `Comparison Figures`
- `Fault Path`

### Baseline vs Stale Sensor Data Hot Stress

Best used for:

- timing/communication fault discussion
- showing delayed control action and thermal consequence
- distinguishing timing faults from direct actuation failure

What to export:

- presentation bundle
- full report

Best screenshots:

- `Comparison Summary`
- `Coolant Temperature Comparison`
- `Cross-Layer Propagation Timeline`
- `Fault Path`

Strongest tabs:

- `Comparison Figures`
- `Fault Path`

### Baseline vs Calibration Memory Corruption

Best used for:

- computation/memory fault discussion
- showing internal control degradation rather than interface-only corruption
- broadening the narrative beyond sensing and actuation faults

What to export:

- presentation bundle
- snapshot

Best screenshots:

- `Comparison Summary`
- `Coolant Temperature Comparison`
- `Propagation Evidence`
- `Fault Path`

Strongest tabs:

- `Comparison Summary`
- `Comparison Figures`

### Multi-Fault Sequence vs Baseline

Best used for:

- advanced staged-propagation discussion
- showing that the framework supports ordered multi-event fault stories

What to export:

- presentation bundle if used in a meeting
- full report for supporting detail

Best screenshots:

- `Custom Experiment`
- `Cross-Layer Propagation Timeline`
- `Fault Path`

Strongest tabs:

- `Custom Experiment`
- `Comparison Figures`
- `Fault Path`

## Practical Workflow Before A Meeting

1. Open the GUI and load the showcase or saved result for each official case.
2. Generate `Export Presentation Bundle` for the main cases.
3. Review the summary, verdict, and key takeaway text in `Comparison Summary`.
4. Capture screenshots from the selected tabs for each case.
5. Keep the resulting bundles and screenshots in the standard output folders rather than scattered ad hoc copies.
6. If time is short, keep `Baseline vs Fan Hot Stress` ready first, then `Baseline vs Stale Sensor Data Hot Stress`, then `Baseline vs Calibration Memory Corruption`.

## Minimum Curated Pack To Keep Ready

For a normal professor meeting, keep these ready:

- one presentation bundle for `Baseline vs Fan Hot Stress`
- one presentation bundle for `Baseline vs Stale Sensor Data Hot Stress`
- one presentation bundle for `Baseline vs Calibration Memory Corruption`
- one strong `Comparison Summary` screenshot
- one strong propagation timeline screenshot
- one `Fault Path` screenshot
- one optional `Batch Results` screenshot

This pack is usually enough to support both a quick verbal explanation and a more detailed discussion if questions arise.
