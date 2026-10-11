# Native frozen-method replay

`prepare.py` exports the retained RF as hexadecimal double constants and builds an isolated shared library. It reads the exact final generated CLOVER source, inserts a clock hook at the existing pre-fusion boundary, and supplies logging-free G2 callbacks. Source identifiers and frozen files are unchanged. `verify.py` must pass before `measure.py` runs. No outcome field enters either native method.

Run from repository root using Python with the existing `/tmp/clo-ml-deps` dependencies. Generated C/model arrays, binaries and transient buffers live in `/tmp/clo-native-resource`; retained evidence lives in `results/native_resource_benchmark`. `frozen_core.c.gz` there preserves the exact generated input for reproducibility if the original temporary build disappears. The build provenance records its original hash.

RF preserves all 174 features, per-case reset, timestamp/finite encodings, 10/50-frame histories, float32 tree inputs, double thresholds/leaf probabilities/accumulation, strict alarm threshold, class tie order and UNKNOWN gates. Full-cohort output parity is exact; this is empirical equivalence on the archive, not a proof for every possible input. Rolling sums are computed in C; no quantization of model parameters or leaf-vote substitution is performed.

Timing is a single pinned-host replay, not embedded WCET. RF feature/inference and CLOVER core boundaries are explicit. The CLOVER pre-fusion interval also includes provenance preparation and is not a clean, separately factored common-provider implementation. Integrity/Triplex/probe producer costs cannot be recovered from the saved output-level records. The arithmetic RF-plus-prefusion sum is descriptive, not a measured end-to-end RF pipeline.

`stack_measure.py` separately measures the unchanged library on all retained frames using `stack_watermark.c` and checks output parity again. Its high-water mark includes pthread and the common replay wrapper. Compiler `.su` reports supply individual function-frame sizes, not independent whole-method stack peaks.

`regress.py` restores pre-existing binaries/objects after build/tests and verifies preservation hashes. No campaign generation or training occurs here.
