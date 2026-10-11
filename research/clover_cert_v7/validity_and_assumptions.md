# Validity and unresolved assumptions

All **41 v6 unresolved findings** are retained verbatim in `v6_import_verification.json` and `two_world_model.json`. No v6 file or finding was rewritten or discharged. Source-anchor verification checks existence, exact line/token and source hash; it does not prove semantic completeness or hardware integrity.

## Explicit model restrictions

- **M_CLOSED:** exactly 67 realizations per context (66 faults plus healthy), at most one fault; no additional writers/faults/coherent evidence corruption. Exhaustiveness means exhaustive over this declared domain only. It is not a physical closed-world assumption declared true.
- **M_CONTEXT:** fixed environment inputs 60/92 C, load/speed zero, common initialization, baseline t=0 before fault starts, no legitimate target writes or external traces. No thermal feedback is simulated. This keeps control/actuator effects inspectable without inventing a quantized plant. Full-ECU observations may differ once omitted dynamics/reactions operate.
- **M_PHASE:** capture after selected component execution, with diagnostic/safety/detector reactions omitted. The fixture does not run the complete scheduler. Its results cannot sanitize production post-reaction commands.
- **M_NUMERIC:** finite binary32 domain, exact equality, explicit compiler semantics. No sensor-noise distribution, measurement tolerance or probabilistic execution distribution is established.

These restrictions bound an experiment; they are not extra trusted sensors or protective mechanisms introduced to obtain a physical positive result.

## v6 obligations retained

| ID | Status in v6 | Meaning for this experiment |
|---|---|---|
| A_PROCESS | UNVERIFIED | Shared process and fields are not protected domains; positives cannot survive arbitrary coherent corruption without an explicit contract. |
| A_SHADOW | UNVERIFIED | Full-view positives require honest shadow/register capture and writer constraints. |
| A_CLOCK | UNVERIFIED | Simulated execution/sample/capture times do not establish physical clock integrity or monitor latency. |
| A_TAP | UNVERIFIED | Source tap and metadata integrity are not guaranteed; front-end bias reaches both tap and delivered observation. |
| A_PUMP | UNVERIFIED | No independent physical pump-health witness; model realization is not measured flow/current. |
| A_SENSOR | UNVERIFIED | Optional redundant sensors are not used; no independence added. |
| A_MAILBOX | UNVERIFIED | CRC/protected witness storage is not used or presumed isolated. |
| A_BUILD | UNVERIFIED | Exact component build recorded here; historical/full/optional build linkage remains unresolved. |
| A_FAULTSET | UNVERIFIED | Physical alternatives need not be exhausted by our declared finite subset. |
| A_ORACLE | VERIFIED | Legacy oracle dependencies are confirmed and excluded, not validated as evidence. |
| A_REPLAY | VERIFIED | Older serializer omits some selected live fields; this fixture uses live capture, not that replay format. |
| A_SUBTICK | UNVERIFIED | No 25/50 ms online availability claim is made. |
| A_POSTWRITE | UNVERIFIED | General arbitrary shared post-write corruption is not established as an implemented fault path. |

Every positive history and each conditionally separable pair lists its complete conservative policy obligation set. Origin transition obligations are separately listed in the manifest. A_PUMP concerns transfer to physical feedback, not an assertion that the component fixture has that witness. No assumption is marked verified merely because the finite oracle returns a singleton.

## Checker boundary

Admissible finite observations are explicit projections of `runtime_observation_capture`: delivered/source measurements, source timestamps and age/freshness, target/register/shadow, execution timestamp and pump command/realization. Source fields share producers. Float hex encoding is lossless serialization, not a derived diagnostic or label.

Excluded: plant truth, clean-reference trajectories, fault mode/behavior, injection start/duration, bit/scale parameters, active flags, propagation scores, generated-history bookkeeping, replay/drop labels. In addition `diagnostic_id`, `safety_state`, `detector_alarm`, and fan-health outputs are excluded due to v6 legacy truth/metadata dependencies (`diag_truth`, `diag_label`, `hybrid_truth`, `detector_onset`, `action_gate`, `safety_truth`, `fan_oracle`). No alarm is presumed independent because it is runtime-published.

The offline oracle requires origin-labeled **model executions** to define the compatibility relation. Those labels are the hypotheses being compared, not input features supplied for the tested world. Runtime `decide` takes only an observation history and the precomputed model relation. Its conditional output is not passed back into production code.

## Independent validation and remaining gaps

The linear compatibility scan and explicit pair cross-product are separate implementations of the index-based reference calculation. Monotonicity and direct hand-picked boundary cases test behavior. The C comparison builds unchanged modules under v7 and checks every finite realization and selected observation bit. This is stronger than testing two Python functions sharing transitions, but neither checks omitted thermal/safety behavior.

No full scheduler run was used: this task's first controlled experiment isolates its component prefix so oracle-dependent safety paths cannot secretly improve classification. This limitation is recorded rather than relabeling component outputs as complete ECU results. Full closed-loop, alternative environment trajectories, legitimate writes, wider parameters, multiple faults, noise, asynchronous clocks and implemented corruption domains are further validation requirements.

All writes, compiler temporary files and outputs are confined to v7. The preflight snapshot hashes every pre-existing file (including ignored/untracked data and all v6 artifacts); the final checker compares byte content, symlink targets, file set and Git HEAD. It reports changes rather than repairing them.
