# CURRENT slow-bias investigation and development protocol

Inspect the36 prior validation ramps and60 benign controls before any new outcomes.
No drift mechanism is selected: the local linear forecast annihilates an added
linear ramp away from its endpoints. For b(t)=a+v*t,
b(t)-b(t0)-[(b(t0)-b(t0-0.4))/0.4]*(t-t0)=0.
Increasing the signed accumulation horizon cannot recover this missing component.
Residuals instead capture curvature, controller/actuator feedback and measurement
variation, which also occur in legitimate thermal motion. This is a limitation of
this observable/model, not proof that every possible runtime observer must fail.

Replay results:36/36 ramp cases have zero response-channel strength. Maximum ramp
interior innovation0.011692C; benign maximum0.781929C. Exploratory five-second signed
accumulator I[n]=.98*I[n-1]+r[n] peaks0–0.169963 on ramps and0.066436–1.948727 on
benign controls. Windows exclude the first500ms after onset; benign controls use
23000–52500ms. These summaries are not a threshold calibration: no parameter is
selected from them. Bounded and signed accumulation alone is not justified by this
signal overlap. Actuator-conditioned absolute physics would require independently
validated thermal assumptions beyond the current local response evidence.

Run one new900-case campaign,600 TRAIN/300 VALIDATION with disjoint operating
families and entirely new profiles/seeds. Same origin balance as the preceding
sensor-response campaign. Slow ramps use +/-1.0,2.4,4.8C over5/15/40s, spanning
0.025–0.96C/s; preserve weak steps/pulses, fast legal load transitions, triangular
benign variation, bounded noise, authorized calibration updates, memory integrity,
communication, actuator and timing cases. No new injection semantics or observables.
No next unseen holdout, parameter search or post-validation selection.

A0 is the exact starting CURRENT core; retained CURRENT is the same source,
compiled as a separate comparator to verify identity. There is no distinct A1
because no new mechanism is scientifically selected. Also compare frozen Fair
Weighted Sum. Report slow ramps separately from step/pulse strata, effective vs
dormant memory, plant propagation, latency and first/runtime localization.
Existing 300ms forecast, acquisition/consumption consistency and causal precedence
remain byte-identical. No runtime access to labels, injected offset or hidden truth.

Keep summaries, classification, exact manifest, findings, validation record and
8 predetermined compressed traces. Preserve historical/previous final-unseen
artifacts and GUI state. Full build/compile/diff/tests,48 legacy and64 RTL at end.
No commit or push.

## Active protected-memory readback diagnostic

CURRENT additionally consumes the result of a periodic atomic target-register
challenge, independent of whether control has used the stored value. Every1000ms
it saves the actual16-bit word, writes/reads0, writes/reads65535, restores the saved
word and verifies restoration. The shadow is neither challenged nor overwritten;
authorized calibration updates still use the original commit path. Four reads plus
three writes cover both stuck polarities of all16 bits. Persistent checker state
is16 bytes per ECU; the simulator assigns no scheduler duration to these accesses.
A hardware deployment needs exclusive access, a safe restore strategy and measured
WCET; simulation results are not a real-time cost guarantee.

The generic checker has no ECU or fault metadata dependency. A separate virtual
storage backend models active stuck-cell write behavior; inference sees readback
mismatch and timestamp only. This is an explicit new virtual-device contract, not
a passive CRC capable of detecting a value-correct stuck cell. Bit-flipped stored
values are restored unchanged by the probe, preserving the prior effective-memory
shadow evidence. Ordinary injection/control behavior remains unchanged.

A fresh failed check contributes direct MEMORY/ABNORMAL evidence in the existing
memory channel; no new DS source, threshold or causal-precedence rule is added.
Results expire after1000ms and are replaced by the next check. Intermittent faults
can require more than one period when their active phase misses a probe.

No qualified sensor anchor is implemented. The operating model has nonzero heat at
zero load and lacks an engine-off/ambient-soak certificate. Low-load intervals must
not be called ambient references. The existing short-horizon sensor channel remains
unchanged, with slow common-mode drift a documented limitation.

