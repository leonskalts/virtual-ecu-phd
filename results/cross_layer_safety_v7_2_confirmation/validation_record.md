# Final CLO-DSF validation record

Status: PASS. Frozen DEVELOPMENT candidate, ready for a separately generated unseen holdout.
No final holdout has been created, inspected or run. No scientific parameter search or post-confirmation tuning occurred.

- Committed baseline: 894cf12a98444d8fb830eb4b528925430c989759. The pre-existing user session edit is byte-identical. All 28242 pre-existing tracked/result files match the initial snapshot. No pre-existing source, configuration, manifest or evidence file was modified. Candidate 1 and Candidate 2 historical hash verification passes.
- Historical gate: all 396 Candidate 2 validation cases replayed before final implementation; raw, summary and comparison metrics reproduced. No-origin-discount: 262 detected, 202 correct first origins, 60 UNKNOWN, zero wrong origins.
- Correction disclosed: the first campaign attempt used illegal injector settings and stopped after 16 completed runs. Its complete available artifacts remain under validation/invalid_attempt_01. Only invalid case-definition settings were corrected, before outcome metrics were inspected; fresh onset times prevent reuse. Detector and baseline parameters were unchanged. The unchanged C configuration validator accepted every corrected case before registration and execution.
- Confirmation: 900 unique corrected configurations (720 faults, 180 benign, 144 per origin). Zero exact physical overlap with Candidate 1/2 development, the excluded partial attempt or within this cohort. Seeds are recorded, but these deterministic injectors do not establish independent random replication. The entire registered valid cohort completed.
- Final result: 606/720 detected, 0/180 benign alarms, 511/547 plant-propagating faults detected, 36 silent plant cases. 462/606 first alarms localized, all correctly; 144 first-alarm UNKNOWN, 248 runs with any CONFIRMED+UNKNOWN step. Full traces contain no wrong localized steps. Weighted Sum has exactly the same binary detection outcomes and lower P95 latency (200 vs 300 ms).
- Identifiability: zero mixed-origin exact full allowed-observation histories; three mixed-origin full extracted-evidence histories. No empirical full-raw sensor/communication collision was found. The inherited composite origin map structurally abstains on SENSOR_CONTROL. Do not confuse feature-map information loss with universal non-identifiability of the raw observables.
- Statistical summaries include nominal Wilson intervals and exploratory paired outcomes. Designed related cases are correlated; no population safety guarantee or final-paper significance claim is made.
- Mathematical freeze: the reference algorithm, mappings, eight copied parameters, protocol, study, machine configuration and contract were hashed before optimization. Origin discount and propagation decision modulation are removed; diagnostic graph metadata cannot feed back into scientific decisions.
- Exact optimization: all 900 archived allowlisted observation streams (1,080,900 samples) replayed through both implementations. Entire persistent detector state bit-identical, zero tolerance and zero decision/timestamp discrepancies. Sparse products preserve floating-point accumulation order; logical cardinalities are cached. Generic dense/sparse/aliasing/total-conflict math checks pass.
- Complete suite: 258 tests PASS. New tests cover hidden-label independence, frame separation, vacuous evidence, temporal accumulation, recovery, strict persistence/margins, diagnostic independence, CSV bit-exact round trips, configuration legality, all cohort identities, paired counts and full equivalence.
- Build: original make and additive optimized build PASS. Python compile PASS. git diff --check PASS. No staged changes.
- Accepted regression: 48 legacy cases, 64 RTL cases and eight v5 representative replays PASS. Accepted lock verifies 141 source/config entries and 5866 evidence entries; v1–v6, HETIA, Hybrid, timing and HT1–HT4 remain unchanged.
- Desktop: 18 final-candidate checks and 181 unchanged legacy desktop checks PASS. New launcher preserves Hybrid default and historical views; live C examples and CONFIRMED+UNKNOWN work. Session/history/export writes are isolated. Display access required approved sandbox escalation. No GUI callback errors.
- Host benchmark: 31 measured interleaved repetitions per mode and scenario after three warmup cycles. Final optimized median overhead vs legacy is 166.98% benign / 145.85% timing; observed improvement vs reference only 1.12% / 0.65%. Raw samples, mean/std/P95, state and section sizes retained. Logging precision differs from historical implementations and is included in end-to-end cost. No embedded WCET, real-time deployment or broad lightweight claim.
- PNG/PDF development-confirmation plots and candid findings retained. Presentation label placement was corrected after visual review; this changed no scientific results.

Scientific pre-optimization identity: clo_dsf_final_scientific_hashes.json.
Complete accepted implementation/dependency/artifact identity: clo_dsf_final_hashes.json.
The complete manifest covers all v7.2 evidence (including the invalid partial attempt), builds, source/configuration/test/report/GUI dependencies and the immutable scientific contract. It excludes only itself, generated Python caches and compiler object/dependency intermediates. Executable identities are included; rebuilding with another compiler may change their byte hashes and requires independent equivalence validation.

Verify without writing: `python3 scripts/package_clo_dsf_final.py --verify`.
Build: `make -f clo_dsf_final_optimized.mk`.
GUI: `python3 scripts/virtual_ecu_final_gui.py`.

Final git status is retained in validation/final_git_status.txt. The single tracked modification is the user's unchanged pre-existing presets/gui_session_state.json edit; all v7.2 additions remain unstaged. No git add, commit, push, reset, restore, checkout or clean was run.
