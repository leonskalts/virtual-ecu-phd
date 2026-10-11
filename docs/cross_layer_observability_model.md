# Cross-layer runtime fault observability model

## Scope and implementation identity

This specification describes **diagnostic/runtime fault distinguishability**, not classical control-theory state observability. It does not construct an observability matrix of a dynamical system, reconstruct a hidden state, or assert an observability-rank theorem. The notation below describes information available at the implemented diagnostic boundary; it is not a new detector, scoring equation, or proof of optimality.

The reference is the final refined A2 evaluated in [integrity_final_unseen](../results/integrity_final_unseen/findings.md): retained Triplex/CLO-DSF, protected digital acquisition records, M2 memory probing, causal-precedence localization, and the G2 sensor confirmation rule selected in [benign_alarm_development](../results/benign_alarm_development/findings.md). The [registration](../results/integrity_final_unseen/registration.json), [protected-file hashes](../results/integrity_final_unseen/protected_hashes.json) and [freeze manifest](../results/integrity_final_unseen/freeze.json) identify the tested implementation. Recorded HEAD is `a340ca5cf0473d7dc572f7cd63e44fbc25b175a7`; HEAD alone is insufficient because the study includes uncommitted scientific files and generated native adapters.

The executable architecture is assembled by [run_integrity_final_unseen.py](../scripts/run_integrity_final_unseen.py), [run_benign_alarm.py](../scripts/run_benign_alarm.py) and [run_digital_integrity.py](../scripts/run_digital_integrity.py). Their build transformations matter: importing an older study's builder does **not** enable that study's rejected classifier. In particular, the final integrity builder removes dynamic-consensus inference and its discounting. A0 in the final study means retained Triplex without the added integrity/M2 architecture; historical A0/A1/A2 names are study-local.

## 1. Fault set and origin classes

Let \(F\) be the set of parameterized fault instances in the final campaign's implemented fault space. Its origin partition is

\[
F=F_M\mathbin{\dot\cup}F_T\mathbin{\dot\cup}F_C\mathbin{\dot\cup}F_S\mathbin{\dot\cup}F_A.
\]

| Origin | Implemented final-cohort models | Relevant instance parameters |
|---|---|---|
| Memory, \(F_M\) | `stuck_bit`, `bit_flip` in the calibration target register | Bit/polarity, activation, active intervals, duration |
| Timing, \(F_T\) | `deadline_miss`, `task_delay` | Release/execution disturbance, duration and temporal behavior |
| Communication, \(F_C\) | `delayed_update`, `dropped_update`, `replayed_sample` | Delivery delay/drop/replay behavior and active intervals |
| Sensor/Control, \(F_S\) | `sensor_bias` steps, `sensor_interface_intermittent` pulses, `sensor_bias_ramp` | Signed magnitude, rise time, duration, affected A/B/C/AB/ABC domains |
| Actuator, \(F_A\) | `pump_degraded`, `fan_stuck_off` | Pump scaling or fan loss of response, active intervals |

Transient/intermittent/permanent behavior is included where supported by the model and manifest. The origin is an evaluation label, never a detector input. Effective versus dormant memory and excited versus unexcited actuator faults are **context-dependent outcomes**, not additional origins. `UNKNOWN` is a localization output, not a sixth fault class.

Let \(f_0\) denote healthy operation, including authorized target/calibration changes, legal sensor offsets, independent noise and operating-profile variation. These benign behaviors are outside \(F\). The broad label SENSOR_CONTROL does not imply that arbitrary control-reference or physical sensor faults were tested: the final sensor campaign mutates post-conversion software values. Integrity replay/tag/witness boundary tests are additional mechanism tests, not extra final-cohort fault runs. See the [campaign manifest](../results/integrity_final_unseen/campaign_manifest.csv), [cross-layer injector](../src/cross_layer_fault.c) and Triplex adapter's `inject_value`/`diagnostic_acquire` in [run_clo_dsf_triplex.py](../scripts/run_clo_dsf_triplex.py).

## 2. Runtime observable set

