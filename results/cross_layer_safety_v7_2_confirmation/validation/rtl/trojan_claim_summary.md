# RTL Hardware Trojan Claim Summary

## Supported claims

These experiments contain real Verilog RTL Hardware Trojan models with explicit trigger and payload logic. They are not renamed C-level fault campaigns.

## HT1_COOLANT_SENSOR: Coolant Sensor Interface

The explicit RTL trigger-payload implementation requires a coolant reading of at least 95.0 C for eight consecutive cycles, then subtracts 8.0 C from the ECU-facing sample.
Verilator activated the payload at 93200 ms. The unchanged Virtual ECU detectors reported 7/8 post-activation detections; the clean replay produced 0/8 detector alarms.
Hybrid Adaptive Kalman latency from the payload was 0 ms.

## HT2_FAN_DRIVER: Fan Driver Interface

The explicit RTL trigger-payload implementation requires a fan command of at least 0.500 for eight consecutive cycles, then forces the realized fan output to zero.
Verilator activated the payload at 96000 ms. The unchanged Virtual ECU detectors reported 7/8 post-activation detections; the clean replay produced 0/8 detector alarms.
Hybrid Adaptive Kalman latency from the payload was 0 ms.

## HT3_CALIBRATION_MEMORY: Calibration Memory Interface

The explicit RTL trigger-payload implementation counts 521 calibration-interface cycles, then adds 16.0 C to the ECU cooling control target.
Verilator activated the payload at 52000 ms. The unchanged Virtual ECU detectors reported 5/8 post-activation detections; the clean replay produced 0/8 detector alarms.
Hybrid Adaptive Kalman latency from the payload was 0 ms.

## HT4_MULTI_STAGE_CHAIN: Multi-Stage RTL Chain

The composite scenario composes the existing HT3 calibration shift, HT1 coolant masking, and HT2 fan suppression outputs into one staged replay without adding another RTL implant.
The actual RTL stage activations were 52000 ms, 93200 ms, and 96000 ms.
Verilator activated the payload at 52000 ms. The unchanged Virtual ECU detectors reported 7/8 post-activation detections; the clean replay produced 0/8 detector alarms.
Hybrid Adaptive Kalman latency from the payload was 0 ms.

## Boundaries

- These are deterministic trace-driven Verilator/Virtual ECU experiments.
- Trigger and payload debug outputs are used only for reporting and latency calculation, never as detector inputs.
- Results apply only to the configured traces, payloads, and detector calibrations.
- The replay is not fully bidirectional cycle-by-cycle RTL/plant co-simulation.
- This is not silicon-proven, fabricated-chip evidence, or a claim that all Hardware Trojans are detected.
