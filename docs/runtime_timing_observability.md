# Trusted runtime timing observability (v4)

Accepted baseline: 8dcefbe. The new monitor is independent of Hybrid and all
existing detectors. It is disabled by default. This is a runtime timing safety
monitor in a test-enabled Virtual ECU, not an ISO 26262 compliance claim.

## Scheduler event boundary

`runtime_timing_observation_t` contains only scheduler-owned fields. Its header
includes no ECU state, fault descriptor, experiment ground truth, propagation
monitor or thermal plant type. `timing_safety_monitor_step` accepts only this
observation, its own state, a mode and a fixed evidence selection. The recorder
implementation also accepts only scheduler events and its own state.

| Field | Origin / meaning |
| --- | --- |
| task_id | Fixed control-task identifier 1 |
| time_ms | Scheduler monotonic observation time |
| period_ms / relative_deadline_ms | Configured control contract; P=D=100 ms |
| release_sequence / current_release_ms | Every nominal periodic release, including rejected releases |
| job_release_ms | Actual admitted job's nominal release, retained while pending |
| actual_start_ms | Callback immediately before the actual control computation |
| actual_completion_ms | Callback immediately after that computation; N/A while unstarted |
| execution_sequence | Successful computation counter |
| last_successful_execution_ms / execution_age_ms | Completion history; age since last completion (startup age from time zero) |
| job_outstanding | An admitted job has not completed or been cancelled |
| missed_expected_execution | A release was actually cancelled/rejected; not merely delayed before its deadline |
| deadline_exceeded | A cancelled job's deadline has arrived, an outstanding job is unfinished at its deadline, or a completion is late |
| cancelled_release_count | Cumulative rejected/cancelled periodic jobs, not a fault count |

The logger prefixes these fields with `trusted_`. There is no injected delay,
fault activity flag, fault ID, model, scenario, reference result or future hazard
in this interface. The existing injector-side v2 telemetry remains separately
logged for evaluation and backwards compatibility.

The accepted dispatch routine is `cross_layer_control_execution` in
`src/cross_layer_fault.c`. Its dispatch decisions are unchanged. V4 adds recorder
callbacks at actual release, admission and cancellation branches. Real computation
start/completion callbacks are in `src/scheduler.c`, surrounding `control_step`.
No monitor reads the dispatch routine's fault metadata or its evaluation state.
The callback arguments contain no configured injected delay or fault selection.
This co-location of the old dispatcher and injector is a prototype limitation,
not a claim that injector memory is an independently secured scheduler.

An explicit cancellation is observable before its deadline: the runtime knows the
expected job was discarded. Merely admitting a job without immediately executing
it is **not** a missed execution; it can still finish within contract. A delayed
job can complete at the same time a new release is discarded. The ledger records
both events and preserves the old job's release identity. It never fabricates an
actual start/completion for an unexecuted job.

Accounting invariant after each scheduler observation:

`release_sequence = execution_sequence + cancelled_release_count + outstanding_job`.

This is tested against actual successful control-execution timestamps. The fixed
single-job dispatcher has D=P, so at most one newly cancelled deadline waits for
the next release boundary. A completion exactly at its deadline is legal. If the
dispatcher rejects the concurrent new release, that is a separate missed job;
the exact-deadline task-delay case is consequently not a benign jitter scenario.

## Trust assumptions

The scheduler clock, configuration, event callbacks, counters and monitor state
are trusted. The modeled faults change dispatch outcomes, not this independent
recording path. The monitor runs independently of the monitored control task,
once per 100 ms scheduler tick, after completions. The surrounding scheduler,
clock and logger continue to execute during control-task absence. CPU starvation
of the supervisor, clock corruption, compromised instrumentation, interrupt
latency and scheduler sabotage are not modeled. The type boundary is an API
contract, not hardware memory protection around the legacy `ecu_state_t`.

## Fixed monitoring rules

For P=period and D=relative deadline, the complete contract evidence is:

1. Deadline violation: the recorder's completion/cancellation ledger establishes
   an overdue/unsatisfied deadline. Pending at D after the completion opportunity
   is a violation; completing exactly at D is legal.
2. Missed expected execution: an actual release cancellation or rejection.
3. Excessive execution age: age strictly greater than P+D (200 ms).

`timing_first_violation_ms` records the first complete-contract evidence even in
disabled/ablated configurations. This provides a common ablation latency origin.
Deadline timestamps and age come from the trusted contract, not injected duration.
Late start is visible through start-minus-release and deadline evidence; the
instantaneous computation model has equal start and completion timestamps.

The selected evidence is deadline-only, execution-age/missed-execution-only, or
combined. A selected violation raises an immediate anomaly alarm. At least three
violating observation periods in the trailing half-open 10P window establish a
repeated/persistent anomaly. The repeated alarm remains active until that evidence
ages out. These count violating **periods**, not necessarily distinct faulty jobs:
cancellation and its later unmet deadline may occupy two adjacent periods. A single
cancelled job occupies at most two, so it cannot alone reach the three-period rule.
Execution age >=3P establishes critical execution absence for the age/combined
monitor. It is already beyond the P+D age limit. The severity priority is critical,
repeated, single transient, normal. First alarm is latched; current alarm can recover.
No model-specific threshold, duration-based fault inference or scenario tuning occurs.

CLI:

```sh
./virtual_ecu /tmp/timing.csv baseline --cross-layer-fault deadline_miss \
  --fault-start-ms 20100 --fault-duration-ms 100 \
  --timing-monitor observe_only --timing-evidence combined
```

Modes are `disabled`, `observe_only`, `protective_action`. Evidence choices are
`deadline_only`, `execution_age_only`, `combined`. Execution-age-only explicitly
includes missed-execution events; it is not an age-scalar-only ablation.
Without any v4 CLI option, old CSV headers/rows and behavior remain unchanged.
Explicitly selecting a v4 mode appends instrumentation; existing fields retain
their order. Disabling the alarm still records the observed contract violations.

## Benign timing and limitations

The 100 ms simulator tick equals the control period. Control computations are
instantaneous in simulated time. Meaningful legal within-period jitter or nonzero
execution duration cannot be generated without changing accepted dispatch/physics
semantics. The study therefore uses real no-fault normal scheduling and profile
transitions as negative controls. Unit fixtures separately exercise legitimate
start/completion jitter at 25/99 ms, exact-deadline completion, and overrun without
any injector. Those fixtures are labeled synthetic and never counted as campaign
evidence. Zero alarms in two deterministic profiles is not a field false-alarm
guarantee. A richer scheduler is the next external-validity experiment.

Tests compile the recorder, timing monitor and response policy independently of
experiment/ECU implementation code. They verify ledger accounting, timing/mode
behavior, cancellation versus pending distinctions, legal completions, and default/
observation regression of existing detector waveforms and all old CSV fields.