## Qualified independent redundant temperature sensing

The optional installed hardware contract is two co-located temperature sensors
with independent ADC/reference, calibration, noise state and acquisition paths.
Enable this modeled hardware with `--revised-reference seed:offset:noise`.
Absent hardware contributes no evidence. The second sensor has a dedicated
`redundant_temperature_t`, 0.01 C quantization and a separate seeded bounded
noise generator. It measures the same physical coolant through its own sensor
model; it never reads primary acquisition/delivery or control estimates. The
runtime allowlist contains only its measured value, timestamp and conversion
status. The counterfactual ECU used for offline propagation scoring is a separate
concept and is never the detector's redundant reference.

The consistency feature is

`m[k] = sum(primary[k-i] - reference[k-i], i=0..319) / 320`

`e[k] = min(1, max(0, (abs(m[k]) - 0.90 C) / 2 C))`.

Only synchronous valid acquisitions enter the full 32 s window; gaps reset it.
The 0.90 C envelope covers earlier legal triangular primary measurement
variation (amplitude <=2.3 C, period <=24.2 s, maximum window mean 0.435 C),
aggregate calibration uncertainty 0.20 C, bounded noise 0.20 C and 0.005 C
quantization. Alternating errors cancel; genuine shared thermal ramps cancel.
Persistent differential drift becomes observable, with unavoidable window delay.
No online calibration learns away a permanent disagreement. This is a conditional
metrology contract, not a universal bound for arbitrary sensor placements or
thermal response lag; independent hardware validation is required before deployment.

A current explicit reference conversion-failure status contributes sensor evidence;
a missing/unconfigured reference or stale timestamp alone does not assign origin.
The feature is max-merged into the existing sensor channel, without an additional
independent DS mass, altered global thresholds or propagation scoring. Existing
causal precedence suppresses downstream localization contamination. Disagreement
can support broad SENSOR_CONTROL origin; **which sensing chain failed remains
UNKNOWN**. No primary-vs-reference fault attribution is asserted.

Reference-only front-end faults are injected separately by the experiment adapter
(`--revised-reference-fault kind:start:rise:duration:period:magnitude`); kind 1 is
ramp, 2 step, 3 conversion failure, 4 pulse. These controls never enter runtime
inference. Common-mode tests separately drive both paths; shared drift is a hard
negative control. The reference does not replace the primary control input, so a
reference-only fault need not propagate into the plant.

## Complementary FAST disagreement contract

The slow window and all other origin mechanisms are unchanged. Let
`d[k] = primary[k] - reference[k]` for valid synchronous acquisitions.
Independent-chain bounded sample error is at most0.20C combined, so a
sample-to-sample change permits0.40C; a legal differential ramp permits1.2C/s.
An excessive edge is `abs(d[k]-d[k-1]) > 0.40 + 1.2*0.1` C.
This is a sensor metrology assumption, not a fault-specific cutoff.

The FAST provider freezes the acquisition immediately preceding an excessive
edge as its baseline for at most300ms. It confirms either two consecutive,
same-direction residuals exceeding `0.40 + 1.2*h` C from that baseline, or
three excessive edges in the last ten acquisitions. The latter covers recurrent
pulses; a single spike and its recovery supply only two edges. A confirmed
contract violation supplies direct sensor evidence1, max-merged with the same
sensor mass as SLOW and inherited primary checks. It is not a probability
calibration or an extra independent DS source. No DS threshold changes.

New evidence disappears on recovery/window expiry, and gaps or invalid samples
reset its history; existing DS temporal decay is unchanged. The check is symmetric
under swapping the sensors. It retains broad SENSOR_CONTROL localization and
unresolved sensor-member identity, with the original causal-precedence rules.
Common-mode faults remain outside its observability. Repeated large impulsive
noise that violates this contract may be indistinguishable from a fault pulse
train; isolated-spike rejection is not a guarantee for arbitrary noise bursts.
