# Virtual ECU Demo Walkthrough

This guide is a lightweight presenter script for showing the virtual ECU framework to a professor, lab audience, or thesis audience.

## Best First Demo

Recommended first comparison: `Baseline vs Fan Hot Stress`

Why this is the strongest opening:

- it is easy to explain: nominal behavior versus a strong actuation-path failure
- the thermal consequence is visible quickly
- the safe-state story is clear
- it shows cross-layer propagation cleanly from fault origin to system effect

## Recommended Live Demo Sequence

1. Open the GUI with:

```sh
python3 scripts/virtual_ecu_gui.py
```

2. Go to `Comparison Summary`.
3. Open `Showcase / Demo Presets`.
4. Load `Baseline vs Fan Hot Stress`.
5. Stay briefly on `Comparison Summary`.
6. Move to `Comparison Figures`.
7. Show the `Propagation Evidence` panel and the `Cross-Layer Propagation Timeline`.
8. Open `Fault Path`.
9. Optionally finish with `Batch Results`.

## What To Show And Say

### 1. Comparison Summary

What it demonstrates:

- the two runs are aligned side by side
- the main metrics already tell the high-level story
- the verdict and takeaway compress the comparison into a thesis-friendly summary

What to say:

- “This is the nominal reference on the left and a stressed fan power-stage fault on the right.”
- “The point is not only that the fault exists, but that we can compare detection timing, thermal severity, and safety outcome in one place.”
- “This gives a compact system-level interpretation before we open the detailed plots.”

### 2. Comparison Figures

Show in this order:

1. `Coolant Temperature Comparison`
2. `Safe-State Comparison`
3. `Cross-Layer Propagation Timeline`

What they demonstrate:

- coolant temperature shows the physical consequence
- safe-state comparison shows controller and protection behavior over time
- propagation timeline shows how an electronics-origin issue becomes an ECU-visible and vehicle-level effect

What to say:

- “First, this plot shows the plant-level thermal consequence.”
- “Next, the safe-state plot shows when protection logic escalates.”
- “Finally, the propagation timeline connects the hardware-origin fault to the ECU manifestation, diagnostics, and system response.”

### 3. Propagation Evidence

What it demonstrates:

- the timeline is not just visual; it is backed by extracted evidence from the run
- the GUI supports interpretation, not only plotting

What to say:

- “This panel gives the compact evidence chain I would use in a presentation slide or discussion.”
- “It helps explain not only what happened, but how we justify each propagation stage.”

### 4. Fault Path

What it demonstrates:

- where the fault begins in the architecture
- which parts of the ECU path are affected
- how to explain the run qualitatively without only relying on time-series plots

What to say:

- “This is the architecture-level story.”
- “The fault starts in the actuation path, then propagates into plant-level thermal stress and stronger safety action.”
- “This is useful when explaining the framework to someone who thinks in blocks and subsystems rather than only in plots.”

### 5. Batch Results

Use this only if time allows.

What it demonstrates:

- the strong single-run examples also fit into a larger sweep-level pattern
- the framework is useful for comparison across fault classes, not only for one handpicked run

What to say:

- “This tab is the aggregate view.”
- “I usually use it to show that the GUI supports both a narrative demo case and broader experiment interpretation.”

## Recommended Comparisons And Why They Matter

### Baseline vs Fan Hot Stress

- best first professor-facing comparison
- strongest actuation-path and safety-escalation story
- easiest to narrate in a short meeting

### Baseline vs Stale Sensor Data Hot Stress

- good timing/communication-path case
- shows that stale data can create real thermal consequence without a direct actuator failure
- useful for explaining why data freshness matters in ECU dependability

### Baseline vs Calibration Memory Corruption

- good computation/memory-path case
- shows that the controller can become wrong internally even when sensing is still nominal
- useful for explaining hidden control degradation

### Multi-Fault Sequence vs Baseline

- use this only if the audience wants a more advanced story
- good for showing staged propagation across more than one fault event
- better as a second or third demo, not the first one

## Thesis / Demo Screenshots

Best tabs to capture:

- `Comparison Summary`
- `Comparison Figures`
- `Fault Path`
- `Batch Results` if you want one aggregate-study figure

Strongest plots to capture:

- coolant temperature comparison
- safe-state comparison
- cross-layer propagation timeline

Most useful exported outputs:

- `Export Snapshot` for compact summary material
- `Export Full Report` for comparison tables plus figures
- `Export Presentation Bundle` for the cleanest handoff package

Useful files to mention or reuse:

- `results/gui_snapshots/`
- `results/gui_comparison_reports/`
- `results/gui_presentation_bundles/`

## Talking Points

### What the framework contributes

- a modular virtual ECU prototype for cross-layer automotive dependability discussion
- a bridge from hardware-origin fault classes to ECU-level and system-level behavior
- repeatable CSV-backed experiments with lightweight GUI interpretation

### Why the fault taxonomy matters

- it separates sensing, actuation, timing/communication, and computation/memory faults
- it makes comparisons clearer and more honest than treating all failures as one generic fault
- it supports research discussion about where faults begin and how they propagate

### How the GUI supports interpretation

- it compares runs side by side
- it turns logs into readable findings, verdicts, and timelines
- it supports live demos, saved results, exports, and presentation-ready bundles

### Why this is useful for research discussion

- it helps explain not only fault injection, but consequence and interpretation
- it is suitable for thesis walkthroughs, paper figures, and lab demos
- it supports conversations about automotive electronics dependability without claiming circuit-level fidelity

## Short Version For A Professor Demo

If you only have a few minutes:

1. Load `Baseline vs Fan Hot Stress`.
2. Show `Comparison Summary`.
3. Show coolant temperature and safe-state plots.
4. Show the propagation timeline.
5. End on `Fault Path`.

That sequence gives the clearest full story with the least setup.
