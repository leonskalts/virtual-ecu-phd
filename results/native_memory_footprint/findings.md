# IEEE native memory footprint analysis

## Verification and boundaries

Six separately linked host executables (normal and external-stack versions of CLOVER, RF and RF+providers) each replayed all **2,161,800** retained frames. All RF probabilities matched exactly; alarm/origin mismatches were zero. No retraining, new fault injections or simulator campaigns.

**A — Method-specific decisions.** RF includes all 174 features, finite/timestamp handling, histories, 200-tree probability inference, alarm and origin/UNKNOWN selection. Its exact isolated footprint is below. CLOVER's frozen optimized function/state interleave local providers with DS, temporal logic, causal localization and G2. Its pure-A code/state allocation cannot be isolated exactly from these builds; report its complete replayable B footprint instead. Do not compare RF A directly with CLOVER B as equal-pipeline RAM.

**B — Matched replayable diagnostic pipelines.** RF B additionally executes the identical frozen pre-fusion provider prefix and availability/origin-support encoding from the same raw observation packet. CLOVER already includes these providers. Each counts them once. No CLOVER prediction is an RF input. Both exclude producer-side Triplex-C, integrity record creation/verification and physical M2 probe transactions, whose outputs are the common inputs available in this archive.

**C — Full producer-side ECU.** Not measured: the retained records lack all producer transactions, and a full-ECU image/hardware integration is outside this task. Never label B as full ECU cost.

## Exact linked payload bytes

Each column is attributed to method payload.o in the final executable map, **excluding replay main, buffers, CRT startup and loader plumbing**. Spans include internal alignment. The packet ABI adapter is included. Libraries are dynamically linked and not included in the payload.

| Resource (bytes) | CLOVER B | RF A | RF B |
|---|---:|---:|---:|
| .text span | 12,605 | 1,084 | 9,305 |
| .rodata span | 356 | 2,438,560 | 2,438,816 |
| .data | 0 | 0 | 0 |
| .bss span | 4,432 | 4,804 | 9,360 |
| Code/constants ROM subtotal | 12,961 | 2,439,644 | 2,448,121 |
| Method .eh_frame metadata | 492 | 84 | 324 |
| ROM including method unwind metadata | **13,453** | **2,439,728** | **2,448,445** |
| Observed method-step touched stack | 3,544 | 2,160 | 4,184 |
| Static RAM + observed stack | **7,976** | **6,964** | **13,544** |

These are host XIP-style code/constant and writable-state budgets, not actual MCU flash/RAM placement or linker-ready memory reservations. Reset's compiler frames are retained; dynamic stack results concern method_step. No heap in the production method path. Input/output buffers belong to the caller and are excluded symmetrically. Stack already contains feature temporaries; do not add them again.

Persistent content before linker padding: CLOVER **4,413 B**, RF A **4,804 B**, RF B **9,333 B**. CLOVER's 4,304-byte state and 12-byte G2 gate are subsets of its BSS, not additions. RF's two histories and index are 4,804 B, already included. RF B also includes one provider context and prepared-evidence buffer, not another whole CLOVER detector.

RF model storage **2,438,432 B** is a subset of .rodata: 33,856 72-byte nodes plus 200 four-byte root indexes. The verified export retains internal-node probability arrays; its 64-bit ABI layout adds **135,424 B** of intra-node padding. No packing, pruning or model-format optimization was attempted. These are exact current-layout costs, not irreducible RF costs.

## Alignment, ELF and linker accounting

Unpadded method .text/.rodata/.bss content:
- CLOVER: 12,455 / 348 / 4,413 B; internal padding 150 / 8 / 19 B.
- RF A: 1,069 / 2,438,552 / 4,804 B; padding 15 / 8 / 0 B.
- RF B: 9,238 / 2,438,808 / 9,333 B; padding 67 / 8 / 27 B.

ELF file sizes including replay/loader/symbol tables are **30,024 / 2,453,536 / 2,462,688 B**, respectively. They are NOT deployed method RAM/ROM. Full executable sections and LOAD file/memory sizes are in footprint.json; readelf program headers retain page alignment and segment gaps. GNU size alone cannot isolate method costs. Linker maps also show constant merging: pre-link object totals must not be substituted for final linked content.

CRT, .plt/.got, dynamic tables, whole-image unwind headers, shared libc/libm/loader and intersegment page gaps are kept in the whole-ELF accounting, not silently charged to one method. Method-local unwind data is reported explicitly. Full process RSS is not inferred from ELF size.

## Fair ratios (RF B / CLOVER B)

- Code/constants: **188.883651×**.
- Including method unwind metadata: **181.999926×**.
- Static RAM: **2.111913×**.
- Static RAM plus observed touched stack: **1.698094×**.

These conditional payload ratios match the replayable provider boundary. They exclude full producer costs and common dynamic libraries, and depend on the exact exported structures. RF B retains the original provider struct layout, including unused members; a compact redesign could change RAM without changing predictions. Do not claim these are minimum algorithm costs or MCU-specific ratios.

## Stack and reproducibility limits

GCC 11.4, x86-64 SysV, -O2 -fno-fast-math -ffp-contract=off, identical function/data-section settings and section GC, no LTO or semantic-changing options. A dedicated 1 MiB aligned measurement stack excludes the replay loop/pthread frame. Dynamic binding is warmed, state reset, then every case/frame executed. A5 watermark reports deepest changed bytes, not untouched stack reservations or a proven worst-case bound. Shared library callees are included in the observed stack, though their code is outside payload ROM. Memory results do not establish timing/WCET.

Maps, readelf, size, nm and compiler stack reports are retained compressed. Build and full-frame equivalence passed; five focused RF/G2 tests, Python compile and git diff check passed. Preservation hashes are recorded separately. No commit/push.
