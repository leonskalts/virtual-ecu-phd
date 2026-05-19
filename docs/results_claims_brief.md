# Results And Claims Brief

This note is a short professor-facing summary of the strongest current comparisons, the most defensible claims supported by the framework, and the best material to show in meetings or early thesis/paper framing.

## Recommended Comparisons

### Baseline vs Fan Hot Stress

What it demonstrates:

- nominal behavior versus a strong permanent actuation-path failure
- clear thermal consequence and safe-state escalation
- a clean cross-layer propagation story from actuator/power-stage loss to plant-level effect

Fault class:

- `actuation-path fault`

Why it is useful:

- strongest first comparison for a short meeting
- easiest case to explain quickly
- shows that the framework can connect hardware-origin fault abstraction to observable system consequence

Best GUI tabs and figures:

- `Comparison Summary`
- `Comparison Figures`
- `Safe-State Comparison`
- `Cross-Layer Propagation Timeline`
- `Fault Path`

Short takeaway it supports:

- “A strong actuation-path fault produces a distinct diagnostic, safe-state, and thermal signature that is clearly visible across the GUI workflow.”

### Baseline vs Stale Sensor Data Hot Stress

What it demonstrates:

- delayed or stale coolant information acting as a timing/communication fault rather than a direct actuator loss
- thermal consequence emerging through delayed control action
- a distinct propagation story relative to sensing or actuation faults

Fault class:

- `timing/communication fault`

Why it is useful:

- separates stale-data timing faults from simple measurement bias or actuator faults
- supports discussion of data freshness as a dependability issue
- useful for arguing that timing/communication faults deserve their own category

Best GUI tabs and figures:

- `Comparison Summary`
- `Comparison Figures`
- `Coolant Temperature Comparison`
- `Cross-Layer Propagation Timeline`
- `Fault Path`

Short takeaway it supports:

- “Timing/communication faults can produce their own thermal and safety consequences even without an immediate actuator failure.”

### Baseline vs Calibration Memory Corruption

What it demonstrates:

- a computation/memory-path disturbance that changes controller behavior internally
- thermal consequence that develops even when sensing remains nominal
- a different pattern from both actuation and timing faults

Fault class:

- `computation/memory fault`

Why it is useful:

- shows that internal ECU corruption can matter even when the interface signals initially look reasonable
- broadens the framework beyond sensor and actuator narratives
- useful for discussion of control-calibration integrity

Best GUI tabs and figures:

- `Comparison Summary`
- `Comparison Figures`
- `Coolant Temperature Comparison`
- `Propagation Evidence`
- `Fault Path`

Short takeaway it supports:

- “Computation/memory faults can create a delayed but meaningful control-performance and thermal-effect signature distinct from sensing and actuation faults.”

### Multi-Fault Sequence vs Baseline

What it demonstrates:

- ordered fault events within a single run
- staged propagation rather than a single isolated disturbance
- how later events can add new symptoms on top of earlier ones

Fault class:

- `multi-fault scenario` spanning more than one path

Why it is useful:

- supports more advanced staged-propagation discussion
- useful after the single-fault comparisons, not as the first example
- shows that the framework is not limited to one-fault-at-a-time stories

Best GUI tabs and figures:

- `Custom Experiment`
- `Comparison Figures`
- `Cross-Layer Propagation Timeline`
- `Fault Path`

Short takeaway it supports:

- “The framework can support staged propagation studies in which multiple hardware-origin disturbances build a more complex ECU/system narrative.”

## Strongest Current Claims

- hardware-origin fault abstractions create distinct cross-layer propagation patterns
- different fault classes produce different diagnostic, safe-state, and thermal signatures
- timing/communication faults can be discussed as a category distinct from sensing and actuation faults
- computation/memory faults can be shown as internally generated control degradation rather than only interface corruption
- multi-fault scenarios support staged propagation studies rather than only isolated single-fault cases
- the GUI makes these differences easier to interpret through comparison, propagation evidence, and exportable presentation bundles

## Limits And Honest Current Scope

What the framework does claim:

- plausible ECU-level abstraction of automotive electronics-origin faults
- cross-layer linkage from fault class to ECU manifestation, diagnostics, safe-state behavior, and thermal outcome
- repeatable experiment comparison and presentation support

What the framework does not claim:

- transistor-level, SPICE-level, or circuit-accurate fidelity
- full vehicle fidelity beyond the modeled thermal-management context
- exhaustive coverage of all automotive fault mechanisms

The strongest honest framing is that this is a research-oriented virtual ECU platform for studying comparative fault-propagation behavior, not a device-physics simulator.

## Best Figures, Screenshots, And Exports

Best figures to show:

- coolant temperature comparison
- safe-state comparison
- cross-layer propagation timeline

Best tabs to capture:

- `Comparison Summary`
- `Comparison Figures`
- `Fault Path`
- `Batch Results` for an aggregate-study view

Best exports to bring to a meeting or draft:

- `Export Snapshot`
- `Export Full Report`
- `Export Presentation Bundle`

Most useful output locations:

- `results/gui_snapshots/`
- `results/gui_comparison_reports/`
- `results/gui_presentation_bundles/`
- `results/batch/paper_quick/`

## Best Professor-Facing Comparison Set

If only three comparisons are shown:

1. `Baseline vs Fan Hot Stress`
2. `Baseline vs Stale Sensor Data Hot Stress`
3. `Baseline vs Calibration Memory Corruption`

This set is the strongest because it covers:

- actuation-path faults
- timing/communication faults
- computation/memory faults

It gives a compact but credible cross-section of the current fault taxonomy and the different propagation signatures supported by the framework.
