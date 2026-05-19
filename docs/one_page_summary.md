# One-Page Summary

## Project Idea

A modular virtual ECU framework for automotive thermal-management fault studies. The platform abstracts plausible hardware-origin electronics faults into ECU-visible disturbances, then traces how they affect diagnostics, safe-state behavior, and thermal outcome.

## Research Angle

The strongest angle is cross-layer fault propagation: not only injecting faults, but showing how sensing, timing/communication, actuation, and computation/memory disturbances produce different system-level signatures and interpretation paths.

## Fault Classes Covered

- `sensing-path faults`
- `timing/communication faults`
- `actuation-path faults`
- `computation/memory faults`

## What The Framework Can Already Do

- run built-in nominal-versus-fault comparisons
- run custom single-fault experiments
- run multi-fault scenarios
- log repeatable CSV outputs
- support batch and claim-oriented summaries
- provide GUI-based comparison, propagation, and export workflows

## Best First Demonstration

Best opening comparison: `Baseline vs Fan Hot Stress`

Why it works:

- easiest to explain quickly
- strongest visible thermal and safety consequence
- clear actuation-path fault story
- strong propagation narrative from fault origin to plant-level effect

Recommended sequence:

1. `Comparison Summary`
2. `Comparison Figures`
3. propagation timeline / evidence
4. `Fault Path`
5. optional `Batch Results`

## Strongest Current Claims

- hardware-origin fault abstractions produce distinct cross-layer propagation patterns
- different fault classes produce different diagnostic, safe-state, and thermal signatures
- timing/communication faults can be discussed separately from sensing and actuation faults
- computation/memory faults can be framed as internal control degradation
- multi-fault scenarios support staged propagation studies

## Honest Scope / Limits

What it is:

- a research-oriented virtual ECU prototype
- a comparative cross-layer dependability framework
- a presentation-friendly experiment platform

What it is not:

- a circuit-accurate or SPICE-level simulator
- a full vehicle model
- a claim of exhaustive automotive fault coverage

## Immediate Next Research Directions

- expand stronger batch-study comparisons across fault classes
- refine claim-focused figure and table selection for thesis writing
- study threshold sensitivity for diagnostics and safe-state timing
- extend multi-fault narratives for staged propagation analysis
- connect the current abstraction layer more explicitly to automotive electronics dependability framing in written work

## Meeting Use

This page is best used as:

- a professor-meeting handout
- a quick verbal project-positioning aid
- a thesis-project framing note before opening the GUI or results bundle

For more detail, see:

- [professor_overview.md](/home/leonskal/code/virtual-ecu-phd/docs/professor_overview.md)
- [results_claims_brief.md](/home/leonskal/code/virtual-ecu-phd/docs/results_claims_brief.md)
- [demo_walkthrough.md](/home/leonskal/code/virtual-ecu-phd/docs/demo_walkthrough.md)
