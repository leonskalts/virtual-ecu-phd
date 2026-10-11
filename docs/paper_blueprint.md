# Observability-Driven Cross-Layer Runtime Fault Diagnosis for Virtual Automotive ECUs

Paper blueprint only. All proposed displays must use existing artifacts; no new experiments, detector changes, statistical fitting or retrospective parameter selection are implied. Counts below are transcribed from frozen evidence; percentages are rounded presentation of those counts.

## 1. Central thesis

Within a defined virtual-ECU fault model, explicitly identifying runtime observability gaps and adding trusted acquisition and diagnostic evidence improves cross-layer fault diagnosis over the retained Triplex baseline, while an equal-observability comparison exposes parity with a frozen SVM and identifies the remaining context-dependent and sampling-limited failures.

## 2. Research questions

- **RQ1 — Origin, distinguishability and propagation:** Which modeled faults produce diagnostically distinguishable runtime traces, which origins can be localized, and how do observed faults and misses relate to independently evaluated plant propagation?
- **RQ2 — Observability-gap-driven improvement:** Which gaps are addressed by independent sensing, protected digital acquisition records and active memory probes, and can provenance-aware confirmation reduce benign alarms without losing the demonstrated diagnostic coverage?
- **RQ3 — Equal-observability comparison:** With the same runtime integrity/cross-layer observables and frozen operating points, how do refined A2 and SVM-INT compare in detection, benign alarms, propagation-conditioned coverage and latency, and what localization does A2 additionally report?
- **RQ4 — Frozen robustness:** How do coverage, benign behavior and localization vary across preregistered ambient/load, legal noise/update and fixed acquisition-phase conditions when neither method is retuned?
- **RQ5 — RTL feasibility:** Can the modeled producer-owned integrity boundary be implemented as a synthesizable monitor matching the software record semantics, and what are its measured logical storage, mapped area and pre-layout timing costs?

## 3. Defensible contributions

1. **An implementation-grounded diagnostic observability specification.** Define the five fault origins, available runtime providers, context-dependent trace effects, healthy-set distinguishability and a Fault–Observable Matrix. Explicitly distinguish information absence from provider/classifier limitations. This is a scoped diagnostic model, not a state-observability theorem.
2. **An observability-led integration of runtime evidence and provenance.** Combine retained Triplex evidence, producer-owned digital integrity, phase-sweeping memory diagnostics and conditional sensor confirmation while preserving the existing DS mathematics. The contribution is the justified integration and demonstrated behavior, not invention of DS, redundancy or CRC.
3. **A frozen, equal-observability empirical comparison.** Report same-case A0/A2/SVM-INT outcomes, per-origin and plant-conditioned results, localization with abstention, and exact paired counts. A2 improves over A0 but matches SVM-INT on the final cohort; the binary comparator does not provide localization.
4. **A preregistered operating-condition robustness analysis with explicit limits.** Show how raw recall changes with actuator excitation while plant coverage and confident localization remain intact in the measured cohorts; preserve sampling and failure-domain limitations instead of hiding hard cases.
5. **A software-referenced RTL feasibility demonstration of the protection boundary.** Provide self-checking simulation and standard-cell mapping of one witness bank, with explicit integration/trust and timing assumptions. This is neither a new integrity primitive nor a physical-security or silicon-validation result.

Position these as the paper's contributions pending a verified literature review. Do not claim priority, “first-ever,” general novelty of individual mechanisms, or superiority to all diagnostic/ML systems.

## 4. Evidence ledger and naming discipline

