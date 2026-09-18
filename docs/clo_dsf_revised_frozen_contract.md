# CLO-DSF v7.3 frozen development contract

Frozen 2026-09-18T14:19:25.218003+00:00. Baseline 30e48538cc063cb62f3363c7075c0650c6a4642f.
No final unseen paper holdout has been created, inspected or executed.

## Scientific identity

Normative machine-readable specification:
results/cross_layer_safety_v7_3_dev/clo_dsf_revised_config.json.
Exact eight-value configuration: results/cross_layer_safety_v7_3_dev/revised.cfg,
byte-identical to v7.2. Reference implementation: src/v7_3/clo_dsf_revised.c.
The source includes the unmodified v7.2 inference body and substitutes only
actuator evidence extraction. Development rationale and protocol are in
docs/clo_dsf_revised_development.md; preregistered identities and the pre-validation
selection record remain archived. No parameter search or post-validation edits.

One replacement source: synchronous actuator command/response conformance.
On the 100 ms actuator cadence, all four values must be finite. Expected response
is clamp(command,0,1); its immediate predecessor and successor representable
float values bound the accepted response. A response outside either pump or fan
interval gives e_act=1; otherwise e_act=0. Unavailable/off-cadence is vacuous.
No duplicate source, fitted severity threshold, origin reliability discount,
propagation bonus, injector label, self-test label proxy or experiment truth.

Detection frame NORMAL/ABNORMAL and five-origin localization remain independent.
Dempster fusion, fixed channel order, vacuous fallback, temporal retention .8,
r_detection 1, suspect .35, confirmation .5, persistence 1, localization .55,
margin .15 and ignorance limit .5 are immutable. UNKNOWN is valid. Conflict,
ignorance and timestamps remain visible; episode paths remain diagnostic-only.
Duplicate/backward samples are ignored. All unchanged semantics are specified
by the hashed v7.2 algorithm and complete revised machine configuration.

## Why freeze, and limits

On new group-held development validation, revision detects 260/300 versus
v7.2 252/300 and frozen Weighted Sum 251/300. Plant-propagating detection is
198/204, versus v7.2 190/204. Silent plant cases fall 14 to 6. No detection loss,
zero benign alarms among 90 cases, 200/260 localized (76.92%), all correct;
60 UNKNOWN and zero wrong localized runtime samples. Median/P95 is 0/200 ms.
All eight gains over v7.2 are .98 intermittent pump degradations across four
profiles/two onsets. This is a material and mechanistically explained reduction
in silent plant misses, not a freeze based merely on a small percentage gain.
The minimum A0/A1 ablation changes only this source; no A2 is needed.

Results are designed correlated development cases, not population safety or
final unseen evidence. Gains do not prove DS is uniquely effective: Weighted Sum
was frozen with its original inputs, and an enhanced pool with the same new
contract source was not evaluated. Six silent communication misses remain;
14 memory and six unexcited pump faults also remain undetected. Sensor/control
origin remains UNKNOWN. The virtual actuator is noiseless and instantaneous;
physical response feedback needs independent trust and a validated physical
error/dynamics envelope. This one-ULP contract is not a hardware tolerance.

## Integrity and future use

269 tests, 48 legacy regressions, 64 RTL regressions and six representative
seven-baseline parity replays passed. Historical source/evidence and the user's
session edit remain unchanged. Verify all hashes before a separately generated
new unseen holdout. After this freeze do not modify scientific parameters,
evidence semantics or localization logic. Any further scientific revision must
receive a new development identity and fresh evaluation.

Build: make -f clo_dsf_revised.mk
Verify: python3 scripts/freeze_clo_dsf_revised.py --verify
Run example (new output destination):
./virtual_ecu_v7_3 /tmp/revised.csv baseline --detector clo_dsf_revised --detector-action observe_only --revised-config results/cross_layer_safety_v7_3_dev/revised.cfg

No optimization, embedded WCET, production readiness or compliance claim is made.
