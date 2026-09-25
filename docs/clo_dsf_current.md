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
