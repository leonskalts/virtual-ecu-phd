# Paper Study v1 Claim Summary

The statements below are cautious claim candidates supported by this generated package.

## Supported Claim Candidates

- The tool produces reproducible, CSV-backed traces for 7 representative virtual ECU scenarios without requiring GUI interaction.
- The raw CSV schema links configured fault events to ECU-visible labels, diagnostics, safe-state labels, actuator/sensor residuals, and thermal state in the same trace.
- In this representative set, 6 of 6 non-baseline scenarios show at least one non-none diagnostic/DTC evidence label during the run.
- In this representative set, 5 of 6 non-baseline scenarios enter or finish in a non-normal safe-state response.
- The fan hot-stress representative run demonstrates a clear actuation-path propagation case: `fan_stuck_off` leads to `fan_tracking_fault`, `limp_home`, and a peak coolant temperature 18.57 C above baseline.
- The included multi-event scenario demonstrates that the framework can represent staged fault narratives across more than one hardware-origin path.

## What This Package Does Not Claim

- It does not validate circuit-level transistor or device physics.
- It does not claim production ECU safety compliance or standards certification.
- It does not estimate field failure rates, coverage probabilities, or statistical confidence.
- It does not claim real-vehicle calibration validity; the thermal plant is a research prototype abstraction.
- It does not replace larger parameter sweeps; it is a compact evidence package for discussion and paper framing.
