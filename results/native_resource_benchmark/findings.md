# Native CLOVER versus Origin RF replay

All 2,161,800 retained frames passed: RF probability maximum absolute error **0**, RF alarm/origin mismatches **0**, CLOVER alarm/origin mismatches **0**. An independent external-stack replay also retained exact RF probabilities and CLOVER outputs. No retraining or campaign was run.

## Instrumented elapsed host time

Pinned logical CPU 0, Intel i7-14700, GCC 11.4, -O2 -fno-fast-math -ffp-contract=off. Microseconds/frame:

| Measured stage | Median | P95 | P99 | Max observed |
|---|---:|---:|---:|---:|
| CLOVER decision + G2 | 4.747 | 5.227 | 7.113 | 1468.846 |
| CLOVER replayable pre-fusion region | 0.095 | 0.145 | 0.295 | 145.504 |
| CLOVER replayable core + G2 | 4.846 | 5.339 | 7.826 | 1468.943 |
| RF feature/history encoding | 0.296 | 0.327 | 0.372 | 133.688 |
| RF trees + alarm/origin gates | 4.442 | 5.320 | 10.513 | 5019.979 |
| RF features + inference | 4.743 | 5.647 | 10.974 | 5020.841 |

One sequential pass, CLOVER before RF, no cache flush/frequency lock/real-time isolation. Includes clock overhead and scheduling interruptions; excludes archive decoding and scoring. CLOCK_MONOTONIC_RAW measures elapsed time, not thread CPU time. Instrumentation affects short intervals. Maxima are not WCET. No statistically replicated speed-superiority claim is supported.

## Resource footprint

- CLOVER native struct: 4,304 bytes; G2: 12 bytes. Includes some upstream provider history.
- RF history: 4,804 bytes; shared providers additional, not included.
- RF constant arrays: 2,438,432 bytes (200 trees, 33,856 nodes, 17,028 leaves, depth 12).
- Combined library .text: 17,885 bytes; .rodata: 2,439,188 bytes; .data/.bss: 8/9,312 bytes. This includes helper/exported functions and the common harness; it is not a separately linked deployment-size comparison.
- Combined observed stack high-water: 9,416 bytes, including pthread/TLS and common replay wrapper. Empty pthread: 4,608 bytes; do not subtract this as an exact method cost. All 2,161,800 frames exercised. Individual compiler frames: replay 2,528 bytes, CLOVER core 1,760 bytes, ds_combine 592 bytes. Per-method whole-path peak is not isolated.

## Explicit incomplete scopes

The saved frames contain outputs of integrity, Triplex and memory probing, not the producer records and callback transactions needed to execute those entire providers. Thus **full shared-provider costs and complete producer-to-decision pipeline costs are not measured**. The measured CLOVER pre-fusion region also includes provenance preparation; it must not be labeled strictly common upstream cost. The recorded RF-plus-prefusion arithmetic sum is not an executed complete pipeline. RF receives the retained same-information evidence; neither method consumes outcomes. Physical sampling/probing latency and hardware acquisition costs remain outside this software replay.

The strongest defensible result is exact native prediction parity with compact CLOVER state versus a 2.44 MB RF model. Median replayable costs are close; tail values from one host pass do not establish embedded guarantees.

## Regression/preservation

Build, Python compile, 366 tests, git diff check, 48 legacy and 64 RTL passed. All 37,977 pre-existing files in the preservation manifest were unchanged, including GUI, frozen methods/results and Hybrid/HETIA. Existing tracked GUI modification was present at entry and preserved. No commit/push.
