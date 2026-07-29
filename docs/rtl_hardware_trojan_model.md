# RTL Hardware Trojan Model

## Scope

This extension adds an actual RTL-level Hardware Trojan experiment path to the
Virtual ECU Research Explorer. It does not rename, wrap, or replace the
existing C-level fault-injection campaigns.

The first model inserts a trigger-payload RTL block in the coolant sensor
interface:

```text
nominal thermal trace
        |
        v
clean RTL ---------> clean ECU-facing trace ------+
        |                                          |
        +-> Trojan RTL -> masked ECU-facing trace -+-> unchanged Virtual ECU
                                                       detectors and GUI
```

The Verilog modules are:

- `rtl/security/coolant_sensor_interface_clean.v`
- `rtl/security/coolant_sensor_interface_trojan.v`

The shared Verilator top-level wrapper is:

- `sim/security/coolant_sensor_interface_tb.v`

## Fixed-point representation

The sensor interface uses signed 16-bit integer values with a scale of
0.1 degrees Celsius per least-significant bit:

```text
rtl_value = temperature_celsius * 10
```

For example, 95.0 C is represented as `950`. This range is intentionally larger
than the temperatures accepted by the Virtual ECU sensor model.

The clean block registers and forwards the input:

```text
sensor_out = sensor_in
```

Both the clean and infected paths therefore have the same one-cycle interface
latency in the RTL simulation.

## Trigger logic

The infected module increments a consecutive-cycle counter while:

```text
sensor_in >= 950
```

The default trigger requires eight consecutive samples at or above 95.0 C.
Dropping below the threshold before activation clears the counter. Once the
eighth qualifying sample arrives, `trojan_triggered` and `payload_active`
become sticky until reset.

The trigger parameters are explicit Verilog parameters:

- `TRIGGER_THRESHOLD = 950`
- `TRIGGER_CYCLES = 8`

The module exposes `trojan_triggered`, `payload_active`, and
`trigger_counter` for experimental observability. These debug outputs are not
inputs to any runtime detector.

## Payload logic

The payload masks elevated coolant temperature from the ECU:

```text
trojan_sensor_value = sensor_in - 80
```

The default `PAYLOAD_BIAS = 80` corresponds to 8.0 C. Before activation, the
infected module matches the clean module. After activation, it continuously
reports the biased value and exposes both `clean_sensor_value` and
`trojan_sensor_value`.

This is a trigger-payload RTL implementation. It is not a claim of a
silicon-proven or fabricated-chip Trojan.

## Verilator and trace-driven integration

Run the complete study with:

```bash
make rtl-trojan-study
```

or:

```bash
python3 scripts/run_rtl_hardware_trojan_study.py
```

The script:

1. runs a nominal Virtual ECU thermal sequence;
2. converts coolant samples to signed deci-degrees Celsius;
3. builds and simulates the clean and infected Verilog modules with Verilator;
4. writes a direct clean-versus-Trojan RTL trace;
5. replays each RTL output through the existing Virtual ECU with every existing
   detector in `observe_only` mode; and
6. writes isolated security-study artifacts under
   `results/rtl_hardware_trojan_study_v1/`.

Verilator is optional for the rest of the project. If it is absent, the study
script exits with:

```text
Verilator is required for the RTL Hardware Trojan study. Install with sudo apt install verilator.
```

Normal `make`, simulator runs, and GUI launch do not require Verilator.

## Virtual ECU sensor-trace boundary

The dedicated replay uses:

```bash
./virtual_ecu logs/example.csv baseline \
  --coolant-sensor-trace path/to/trace.csv \
  --detector hybrid_adaptive_kalman \
  --detector-action observe_only
```

The trace schema is:

```csv
time_ms,coolant_temp_c
0,88.0
100,87.7
```

Samples must start at 0 ms, be spaced by the 100 ms sensor period, and cover
the full requested simulation. This option replaces only the ECU-facing
coolant sample and is inactive unless explicitly supplied. Existing fault
campaign definitions, the sensor-fault code, detector implementations, and
ordinary CSV schemas are unchanged.

The generated raw replay CSVs can be loaded in the existing GUI Compare view.
No dedicated GUI page is needed: the Virtual ECU remains the runtime
detection, physical-consequence, logging, and visualization environment.

## Security-study outputs

The generated directory contains:

- `rtl_trojan_sensor_trace.csv`: direct Verilator output with input, clean
  output, infected output, trigger state, payload state, and counter;
- `virtual_ecu_clean_sensor_trace.csv` and
  `virtual_ecu_trojan_sensor_trace.csv`: explicit replay inputs;
- `detector_comparison.csv`: clean and infected outcomes for all existing
  detectors, with RTL security metadata;
- `attack_taxonomy_table.csv`: target, trigger, payload, and evaluation scope;
- `raw/`: GUI-compatible Virtual ECU logs and summary CSVs;
- `trojan_claim_summary.md`: measured result and bounded claim; and
- `README.md`: reproduction and output guide.

The directory is ignored by git because it contains generated evidence.

## Detection interpretation

The detectors are not rewritten and receive no `trojan_triggered`,
`payload_active`, attack label, trigger time, or scenario identifier. They see
only their existing runtime-observable Virtual ECU signals. The study script
uses the RTL trigger time after the run to classify alarms as pre-activation or
post-activation evaluation outcomes.

Because the replay deliberately uses the ordinary `baseline` campaign rather
than inventing a C-level Trojan fault, the generic raw runtime
`false_positive_count` does not know that an external RTL payload activated.
The security report therefore uses the clean replay for the false-positive
reference and separately reports post-payload detection.

## Limitations

- This first version is deterministic and trace-driven. The RTL consumes a
  prerecorded nominal sensor-input trace; the Virtual ECU replay is not a
  bidirectional cycle-by-cycle plant/RTL co-simulation.
- The payload and trigger are one configured example, not a representative
  sample of all Hardware Trojan designs.
- Detection results apply only to this simulation, detector calibration, input
  trace, trigger, and payload.
- The experiment does not establish fabrication feasibility, physical
  stealth, gate-level properties, or silicon behavior.
- It is a research prototype, not a production-ready security solution.
