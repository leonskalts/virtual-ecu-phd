# Protected digital-integrity witness: RTL feasibility proof of concept

This is a logical implementation of `di_publish`/`di_verify` and the protected-record update performed by `di_transform` in [the frozen C witness](../../src/v7_3/digital_sensor_integrity.c). It does not change the final A2 detector, its evidence mapping, its 300-ms FAIL retention, or any campaign. One module instance holds one sensor's record; A/B/C would use separate instances.

## Interface and trust boundary

- A rising edge with `publish` seals channel ID, 32-bit measurement bits, sequence, timestamp and CRC-32. The first sequence is 1; later publications increment modulo 2^32. Synchronous `reset` invalidates the witness. Reset has priority over publication, which has priority over transformation.
- A trusted producer may assert `transform` with its legitimately transformed `producer_bits`. Channel, sequence and timestamp remain unchanged; value bits and CRC are updated. Transformation of an unavailable witness does nothing. Floating-point calibration arithmetic remains in the producer; this monitor contains no FPU and never derives a trusted value from a consumer input. The C testbench checks a real `di_transform(+0.5f)` against this interface.
- `sealed_*` exposes the producer-owned envelope for downstream transport. Consumer inputs are a separate envelope plus the actual consumed value bits/timestamp. There is no consumer write path to the protected registers. Consumer inputs cannot increment sequence or reseal the witness.
- CRC uses the exact C polynomial, initialization/final complement and little-endian channel/bits/sequence/timestamp ordering. It checks both the protected record's CRC and the consumer record's CRC.
- `causes[0]` = value/identity/tag comparison mismatch; `causes[1]` = timestamp/sequence mismatch; `causes[2]` = invalid CRC. These bits can coexist. For example, an unresealed sequence change also makes the CRC invalid. Values 1/2/4 match the software bitmask exactly.
- `result`: 0 UNAVAILABLE, 1 PASS, 2 FAIL. Unavailable gives zero causes, matching the C verifier's return value while exposing the witness-valid state separately, as the final provider does. There is no timeout or independent freshness claim beyond comparison with the current producer-owned record.

Verification is combinational: zero additional clock cycles, **not zero physical delay**. Inputs must settle before a result is consumed. Publication/transform commits at one rising edge; concurrent verification after that edge refers to the new record. Integration must preserve this ordering and provide any needed output sampling/CDC. No consumer-ready protocol or FAIL latch is included.

## Verification and reproduction

Run from the repository root:

```sh
python3 -B scripts/run_rtl_integrity_poc.py
```

The self-checking [C testbench](../../sim/integrity/digital_integrity_tb.c) links the unchanged C witness as an independent oracle. Verilator needs a small generated C++ signal binding in a temporary directory; no virtual-ECU runtime C++ is added. No fault campaign is invoked.

**3,348 checks passed**, each comparing validity, all five protected-record words, cause bits and result. Directed coverage includes PASS, consumed-value corruption, envelope-value corruption, channel mismatch, sequence mismatch, record timestamp mismatch, consumed timestamp mismatch, bad tag, reset/unavailable, modification of data with a correctly recomputed tag, replay with a valid tag, combined causes, producer update and authorized transformation. It also compares 256 deterministic arbitrary-bit records and their mutations. Clean verification after each corruption checks that consumer activity did not overwrite the witness. This is simulation evidence, not exhaustive formal equivalence; physical register upsets, CDC, sequence-wrap execution and X-state behavior are not exhaustively verified.

## Synthesis and timing result

Evidence is in [results/rtl_integrity_poc](../../results/rtl_integrity_poc/): RTL simulation/build logs, Yosys statistics and mapped netlist, OpenSTA report/constraints, source/library hashes and preservation record.

| Item | Result |
|---|---:|
| Synthesizable RTL | 62 lines, 1 module |
| Protected storage | 160 record bits + 1 validity bit |
| Mapped flip-flops | 161 `DFF_X1` |
| Combinational cells | 4,395 |
| Total mapped cells | 4,556 |
| Summed library cell area | 7,425.656 µm² |
| Sequential cell area | 728.042 µm² |
| Worst reported logic path | 3.4930 ns, consumer channel bit to result |
| Verification latency | Combinational; zero added cycles |

Tools: Verilator 4.038, Yosys 0.58+76 (`1598771a3`), OpenSTA 2.7.0. Mapping uses the existing `/usr/local/share/qflow/tech/nangate45nm/nangate45nm_copy.lib` typical Nangate45 library. The neighboring `nangate45nm.lib` comments out its sequential cells and could not map flip-flops; the complete installed copy was used without altering either library or installing tools.

Timing assumptions: ideal 100-ns clock, 1-ns input and output delays, 0.01-pF output loads, library/default input slew assumptions, no extracted interconnect or placement/clock tree. The worst arrival is 4.4930 ns including 1 ns of input delay; worst setup slack is 94.5070 ns. The implied 5.4930-ns interface period budget (approximately 182 MHz with these I/O assumptions) is only a pre-layout estimate, **not a sign-off maximum frequency**. Cell area excludes routing, pads, floorplan/utilization overhead and external producer/access-control logic. The fully combinational CRC dominates the cell count; no minimum-area claim is made.

## Limits

The producer/reset/transform ports must be reachable only by a trusted producer in the enclosing system. This module enforces separation of logical ports, not physical tamper resistance, bus privilege policy or independence of power/clock domains. CRC is not a MAC. Corruption before trusted publication, or consistent common corruption of record plus witness, is outside the guarantee. The monitor observes neither physical temperature nor injected fault metadata. It does not detect an unsampled event, identify the physically faulty sensor, or prevent an untrusted component from violating integration assumptions.

The frozen witness sources, GUI state and digital-integrity/benign-alarm/final-unseen result files were hash-checked unchanged during the successful run. No final detector/result changes, new campaigns, commit or push were performed.
