# ONE new final unseen validation of CURRENT CLO-DSF

Registered UTC 2026-09-24T13:47:40.943640+00:00, before any outcomes.
Exact baseline commit d040c341f22be2dcd4483c65786c07c696020f9c. No algorithm copies,
changes, fitting, calibration, selection, early stopping or outcome-dependent redesign.
Rejected thermal_contract.cfg is NOT loaded. Existing 300ms sensor-response channel,
causal precedence and all scientific code/config are committed CURRENT, hash-verified.

1500 deterministic120s cases:1200 faults,240 per origin,300 benign. Ten new operating
families, all1500 full physical profiles distinct; complete commands/profile/seed/onset/
duration/magnitude/workload in campaign_manifest.csv. Discrete bit positions/ticks and
fan-off necessarily share legal domain values; exact configurations do not overlap.
New profile boundaries16700/30100/46700/69400/91300ms; speeds11..104kph and loads.36..98
before segment factors; ambient changes and load transitions produce legitimate ramps.
All cases validated through the public unchanged C parser before outcome execution.

MEMORY180 stuck-bit configurations (both polarities, three behaviors) plus60 bit flips.
Post-hoc effective corruption means trusted register-shadow inconsistency after onset;
dormant stuck bits have no such mismatch. Never feed classification to inference.
TIMING120 deadline and120 task-delay cases. COMMUNICATION80 each delayed/dropped/replay,
short200/700ms and longer2300/13100ms windows, intermittent/permanent where supported.
SENSOR_CONTROL120 slow permanent ramps: signs+/-; amplitudes1.15/2.65C; rise7/19/47s
(rate magnitudes.02447..37857C/s);60 weak steps of.84..1.029C;60 pulses of.38..533C
and1.85..2.093C. Steps/pulses transient/intermittent/permanent with200/1100/5300ms
finite windows. No fault sample is removed if runtime evidence remains insufficient.
ACTUATOR180 pump degradation and60 fan-off cases. Intermittent hardware800on/1700off;
legacy intermittent two events with1900ms gap. Seeds710003+1009*family+19*cell; only
injectors supporting seeds consume them. Seed changes do not imply random replicates.
Half each family uses legal target updates105C at35300ms, then92C at72700ms.
Benign variants: no variation; alternating jitter.019/.057/.089C; jitter.031C plus
triangular drift1.3C/16200ms, or.071C plus2.1C/22600ms. No transport faults composed
with sensor variation. These nuisance variations are symmetric acquisition/consumption
workloads, not hidden runtime labels. Known slow common-mode bias limit is tested honestly.

All historical data are SEEN, including committed previous final_unseen manifest
SHA256 93a22e848226fae16db6969aaa15694bc1515a6b0fbb4c528c16d42f8a4aace7. That manifest was read,
backed up before replacement, and included as the first overlap-audit source. Git holds
the previous full evidence at baseline commit. Audit scans reachable Git campaign/profile
identities, current results/presets and surviving /tmp manifests, including overwritten
CURRENT developments and prior confirmation/holdout. 943 distinct identity sources.
Full numeric physical profile disjointness is sufficient proof of zero exact configuration
overlap, independent of inconsistent historical configuration-hash conventions. This is
exact configuration novelty, not a claim of statistically independent operating families.

All methods run observe-only on the SAME physics stream: CURRENT CLO-DSF, frozen Fair
Weighted Sum(choice6), Simple OR, Plain DS, Hybrid. Timing Monitor reported only for
TIMING cases. Original extraction and thresholds remain unchanged for all baselines.
Inactive internal observers may execute but are not additional candidate copies.

Endpoints: first post-onset alarm sample; latency relative to scheduled activation among
detections; precisionTP/(TP+benign false alarms); recall includes dormant states in denominator.
Any benign alarm counts. Pre-onset fault-run alarms are reported separately. Offline
unchanged reference-based evaluator supplies plant propagation, never inference truth.
Pre/same/post-plant timestamps conditional on detected plant-propagating runs; undetected
or no-plant cases are separate. Median/P95 use existing linear interpolation convention.
Localization: first-known coverage among detections, first accuracy among localized;
all-runtime accuracy among localized alarm samples, UNKNOWN among all alarm samples,
wrong known-origin samples/runs, confusion includingUNKNOWN. Benign known-origin alarms,
if any, count as wrong origins. Wilson95 intervals are descriptive case intervals;
correlated deterministic profiles limit population claims. No binomial interval for macro mean.
Paired CLO vs Weighted Sum both/onlyCLO/onlyWS/neither on fault cases; exact two-sided
conditional binomial McNemar for>=10 discordances, otherwise counts only. Paired benign,
silent misses and common-detection latencies also reported. No superiority unless supported;
a small p-value cannot establish population generalization or correct causal attribution.

All1500 cases execute once, no reruns/selection. Streaming raw files deleted after compact
scoring. Eight representatives selected now: final_new_0000,final_new_0024,final_new_0048,final_new_0072,final_new_0084,final_new_0090,final_new_0096,final_new_0120. No bulk trace retention.
Protocol/manifest/audit/implementation hashes frozen below before runtime. Final build,
Python compile,diff check,full tests,legacy48,RTL64; Hybrid/HETIA and GUI preserved.
No commit/push. No subsequent algorithm work authorized by this evaluation.

## Exact command replay
For each manifest row create its named profile CSV with the seven fields in profile_json
under $WORK/profiles, create $WORK/raw, expand $ROOT and $WORK in command_json, and execute
that argument list without shell interpolation. Use the committed report/execution helpers
for metrics; rename sensor_bias_ramp only in command construction as recorded (zero base
bias plus the already-committed --revised-sensor-ramp workload). No inference code duplication.