An observable is a timestamped runtime field or a specified relation between runtime fields, including availability and provenance. It need not be a scalar. Define

\[
O=O_M\cup O_T\cup O_C\cup O_S\cup O_I\cup O_{AP}.
\]

These groups can share inputs; this union does not assert statistical independence or independent DS votes. Related sensor checks feed the existing sensor evidence channel through maxima, not additional independent fusion sources.

| Provider | Runtime observables and implemented relations | Availability/resolution boundary |
|---|---|---|
| Memory, \(O_M\) | Target register, trusted calibration shadow and validity, consumed control target; register/shadow and consumption/shadow consistency; probe validity, check time and read/write/restore failure | Integer register equality; checks must be valid and recent. Legal calibration changes update the trusted state. M2 performs active diagnostic transactions, not passive observation. |
| Timing, \(O_T\) | Scheduler-owned release/execution sequences, release/start/completion times, period/deadline, last successful execution, execution age, outstanding/missed/deadline status | Ledger availability and integer scheduler times; detector consumes event-derived age/late/missed flags, not injection flags. |
| Communication, \(O_C\) | Delivered measurement timestamp/age/freshness, expected period, acquisition source timestamp and control execution time | Freshness/regression and production-to-consumption ordering: a new acquisition consumed as an older delivered sample at the same control epoch is evidence. |
| Sensor/Triplex, \(O_S\) | A acquisition/current/previous values and timestamps; B independent reference value/status/time; C independent readout/history/status/time; consumed measurement; range/slew, bounded trajectory response, FAST/SLOW pair disagreements, C alignment and disagreement pattern | Finite/fresh/contiguous acquisition requirements, modeled quantization/noise, C phase and causal projection. Missing or failed qualification is not a healthy vote. |
| Digital integrity, \(O_I\) | Per-channel protected record and delivered envelope: channel, float value bits, sequence, timestamp, CRC tag; witness availability, mismatch status and 300-ms FAIL retention | Exact value-bit/record consistency with a valid independent witness. Status bits encode value/identity mismatch (1), sequence/time mismatch (2), invalid tag (4). PASS requires availability; an unavailable witness is not evidence of correctness. |
| Actuator/plant-related, \(O_{AP}\) | Pump/fan command and modeled actual response; measured coolant temperature; load, ambient, speed and target context used by sensor checks | Synchronous clamped-command response contract on actuator cadence, allowing adjacent representable floats. The “plant” evidence is measured-temperature warning/critical evidence, **not hidden true temperature or counterfactual plant divergence**. |

Sources: [runtime observation interface](../include/runtime_observation.h), [capture](../src/runtime_observation.c), [timing ledger](../include/runtime_timing_observation.h), [base evidence](../src/v7_1/candidate2_evidence.c), [retained core](../src/v7_3/clo_dsf_revised.c), [Triplex consistency](../src/v7_3/triplex_consistency.c), [integrity interface](../include/digital_sensor_integrity.h) and [integrity verification](../src/v7_3/digital_sensor_integrity.c).

The core's short trajectory forecast uses five acquisitions and at most a 300-ms prediction horizon. SLOW disagreement requires 320 contiguous 100-ms acquisitions. FAST uses short disagreement history, persistence and bounded same-sign integration. C has its own noise, gain/offset, quantization and acquisition phase; its causal projection is qualified, not an exact simultaneous truth reference. The final architecture uses `triplex_consistency_step`; alternative staggered/learned/parity providers present elsewhere in the repository are not assumed active.

M2 is specifically `dc_probe` retained by the integrity builder from [run_dynamic_consensus.py](../scripts/run_dynamic_consensus.py): 40 selected 100-ms scheduler positions per 10 seconds, containing the original phase-sweep positions. It reads the saved register, writes/reads zero and all ones, restores and checks the saved value. “250 ms” names its average budget, not a guaranteed uniform 250-ms grid. The separately implemented alternating 200/300-ms provider must not be substituted for this final M2 schedule.