| Evidence class | Authoritative artifacts | Permitted use | Separation rule |
|---|---|---|---|
| Retained Triplex development/history | [symmetry findings](../results/clo_dsf_current/symmetry_findings.md), [symmetry retention](../results/clo_dsf_current/symmetry_retention.json), [earlier Triplex-only findings](../results/clo_dsf_current/triplex_only_findings.md) | Explain independent-C rationale, member ambiguity and retained architecture lineage | Earlier failed retention and later cohort success must both remain visible; the later percentage change did not establish a code improvement |
| Historical comparative benchmark | [findings](../results/comparative_benchmark/findings.md), [manuscript table](../results/comparative_benchmark/manuscript_table.md) | Motivate observability-matched comparisons and distinguish architecture from backend effects | Its SVM and cohort are not final SVM-INT; treat as historical/development context for the current paper |
| Digital-integrity development | [findings](../results/digital_integrity_development/findings.md), [protocol](../results/digital_integrity_development/protocol.md), [SVM selection](../results/digital_integrity_development/svm_selection.json) | A0/A1/A2 mechanism ablation; historical weak-fault audit; comparator training/calibration provenance | Development validation and the seen-90 audit are not final unseen evidence |
| Benign-alarm development | [findings](../results/benign_alarm_development/findings.md), [selection](../results/benign_alarm_development/selection.json), [protocol](../results/benign_alarm_development/protocol.md) | Explain G2 selection on new TRAIN/CAL and its subsequent locked development validation | Do not present retrospective reconstruction of the 55 alarms as new validation |
| **Primary final unseen** | [registration](../results/integrity_final_unseen/registration.json), [freeze](../results/integrity_final_unseen/freeze.json), [summary](../results/integrity_final_unseen/summary.csv), [paired](../results/integrity_final_unseen/paired.csv), [localization](../results/integrity_final_unseen/localization.csv), [misses](../results/integrity_final_unseen/misses.csv) | Main frozen A0/A2/SVM-INT claim | Exactly 1,200 faults + 600 benign; do not combine with development counts or relabel older unseen campaigns as independent confirmation of the final architecture |
| **Frozen robustness** | [protocol](../results/frozen_robustness/protocol.md), [summary](../results/frozen_robustness/summary.csv), [per-origin](../results/frozen_robustness/per_origin.csv), [findings](../results/frozen_robustness/findings.md) | Six-condition robustness of the unchanged final methods | Separate 1,800 faults + 600 benign; matched fault templates across profiles are correlated, not 1,800 independent fault mechanisms |
| **RTL feasibility** | [RTL README](../rtl/integrity/README.md), [record](../results/rtl_integrity_poc/record.json), [simulation](../results/rtl_integrity_poc/simulation.log), [statistics](../results/rtl_integrity_poc/statistics.json), [timing](../results/rtl_integrity_poc/timing.log) | Logical implementation and pre-layout cost of the witness primitive | No hardware-in-the-loop campaign, routed silicon result, or hardware-validated A2 performance |

Use manuscript names consistently: **Triplex baseline (final-study A0)**; **Triplex + integrity (digital-development A1)**; **unrefined integrity + M2 (digital-development A2)**; **final refined A2**; **frozen SVM-INT default**; **frozen SVM-INT CAL1** as secondary. A historical “A2 rejected” label may describe a different temporal-consensus candidate. Never equate these labels across study directories.

Final study HEAD is `a340ca5cf0473d7dc572f7cd63e44fbc25b175a7`, but uncommitted scientific files and generated adapters are part of the evaluated implementation. Cite the recorded source/config/model and executable hashes, not HEAD alone. Final unseen registration records zero overlap across 985 historical sources; robustness records zero overlap across 987. These are configuration/profile audits, not evidence of new physical fault families or independent external replication.

## 5. Full manuscript outline and section-level claim map

F1/F2 and T1–T5 refer to the minimum display set in Section 8 below. “No additional display” means use the cited shared display, not invent another experiment.

