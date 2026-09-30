# Triplex implementation audit, before new campaign outcomes

No detector correction selected. No thresholds, fusion, memory schedule, C model, latch or actuator changes.

## A/B differences and classifications

- **B, inherited ECU semantics:** `src/v7_3/clo_dsf_revised.c` acquisition plausibility/slew (`acquisition_sensor`), acquisition-to-consumption, 300ms `sensor_response`, startup `slew_qualification_count` and actuator recovery checks refer to primary A. A feeds control; B does not. Swapping physical A/B roles therefore does not imply full ECU score invariance. Adding these providers to B would be a detector redesign, not a pairwise bug fix.
- **A, physically intentional:** `src/sensors.c` primary acquisition versus `src/redundant_temperature.c` independently seeded noise, offset and 0.01C quantization. B-only perturbations do not change closed-loop control; A-only perturbations do. Sensor C has independent gain/noise/ADC/quantization and acquisition phase. Compare identical observations for symmetry, not merely similarly named injection cases.
- **B, inherited status contract:** the original AB provider has an explicit B conversion-failure flag; A validity/timestamp and consumed-value contracts use primary ECU diagnostics. Reversing endpoints including different hardware status semantics is not an equivalent observation. Normal valid pair residual arithmetic is symmetric.
- **A, timing topology:** C is causally projected from its two past samples to the ECU epoch; A/B are synchronous. AC and BC use the same projection and 5-C-sample startup qualification. AB has its original availability/startup semantics and no C dependency. Stale/failed C has its explicit acquisition contract. This does not favor A over B.
- **No C/D implementation or ordering artifact found:** AC and BC have independent identically initialized state. BC remaps source value, validity and timestamp to B; the pair functions consume no other A-specific fields. `fmax` of pair strengths feeds one sensor source; pairs receive no different DS reliability or extra votes. AB stays the original source. Pattern1 A|BC swaps to pattern2 B|AC; pattern3 C|AB and all-disagree UNKNOWN are symmetric. No claim identifies the faulty individual sensor.
- **No E numerical/scaling artifact found:** all valid pairs use signed double subtraction of float readouts, identical absolute 0.90C slow envelope, 320 samples, 0.40C fast floor, 1.2C/s slew envelope, 300ms anchor, same-sign accumulation and 10-edge history. Reversing endpoints negates signed state and leaves strength unchanged. C projection is cast to float for both AC/BC. Pattern classification uses the same unrounded C projection for both sides; this is a uniform representation difference, not A/B bias. Noise bounds are fixed, not fitted per sensor.
- **Localization:** only SENSOR_CONTROL main origin is exposed, not A/B member labels. Earlier direct-origin causal precedence remains unchanged. All-mutually-disagree qualification suppresses confident localization equally under A/B exchange.

## Permutation tests

`tests/test_triplex_symmetry.py`: nine runtime-equivalent scenarios, 899 samples each: positive/negative step, drift, pulse, alternating bounded noise, single spike, mutual disagreement and invalid/stale acquisition and asynchronous C projection. AC/BC exchange, combined strength, qualification, ambiguity and member-pattern exchange are asserted at every timestamp. AB/BA, AC/CA, BC/CB strengths match within 1e-12 at every timestamp, hence provider detection crossings/timing agree. Full ECU A/B swapping is deliberately not asserted: it swaps a control input with a diagnostic-only channel and changes physical semantics. Main-origin localization remains SENSOR_CONTROL under member exchange.

## Memory bug audit

All five historical A1 memory misses have effective_memory_corruption=0. The unchanged scheduler probes at 0,1100,...,9900,10000,... ms; fault windows are half-open and intermittent phase is relative to activation. Active-probe intersections:

|Case|Window ms|Active probe epochs|
|---|---|---|
|latch_1809|24500–25000|none|
|latch_1959|25800–26700, first on600ms|none (26600 is off)|
|latch_2104|27100–27600|none|
|latch_2106|27900–30600, on900/off1600|none (28800 off boundary; 29900/30000 off)|
|latch_2263|28200–28700|none|

Backend and shadow address the same target_register_c; probe saves, writes0/65535, reads and restores, verifies restoration. Bookkeeping counts seven operations and phases modulo10 correctly. Fault application precedes the atomic diagnostic transaction. None of these cases is near the120000ms run end. No address mismatch, stale state, indexing or end-accounting defect found. A later positive feature in latch_1959 does not establish contemporaneous memory corruption. Leave memory unchanged; do not increase probe frequency or force dormant alarms.

## Decision before new outcomes

No unjustified pairwise A/B asymmetry or memory defect found. No fix applied. The 28/28 versus24/28 result alone is not proof of a symmetry defect. New TRAIN/CALIBRATION verify the unchanged implementation; new validation retains all difficult actuator and memory cases. No tuning on old or new validation.

Focused tests: permutation test and seven existing memory diagnostic checks pass (including phase coverage, restore, legal updates and stale evidence). TRAIN/CALIBRATION are verification only; no parameters selected or adjusted.