The simulator supplies physical state to the sensor/actuator **plant models** to generate runtime outputs. That is distinct from exposing physical truth to diagnostic inference. No injected origin/model, activation label, bit index, counterfactual healthy trace, true coolant temperature, or propagation label belongs to \(O\). Those fields are used only by simulation or post-hoc evaluation. No raw ADC-code monitor, independent ADC-reference monitor or general pump idle-health channel is added by this specification.

## 3. Context-dependent observability relation

Let \(x\) describe a matched comparison context: initial conditions, external operating inputs, legitimate updates, noise realization, enabled architecture, acquisition/probe schedules, availability, failure-domain assumptions, and an observation window \(W\). Holding a noise realization fixed is an analytical comparison convention, not access to a hidden seed by the detector. Controller actions are generated by each execution and may diverge after the fault; they are not artificially held equal.

Write \(\tau_o(f,x;W)\) for the available runtime record trace of observable \(o\) under fault \(f\), and \(\tau_o(f_0,x;W)\) for the matched healthy trace. Record traces retain timestamps and availability; unavailable payloads are marked \(\bot\), not replaced by healthy values. Let \(\equiv_o\) mean equality at that observable's actual modeled representation/resolution, including its availability record. Then define the descriptive relation

\[
\Gamma(f,o,x)=
\begin{cases}
1,&\tau_o(f,x;W)\not\equiv_o\tau_o(f_0,x;W),\\
0,&\tau_o(f,x;W)\equiv_o\tau_o(f_0,x;W).
\end{cases}
\]

This is a **matched-context trace-effect relation**, not an implemented runtime test or a probability of detection. A fault-induced change in availability can be observable; two identically unavailable traces provide no value information. Relational observables, such as delivered-value/witness consistency, must be evaluated jointly rather than by comparing only a single marginal sensor value.

The requested observable set is

\[
O_f(x)=\{o\in O:\Gamma(f,o,x)=1\}.
\]

Resolution must not be chosen after results: register/sequence/tag/status comparisons are discrete; integrity compares float bits exactly; sensor outputs already contain the implemented conversion/quantization and timestamps. Existing noise allowances, alignment guards and persistence thresholds determine **provider evidence**, not an arbitrary new global epsilon equating raw traces. A raw difference can survive representation yet produce zero qualified evidence. No fitted noise distribution or new tolerance is introduced here.

## 4. Distinguishability over a window

Two executions are runtime-indistinguishable on \(O,W\) when their available observation traces are equivalent componentwise, including relational records:

\[
\tau_O(f,x;W)\equiv\tau_O(f_0,x;W)
\quad\Longleftrightarrow\quad
\forall o\in O,\ \tau_o(f,x;W)\equiv_o\tau_o(f_0,x;W).
\]

Under these definitions this is the same as \(O_f(x)=\varnothing\) for the matched pair. This is a definitional statement, not an empirically proved property of all misses. With identical initial diagnostic state and complete input history, a deterministic observer of identical traces cannot assign different outputs to those two executions. For a truncated window, relevant pre-window diagnostic state/history must also be included; otherwise identical window inputs need not imply identical alarms.

For **healthy-set distinguishability**, define the admissible healthy runtime trace set

\[
T_H(W)=\{\tau_O(f_0,x_h;W):x_h\text{ is an admissible healthy context}\}.
\]

Admissibility follows the existing architecture, trust assumptions and legal operating behavior, including offsets, noise, calibration changes and workload variation; it is not restricted to the finite healthy traces sampled in the campaigns. Membership is understood at the same modeled trace equivalence/resolution defined above. A faulty trace is diagnostically distinguishable from healthy behavior only if

\[
\tau_O(f,x;W)\notin T_H(W),
\]

meaning that no admissible healthy trace is equivalent to it. This defines information-level separation, not a guarantee that the implemented detector recognizes it. In contrast, **trace-effect observability** \(\Gamma(f,o,x)=1\) only establishes a change relative to the matched healthy execution. Such a change may still be compatible with another healthy context; therefore \(\Gamma=1\) does **not** guarantee reliable fault diagnosis.