| Proposed section/subsection | Exact claim to make | Existing supporting artifact/result | Figure/table | Required limitation |
|---|---|---|---|---|
| **Abstract** | Final A2 detects 1,124/1,200 faults with 0/600 benign alarms and 645/645 plant-propagating detections; it matches SVM-INT and adds reported origin diagnosis; RTL demonstrates logical feasibility | Final `summary.csv`, `localization.csv`; RTL `statistics.json` | Summarize T3/T5; no extra display | Say “in a virtual-ECU cohort”; no automotive field-reliability claim |
| **1. Introduction — 1.1 Problem and motivation** | Detection algorithms are constrained by the runtime information and operating context presented to them | [Observability specification](cross_layer_observability_model.md); final `misses.csv` | F1, F2 | Do not infer absence of information from a missed alarm alone |
| **1.2 Questions and contributions** | The paper tests observability-led integration, equal-information comparison, frozen robustness and logical hardware feasibility | Evidence ledger above and preregistrations | No additional display | Integration/evaluation contribution, not primitive invention |
| **2. Related work — 2.1 Runtime diagnostics and fault isolation** | Scope the paper against diagnostic distinguishability and cross-layer evidence; state observability is a different concept | Local model defines the paper's scope; external supporting references still require verification | T1 as scope aid | This blueprint supplies no invented references and establishes no literature-priority claim |
| **2.2 Evidence fusion, redundancy and learned comparators; 2.3 data integrity** | Reuse known categories of DS fusion, redundant sensing, SVM classification and integrity checking; explain the distinction between new evidence and a changed decision rule | Core/provider sources linked by the observability model; comparative findings; digital-integrity findings | F1 | Do not call DS/Triplex/CRC novel; technical positioning needs a verified bibliography before submission |
| **3. Virtual ECU and fault model — 3.1 Runtime pipeline** | Sensors, acquisition/delivery, control, actuators and diagnostics expose specific runtime fields and ownership boundaries | [Runtime interface](../include/runtime_observation.h), [capture](../src/runtime_observation.c), final runner and model | F1 | Plant truth generates simulation physics but is excluded from detector inputs |
| **3.2 Five fault origins and benign conditions** | Faults cover memory, timing, communication, sensor/control and actuator behavior, including dormant/short/unexcited cases | Final `campaign_manifest.csv`; robustness manifest/protocol | T1, T3 | Final sensor faults are post-conversion value corruptions; legal changes are not injected faults |
| **4. Diagnostic observability — 4.1 Trace effects** | Define Γ(f,o,x) and O_f(x) relative to a matched healthy execution, including availability and resolution | [Observability model, Sections 2–3](cross_layer_observability_model.md) | T1 | Γ=1 is not a fault-specific signature or proof of reliable diagnosis |
| **4.2 Healthy-set distinguishability** | Define T_H(W); a trace is separable from healthy behavior only if no admissible healthy trace is equivalent to it | Model Section 4, including the healthy-set refinement | F1/T1 | T_H is not merely the sampled benign cohort; no exhaustive membership algorithm or theorem is supplied |
| **4.3 Limit categories and failure domains** | Separate structural, temporal, shared-failure-domain and classifier limitations; explain idle pump, missed pulse, dormant probe and AB/ABC examples | Model Sections 5–8; final `misses.csv` | F2 | Stored summaries/code support attribution but do not prove pointwise healthy/faulty equivalence for every discarded trace |
| **5. Observability-led architecture — 5.1 Retained Triplex and causal origins** | Independent C adds relative evidence; causal precedence limits downstream origin contamination while allowing UNKNOWN | Retained symmetry findings; [Triplex provider](../src/v7_3/triplex_consistency.c); [core](../src/v7_3/clo_dsf_revised.c) | F1, development panel in T2 | A C\|AB cut does not identify whether C or AB is faulty; this is diagnosis, not TMR majority-based control recovery |
| **5.2 Protected producer record** | Channel/value bits/sequence/time/tag are sealed at the trusted producer; a sampled post-publication mismatch violates a deterministic integrity relation | Digital-development findings; [C verifier](../src/v7_3/digital_sensor_integrity.c); frozen integrity builder | F1, T2 | The witness's isolated storage is assumed; pre-publication and consistent data+witness corruption can pass |
| **5.3 Active memory diagnostics** | M2 can expose dormant stuck conditions through finite, phase-sweeping read/write/restore probes | `dc_probe` in [builder](../scripts/run_dynamic_consensus.py), retained through [integrity builder](../scripts/run_digital_integrity.py); final memory subgroups | T2/T3 | Active diagnostic stimulus, not a passive detector; nominal 250-ms average does not imply a uniform grid or coverage of every short window |
| **5.4 Provenance-aware benign confirmation** | G2 confirms three consecutive qualified sensor samples only with complete integrity PASS and no independent other-layer/direct-origin support | [Selection](../results/benign_alarm_development/selection.json), findings and [confirmation module](../src/v7_3/sensor_confirmation.c) | T2 | FAIL/UNKNOWN and independent support bypass it; brief pre-protection physical anomalies remain outside demonstrated sensitivity preservation |
| **6. Evaluation design — 6.1 Partitions, freeze and metrics** | Separate development selection, untouched final configurations and later frozen robustness; preserve original edge-based detection and conditional denominators | All four study protocols, registrations, overlap audits and validation records | T2/T3 captions and supplementary ledger | Extensive historical development exists; “unseen” means audited new configurations, not an untouched problem domain |
| **6.2 Fair comparator and statistical accounting** | Frozen SVM-INT receives the same runtime integrity/cross-layer observables; default is primary and old CAL1 is secondary; use paired counts/Wilson intervals | Digital `svm_selection.json`, final registration, runner and `paired.csv` | T3 | SVM has no localization head; no SVM-localization superiority test; grouped simulator statistics are descriptive |
| **7. Results — 7.1 Development ablations** | Within-cohort integrity and M2 ablations improve detection; subsequent confirmation removes observed benign alarms without loss on its own validation | Digital and benign-development findings | T2 | Keep denominators separate; do not subtract across cohorts as an ablation |
| **7.2 Final unseen detection and propagation** | Final A2 gains 105 detections over A0 without losing any; plant-conditioned detection rises from 588/645 to 645/645 | Final `summary.csv`, `subgroups.csv`, `paired.csv` | T3 | Overall improvement combines architecture and confirmation; final cohort alone does not separately identify each component's effect |
| **7.3 Localization, equal-observability SVM and remaining misses** | A2 matches SVM-INT's detections/latencies, localizes all detected runs correctly, and retains 76 misses with explicit causes | Final `localization.csv`, `confusion.csv`, `misses.csv`, paired data | T3, F2 | Runtime accuracy excludes UNKNOWN; no member-isolation or classifier-optimality theorem |
| **8. Frozen robustness — 8.1 Six profiles; 8.2 spread and causes** | Both methods range from 85% to 96% recall; recorded plant coverage remains 100%, benign alarms zero; changed detections versus P0 are actuator cases | Robustness protocol, findings, per-origin/localization/miss tables | T4, F2 | Fixed Sensor C phase variation is not scheduler jitter; changed excitation is an operating-context effect, not an altered fault definition |
| **9. RTL feasibility — 9.1 Boundary and tests; 9.2 cost** | One producer-owned bank implements the logical record/verification semantics and passes software-oracle tests; mapped costs are measured | RTL README/module, C testbench, simulation/statistics/timing records | F1 inset, T5 | No silicon/HIL, routing, physical containment, access-control implementation or exhaustive equivalence proof |
| **10. Discussion — 10.1 What improved; 10.2 limitations and threats** | New information paths explain measured gains; decision logic cannot rescue an uncaptured event; SVM parity prevents a fusion-superiority interpretation | T2–T4 and observability model | F2; no additional display | Finite benign samples, shared simulator families, context-dependent exposure, failure-domain assumptions, metric attribution and conditional latency |
| **11. Conclusion** | Restate scoped architecture/diagnosis result, equal-observability parity, and unresolved idle/sampling limits | Final and robustness findings plus RTL cost | No additional display | No deployment-readiness or universal safety conclusion |
| **Appendix / reproducibility package — A. metrics; B. provenance; C. historical comparisons; D. RTL constraints** | Existing hashes, sufficient statistics and protocols trace reported claims to the tested artifacts | Freeze/protected hashes; case statistics; comparative table; regression records; RTL timing constraints | Expanded T1/T3 and historical tables only if needed | HEAD is not a complete freeze; raw traces were not retained; do not invent waveforms/ROC curves from summary counts |

