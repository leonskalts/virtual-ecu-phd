# Final retained CURRENT CLO-DSF

Development is closed. The implementation is `src/v7_3/clo_dsf_revised.c`,
`include/clo_dsf_revised.h`, and the existing runtime adapter. Configuration remains
`results/cross_layer_safety_v7_3_dev/revised.cfg`. Global confirmation threshold
0.5, persistence1, temporal discount0.8 and localization thresholds are unchanged.

Retained runtime evidence:

- Trusted calibration shadow and acquisition-to-consumption consistency.
- Atomic protected-memory save/challenge/read/restore diagnostic with deterministic
  phase sweeping: nine1100ms gaps followed by100ms, average1Hz, maximum1100ms.
  Probe freshness follows the existing maximum interval. The diagnostic consumes
  readback/status/timestamps, never injected labels. Effective stored-value
  corruption and dormant/value-consistent stuck cells are reported separately.
- Independent redundant coolant sensor, long-horizon signed disagreement and
  short-horizon FAST disagreement with bounded same-sign integration. The
  existing300ms local trajectory forecast is retained. A redundant pair does not
  identify which member is faulty; common-mode drift can remain plausible.
- Runtime command/actual actuator consistency. No active excitation, added health
  telemetry or pre-mission BIST. Zero command may conceal authority degradation.
- Causal-precedence localization. Later downstream sensor evidence cannot rewrite
  an established direct origin. Ambiguous origins remain UNKNOWN.
- Startup qualification: absolute slew requires five contiguous in-envelope
  acquisitions for origin evidence. Anomaly history alone from unqualified slew
  cannot confirm without independently qualified evidence. Direct memory,
  communication, timing, actuator and independent sensor evidence remain usable.

No hidden plant truth, fault labels or counterfactual reference feeds inference.
Counterfactual propagation metrics are post-hoc evaluation only. Memory accesses
have no measured hardware WCET in this simulator; results are not certification.

Rejected mechanisms remain absent: supervised residual ML, one-class ML,
control-action contracts, radiator reference, multi-node thermal model, active
actuator excitation, pre-mission actuator BIST and passive actuator-health
extensions. The final supervised trial improved detection331/396 to366/396 but
introduced17/108 benign alarms, failing both its95% recall and1% benign gates.
Its compact rejection record is development evidence, not the retained detector.

`results/clo_dsf_current/` keeps required historical identities, development
manifests and compact summaries. All earlier campaigns, including previous
`clo_dsf_final_unseen` contents, are seen development evidence. The final new
holdout must record the freeze commit, lock its manifest/protocol before outcomes,
execute each case once and report all faults including latent/unobservable cases.
No further selection, tuning or reruns for poor performance are permitted.
