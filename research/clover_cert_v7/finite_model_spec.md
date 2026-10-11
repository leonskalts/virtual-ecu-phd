# Finite timed component model

This experiment is a finite restriction of real ECU **component behavior**, with an explicitly controlled open-loop environment. It does not enumerate every execution of `scheduler_run`, the thermal plant, optional wrappers or hardware. Exact copied source anchors (relative path, 1-based line, function, token) are in `two_world_model.json`; all 134 v6 anchors and 36 file hashes were rechecked before modeling.

## Bounds and admissibility

Time is 0,100,200,300,400 ms. Fault starts are independently chosen per world from 100 and 200 ms; normal durations are 100 and 200 ms. All intervals are half-open. The diagnostic deadlines 100,200,400 ms are **absolute from experiment start**, not relative to fault onset. A not-yet-active fault legitimately competes at an early deadline. Contexts set coolant input to 60 C or 92 C throughout and load/speed to zero. No plant integration occurs. This is an open-loop component fixture, not a physically established steady trajectory.

The complete finite realization domain per context is:

| Origin | Realizations | Parameter choices |
|---|---:|---|
| Memory | 24 | flip bits 0 or 2; stuck bits 0 or 2, polarities 0 or 1; both starts/durations |
| Timing | 10 | skip duration 100 only; delay 100 or 200, both starts/durations |
| Communication | 12 | delay 100, replay age 100, first-one-drop; both starts/durations |
| Sensor | 12 | bias -4/+4 with both starts/durations; also 25 ms windows at 100 or 150 |
| Actuator | 8 | pump scale 0 or 0.5, both starts/durations |
| Healthy | 1 | no fault; included to prevent forced classification |

Each pair uses the Cartesian product of its domains, never a shared parameter choice constraint. Cross-layer configurations pass the existing `cross_layer_validate` in the C fixture. Sensor/pump faults use the existing legacy event structure and gate; mixed legacy/new faults are not composed. A 150–175 ms sensor event is never visited by the scheduler-style 100 ms calls: it is a configured, missed legacy window, not measured evidence that a physical pulse actually occurred. See v6 `legacy_window`, `legacy_config`, `alignment` and `mixed_reject` anchors.

## State and transition order

Initial register/shadow/active target are 92; pump command and realization start at 0.25; last control execution is -1. Source and delivered values start at the chosen environment value. At t=0 normal control executes before the first observation. The selected control expression has zero load, and uses the actual constants 0.30 and 0.025. Both environment values and all parameters are finite binary32 values.

1. Fault activation/restoration: flip on activation, save original register, restore on exit; active stuck forces its bit every visited tick. Matching polarity has no value difference (`active_window`, `memory_save`, `flip`, `restore`, `stuck`).
2. Acquisition at every tick: bias before source tap; current acquisition value is the producer for both tap and normal delivery (`sensor_bias`, `source_tap`, `acquire`). No pristine reference goes into inference.
3. Communication records history and either delivers a selected historical sample or retains the previous value and source time. Delay suppresses its initial delay interval; replay selects t−age; drop suppresses the first active update (`history`, `comm_delay`, `comm_drop`, `comm_replay`). The published age is t−source time, with freshness true below 300 ms.
4. Control release/gate: skip suppresses execution; delay retains one job and discards releases while pending, including the completion tick. A pending job can execute after fault recovery (`release`, `skip`, `delay_due`, `delay_complete`, `discard`). On execution, the register is consumed and `last_execution_ms` updated. Otherwise the target and command hold.
5. Actuator realization: clamp command, then scale if pump fault active (`pump_scale`, `pump_publish`). The thermal consequence is excluded, not approximated as an observed outcome.
6. Capture selected fields after actuator realization. The actual base scheduler has diagnostic/safety/detector reactions before its later capture; those paths are deliberately absent from this fixture. `M_PHASE` prevents transferring its results to that full path without further validation.

Every modeled execution includes a time-indexed event trace with phase effects, pending job, consumption and acquisition/delivery events. These events, origin labels, injected parameters, and activation metadata are **offline model data**, never arguments to the runtime decision procedure.

## Observation policies and comparison

All policies leave source acquisition/control at 100 ms. They vary the **checker observation selection/capture**, not the ECU acquisition schedule:

- `values_100`: delivered coolant, pump command, pump realization every 100 ms.
- `timestamp_100`: those values plus published sample timestamp, age and freshness.
- `full_100`: additionally register, shadow/validity, consumed target, last execution time, source tap/time/validity. “Full” means the full selected allowlist, not every ECU field.
- `full_200`: the same allowlist, observed at 0,200,400 ms. Intermediate observations are not retained; no latch is invented.

Capture time is included in every history. Floats are represented as eight hex digits of IEEE binary32. Equality compares bits, exact integers and booleans, with **zero absolute/relative tolerance**. Python rounds each modeled arithmetic operation to binary32; gcc runs use no FMA or fast-math. The finite domain excludes NaN/infinity. This choice makes the finite software comparison reproducible; it is not a realistic physical noise model or a claim of sub-bit measurement resolution.

## Reference oracle and two-world relation

Let E(c) be all 67 modeled executions for context c. For policy p and deadline d, H(e,p,d) is its selected observation prefix. Define C(h) = {origin(e): e in E(c), H(e,p,d)=h}. The decision is the sole member of C(h) if |C(h)|=1, otherwise UNKNOWN (including C(h) empty). Healthy is a possible origin, not an omitted negative class. Context selects an experiment-specific model; the online decision receives only h and the offline relation, never the injected world's origin, parameter or plant truth.

A pair is INDISTINGUISHABLE if there exists eA,eB with different origins and equal prefixes. It is CONDITIONALLY_SEPARABLE if their entire finite history sets are disjoint under the stated context, policy and deadline. This is stronger than finding one visibly different pair, but only over this finite domain. A particular singleton history is also reported separately; it does not establish pairwise disjointness globally.

The singleton rule is sound **for E(c)**: the actual modeled execution belongs to the enumerated compatible set, so if that set has one origin, it is its origin. If two origins remain, any specific answer fails in at least one admissible world. This elementary argument neither proves model completeness nor resolves integrity. Every positive result retains policy-specific obligations; physical certificates and PROVEN_SEPARABLE_WITH_VERIFIED_CONTRACTS results number zero.

The reference is intentionally simple enumeration/indexing. An independent linear scan and explicit Cartesian-product checker test it; unchanged C modules independently test the transition predictions. It is not the proposed paper algorithm.