## 6. Locked headline numbers

### 6.1 Primary final unseen evidence

Source of truth: [final summary](../results/integrity_final_unseen/summary.csv), [subgroups](../results/integrity_final_unseen/subgroups.csv), [paired comparison](../results/integrity_final_unseen/paired.csv) and [localization](../results/integrity_final_unseen/localization.csv). Cohort: **1,200 faults, 240 per origin, plus 600 benign**.

| Metric | A0 retained Triplex | Final refined A2 | Frozen SVM-INT default |
|---|---:|---:|---:|
| Detection | 1,019/1,200 = 84.9167% | **1,124/1,200 = 93.6667%** | 1,124/1,200 = 93.6667% |
| Wilson 95% detection CI | 82.7805–86.8300% | **92.1444–94.9102%** | 92.1444–94.9102% |
| Benign alarm runs | 5/600 | **0/600** | 0/600 |
| Run-level precision | 1,019/1,024 = 99.5117% | 100% | 100% |
| Plant-propagating detection | 588/645 | **645/645** | 645/645 |
| Silent plant misses | 57 | **0** | 0 |
| Median/P95 latency, detected faults | 0/1,000 ms | **0/167 ms** | 0/167 ms |
| Integrity-observable subgroup | 144/232 | **232/232** | 232/232 |

