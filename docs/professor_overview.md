# Professor Overview

This repository contains a modular virtual ECU framework for automotive thermal-management dependability studies. It is designed as a lightweight research prototype that connects hardware-origin fault abstractions to ECU-visible behavior, diagnostics, safety actions, and system-level thermal outcome.

## What The Framework Is

The project models a simplified engine-cooling ECU in C with separate modules for:

- sensors
- control
- actuators
- diagnostics
- fault injection
- safety monitoring
- logging

It is not a circuit-accurate electronics simulator. Instead, it provides a research-oriented abstraction layer for studying how plausible electronics-origin faults appear at ECU interfaces and propagate upward into observable behavior.

## What Problem It Addresses

Automotive electronics faults are often discussed either too low in the stack or too generically at system level. This framework addresses that gap by showing how hardware-origin faults can be represented as ECU-visible disturbances and then traced through:

- diagnostics
- safe-state response
- thermal-management consequence
- comparison across scenarios

This makes the platform useful for cross-layer fault-propagation discussion in thesis, lab, and paper settings.

## Why The Fault Taxonomy Matters

The framework distinguishes fault classes because different electronics-origin faults do not produce the same ECU story.

Main fault classes:

- `sensing-path faults`
- `timing/communication faults`
- `actuation-path faults`
- `computation/memory faults`

This taxonomy matters because it helps separate:

- where the fault begins
- how the ECU experiences it
- what diagnostic evidence is expected
- what thermal and safety consequence follows

## What Experiments It Supports

The framework already supports:

- built-in campaign comparisons
- custom single-fault experiments
- custom multi-fault scenarios
- repeatable CSV-backed logging
- batch studies across fault classes and settings
- exported comparison, snapshot, and presentation bundles

Typical experiment questions include:

- detection latency
- safe-state entry latency
- peak thermal severity
- actuator-tracking consequence
- differences between nominal and faulty operation
- differences between mild and stressed operating contexts

## What The GUI Contributes

The Python/Tkinter GUI is a lightweight interpretation and presentation layer over the simulator workflow. It supports:

- side-by-side comparison of runs
- saved result loading
- showcase presets for clean demos
- custom fault configuration
- propagation-oriented visualization
- batch summary review
- export and presentation handoff

This makes the platform much easier to explain to an academic audience than raw CSV logs alone.

## Research Contribution Framing

The strongest framing is:

- `hardware-origin fault abstraction`
  The framework does not claim transistor-level fidelity; it captures plausible electronics-origin failures as ECU-visible abstractions.
- `cross-layer propagation`
  It links fault origin to ECU manifestation, diagnostics, safety logic, and plant-level outcome.
- `diagnostics / safe-state / thermal outcome linkage`
  It makes visible how a disturbance becomes confirmed evidence, protective action, and measurable thermal consequence.
- `automotive electronics dependability relevance`
  It supports discussion about fault taxonomy, observability, mitigation, and system consequence in a form suitable for thesis and research communication.

## What Can Already Be Demonstrated

- built-in left/right comparisons for nominal versus faulty cases
- custom single faults for targeted experiments
- multi-fault scenarios for staged propagation stories
- batch studies for sweep-level interpretation
- snapshot, report, and presentation bundle export support

Representative professor-facing examples include:

- `Baseline vs Fan Hot Stress`
- `Baseline vs Stale Sensor Data Hot Stress`
- `Baseline vs Calibration Memory Corruption`

## Best First Demonstration

Best first demonstration: `Baseline vs Fan Hot Stress`

Why it is the strongest opening:

- easy to explain quickly
- strong thermal consequence
- clear safe-state escalation
- clean actuation-path fault story
- strong cross-layer propagation narrative

Recommended live flow:

1. Open `Comparison Summary`
2. Load the showcase preset `Baseline vs Fan Hot Stress`
3. Show `Comparison Summary`
4. Show `Comparison Figures`
5. Show the propagation timeline and evidence
6. Show `Fault Path`
7. Optionally finish with `Batch Results`

For a more presenter-oriented script, see [demo_walkthrough.md](/home/leonskal/code/virtual-ecu-phd/docs/demo_walkthrough.md).

## Why This Is Useful For Thesis And Demo Work

- it gives a clear framework story, not only isolated plots
- it supports repeatable experiments and comparison-driven explanation
- it is compact enough for live demos
- it is structured enough for thesis screenshots, figure discussion, and research framing
- it helps communicate automotive electronics dependability without overclaiming physical fidelity