Under the protected witness's trust assumption, a verified post-publication value mismatch is stronger evidence: it violates a deterministic value/record integrity relation rather than merely deviating statistically. Authorized transformations update that relation consistently. This argument does not cover unavailable witnesses, errors sealed before publication, or consistent corruption of both data and witness. It introduces no fitted distribution, new threshold or theorem.

Sensor member isolation is stronger again: A+B faulty versus C faulty can generate the same disagreement cut. Neither healthy-set separation nor nonempty \(O_f\) establishes a unique origin or an alarm at the frozen threshold.

The implementation has separate stages: runtime records → qualified provider evidence → DS/temporal decision → provenance-aware final confirmation and localization. Loss of information at sampling is different from suppression by evidence qualification or final confirmation. The G2 rule requires three consecutive qualified sensor samples ≥0.5 only for complete integrity PASS with no independent cross-layer support or retained direct-origin provenance. Integrity FAIL/UNKNOWN and other-layer support bypass it. It creates no new observable and changes neither DS mathematics nor origin evidence. See [sensor_confirmation.c](../src/v7_3/sensor_confirmation.c) and the adapter in [run_benign_alarm.py](../scripts/run_benign_alarm.py).

## 5. Implementation-grounded examples

### Unexcited pump degradation

In [actuators.c](../src/actuators.c), normal pump response is the clamped command and degraded response is that command multiplied by `pump_scale`. At zero command, both responses are zero. If the command remains zero throughout the fault-active intervals and no prior effect persists, this performance fault has no command/response or thermal effect through the modeled pump path. There is no independent pump idle-health observable. This is structural non-observability **under the idle context**, not a claim about every electrical motor fault. Later excitation can change \(O_f(x)\).

The fan model contains a synthetic stuck-off self-test status, but final A2's actuator evidence uses command/actual response, not those fan health fields. The status must not be generalized into passive coverage for pump degradation. The actual-response signal is a virtual-ECU interface contract, not a validated physical speed/current sensor model.

### Unsampled 50-ms sensor pulse

The Triplex adapter applies A/B mutations at its acquisition processing epochs and C mutations when C acquires, using C's sample timestamp. If a 50-ms active interval contains none of the relevant mutation/acquisition opportunities, no corrupted delivered sample is produced or retained. An intact digital witness cannot authenticate a sample that never captured the disturbance. Within that context there is no pulse-caused runtime discrepancy, even though the configured fault interval exists. Other 50-ms phases can intersect acquisition: duration alone does not establish invisibility.

### Dormant/intermittent memory outside probes

A stuck bit matching the currently stored/used bit leaves the register/shadow relation unchanged. Active zero/all-one probe writes can expose the stuck condition if a probe overlaps its active interval. If the stored value remains consistent and all active intervals fall outside probe transactions, neither shadow consistency nor the diagnostic transaction produces a fault indication. Intermittency and phase therefore matter. Dormant stored-value state is not synonymous with permanent undetectability; the active probe deliberately changes the diagnostic stimulus and restores the register.

### Post-conversion corruption, with and without protection

Without the integrity architecture (A0), a weak post-conversion offset can remain within range/slew/disagreement allowances; observing a small changed value does not by itself establish corruption. With A2, `di_publish` seals the legitimate producer result before downstream mutation; `di_verify` compares the consumed value and envelope to the protected record. A sampled value-bit mismatch against an intact witness creates direct digital-path evidence even when the numerical offset is small. The integrity builder represents authorized reference offsets and primary variation through `di_transform`, not by resealing arbitrary consumed data.

“Before protection” also has a distinct physical meaning: an erroneous value already present **before publication** can be sealed consistently. Protection then detects no integrity violation. Likewise, consistent corruption of both data and protected witness can pass. CRC-32 is not a MAC and is not the isolation mechanism; independently protected storage is an explicit architectural assumption, simulated in ordinary C memory. An invalid witness tag can be detected, but not every shared witness failure. Replay is checked relative to the producer's current sequence/time; freezing producer and consumer consistently is not an independent age timeout. These distinctions are documented and boundary-tested in [digital_integrity_development](../results/digital_integrity_development/findings.md).

### A+B common-mode corruption, with and without independent C