Frozen CAL1 yields the same final counts and latencies; label it a prespecified secondary point, not a threshold selected from final outcomes. Zero median is at the simulator's observation/scoring resolution, not zero physical computation delay. Precision uses the registered cohort's fault/benign balance, not fleet prevalence.

| Origin, denominator 240 | A0 | Final A2 | SVM-INT |
|---|---:|---:|---:|
| Memory | 218 | 235 | 235 |
| Timing | 240 | 240 | 240 |
| Communication | 240 | 240 | 240 |
| Sensor/control | 144 | 232 | 232 |
| Actuator | 177 | 177 | 177 |

A2 subgroups: effective memory **162/162**; dormant memory **73/78** through active diagnostic coverage; weak steps **90/90**; pulses **52/60**; AB/ABC common-mode digital-value corruption **93/96**; unexcited actuator **0/63**. Do not describe common-mode digital-value coverage as coverage of common physical sensor/reference or shared witness faults.

Paired fault counts, in order **both / A2-only / comparator-only / neither**:

- A2 versus A0: **1,019 / 105 / 0 / 76**; exact two-sided McNemar **p = 4.930380657631324×10⁻³²**. Absolute recall gain **8.75 percentage points**. The per-origin gains are 17 memory and 88 sensor/control cases.
- A2 versus SVM-INT: **1,124 / 0 / 0 / 76**; no discordance, reported **p = 1**. This supports observed parity, not statistical equivalence on a population or A2 superiority.
- Benign alarms: A0-only **5**, A2-only **0**, exact **p = 0.0625**. Do not claim a statistically established final-cohort benign-alarm advantage at a 0.05 threshold. Both SVM operating points and A2 have zero benign alarms.
- Among the **1,019 jointly detected A0/A2 cases**, A2 is earlier in **189**, equal in **830**, later in **0**. This is a paired latency statement; marginal P95s use different detected sets.

A2 first-localization coverage/accuracy: **1,124/1,124** detected faults localized correctly. Runtime localized accuracy: **435,691/435,691 = 100%**. UNKNOWN: **1,851/437,542 = 0.423045%** of fault alarm samples; first-detection UNKNOWN **0**. Wrong confident fault-origin runs/samples **0/0**. SVM-INT supplies binary decisions, not localization. Preserve these denominators rather than saying “100% localization of all injected faults.”

Remaining **76 A2/SVM misses**: **63 unexcited pump degradations** (24 transient, 24 intermittent, 15 permanent), **8 uncaptured 50-ms pulses**, **5 dormant stuck-bit cases outside active probe checks** (2 transient, 3 intermittent). All have recorded plant manifestation **0**. This supports a scoped **63 structural/context-dependent + 13 temporal** attribution, not proof that an arbitrary better sensor or classifier could never help.

### 6.2 Development evidence, not headline unseen evidence

| Development comparison | Same-cohort result | Interpretation |
|---|---|---|
| Retained Triplex symmetry validation | 417/480 → 437/480; all 20 gains AB common-mode; plant 214/231 → 231/231; both 0/120 benign | Independent-C information gain in this earlier cohort; unchanged implementation, not a symmetry “fix” |
| Digital-integrity validation | A0 1,014/1,200; A1 1,103/1,200; A2 1,125/1,200; all 55/1,200 benign | Integrity contributes 89 additional run detections; M2 contributes 22 further detections in this ablation |
| Same digital validation, plant | 583/639 → 639/639 → 639/639 | Plant coverage gained at the integrity stage in this cohort |
| Seen weak-fault audit | 82/90 recovered; remaining 8 unsampled | Retrospective diagnostic support; not an untouched validation result |
| Benign refinement validation | Original/refined A2 both 1,124/1,200; benign 49/2,400 → 0/2,400; plant both 641/641; integrity both 232/232 | G2 removes observed benign alarms without casewise detection loss on its locked development validation |

