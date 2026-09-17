# Cross-Layer Safety v7: CLO-DSF

## Problem and scope

CLO-DSF detects runtime abnormalities, represents ignorance/conflict, and abstains
from origin localization when evidence is insufficient. The hypothesis is that
cross-layer coverage depends on where evidence is observable. Detection percentage
alone is not the objective. This is deterministic C11 development research, not a
final holdout, safety policy, physical model, machine-learning model or compliance
claim. Existing diagnostics, detectors, timing monitor, hazard/FTTI/containment
logic, RTL Trojan models and v1–v6 evidence remain unchanged.

Dempster–Shafer theory is established, not novel here. The proposed contributions
are the architectural observability map, conservative runtime evidence-order
modulation and their explicit sequential composition. They require empirical
validation; correlated sources are not made independent by naming them layers.

## Frame and representation

Six atoms use bits 0–5: NORMAL, MEMORY, TIMING, COMMUNICATION, SENSOR_CONTROL,
ACTUATOR. Thus Θ=63 and F=Θ\{NORMAL}=62. SENSOR_CONTROL maps the accepted
`FAULT_LAYER_SENSING_CONTROL`; other named origins map directly to their accepted
`FAULT_LAYER_*` categories. The generic `HARDWARE` umbrella is not an independently
identifiable origin. Plant is a consequence, never an origin. A subset denotes
uncertainty among alternative single origins, not simultaneous faults.

Each mass function has 64 double entries, m(∅)=0, nonnegative finite masses, and
Σ m(A)=1. Θ carries ignorance, including information lost through discounting.
The C core validates input masses and normalizes numerical roundoff. Empty
initialization is an unfinished mass function; vacuous initialization is m(Θ)=1.
`ds_assign` accepts a singleton or nonempty subset; callers normalize assembled
masses. Invalid inputs are rejected rather than silently clipping invalid masses.

## Runtime boundary and evidence

The algorithm receives only `runtime_observation_t`, never `ecu_state_t`. Its
transitive project-header allowlist is `clo_dsf.h`, `ds_evidence.h`,
`runtime_observation.h`, `runtime_timing_observation.h`, and `config.h`.
The integration adapter in `src/v7/clo_runtime.c` captures observations at the
accepted scheduler's detection call boundary, after actuator and built-in safety
updates and before experimental observe-only output. It uses GNU ld's `--wrap`
to intercept that existing call. The v7 binary links the original scheduler and
all frozen modules; `src/main.c` is compiled with a renamed entry point. The
original executable and accepted sources remain byte-identical. No completed CSV
is an input to a detector. No reference state enters the observer bank.

Let clip(z)=min(1,max(0,z)). Every available channel assigns m(Sᵢ)=eᵢ,
m(Θ)=1−eᵢ; unavailable channels are vacuous. Nonfinite numeric channel inputs are
unavailable. Runtime timestamps are required to be ordered. Duplicate/backward
steps are ignored. The scheduler cadence is fixed at 100 ms; temporal retention
and persistence are defined per such step.

| Channel | Runtime inputs and normal contract | Abnormal transformation e | Supported S | Class |
|---|---|---|---|---|
| Timing | Scheduler-owned period, relative deadline, release/completion, missed execution, execution age | max of deadline/missed/completion-late flag and clip((age−period−deadline)/period) | TIMING | DIRECT |
| Communication | Received sample timestamp, age, expected period, freshness status | 1 on freshness failure or backward received timestamp; otherwise clip((age−300)/300); future timestamp unavailable | COMMUNICATION | DIRECT |
| Memory/control | Active ECU control target, nominal 92 °C | clip(abs(target−92)/4) | MEMORY | DIRECT |
| Sensor/control | Measured coolant, prior measured coolant and timestamp | clip((abs(ΔT)−2.5 Δt_seconds)/2), or 1 outside −40…150 °C | {COMMUNICATION,SENSOR_CONTROL} | INDIRECT |
| Actuator | Fan/pump command and actual feedback | clip(max(abs(fan gap)/0.25,abs(pump gap)/0.20)) | ACTUATOR | DIRECT |
| Plant consequence | Measured coolant temperature | clip((T−108)/(115−108)) | All abnormal origins F | INDIRECT |