An equal additive error on A and B cancels in their pair difference, so A–B disagreement alone has no common-mode signature. Other plausibility or downstream checks may still react; cancellation is not a proof that the complete runtime trace is healthy-equivalent. With independent, available and adequately aligned C, A–C and B–C relations can acquire a signature, subject to magnitude, duration and provider qualification. The cut C|AB does not prove whether C or the A+B pair is faulty; SENSOR_CONTROL is the origin class, not a declaration of a particular bad member. Corruption shared by A, B and C can remove this relative reference. In A2, sampled AB/ABC **post-publication data-only** corruption can instead be visible to the intact integrity witnesses. This does not establish coverage of a shared physical/reference error before protection or common corruption of data plus witnesses.

## 6. Fault–Observable Matrix

Entries describe the specified provider's information path, not guaranteed final alarm coverage or unique origin identification. **YES**: a direct signature under the row's stated availability/trust conditions. **PARTIAL**: only some manifestations of the row's fault family are represented. **NO**: no direct signature in that provider under those conditions. **CONTEXT-DEPENDENT**: activation, sampling, excitation, qualification or downstream propagation is decisive. Secondary effects are summarized in the actuator/plant column; NO in another column does not prohibit an indirect later effect elsewhere. For integrity, “intact witness” and actual verification are required.

| Fault/condition | Memory | Timing | Communication | Sensor/Triplex | Digital integrity | Actuator/plant |
|---|---|---|---|---|---|---|
| Effective target-register corruption at a check | YES | NO | NO | NO | NO | CONTEXT-DEPENDENT |
| Dormant stuck bit, finite/intermittent activity | CONTEXT-DEPENDENT | NO | NO | NO | NO | CONTEXT-DEPENDENT |
| Missed/deferred control execution | NO | YES | CONTEXT-DEPENDENT | NO | NO | CONTEXT-DEPENDENT |
| Delayed/dropped/replayed delivery | NO | NO | YES | PARTIAL | PARTIAL | CONTEXT-DEPENDENT |
| Sampled post-publication A/B/C value corruption, intact witness | NO | NO | NO | PARTIAL | YES | CONTEXT-DEPENDENT |
| Pulse missing all affected acquisition/mutation opportunities | NO | NO | NO | NO | NO | NO |
| AB common-mode values, independent C available | NO | NO | NO | CONTEXT-DEPENDENT | CONTEXT-DEPENDENT | CONTEXT-DEPENDENT |
| ABC common-mode values | NO | NO | NO | PARTIAL | CONTEXT-DEPENDENT | CONTEXT-DEPENDENT |
| Error before protected publication | NO | NO | NO | CONTEXT-DEPENDENT | NO | CONTEXT-DEPENDENT |
| Record replay or value+recomputed tag, intact independent witness | NO | NO | CONTEXT-DEPENDENT | PARTIAL | YES | CONTEXT-DEPENDENT |
| Consistent data+witness common corruption | NO | NO | CONTEXT-DEPENDENT | CONTEXT-DEPENDENT | NO | CONTEXT-DEPENDENT |
| Pump degradation throughout zero-command active intervals | NO | NO | NO | NO | NO | NO |
| Excited pump degradation / fan stuck-off | NO | NO | NO | CONTEXT-DEPENDENT | NO | CONTEXT-DEPENDENT |

Communication YES presumes an observable violation of the implemented delivery contract; no claim is made for an abstract disturbance leaving that contract unchanged. Integrity PARTIAL for communication reflects its protection boundary: it is not a replacement for delivery freshness or consumption-order monitoring. The pre-protection, replay/tag and shared-witness rows state boundary semantics, not additional fault types sampled in the final 1,200 faults. AB/ABC integrity coverage depends on whether only post-publication values or also the witnesses are affected. Excited actuator coverage still requires a represented response difference on the observation cadence; the synchronous response contract is simulator-specific.

## 7. Limitation taxonomy and final 76 misses

