# Frozen timing-monitor and policy contract, v5

Baseline: da126cb (accepted v4). This specification precedes final holdout execution.
The v4 monitor, its observation type and its original event recorder are unchanged.
No implementation correction to the monitor was needed. Exact source/configuration
hashes are frozen in `results/cross_layer_safety_v5/timing_monitor_contract.json`.
The runner refuses a changed frozen source/configuration/profile hash.

The primary monitor is combined evidence, observe-only, sampled once per 100 ms.
P=D=100 ms. A job unfinished at its deadline after the completion opportunity,
a late completion, or an actual cancelled/rejected release violates the contract.
Execution age >P+D is evidence. Three violating observation periods in the trailing
half-open 10P establish repeated severity. Age >=3P establishes critical absence.
The unchanged v4 source defines exact priority, latching and timestamp semantics.
One cancelled job can occupy two violating periods; these are not independent jobs.
Ablations replay the exact same telemetry through the unchanged compiled C monitor;
they are secondary fixed evidence selections, not alternative tuned primary rules.

Policies are frozen before outcome inspection:

- Observe-only: no new runtime policy request.
- Immediate: exact v4 qualification/actions. Repeated timing -> precautionary
  cooling; critical absence -> limp-home. Existing detector alarm AND failed
  existing freshness status -> limp-home immediately.
- Graded: same qualified timing and communication events -> precautionary cooling.
  Escalate to limp-home only when control execution age >=5P or a continuously
  qualified communication alarm has lasted >=5P. An isolated timing transient
  still gets no action. Alarm gaps reset communication persistence.

No fault identity, injected duration/delay, severity label, reference, plant truth,
future hazard, or legal/overload label enters either runtime monitor or policy.
A policy can change subsequent detector signals through closed-loop feedback.
Existing safety recovery/hysteresis and diagnostic reactions remain in force.
No policy treats requests already satisfied by existing safety as new interventions.

The new opt-in scheduler explicitly models deterministic availability/start jitter
and CPU occupancy. Legal envelope: maximum release jitter + maximum start jitter +
execution duration <=100 ms, with deadlines anchored to nominal releases. Seeded
LCG variation is workload generation, not sensor noise or fault randomness. Queue
capacity is four jobs; only an actual full-queue rejection is missed-execution
telemetry. Backlog alone is not cancellation. This separates short deadline overruns
from execution-age/missed-execution evidence. The queue observes all job deadlines,
including waiting jobs. Exact-deadline completion precedes deadline checking.

The monitor still samples every 100 ms; event bookkeeping has 1 ms resolution.
C control computations occur at modeled completion events, using held sensor data.
Simulated CPU duration is explicit occupancy, not measured host time or ECU WCET.
Plant, sensor, actuator, diagnostic and existing detector macrosteps retain 100 ms
scheduling. Between-boundary completions affect commands at the next macrostep;
substep thermal feedback is not modeled. The plant equation/integrator is unchanged.
The alternate scheduler cannot be combined with direct fault injection. Direct v5
fault cases still use the accepted v4 dispatcher. Neither backend changes the other.

Scheduler event CSVs record each completed/rejected job, nominal/actual release,
actual start/completion, deadline, jitter, duration, margin and violation. Final
unfinished jobs remain visible in the queue/deadline counters, not fabricated as
completed event rows. The queue conservation law is releases=completions+rejections+
queued jobs. Deadline/cancellation evidence is accumulated between monitor samples.

Trusted supervision, clock, event collection and monitor state are assumptions.
This is an API boundary, not hardware isolation. The legacy dispatcher shares its
module with the fault injector; the separate workload scheduler contains no injector.

Final logging correction: a rejected job never reaches actual release/start/completion, so those event endpoints and its margin are N/A. Completed-job minimum margin is N/A before the first completion. The logged fields were corrected without changing event scheduling or monitor/policy decisions; the frozen source manifest was refreshed before the final rerun.