The historical 55-alarm audit found 53 legal-offset and two authorized-update cases, all integrity PASS, with short FAST/Triplex bursts and no independent other-layer support. It explains the confirmation hypothesis; only new TRAIN/CAL selected G2. Do not merge “55 historical” with “49 new validation” as though they were the same cohort.

Historical comparative evidence is useful but not a final SVM-INT headline: its C2 Triplex detected **1,089/1,200**, whereas its earlier C2 SVM detected **1,118/1,200** with **49/300** benign alarms versus Triplex **0/300**. The final SVM-INT has new integrity observables and **0/600** benign alarms. Using the historical SVM's false alarms to claim a final-method advantage would be misleading. The older benchmark also documents one very late credited SVM memory alarm; preserve the registered post-onset scoring caveat rather than presenting that credit as direct memory observability.

### 6.3 Frozen robustness evidence

Each profile contains **300 faults + 100 benign**, with 60 faults per origin. A2 and default SVM-INT match every case-level detection and first-detection latency.

| Profile | Detection | Actuator /60 | Plant detection | Median/P95 ms | Recall difference from final unseen |
|---|---:|---:|---:|---:|---:|
| P0 nominal | 281/300 = 93.6667% | 44 | 170/170 | 0/100 | 0 pp |
| P1 low ambient/load | 255/300 = 85% | 18 | 37/37 | 0/200 | −8.6667 pp |
| P2 high ambient/load | 288/300 = 96% | 51 | 192/192 | 0/100 | +2.3333 pp |
| P3 elevated legal noise/quantization | 281/300 = 93.6667% | 44 | 187/187 | 0/100 | 0 pp |
| P4 fixed acquisition-phase variation | 281/300 = 93.6667% | 44 | 170/170 | 0/100 | 0 pp |
| P5 combined legal stress | 288/300 = 96% | 51 | 227/227 | 0/100 | +2.3333 pp |
| **Pooled** | **1,674/1,800 = 93%** | **252/360** | **983/983** | **0/100** | **−0.6667 pp** |

Every profile: memory **58/60**, timing **60/60**, communication **60/60**, sensor/control **59/60**, integrity-observable **59/59**, benign **0/100**, precision **100%**, silent plant **0**. Pooled non-actuator counts: **348/360, 360/360, 360/360, 354/360** respectively; integrity **354/354**. A2 first coverage/accuracy and runtime accuracy among localized samples remain **100%**, with wrong fault-origin runs/samples **0/0**. Pooled runtime UNKNOWN is **0.4399846%**, reported as **0.4400%**; per-profile values are in robustness `localization.csv`.

All changes relative to the matched P0 panel are actuator detections: P1 loses **26**, P2 gains **7**, P3/P4 change **0**, P5 gains **7**. Remaining **126 misses** comprise **108 unexcited pumps + 6 uncaptured pulses + 12 dormant-memory probe misses**, with no new classifier-only category identified. P1 is worst for recall; every profile ties at zero benign alarms and complete plant-conditioned coverage. There is no supported “robustly >90% in every condition” claim.

P4/P5 use constant Sensor C phases **1/21/41/61/81/99 ms**. **Scheduler-jitter robustness was not evaluated** because the simulator's scheduler-stress and direct timing-fault paths are incompatible. Neither within-run temporal jitter nor fault semantics were changed. Robustness uses matched fault definitions but different seeds and operating contexts; pooled and final-unseen denominators must remain separate.

### 6.4 RTL feasibility evidence

| Metric | Frozen recorded result | Qualification |
|---|---:|---|
| Module size | 62 RTL lines, 1 module | One sensor-channel witness bank |
| Simulation | 3,348 software-oracle checks passed | Directed cases plus 256 arbitrary-bit records/mutations; not exhaustive equivalence |
| Storage | 161 bits / 161 flip-flops | Five 32-bit record words plus validity |
| Mapped cells | 4,395 combinational; 4,556 total | Fully combinational CRC dominates cost |
| Library cell area | 7,425.656 µm² | Summed Nangate45 cell area; not placed/routed area |
| Worst logic path | 3.4930 ns | OpenSTA pre-layout, ideal clock and stated I/O/load assumptions |
| Verification/publication latency | Combinational / one rising edge | Zero added cycles does not mean zero propagation delay |

