# Final unseen findings

**Execution finished; one per-method summary is missing. Not a complete paired 1500-case result.**

Commit 48315a665adb91b58be5b754c3bf2478be2fe105. All 1500 registered simulations executed once. No rerun, tuning, exclusion based on outcomes, or scientific modification. No commit/push.

The first run completed but an offline collector read probe fields from the wrong CSV and exited after raw cleanup. Its preselected original current trace survives: 1201 samples, no alarms, no register/shadow corruption and no failed probe. This establishes a current MEMORY miss and dormant phase-gap miss. It does not recover any baseline or counterfactual plant metric. All other1499 summaries are complete. The recovery collector corrected only offline field access and checkpointed each result before enrichment.

Full CURRENT detection uses1200 faults (including the trace-recovered miss); paired comparisons and plant metrics use1199 faults. Benign denominator300 is complete. No missing baseline result was imputed. Main detection_summary.csv preserves the comparable1499-case subset; full_current_detection_summary.csv supplies full CURRENT detection. execution_status.csv identifies the missing summary.

Historical audit:1808 sources,18504 distinct profile identities,18788 configuration identities; zero profile/configuration overlap with all recoverable historical campaigns. Previous final_unseen identity sets preserved before replacement. Unrecorded experiments cannot be audited.

Full CURRENT detection: 1054/1200 = 87.833333%; Wilson95 85.862039%–89.563175%.

| Origin | Detection |
|---|---:|
| MEMORY | 233/240 |
| TIMING | 240/240 |
| COMMUNICATION | 240/240 |
| SENSOR_CONTROL | 151/240 |
| ACTUATOR | 190/240 |

Effective memory 174/174; dormant 59/66; phase-gap misses 7. Legal-update alarms 0/150.

| Sensor subgroup | Detection |
|---|---:|
| primary_slow | 40/40 |
| reference_slow | 40/40 |
| common_mode | 0/40 |
| weak_steps | 34/60 |
| pulses | 37/60 |

| Actuator subgroup | Detection |
|---|---:|
| actuator_excited | 190/190 |
| actuator_unexcited | 0/50 |
| actuator_transient | 60/80 |
| actuator_intermittent | 60/80 |
| actuator_permanent | 70/80 |

Plant-propagating 709/760; silent 51 (first case plant status unavailable). Benign 0/300. Precision 1.0; full recall 0.8783333333333333. Median/P95 0.0/32939.99999999996 ms. Pre/same/post-plant 636/25/48. Pre-onset alarm runs 60.

First localization coverage 1054/1054; accuracy 1054/1054. Runtime localized accuracy 367109/367209; coverage 367209/369418; UNKNOWN 2209/369418. Wrong-origin runs/samples 60/100. Benign confident origins count as wrong in all-runtime statistics; sensor member attribution remains unknown.

| Method (complete paired subset) | Detection | Silent plant | Benign alarms | Median/P95 ms |
|---|---:|---:|---:|---:|
| Revised CLO-DSF | 1054/1199 | 51 | 0/300 | 0.0/32939.99999999996 |
| Pre-change CLO-DSF | 1046/1199 | 52 | 0/300 | 0.0/33100.0 |
| Weighted Sum | 900/1199 | 106 | 150/300 | 100.0/14404.999999999996 |
| Simple OR | 869/1199 | 137 | 150/300 | 100.0/14900.0 |
| Plain DS | 849/1199 | 157 | 150/300 | 100.0/14959.99999999999 |
| Hybrid | 775/1199 | 181 | 225/300 | 8100.0/16429.999999999996 |
| Timing Monitor | 240/240 | 0 | 0/0 | 50.0/100.0 |

Paired final vs WS (1199 faults): both 855, only final 199, only WS 45, neither 100; exact two-sided McNemar p=2.7162366408315494e-24. Both-detected latency final faster/same/slower 261/554/40. Missing first comparison is not inferred. Statistical evidence describes this deterministic campaign; incomplete paired recovery prevents a complete registered-evaluation claim.

Pre-refinement paired gains/losses: [{"group": "ALL", "both": 1042, "only_final": 12, "only_pre": 4, "neither": 141}, {"group": "MEMORY", "both": 223, "only_final": 10, "only_pre": 4, "neither": 2}, {"group": "SENSOR_CONTROL", "both": 149, "only_final": 2, "only_pre": 0, "neither": 89}, {"group": "weak_steps", "both": 32, "only_final": 2, "only_pre": 0, "neither": 26}, {"group": "pulses", "both": 37, "only_final": 0, "only_pre": 0, "neither": 23}]

All scientific, config, protocol and manifest hashes unchanged. Regression PASS:327 tests, build, Python compile, diff check,48 legacy,64 RTL. Hybrid/HETIA, all historical evidence outside authorized replacement, CURRENT results and GUI match task-start hashes. Eight compressed traces retained; no bulk raw run traces.

**Ready for manuscript: NO as a complete preregistered paired evaluation.** The partial evidence and instrument failure are documented; no additional holdout was run or authorized here.

## Interpretation and limits

Overall87.83% is below90%; no retuning occurred. The phase sweep shows a net gain of six on1199 comparable faults (ten memory gains, four memory losses); its coverage improvement is not monotonic. Seven full-campaign dormant probe-phase misses remain. FAST integration generalizes modestly to two additional weak steps, with zero lost sensor detections and no additional pulse detections. Independent primary/reference slow drift is40/40 each; common-mode remains0/40. Excited actuators190/190 contrast with unexcited0/50.

Causal localization is correct at first post-onset detection in1054/1054 cases, but the all-runtime zero-wrong-origin claim did not generalize. All60 wrong-origin runs are the registered cold-profile actuator cases (50 pump,10 fan), with100 SENSOR_CONTROL alarm samples. Those same runs contain100 pre-onset alarm samples, exactly matching per-run wrong counts. The preserved representative final_retained_0096 explicitly places its sensor-origin alarms at600/800ms, long before fault onset22700ms. This supports a startup/workload sensitivity concern, not an established later actuator-origin overwrite. Do not interpret the zero0/300 benign cohort result as proof of false-alarm immunity on cold profiles: that physical workload was included only in the actuator cohort. No matched benign cases were added after seeing this result.

Within the complete1199-fault paired subset, final detection1054 exceeds WS900 with199 vs45 discordances and a small exact McNemar p-value. This supports greater detection on that subset, alongside lower observed benign alarms and silent plant misses. It does not establish complete1500-case paired evidence or population-wide superiority. WS latency uses a different detected population; joint-detection latency counts are in paired_comparison.csv.

Final readiness: detector unchanged, regression passed; manuscript-ready complete evaluation NO because one baseline/plant summary is unavailable. The lower-than-target result and all sensitivity limits remain final, without rerun or tuning.
