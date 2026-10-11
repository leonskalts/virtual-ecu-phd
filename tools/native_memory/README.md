# Isolated native memory analysis

Build: `python3 -B tools/native_memory/build.py`, then `build_pipeline.py`.
Verify: `PYTHONDONTWRITEBYTECODE=1 python3 -B tools/native_memory/verify.py` and `verify.py rf_pipeline`.
Account: `python3 -B tools/native_memory/report.py`.

Generated files stay in `/tmp/clo-native-memory`; compact maps/symbols/sections and findings stay in `results/native_memory_footprint`. The build reconstructs the exact previously verified hexadecimal model export from the frozen pickle and asserts its published hash. No training or simulator invocation.

Both methods use identical optimization/FP settings. Each has an independent ELF. Link-time section GC keeps only method_reset/method_step dependencies in payload.o. The replay main is in a separate object, and map accounting excludes it and CRT/linker infrastructure. The native packet-to-observation ABI adapter remains included, as do method-specific local calculations, feature histories and localization gates.

Three payloads:
- clover: full frozen replayable core, DS/temporal/localization/G2 and its local provider extraction.
- rf: complete 174-feature/history/model/alarm/localization processing with already-prepared evidence.
- rf_pipeline: RF plus the identical frozen upstream prefix, including startup qualification and provider support mapping; no DS alarm/origin enters RF. Producer-side integrity, Triplex-C and physical memory-probe transactions are outside both B boundaries.

CLOVER's pure decision code and its provider state are intertwined. The report does not fabricate a pure-A size by subtracting ELF totals, nor count its combined state twice. The B comparison is the matched footprint comparison. RF's common provider struct retains unused members of the original frozen layout; it is not a minimal packed implementation. Model nodes also retain the verified export's padding and internal-node probabilities.

Stack probe: dedicated aligned 1 MiB x86-64 SysV stack via stack_call.S; method_step itself is unchanged. Warm binding followed by reset, then all frames per case, A5 watermark. Counts method call/callees and excludes replay loop and pthread. Touched bytes may undercount untouched reservations or matching marker bytes; not a proven stack bound. Compiler .su files retained. No deployment heap is allocated; replay heaps/1MiB stack reservation are measurement-only.