The timing age contract follows the frozen Timing Monitor semantics without
calling its alarm independent evidence. Freshness uses the frozen 300 ms runtime
contract. Memory's 4 °C scale and actuator 0.25/0.20 scales are existing detector
semantic scales; none is retuned. The sensor slew envelope (2.5 °C/s) is a new,
explicit broad physical plausibility assumption and its 2 °C scale is fixed before
development. It cannot observe a small constant sensor bias. Plant warning and
critical scales reuse frozen 108/115 °C contracts. Measured overheating can reflect
benign load or sensor error: its mass supports a broad abnormal subset and may
produce false alarms. This detector does not claim hazard prediction.

A single joint absence source assigns m({NORMAL})=0.5(1−maxᵢ eᵢ), remainder to Θ,
only when ALL channels are available. This avoids treating six absence signals as
independent normal votes. Lack of a timing violation alone cannot exclude memory
corruption. The absence source remains dependent on the anomaly channels; the
combination is an explainable engineering evidence model, not calibrated inference.

Raw diagnostic IDs, previous detector alarms and safety states are explicitly
ignored even though present in the snapshot: legacy diagnostic provenance includes
true coolant and fault permanence. True-coolant sensor residual, existing Kalman
innovation/thermal observer internals, generated/dropped packet flags, delivery
history, injector replay age/bit index, and reference-based propagation are NOT
inputs. Kalman/thermal observer residuals are not separately exposed through the
allowlisted observation API. Their legacy alarm outputs are not substituted as
independent measurements. Measured slew and temperature are the available runtime
alternatives. Engine load/ambient/speed are available but not needed by this mapping.

## Architectural observability and discounting

`src/v7/clo_observability.c` contains the six-by-six source/hypothesis map. DIRECT
means a matching local contract/feedback, not certain causality. INDIRECT means a
compatible downstream or ambiguous measurement. NOT_APPLICABLE marks hypotheses
that are not supported by that source; UNAVAILABLE denotes absent evidence and
has zero reliability. Missing input channels also receive zero reliability.
The v3 conceptual analysis is reused, with the v4/v5 scheduler ledger now available;
v3 measured detection outcomes are never copied into the runtime map.

Only two informative reliability classes exist: r_direct and r_indirect. For a
supported subset, r=min of its member classes. Unsupported entries never acquire
mass. Reliability discounting is exactly:

mʳ(A)=r m(A), ∅≠A≠Θ; mʳ(Θ)=1−r+r m(Θ).

This transfers uncertainty to ignorance and preserves unit total. Initial values
are 0.9/0.6; candidate values and all constants are recorded in the contract.

## Combination and conflict

For two masses, q(A)=Σ_{B∩C=A}m₁(B)m₂(C), K=q(∅).
Dempster: m(A)=q(A)/(1−K), for nonempty A.
Yager: m(A)=q(A) for ∅≠A≠Θ, m(Θ)=q(Θ)+K.
Both close the empty set to zero. Dempster total conflict (1−K≤10⁻¹²) returns a
flagged vacuous fallback, retaining K; it never emits NaN or silently normalizes
an undefined result. Invalid mass/configuration is rejected by APIs/config parser.

Yager is not associative. The deterministic, documented fold order is TIMING,
COMMUNICATION, MEMORY_CONTROL, SENSOR_CONTROL, ACTUATOR, PLANT, joint NORMAL,
then discounted previous state (full variant only). This ordering is part of the
candidate, not a claim of permutation invariance. Per-step K₀…K₇ and any fallback
are logged. `conflict_mass` is max K across this timestep, not a combined posterior
conflict probability. High conflict is K≥0.5 for any step.

