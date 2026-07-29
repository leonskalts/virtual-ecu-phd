# RTL Hardware Trojan Model

## Scope

This extension adds an actual RTL-level Hardware Trojan experiment path to the
Virtual ECU Research Explorer. It does not rename, wrap, or replace the
existing C-level fault-injection campaigns.

The security extension provides three isolated trigger-payload RTL targets:

- **HT1 — Coolant Sensor Interface Trojan**
- **HT2 — Fan Driver Interface Trojan**
- **HT3 — Calibration Memory / Control Parameter Interface Trojan**

It also provides **HT4 — Multi-Stage RTL Trojan Chain**, a composite scenario
that reuses HT1, HT2, and HT3. HT4 does not add an independent RTL module.

```text
nominal thermal trace
        +-> HT1 coolant RTL -> ECU-facing sensor trace --+
        |                                                 |
        +-> HT2 fan RTL ----> realized fan trace ----------+
        |                                                 |
        +-> HT3 calibration RTL -> control-target trace ---+-> unchanged
                                                            Virtual ECU
                                                            detectors and GUI
```

The HT1 Verilog modules are:

- `rtl/security/coolant_sensor_interface_clean.v`
- `rtl/security/coolant_sensor_interface_trojan.v`

The shared Verilator top-level wrapper is:

- `sim/security/coolant_sensor_interface_tb.v`

The HT2 Verilog modules and wrapper are:

- `rtl/security/fan_driver_interface_clean.v`
- `rtl/security/fan_driver_interface_trojan.v`
- `sim/security/fan_driver_interface_tb.v`

The HT3 Verilog modules and wrapper are:

- `rtl/security/calibration_memory_interface_clean.v`
- `rtl/security/calibration_memory_interface_trojan.v`
- `sim/security/calibration_memory_interface_tb.v`

## HT1 — Coolant Sensor Interface Trojan

### Fixed-point representation

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

### Trigger logic

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

### Payload logic

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

## HT2 — Fan Driver Interface Trojan

### Fixed-point representation

The fan-driver interface uses an unsigned 16-bit value with 1000 counts per
full-scale fan command:

```text
rtl_value = normalized_fan_command * 1000
```

For example, a normalized command of `0.504` is represented as `504`. The clean
module registers `fan_command` and forwards it as `fan_actual`, preserving the
same one-cycle latency as the infected module.

### Trigger logic

HT2 increments a consecutive-cycle counter while:

```text
fan_command >= 500
```

The default trigger requires eight consecutive interface cycles at or above a
normalized command of `0.500`. A lower command clears the counter before
activation. On the eighth qualifying sample, `trojan_triggered` and
`payload_active` latch until reset.

The explicit parameters are:

- `TRIGGER_THRESHOLD = 500`
- `TRIGGER_CYCLES = 8`

### Payload logic

After activation, HT2 forces the realized fan output to zero:

```text
fan_actual = PAYLOAD_CLAMP = 0
```

The module exposes `trigger_counter`, `clean_fan_command`, and
`trojan_fan_actual` alongside the trigger and payload flags. These status
signals are recorded only by the RTL study. The Virtual ECU detectors do not
receive them.

The runtime consequence is a command-versus-realized fan mismatch. Existing
actuator feedback, diagnostics, and runtime detectors observe that consequence
through their normal signals, not through an attack label.

## HT3 — Calibration Memory / Control Parameter Interface Trojan

### Target path and scaling

HT3 models the calibration/configuration memory path that supplies the existing
coolant-control target. It uses the same signed 16-bit deci-degrees Celsius
representation as HT1:

```text
rtl_value = control_target_celsius * 10
```

The nominal `92.0 C` target is therefore `920`. The clean module registers and
forwards `calibration_in` as `calibration_out`. The infected module has the same
one-cycle interface latency before activation.

### Trigger logic

The infected module contains an internal warm-up counter. With the default
`TRIGGER_CYCLES = 521`, the counter advances once for each 100 ms calibration
sample and activates on the sample at `52000 ms`. On activation,
`trojan_triggered` and `payload_active` latch until reset.

This trigger is implemented entirely in
`calibration_memory_interface_trojan.v`; the C simulator does not generate an
attack flag or decide when it activates.

### Payload logic and runtime effect

The payload adds the bounded `PAYLOAD_OFFSET = 160`, corresponding to
`+16.0 C`, to the stored cooling target:

```text
trojan_calibration_value = calibration_in + 160
```