Tools: Verilator **4.038**, Yosys **0.58+76**, OpenSTA **2.7.0**, installed typical `nangate45nm_copy.lib`. Do not headline “182 MHz silicon”: the approximately 182-MHz interface-budget estimate depends on the recorded 1-ns input/output delays, 0.01-pF output loads and no extracted interconnect. Legitimate floating-point transforms are computed by the producer; the monitor reseals supplied trusted bits. Access control, physical independence, power/clock separation and the full A2 detector are not implemented by this single RTL bank.

## 7. Metric and interpretation rules for drafting

- Keep fault detection/recall, benign alarm runs, precision and plant-conditioned detection distinct. The registered detection metric credits a post-onset alarm rising edge; it is not automatically evidence of attribution to the active fault interval.
- Compute latency among detected faults and state that denominator. Use the stored paired-latency counts when discussing A0/A2 timing improvement; do not infer it solely from marginal P95.
- Report first-localization coverage conditional on detected faults, accuracy among localized outputs, and UNKNOWN separately. Correct origin class does not identify the individual bad sensor.
- Plant propagation is an offline counterfactual evaluation label; it is not an input to either runtime method. Detecting all measured propagating faults does not prove prevention of damage, a safety integrity level or intervention efficacy.
- Γ describes a matched trace effect; exclusion from the admissible healthy set is a stronger diagnostic requirement. Legal offsets/noise/updates can explain changed traces. The integrity relation is deterministic only under the stated trusted-producer/witness assumptions.
- Exact configuration overlap is zero; scenarios still share simulator equations, fault families and design history. Wilson intervals and McNemar tests are descriptive for the grouped deterministic cohorts, not population reliability guarantees or corrections for the entire historical search process.
- State SVM information access and frozen default/CAL1 points explicitly. Binary parity on measured cases is not an equivalence theorem; missing SVM localization is a comparator-scope fact, not a claim that SVMs cannot localize.
- Do not pool development, final unseen and robustness into one recall/CI or one “zero false alarms in N” headline. Their selection roles, repeated templates and operating distributions differ.

## 8. Minimum final figure/table set

**Two figures and five compact tables** suffice; all are presentation work from existing evidence, not requests for new experiments.

| ID | Display | Source and required caption |
|---|---|---|
| **F1** | End-to-end architecture with producer/witness/consumer boundary, A/B/C acquisition, memory/timing/communication/actuator providers, unchanged fusion, G2 confirmation, and separate offline evaluator; small RTL-bank inset | Runtime interfaces and frozen builders. Show fault mutation sites outside detector inputs; mark protected ownership as an assumption and ground truth as offline-only. Do not draw a fault-label input to the witness. |
| **F2** | Miss-category composition: final 76 and robustness per-profile misses | Final and robustness `misses.csv`. Use labeled counts and cohort denominators; distinguish idle/no-excitation from uncaptured temporal events. No reconstructed waveforms or claim of complete trace-equivalence proof. |
| **T1** | Fault–Observable Matrix with provider/trust/availability legend | Condense `cross_layer_observability_model.md`; retain YES/PARTIAL/NO/CONTEXT-DEPENDENT and the meaning of direct signature versus final alarm. |
| **T2** | Development ablation panels: retained independent-C context, integrity/M2 validation, and separate benign-confirmation validation | The three development sources above. Print each panel's denominator and selection role; historical seen-90 recovery belongs in a clearly marked note. |
| **T3** | Primary final unseen: overall/per-origin detection and CIs, plant/benign/precision/latency, localization/UNKNOWN, paired counts | Final CSVs, with SVM default primary and CAL1 equality noted. Include the conditional localization denominator and benign-pair p=0.0625. |
| **T4** | Six frozen profiles plus pooled metrics and operating definitions | Robustness protocol/CSVs. Show actuator recall to explain variation, zero benign/silent counts and fixed C phases; explicitly exclude scheduler jitter. |
| **T5** | RTL interface semantics, verification coverage, storage/cell area and timing assumptions | RTL records/README. Mark pre-layout, one-bank scope, producer-side arithmetic, and absence of hardware security/silicon validation. |

