# Independent validation roadmap

This is a future plan, not implemented or measured validation. The frozen v5
holdout remains unchanged. Define success criteria and reserve independent traces
before evaluating an extension; do not tune current thresholds against new outcomes
and then label those same outcomes holdout validation.

| Step | Classification | Required evidence / decision |
| --- | --- | --- |
| Measured task execution duration | Required before stronger claim | Capture nominal release, availability, start and completion on a specified target; quantify instrumentation perturbation and clock error. Replace occupancy assumptions only in a separately versioned experiment. |
| Real OS/RTOS scheduler jitter | Required before stronger real-time claim | Independent legal and violating workloads, scheduler configuration, priorities and interference; compare trace-derived contract endpoints with monitor decisions. |
| Hardware-in-the-loop | Useful extension; required before HIL-backed claim | Instrumented ECU/plant interface with reproducible loads and fault schedules. Validate plant fidelity and timestamp alignment before claiming closed-loop benefit. |
| Embedded scheduling trace replay | Required before stronger timing generalization | Independent trace schema, dropped-event detection, clock rollover and job identity. Replay with frozen rules and preregister missed/false-alarm criteria. |
| CAN/network timing traces | Required before stronger communication claim | Sender/receiver timestamps, age, loss/replay patterns and clock synchronization. Separate legal network variation from system-specified violations and test realistic consequences. |
| Microarchitectural timing integration | Useful extension | Model or measure cache/memory/interconnect interference, relating completion traces to task contracts without equating simulator cycles with a certified bound. |
| gem5 for heterogeneous automotive compute | Future paper opportunity | Explore heterogeneous CPU/memory scheduling and extract timestamped task traces. Select and validate the CPU/memory models against the target; model availability alone is not fidelity evidence. |
| Embedded timing-monitor implementation | Required before target footprint/runtime claim | Port the unchanged C rules to a specified compiler/ABI, event source and timer; verify functional equivalence and supervisor independence on that target. |
| Runtime and WCET evaluation | Required before embedded timing/WCET claim | Separate typical measured duration from a defensible worst-case bound; include interrupts, caches, preemption and instrumentation limits in a system-specific method. |
| FTTI/hazard calibration | Required before system-level safety claim | Define the item, physical consequence and requirements independently. Justify threshold/exposure/hold/response budgets against that specification, not this simulator's favorable outcomes. |

Priority order: independent scheduling trace capture/replay and signal-boundary audit;
then target monitor measurements; then network/HIL and system-specific hazard/FTTI
calibration. gem5 is an optional later research avenue, not a prerequisite for the
bounded simulation paper or a task implemented in v6.

The Linux [rtla timerlat documentation](https://docs.kernel.org/tools/rtla/rtla-timerlat.html)
describes timer interrupt/thread latency observations. Such data can characterize
OS timing, but do not by themselves measure the application's complete job latency
or establish WCET. Use explicit application event instrumentation alongside them.

The [gem5 documentation](https://www.gem5.org/documentation/) describes its modeling
and event-driven simulation infrastructure; its
[SimpleCPU documentation](https://www.gem5.org/documentation/general_docs/cpu_models/SimpleCPU)
distinguishes CPU modeling choices. Using a model is a proposed research method;
validation against a specified automotive target would remain separate work.

No package installation, gem5 implementation, HIL integration, embedded port or
claim of certified timing is part of this platform freeze.
