# Formal problem: bounded conditional observation/checker synthesis

## Reused model and boundary

The source-backed dataset is exactly v7's 134 modeled executions (67 in each fixed-input component context), with diagnostic deadlines 100, 200 and 400 ms and exact binary32/integer/Boolean equality. The unchanged v7 C comparison checked 670 rows; v8 imports those results and does not rerun or overwrite them. These are component traces, not full closed-loop or physical ECU guarantees.

V8 reads every v6/v7 artifact and rechecks all 134 v6 source anchors and 36 source hashes. `research_import.json` contains the inventory and all 41 unresolved findings unchanged. The v7 model restrictions M_CLOSED, M_CONTEXT, M_PHASE and M_NUMERIC, plus unresolved process, timestamp, tap, shadow, actuator-feedback, build and fault-set obligations remain applicable. No physical trust contract is added.

Source-backed paths used for structural bounds:

| Origin | Mutation and temporal propagation | v6 anchor IDs |
|---|---|---|
| Memory | register mutation → executed target → command → realization; no shadow mutation in this finite domain | `flip`, `stuck`, `restore`, `consume`, `pump_cmd` |
| Timing | control gate/pending job → held command and execution timestamp; pending effects can outlive activation | `skip`, `delay_due`, `delay_complete`, `discard`, `timing_complete` |
| Communication | historical delivery/hold → delivered value/time/age → control command → realization | `history`, `comm_delay`, `comm_drop`, `comm_replay`, `timestamp_publish` |
| Sensor | front-end bias → shared source tap/delivered value → control and realization | `legacy_window`, `sensor_bias`, `source_tap`, `control_error` |
| Actuator | scale after control → modeled pump realization; zero excitation masks the effect | `pump_scale`, `pump_publish` |

Exact relative paths, lines, functions and tokens remain in the immutable v6/v7 manifests. The implemented support bound retains all allowed affected fields from activation through the horizon, even after recovery; this deliberately overapproximates persistence and pending work. It is checked against all actual finite trace differences. Labels and activation times can inform **offline synthesis bounds**; neither is an online checker input.

## Mathematical input

Let E be a finite set of admissible executions; o(e) is the origin hypothesis, including healthy. For each available runtime coordinate q=(field, publication time), v(e,q) is its exact published value. Each execution already incorporates its allowed origin-dependent corruption and all correlations between common-cause writes. A domain identifier is a dependency annotation, not an independent witness. The real-case metric domains=5 counts the five logical origin-mutation groups in the support map; it does not assert five physical fault-containment domains. The actual process boundary remains shared and unverified.

An implementation-backed observation contract selects a subset S of available coordinates without modifying E. A menu can bundle coordinates and restrict their schedules. Let h_S(e,d) be the ordered selected history through deadline d. Define K_S(h,d)={o(e): h_S(e,d)=h}. The checker returns its sole origin if |K_S|=1 and UNKNOWN otherwise, including for histories outside E. Runtime input is h alone; labels, clean reference trajectories, injection metadata and legacy oracle-derived fields are excluded.

For general synthesis, R_d is a specified set of execution pairs required to be distinguishable by d. In the executed comparison, derive R_d from the full selected v7 view: whenever the full-view verdict for e is a singleton a, require e to differ from every world of origin other than a. Full-view UNKNOWN histories impose no impossible positive requirement. This yields exact preservation of the full-view **verdict** at the specified deadline, not necessarily identical compatible sets or equally early answers at other times.

Corruption/trust extension: replace E by E_A,W, containing every allowed correlated write realization under conditional assumptions A and domain relation W(o,t). All subsequent quantifiers range over this expanded set. An arbitrary physical W is **not established** by CLOVER-ECU; source-backed writes are used in real cases, and the separately labeled synthetic examples define their own finite W. Simply erasing every possibly corrupted field is an information-losing abstraction, not exact attack diagnosis.

## Observation menu and joint objective

Five bundles partition the 14 selected v7 fields:

1. Delivered coolant, pump command, pump realization.
2. Published sample timestamp, age, freshness.
3. Register, shadow, shadow validity, executed target.
4. Last execution timestamp.
5. Source value, timestamp, validity.

Select any bundle subset at a 100 or 200 ms capture period: 64 contracts per real case. Source acquisition remains 100 ms; capture selection is an offline design menu, not a production ECU change. Empty contracts are permitted. Clock/time is included in symbols and excluded from the uniform scalar-field read cost. No buffering of unselected 100 ms observations is invented for 200 ms capture.

The shared objective is J(S)=number of selected scalar reads through d + number of states in the compact deterministic finite-history checker. Both weights equal one and are arbitrary, disclosed modeling weights. The checker is a prefix trie with singleton/UNKNOWN outputs, reduced by bottom-up equality of residual output/transition behavior, with a default absorbing UNKNOWN state for unsupported continuations. This is standard acyclic Moore minimization. It is an abstract state-count objective, not executable bytes, physical RAM or WCET. All methods generate the same checker and optimize the same J over the same feasible contracts.

The executed algorithms enumerate every candidate contract and report the full feasible set, every feasible objective and all optimum contracts. They do not stop after finding a cheap plausible configuration. The finite Boolean backend is transparent positive-clause evaluation; neither Z3 nor cvc5 is installed, and no SMT/BDD runtime claim is made.

## Hypotheses needed by the mathematics

The pruning proofs assume a fixed finite E, common context/baseline for compared worlds, a sound dependency upper bound, correct publication times, and passive contracts. Unknown physical integrity must either remain a conditional assumption or enter E as additional realizations. Repeated observations sharing a writer do not acquire independence. Active probes, scheduler interference and protection choices that alter E require a different quantified problem and invalidate the simple monotone-selection proof.

No direct plant truth, fault label, fault onset flag, diagnostic_id, safety_state, detector_alarm or fan-health label output appears in selected histories. Source timestamps/age are visible; their integrity remains unverified. A singleton in E is only a conditional model certificate. No deployed certificate follows from the synthesis or tests.