For the nominal input this changes `92.0 C` to `108.0 C`, delaying ordinary
cooling demand. The module exposes `trigger_counter`,
`clean_calibration_value`, and `trojan_calibration_value` together with the
trigger and payload flags. Those fields are recorded only in the direct RTL
trace and used after replay for reporting and latency calculation.

This differs from the ordinary C-level
`calibration_memory_corruption` reliability fault: the security study runs the
baseline campaign, obtains the modified value from an explicit Verilog
trigger-payload module, and supplies only that value at the control boundary.
The runtime detectors never receive the RTL debug/status fields.

## HT4 — Multi-Stage RTL Trojan Chain

### Composite scenario

HT4 is a coordinated trigger-payload RTL security scenario built from the
existing three Verilog targets. It represents a staged attack across the
calibration/configuration, sensor, and actuator paths:

1. **Stage 1 — HT3 calibration path:** raises the coolant-control target by
   16.0 C, delaying cooling demand.
2. **Stage 2 — HT1 sensor path:** subtracts 8.0 C from the ECU-facing coolant
   sample after its temperature-persistence trigger.
3. **Stage 3 — HT2 actuator path:** forces realized fan output to zero after
   its fan-command-persistence trigger.

No stage activation time is synthesized by Python or C. The study builds and
runs each existing RTL module, locates the first asserted `payload_active` row,
and records that RTL-produced time in `multi_stage_chain_trace_index.csv`. In
the standard 120-second nominal input sequence, the current modules activate at
52000 ms, 93200 ms, and 96000 ms respectively. These values are measured study
outputs, not detector inputs.

### Combined replay and runtime effect

The clean chain replay supplies all three clean traces together. The infected
chain replay supplies all three Trojan traces together using the existing
explicit CLI boundaries:

```text
--calibration-trace
--coolant-sensor-trace
--fan-actual-trace
```

This composes a weakened cooling target, masked temperature observation, and
suppressed realized fan output in one Virtual ECU baseline run. Existing
detectors observe only ordinary runtime signals and consequences. They do not
receive `multi_stage`, stage identifiers, trigger flags, payload flags, or
activation times.

### Trace-driven limitation

Each RTL module consumes the same prerecorded nominal source sequence. The
three resulting outputs are then replayed together; a change caused by Stage 1
does not feed back into the prerecorded HT1 or HT2 RTL inputs. This is a
deterministic trace-driven RTL/ECU replay, not fully bidirectional cycle-level
co-simulation. Combined thermal consequences can therefore be stronger than an
interactively coupled plant/RTL model and must be interpreted within this
boundary.

## Verilator and trace-driven integration

Run the complete study with:

```bash
make rtl-trojan-study
```

or:

```bash
python3 scripts/run_rtl_hardware_trojan_study.py
```

The script defaults to all targets. A single target or scenario can be selected
with `--target coolant_sensor`, `--target fan_driver`,
`--target calibration_memory`, or `--target multi_stage_chain`.
`--target all` runs the three individual targets and the composite chain.

The script:

1. runs a nominal Virtual ECU thermal sequence;
2. converts coolant and calibration values to deci-degrees Celsius and fan
   commands to thousandths of full scale;
3. builds and simulates each clean/infected RTL interface pair with Verilator;
4. writes direct clean-versus-Trojan traces for HT1, HT2, and HT3;
5. replays each individual RTL output and the three-path composition through
   the existing Virtual ECU with every existing detector in `observe_only`
   mode; and
6. writes isolated security-study artifacts under
   `results/rtl_hardware_trojan_study_v1/`.

Verilator is optional for the rest of the project. If it is absent, the study
script exits with:

```text
Verilator is required for the RTL security analysis. Install with sudo apt install verilator.
```

Normal `make`, simulator runs, and GUI launch do not require Verilator.

## Virtual ECU trace boundaries

### HT1 coolant sensor replay

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

### HT2 fan actuator replay

The fan integration is also explicit:

```bash
./virtual_ecu logs/example.csv baseline \
  --fan-actual-trace path/to/trace.csv \
  --detector hybrid_adaptive_kalman \
  --detector-action observe_only
```

The trace schema is:

```csv
time_ms,fan_actual
0,0.000
100,0.000
```

Samples start at 0 ms, use the 100 ms actuator period, remain within
`0.000..1.000`, and cover the full run. The replay overrides only the realized
fan value after ordinary actuator processing. Without the option, normal
control, fault injection, logging, and detector behavior are unchanged.

### HT3 calibration replay

HT3 uses an explicit opt-in control-parameter trace:

```bash
./virtual_ecu logs/example.csv baseline \
  --calibration-trace path/to/trace.csv \
  --detector hybrid_adaptive_kalman \
  --detector-action observe_only
```

The trace schema is:

```csv
time_ms,control_target_c
0,92.0
100,92.0
```

Samples start at 0 ms, use the 100 ms control period, stay within
`60.0..130.0 C`, and cover the full run. When explicitly supplied, the trace
replaces only the effective coolant-control target after ordinary C-level
fault processing. The RTL study uses the baseline campaign and does not combine
the replay with a C-level calibration fault. Without `--calibration-trace`,
normal control behavior is byte-for-byte unchanged.

### HT4 multi-stage replay

The script invokes the three trace options together for both clean and infected
chain variants. Direct manual replay is possible with the generated clean or
Trojan trace triplet, but `--target multi_stage_chain` is the reproducible
orchestration path:

```bash
python3 scripts/run_rtl_hardware_trojan_study.py \
  --target multi_stage_chain
```

Normal runs remain unchanged because none of the three replay options is active
unless supplied explicitly.

### GUI entry point

The GUI page named **Security / RTL Analysis** provides a target selector,
analysis button, output path, and results-folder action. It is deliberately
separate from **Custom Faults**: the former runs actual RTL trigger-payload
modules, while the latter remains the reliability/safety fault-injection
workflow. The **Multi-Stage RTL Chain** selector choice composes all three
existing paths; the other choices remain isolated single-path runs.

Generated Virtual ECU replay CSVs remain compatible with the existing Compare
view. Verilator is not imported or invoked during ordinary GUI use.

## Security-study outputs

The generated directory contains:

- `rtl_trojan_sensor_trace.csv`: direct Verilator output with input, clean
  output, infected output, trigger state, payload state, and counter;
- `virtual_ecu_clean_sensor_trace.csv` and
  `virtual_ecu_trojan_sensor_trace.csv`: explicit replay inputs;
- `rtl_fan_driver_trojan_trace.csv`: direct HT2 Verilator fan command,
  clean output, infected output, trigger state, payload state, and counter;
- `virtual_ecu_clean_fan_actual_trace.csv` and
  `virtual_ecu_trojan_fan_actual_trace.csv`: HT2 replay inputs;
- `rtl_calibration_memory_trojan_trace.csv`: direct HT3 calibration input,
  clean output, infected output, trigger state, payload state, counter, and
  debug values;
- `virtual_ecu_clean_calibration_trace.csv` and
  `virtual_ecu_trojan_calibration_trace.csv`: HT3 replay inputs;
- `multi_stage_chain_trace_index.csv`: stage order, actual RTL trigger times,
  direct RTL traces, and the clean/Trojan replay inputs used by HT4;
- `multi_stage_chain_summary.csv`: compact composite detector outcomes;
- `detector_comparison.csv`: clean and infected outcomes for all existing
  detectors, with RTL security metadata;
- `attack_taxonomy_table.csv`: target, trigger, payload, and evaluation scope;
- `raw/`: GUI-compatible Virtual ECU logs and summary CSVs;
- `trojan_claim_summary.md`: measured result and bounded claim; and
- `README.md`: reproduction and output guide.

The directory is ignored by git because it contains generated evidence.

## Detection interpretation

The detectors are not rewritten and receive no `trojan_triggered`,
`payload_active`, `multi_stage`, stage flag, attack label, trigger time, or
scenario identifier. They see only their existing runtime-observable Virtual
ECU signals. The study script uses the RTL trigger times after the run to
classify alarms as pre-activation or post-activation evaluation outcomes.

Because the replay deliberately uses the ordinary `baseline` campaign rather
than inventing a C-level Trojan fault, the generic raw runtime
`false_positive_count` does not know that an external RTL payload activated.
The security report therefore uses the clean replay for the false-positive
reference and separately reports post-payload detection.

## Limitations

- This version is deterministic and trace-driven. The RTL consumes prerecorded
  nominal coolant, fan-command, and calibration inputs; the Virtual ECU replay
  is not a bidirectional cycle-by-cycle plant/RTL co-simulation.
- In the multi-stage chain, upstream runtime effects do not alter the
  prerecorded downstream RTL inputs, so combined thermal severity is not a
  closed-loop hardware prediction.
- The three payloads and triggers are configured examples, not a representative
  sample of all Hardware Trojan designs.
- Detection results apply only to this simulation, detector calibration, input
  trace, trigger, and payload.
- The experiment does not establish fabrication feasibility, physical
  stealth, gate-level properties, or silicon behavior.
- It is a research prototype, not a production-ready security solution.
