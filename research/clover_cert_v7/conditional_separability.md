# Conditional separability and ambiguity cases

Outcome definitions:

- **PROVEN_SEPARABLE_WITH_VERIFIED_CONTRACTS:** disjoint histories with all relevant deployment contracts established. No case qualifies here.
- **CONDITIONALLY_SEPARABLE:** disjoint finite history sets, or a singleton finite history, subject to named unresolved/model assumptions. Pair results and singleton results are distinguished.
- **INDISTINGUISHABLE:** explicit admissible equal-history worlds exist for the chosen view/deadline. The checker must return UNKNOWN for that history.
- **INSUFFICIENT_MODEL_EVIDENCE:** the requested behavior, acquisition point or adversarial corruption is not represented by a verified path in this experiment; no fabricated counterexample or positive proof is substituted.

Every positive uses M_CLOSED, M_CONTEXT, M_PHASE, M_NUMERIC, A_PROCESS, A_BUILD, A_FAULTSET, A_CLOCK, A_TAP and A_PUMP; full views additionally use A_SHADOW. These are conservative whole-view obligations, not claimed minimal certificates. Their statements and unresolved statuses are in `validity_and_assumptions.md` and the manifest. No independence is inferred from separate field names.

## A. Memory before versus after consumption

The source order mutates register before same-tick control consumption (`flip`, `consume`). The offline event trace shows this transition; it is not a runtime pre-consumption measurement. Under single-fault/base scheduling, memory faults do not also skip control. Consequently a long dormant-before-consumption observation window or a pre-control checker is **INSUFFICIENT_MODEL_EVIDENCE** here. Adding it would be a design alternative.

After consumption, a changed register/target can be conditionally distinguished with full capture. Under zero command, saturated commands alone mask the change. A stuck bit already equal to its forced polarity yields no mismatch even after consumption: at bit 0/polarity 0, full history matches a healthy world and a zero-command degraded pump. This is **INDISTINGUISHABLE** through 400 ms. Optional v6 probes exist, but are not enabled in this selected component model; no probe result is silently added. Deployment use needs protected shadow/writer provenance (A_SHADOW), not merely agreement.

## B. Aligned versus missed sensor window

Legacy bias [100,125) is sampled at 100 ms; [150,175) is missed by all 100 ms acquisition calls. The first produces a source/delivered change and conditionally unique sensor histories in the finite constant-input context. The second matches healthy, latent memory and other invisible manifestations. A full_200 checker can additionally miss an acquired 100 ms pulse because it does not preserve that observation. These are different gaps: acquisition versus checker capture.

The C fixture verifies sampled legacy gate behavior, not existence of a physical inter-tick pulse. Optional 25/50 ms batched interpolation is not modeled; no online publication bound follows from it. A hardware pulse latch or a verified faster acquisition path remains a hypothetical extension.

## C. Zero versus nonzero pump command

At 60 C/load zero, control clamps to zero; scaling by 0 or 0.5 yields identical zero realization. World A: stuck bit 0/polarity 0, start 100/duration 100. World B: pump scale 0.5, start 100/duration 100. Their full selected histories are identical. This is a cross-origin counterexample, not just two severities of the same fault.

At 92 C/load zero, the model commands binary32 0.30; degradation yields a command/realization gap. Against timing faults with full_100 through 400 ms, the **entire finite sets** are conditionally disjoint: timing suppresses a recorded execution, actuator faults do not. All realization choices are independent. Pump feedback is a model realization, not an independently acquired physical measurement (A_PUMP). Adding real current/flow instrumentation would require a new source-backed contract.

## D. Replay with available timestamp/freshness

At constant temperature, values alone hide replay. With timestamp_100, age 100 and source time t−100 expose stale provenance. Freshness remains true for age 100 because its source threshold is 300 ms: timestamp evidence can matter before that flag changes. Communication origins are conditionally separable from latent memory under this view through 400 ms, provided timestamp integrity and the closed fault set hold.

Source visibility does not authenticate timestamps. External restamped traces and arbitrary timestamp corruption are outside this finite domain. Communication submechanisms are not individually certified: delay-100, first-one-drop and replay-age-100 during [100,200) all publish the same value and source time at t=100 and recover at 200. `case_examples.json` records their equal full histories. Injection metadata could name them, but is excluded from checker inputs.

## E. Shared upstream/downstream dependencies

Bias is applied before both source tap and delivered value in the actual `sensors_step`; their matching change is one producer dependency, not independent corroboration. Control then consumes delivered value and register; pump realization depends on command and active scale. The manifest retains time-indexed phases and v6 shared domains/typed edges.

Arbitrary coherent post-control corruption of register/shadow, source/delivered, clock, verifier or both command/response is **INSUFFICIENT_MODEL_EVIDENCE** in this selected source-backed domain. The implementation does not justify inventing an arbitrary adversary and calling its traces observed ECU behavior. Nor does omission justify positive physical certificates: unresolved A_PROCESS, A_POSTWRITE, A_TAP, A_MAILBOX and A_SHADOW block that transfer. Proposed protection or independent witnesses must be evaluated separately.

All 240 pair outcomes, including counterexample realizations, histories, source anchors and assumptions, are in `competing_fault_worlds.json`. Distinct pairwise separation is not the same as five-way singleton classification; the frontier computes the latter including healthy.
