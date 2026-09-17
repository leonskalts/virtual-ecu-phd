# Virtual ECU Results Snapshot

## Comparison

- Left campaign: `baseline` (Baseline)
- Right campaign: `baseline` (Baseline)
- Left fault class: baseline / no injected fault
- Right fault class: baseline / no injected fault

## Key Metrics

| Metric | Left | Right |
| --- | --- | --- |
| Final DTC | none | none |
| Final Safe State | normal | normal |
| Maximum Coolant Temperature | 96.00 C | 96.00 C |
| Detection Latency | n/a | n/a |
| Safe-State Latency | n/a | n/a |

## Key Findings

- Thermal severity: both campaigns reach the same peak coolant temperature (96.00 C).
- Fault detection: Neither campaign confirms a fault during the run.
- Safe-state impact: both campaigns finish with comparable safe-state severity (normal vs normal).
- Critical end state: both campaigns finish with similar end-of-run criticality (none / normal vs none / normal).

## Interpretation

- The two cases drives the stronger thermal outcome in this comparison.
- Neither campaign confirms a fault during the run.
- Both campaigns shows the stronger protection response at ECU safe-state level.
- The end states gives the more critical end-of-run diagnostic/safety outcome.
