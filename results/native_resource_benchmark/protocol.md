# Native resource replay protocol

Frozen references: ieee_origin_rf archive/model/selection and final assembled A2 core. No fitting, campaign or change to either method. Export constant arrays losslessly; compile both in one C translation unit with GCC -O2 -fno-fast-math -ffp-contract=off. Reset all histories per case.

Gate: all 2,161,800 frames must agree on both methods' alarm/origin predictions. RF probabilities must differ by at most 1e-14 (also report exact maximum). Stop on failure; no timing before a successful gate.

After gate, one sequential pass pinned to the lowest permitted logical CPU on the i7-14700. CLOCK_MONOTONIC_RAW per-frame elapsed intervals; median/P95/P99/max. No cache flush, frequency lock, real-time isolation or overhead subtraction. CLOVER precedes RF. These are instrumented host elapsed times, not MCU timings, CPU-cycle bounds or WCET.

Report RF feature encoding plus inference, and CLOVER retained core plus G2. Instrument the existing pre-fusion boundary. Common measured extraction is only a PARTIAL upstream cost: saved integrity/probe/Triplex outputs cannot recreate producer-owned records, physical acquisition/probe callbacks or original asynchronous provider execution. No fabricated complete-pipeline cost. Exclude scoring, diagnostic bookkeeping, logging, decompression and replay conversion from timed sections.

RAM: ABI-specific persistent structs, const model arrays, compiler stack-usage reports; do not conflate Python process memory or pickle size with native resources. Do not call per-function stack frames measured peak stack.
