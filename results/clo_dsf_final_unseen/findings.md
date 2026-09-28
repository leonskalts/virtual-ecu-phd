# Final unseen CLO-DSF: development closed

The pushed freeze commit is `9f9935876dd15a9668c76f3cd5634f77a2dde6ad`. Exactly1500 predetermined cases executed once:1200faults,300benign. Historical overlap0 against32,244 recovered profile identities and34,328 configuration identities. Manifest and scientific hashes match their pre-execution lock. No algorithm change, tuning, rerun, replacement or exclusion.

| Endpoint | CURRENT CLO-DSF | Frozen Fair Weighted Sum |
|---|---:|---:|
| Overall fault detection |1051/1200 (87.58%)|898/1200 (74.83%)|
| Plant-propagating detection |669/720 (92.92%)|615/720 (85.42%)|
| Silent plant misses |51|105|
| Benign alarm runs |0/300|150/300|
| Median/P95 latency |0/33.5s|0.1/10.915s|

Overall Wilson95% CI85.60–89.33%. Overall detection remains below90%; consequence-conditioned detection does not replace that metric. Run-level precision100%,recall87.58%. Pre/same/post-plant detections593/35/41. No pre-injection alarm runs for CURRENT.

Memory228/240,timing240/240,communication240/240,sensor-control153/240,actuator190/240. Effective memory162/162; dormant/value-consistent stuck cells66/78. All12 memory misses had zero active-window diagnostic checks and no plant propagation. Dormant readback detections are legitimate active diagnostic evidence, not benign false alarms.

Independent primary/reference drift80/80; common-mode drift0/40; weak steps34/60;pulses39/60. All40 missed common-mode cases propagated. The remaining11 silent plant misses are8weak steps and3pulses. Independent drift is detected slowly: subgroup median43.95s/P9573.695s; this drives the overall latency tail. Short/weak sensor misses are sensitivity limits, not automatically proven unobservable.

Initially excited actuator147/147; initially unexcited43/93. All43 recovered initially unexcited cases became excited during their active windows. The remaining50 had no active-window command excitation, no plant propagation and no detection. No artificial excitation or health metadata was introduced.

First-detection localized accuracy1051/1051,coverage1051/1051 detected faults. Runtime localized accuracy345202/345202,zero wrong-origin runs/samples. UNKNOWN2118/347320 alarm samples (0.610%); runtime coverage99.390%. Accuracy is conditional on localization/detection, not a claim about undetected cases. Sensor-pair member identity is not inferred.

Paired fault detections: both852,CLO-only199,Weighted-Sum-only46,neither103. Exact two-sided McNemar p=7.279788723269732e-24. This supports a binary detection advantage on this specific campaign; it does not establish universal superiority. CLO has lower silent misses/benign alarms here but a materially longer P95 latency. Frozen baseline settings were not recalibrated.

Strongest result: zero benign alarms and zero wrong confident origins, with92.92% consequence-conditioned detection and complete timing/communication/effective-memory coverage. Strongest limitation: common-mode drift remains undetected and contributes40/51silent plant misses; independent drift detection can be late. Latent/no-excitation misses remain in the overall denominator.

All328 unit/integration tests,project build,Python compile,diff checks,48legacy,64RTL and Hybrid/HETIA integrity checks passed before freeze. Post-execution scientific/GUI/historical integrity verified again. No certification claims. Wilson intervals are descriptive for correlated deterministic campaign cases; runtime samples are not independent trials. Evidence is manuscript-ready with these limitations explicit. No further development.