Supplement only if space permits: full confusion matrices and per-origin localization, full historical C1/C2 benchmark, complete freeze/overlap provenance, and expanded RTL test coverage. Avoid redundant detection bar charts duplicating T3/T4, unsupported ROC curves, decorative screenshots, or plots implying retained raw traces exist.

## 9. Evidence gaps and claims to avoid

| Unsupported or overstated claim | Why current evidence is insufficient | Defensible wording |
|---|---|---|
| Novel DS algorithm, novel Triplex/TMR, novel CRC | The primitives are reused; no such novelty is demonstrated | Observability-led integration and evaluation of runtime evidence |
| A2 beats SVM / ML is unnecessary | Final and robustness case-level results match frozen SVM-INT | Comparable binary performance in these cohorts; A2 additionally reports evaluated origins |
| First-ever automotive diagnosis or unique research priority | No verified systematic literature positioning supplied | State contributions without priority language; verify actual references during manuscript preparation |
| Universal healthy-set separation or completeness theorem | T_H is not exhaustively enumerated; raw traces were discarded | Implementation-grounded specification with finite-cohort corroboration |
| All common-mode faults detected | AB/ABC samples mutate digital values while witnesses remain intact | Coverage of specified sampled post-publication corruption; shared physical/witness failures excluded |
| 100% fault detection or 100% localization of all faults | A2 misses 76 final cases; localization accuracy is conditional | 93.6667% final recall and 100% localization accuracy among localized detected cases |
| Zero population false-alarm rate | Only finite benign runs were observed | Zero observed benign alarm runs with explicit denominator |
| Robustness to scheduler jitter | Only fixed Sensor C phases were authorized/evaluated | Fixed acquisition-phase robustness under six registered operating conditions |
| Robustly above 90% in all conditions | P1 recall is 85% | Complete measured plant coverage despite excitation-dependent overall recall |
| Safety assurance / ISO compliance / fault prevention | No certification, safety case or intervention study established here | Diagnostic detection/localization and offline propagation-conditioned metrics |
| Cryptographic security, tamper resistance, isolated power/clock domains | CRC and logical producer ports do not establish those properties | Logical producer-owned boundary under explicit integration assumptions |
| RTL silicon cost/frequency, minimum area, or full A2 hardware realization | Mapping is pre-layout; the monitor is only one witness bank; no optimization lower bound or routed implementation | Measured standard-cell area and assumed-condition STA for the witness PoC |
| General superiority of DS over OR/weighted sums | Historical comparisons depend on engineered evidence and calibrated operating points; final campaign did not rerun all backends | Historical backend trade-offs are contextual, not the primary novelty or final superiority claim |
| Final 105-case gain is exclusively the integrity channel | Final A2 bundles integrity, M2 and confirmation; component evidence comes from separate development ablations | Combined final architecture gain, supported by separate within-cohort development ablations |

No missing evidence should be manufactured to complete the narrative. Limit or omit the corresponding claim; do not reopen detector development through this blueprint.

## PAPER STORY CONSISTENCY CHECK

- **Strongest novelty claim:** An implementation-grounded, reproducible observability-led integration and evaluation framework connecting fault-path/failure-domain analysis, protected runtime evidence, origin diagnosis and logical hardware feasibility—not novelty of DS, redundancy or CRC, and subject to verified literature positioning.
- **Strongest experimental result:** Final refined A2 gains **105** detections over same-cohort A0 with **zero losses**, detects **645/645** plant-propagating faults with **0/600** benign alarms, and reports **0/0** wrong confident fault-origin runs/samples; frozen equal-observability SVM-INT **matches** its binary results.
- **Strongest limitation:** All evidence is simulator- and boundary-dependent: idle pump faults and uncaptured events remain missed, trusted witness independence is assumed, and low-load recall falls to **85%** despite complete measured plant coverage; no field, scheduler-jitter or physical-security guarantee follows.
- **Unsupported claims to avoid:** SVM superiority, new DS/Triplex/CRC primitives, first-ever priority, universal fault distinguishability, zero population false alarms, all-fault/common-mode coverage, classical state-observability proofs, safety certification, and routed/silicon/tamper-resistant RTL claims.