References for the established framework and conflict handling:
[Glenn Shafer, Constructive Probability](https://glennshafer.com/assets/downloads/articles/article05_constructive.pdf)
and [Ronald R. Yager (1987), On the Dempster-Shafer framework and new combination rules](https://www.sciencedirect.com/science/article/pii/0020025587900077).
Equations and implementation description here are independently written.

## Runtime propagation consistency

Channel evidence is active at e≥0.5. Store each CURRENT episode's first activation
time; reset on recovery. The allowed evidence graph is:

- timing, communication, memory/control → sensor/control, actuator, plant;
- sensor/control → actuator, plant;
- actuator → plant.

An edge i→j supports consistency only when both episodes are still active,
0≤tᵢ<tⱼ≤t_now and t_now−tᵢ≤propagation_window_ms. Same-tick, reversed, incomplete
and future sequences cannot add support. Edges can skip intermediate channels;
normal actuator command tracking does not veto a path to plant. At least one
supported outgoing edge multiplies upstream r by (1+propagation_bonus), capped
at 1. Multiple edges do not stack bonuses. No new singleton mass is fabricated
from a plant observation. Co-occurrence is consistency, not proof of causation.
`propagation_transitions` bit (6i+j) identifies the exact applied source→destination
edge; channels are indexed in the fold order above. `propagation_support` records
whether modulation was enabled and supported; raw transition bits can also be
present in ablated states without applying modulation.

## Temporal fusion and readout

Prior evidence is discounted once: m_prior=D_λ(m_previous). Combine current
sources with that prior using the selected rule. λ<1 bounds persistence; stale
support tends to zero in recovery. Temporal samples are dependent; discounts limit
but do not eliminate overconfidence. The retention is per 100 ms step, not a
continuous-time rate and not a claim of statistically independent observations.

Bel(A)=Σ_{B⊆A}m(B); Pl(A)=Σ_{B∩A≠∅}m(B).
BetP(h)=Σ_{A∋h}m(A)/|A| (pignistic decision score, NOT Bayesian probability).
Anomaly score is Bel(F); ignorance is m(Θ).

Below alarm_threshold_suspect: NORMAL. At or above that threshold: SUSPECT.
At or above alarm_threshold_confirmed for confirmation_persistence consecutive
steps: CONFIRMED. Falling below confirmation breaks its streak immediately;
alarm state can recover. First alarm timestamp remains as historical evidence.

Among the five abnormal singleton BetP scores choose the largest (fixed index
breaks ties for readout only), and compute its margin over the runner-up. Only a
confirmed alarm with score≥localization_threshold, margin≥localization_margin_threshold,
and ignorance≤ignorance_limit returns the origin; otherwise UNKNOWN. Bel/Pl for
the leading singleton and its score/margin are still recorded. First valid
localization timestamp is historical, not necessarily the first alarm timestamp.
The readout never feeds alarm logic.

## Pseudocode

```
step(runtime_snapshot, previous_state, global_config):
    reject duplicate/backward timestamp
    for channel in fixed order:
        evidence[channel] = bounded_runtime_transform(snapshot, history)
        mass[channel] = simple_support(evidence, supported_subset) or vacuous
    update current evidence-episode onset times
    support = allowed forward edges with active endpoints within global window
    current = vacuous
    for channel in fixed order:
        reliability = architectural class (or zero if unavailable)
        if supported outgoing edge: reliability = min(1, reliability*(1+bonus))
        current, K[channel] = combine(current, discount(mass[channel], reliability))
    current, K[6] = combine(current, joint_absence_mass)
    fused, K[7] = combine(current, discount(previous_fused, lambda))
    score = belief(fused, abnormal_subset)
    update confirmation streak and NORMAL / SUSPECT / CONFIRMED
    scores = pignistic(fused)
    origin = UNKNOWN unless confirmed and confidence/margin/ignorance gates pass
    emit state, score, origin, scores, belief/plausibility, ignorance, all K,
         support edge mask, alarm/localization timestamps
```

## Baselines, integration and logging

F1 OR alarms at any raw e≥0.5, one sample. F2 weighted sum uses equal fixed weights
1/6 and threshold 0.5, one sample. These deliberately simple global baselines have
no localization. F3/A0 uses standard Dempster, reliability 1, no propagation or
temporal extension, and the same global DS decision/localization thresholds.
A1 adds reliability (and selected conflict rule); A2 adds propagation; A3 is full.
Both conflict rules are compared in the preregistered TRAIN search at otherwise
matched parameters. All six accepted detector comparators and specialized Timing
Monitor run unchanged; old residual truth dependencies are reported honestly.

`make` builds both `virtual_ecu` and `virtual_ecu_v7`. Example:

```
./virtual_ecu_v7 /tmp/clo.csv baseline --detector clo_dsf --detector-action observe_only
python3 scripts/run_clo_dsf_development.py
```

The first command writes `/tmp/clo.csv.clo_dsf.csv`. To run a chosen development
configuration pass `--clo-config path/to/selected_config.cfg`. Other adapter options
are `--clo-evidence`, `--clo-metrics`, `--clo-comparison train|validation`, and
`--clo-evaluation-start` (used only by score accumulation, never passed to CLO-DSF).
Validation mode excludes candidate search. Strict complete key=value config parsing
rejects missing/duplicate/unknown fields and invalid ranges.

Primary experimental mode supports observe-only. The legacy main CSV's algorithm
enum remains `builtin_ecu` because the frozen schema has no v7 enum; its runtime
label is `clo_dsf_experimental`. The **named v7 sidecar is authoritative**. Legacy
CSV alone must not be interpreted as an accepted detector study for this mode.
Default v7 study mode uses builtin ECU observe-only trajectories and a shadow
observer bank; original CSVs therefore retain the accepted detector semantics.
GUI runtime view reads the sidecar, never inferred truth labels. Primary mode does
not alter safety requests/policies. Experimental fault detection must not be used
to claim validated safety containment.

The adapter's experiment-only metrics writer holds first/post-injection alarm,
pre-injection counts, localization-at-first-alarm and later localization, full-run
ignorance/conflict and support statistics. Only this evaluator sees the scoring
start; the detector never does. The Python evaluator reads origin/reference
propagation from experiment CSVs to score results. No such fields appear in runtime
evidence sidecars, which include every step's masses/readouts and evidence values.

## Complexity and overhead

The fixed 64-entry core has O(4⁶)=4096 pair intersections per generic combination
worst case, skipping zero entries; seven current combinations and one temporal
combination per step. Bel/Pl/readout cost O(6·2⁶). State is O(2⁶+channels). Local
combination buffers consume additional stack; sizeof measurements exclude stack,
FILE buffers, simulator state and the development comparison bank. The benchmark
reports detector state, mass/evidence state, binary text/data/bss delta, and
**host-evaluated simulation overhead**, with I/O/no-I/O qualifications. No embedded
WCET is measured or claimed. GNU ld wrapping is Linux/gcc integration, not an
embedded-portability guarantee for the adapter; the evidence core is plain C11.

## Limitations and validation boundary

Static normal target, reliable received timestamps, trustworthy scheduler ledger,
and representative actuator feedback are architectural assumptions. A compromised
observation channel can conceal its own fault. Sensor/control origin is often
inseparable from communication with available measured evidence; UNKNOWN is
expected. Noisy real measurements, multiple simultaneous faults, real clock drift,
dynamic calibration targets, independent hardware and non-100-ms execution require
new validation. Plant excursions may be benign. The fixed propagation graph can
miss recovered-upstream episodes and cannot establish causality.

Tests include hand-computable core examples, finite/unit mass checks, observability,
propagation order, temporal behavior, localization gates, transitive include
isolation and hidden metadata invariance. The full study uses grouped TRAIN and
DEVELOPMENT-VALIDATION; selection is TRAIN-only. Candidate freezing is conditional
on the preregistered continuation gate and complete scientific regression. No
configuration or scenario for a future independent holdout is created here.