| Category | Meaning | What a missed alarm alone does not establish |
|---|---|---|
| Structural observability limitation | No modeled information path distinguishes the fault in the given operating condition; e.g. multiplicative pump degradation at zero command | That the fault stays invisible after excitation or with a genuinely new sensor |
| Temporal/sampling limitation | A potentially informative event is not captured by acquisition or a diagnostic transaction in the window | That a different threshold can recover an absent event |
| Failure-domain/common-mode limitation | Data and its reference share the error, or the assumed independent witness fails consistently | That another copy in the same failure domain adds independent information |
| Detector/classifier limitation | Available traces contain a potentially usable discrepancy, but preprocessing, thresholds, persistence, confirmation or classification do not produce the desired decision | That every nonzero raw difference is uniquely faulty rather than admissible benign variation |

These categories can overlap; the following assigns a primary, implementation-supported cause to avoid double counting. It uses the already-recorded [miss table](../results/integrity_final_unseen/misses.csv), [subgroups](../results/integrity_final_unseen/subgroups.csv), and final runner's post-hoc `actuator_excited` and `active_probe_samples` accounting. No new experiments or healthy/faulty trace reconstruction were performed for this document.

| A2 missed subgroup | Count | Stored evidence / implemented mechanism | Primary category |
|---|---:|---|---|
| Unexcited `pump_degraded` | 63: 24 transient, 24 intermittent, 15 permanent | No positive command during active fault intervals; no plant manifestation; zero-command scaling has no effect | Structural, conditional on the idle operating context |
| `sensor_interface_intermittent` pulses | 8 transient, each 50 ms | No captured integrity violation; acquisition/mutation-window limitation; no plant manifestation | Temporal/sampling |
| Dormant `stuck_bit` | 5: 2 transient, 3 intermittent | No effective stored-value corruption; zero probe checks while active; four 100-ms and one 200-ms configured windows; no plant manifestation | Temporal/probe-window, with a dormant value prerequisite |
| Additional misses established as common-mode/failure-domain limitations | 0 | No such additional primary cause established for these 76 | Failure-domain/common-mode |
| Additional misses established as classifier-only limitations | 0 | No such additional primary cause established for these 76 | Detector/classifier |
| **Total** | **76** | **All have recorded plant_manifestation = 0** | **63 structural + 13 temporal** |

Zero assigned classifier-only/common-mode misses is not a general theorem excluding those limitations. Three common-mode AB/ABC cases are missed within the sensor cohort, but their primary reported mechanism is uncaptured pulses, already counted among the eight. Common-mode data-plus-witness and physical pre-protection failures were not evaluated by this unseen cohort. The raw per-run traces were deliberately discarded; stored sufficient statistics and code support the above attribution, but do not constitute a complete pointwise proof that every missed trace equals a healthy trace.

For context, A2 and frozen SVM-INT both detected 1,124/1,200 faults; A2 detected all 232 integrity-observed sensor cases and all 645 plant-propagating faults, with zero benign alarms in 600 runs. These results support the reported finite-cohort coverage, not completeness of \(F\), universal distinguishability, or physical field reliability. The G2 confirmation refinement removed benign false alarms without creating a new observability channel; it may still delay or miss brief legitimate-integrity-PASS physical anomalies outside the modeled fault space.

## 8. Interpretation limits for the paper

- Distinguish **raw runtime information**, **qualified evidence**, **alarm detection**, and **origin/member isolation**. In particular, a Triplex disagreement cut is not a uniquely identified faulty sensor.
- “Plant detection” in the results uses offline counterfactual propagation labels; runtime plant-related evidence does not receive that label or the healthy reference trajectory.
- “Independent sensor C” and “protected witness” are modeled failure-domain assumptions. They do not prove hardware independence, isolation, CRC security, or coverage of arbitrary shared failures.
- “Dormant” describes the operational stored value. Active probing can detect a dormant stuck condition; a missed finite window is not equivalent to permanent unobservability.
- “Unsampled” is relative to the modeled acquisition/mutation opportunities, not a claim about an unmodeled continuous-time analogue waveform.
- No theorem, new threshold, new physical coupling, or classical state-observability claim follows from the matrix. It is a scoped specification of the implemented diagnostic information boundary and the evidence available from the frozen studies.
