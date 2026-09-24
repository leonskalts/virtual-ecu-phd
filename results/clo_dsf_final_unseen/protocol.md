# Final unseen CURRENT validation

Commit: 145794476b51e8d75fbe3043fa0672e136aaa1e9. Registered UTC 2026-09-20T13:02:48.571026+00:00 before any outcomes.
1500 unique cases: 240 per fault origin, 300 benign. Ten new operating families;
new profiles, seeds, activation times, finite durations, continuous magnitudes.
Discrete bits/ticks and minimum short delays necessarily reuse physically valid values.
Seeds are effective only where supported by the original injector; deterministic
cases are not claimed to be independent random replicates. Exact commands and full
profiles are in the manifest. Profile disjointness proves zero exact overlap even
if historical seed/metadata representations differ. Audit covers saved profiles,
inline profiles, previous holdout, CURRENT history and surviving overwritten manifests.

MEMORY: stuck bits of both polarities and bit flips, static/legal updates. Effective
means observed register-shadow mismatch after onset, classified only after runtime.
Dormant means stuck-bit run with no such mismatch. TIMING: deadline/task delays.
COMMUNICATION: delays/drops/replays including shortest one-tick disturbances.
SENSOR_CONTROL: +/-1.05 and +/-1.30 C biases, .35/.65/2.3/6.7 C pulses.
Weak isolated subgroup is non-intermittent bias (80 cases), predeclared regardless
of outcomes. ACTUATOR: six pump degradation strengths plus fan-off cases.
Behavior is transient/intermittent/permanent where supported. Permanent duration
is explicitly zero, so legacy permanent sensor/actuator events truly continue.
Legacy intermittent events are two separated episodes, not an invented new injector.
Benign cases include static and legal target updates at33700/68300 ms, alternating
measurement variation and slow triangular drift using the committed workload adapter.
No noise is composed with transport faults. All cases last120s, 100ms ticks.

No selection, calibration or redesign. Known weak bias limits remain. CURRENT,
frozen Fair Weighted Sum (choice6), Simple OR, Plain DS and Hybrid observe the same
runtime stream. Timing Monitor is scored ONLY for timing cases. Other internal
observers may execute but are not reported. Source/config hashes recorded below.
No injection labels/truth enter inference; only offline evaluation uses them.

Detection is first post-onset alarm, latency relative to scheduled activation;
plant propagation uses unchanged reference-based evaluator. Pre-onset alarms are
reported separately. Benign alarms count any alarm. First-origin accuracy among
localized detections; coverage among detections; runtime known-origin accuracy,
UNKNOWN and wrong counts cover all alarm samples, including pre-onset samples.
Report per-origin, effective/dormant memory, weak isolated bias and actuator subtypes.
Wilson95 intervals are descriptive case intervals; correlated deterministic cases
are not random population samples. Paired exact two-sided binomial McNemar on
fault detection discordances if nonzero (otherwise not applicable); no population
superiority claim from this test alone. Paired benign counts and joint latencies
also reported. Retain all failures without changing settings or removing cases.

Keep eight traces chosen before outcomes: first of six origins, first isolated
negative bias, first weak pump case distinct from the initial actuator trace.
Process and delete per-run temporary raw data. Full regression after all1500:
build, compile, diff check, tests, legacy48, RTL64; hash checks before/after.
No commit/push; GUI session bytes preserved. No scientific implementation edits.
