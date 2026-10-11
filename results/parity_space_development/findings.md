# Multiscale parity-space findings

Retained architecture: MEMORY. Parity promotion: False.
Gate: {"gain_ge_1pp": true, "no_parity_losses": true, "benign_le_01": false, "zero_wrong_fault_origins": true, "plant_ge_98": false, "localization_preserved": false, "startup_preserved": true, "MEMORY_preserved": true, "TIMING_preserved": true, "COMMUNICATION_preserved": true}.

| Method | Detection | Wilson95% | Benign | Plant | Precision | Median/P95 ms |
|---|---|---|---|---|---|---|
| A0 | 998/1200 | 80.94–85.18% | 5/300 | 572/641 | 0.99501 | 0.0/1000.0 |
| A1 | 1020/1200 | 82.87–86.91% | 6/300 | 581/641 | 0.99415 | 0.0/2520.299999999997 |
| A2 | 1016/1200 | 82.52–86.59% | 5/300 | 572/641 | 0.99510 | 0.0/400.0 |
| A3 | 1038/1200 | 84.45–88.32% | 6/300 | 581/641 | 0.99425 | 0.0/2032.499999999987 |
| SVM-R default | 1080/1200 | 88.17–91.57% | 89/300 | 631/641 | 0.92387 | 0.0/400.0 |
| SVM-R matched | 44/1200 | 2.74–4.89% | 5/300 | 7/641 | 0.89796 | 183.0/1010.0000000000009 |
| SVM-P default | 1103/1200 | 90.24–93.33% | 166/300 | 631/641 | 0.86919 | 0.0/685.2999999999568 |
| SVM-P matched | 73/1200 | 4.87–7.58% | 2/300 | 32/641 | 0.97333 | 3783.0/23723.39999999999 |

Parity incremental A1 vsA0: 22; A3 vsA2: 22. Parity losses: {'A1_vs_A0': [], 'A3_vs_A0': [], 'A3_vs_A2': []}. Memory: [{"comparison": "A2_vs_A0", "group": "effective", "cases": 162, "before": 162, "after": 162, "gained": 0, "lost": 0, "benign_alarm_delta": 0}, {"comparison": "A2_vs_A0", "group": "dormant", "cases": 78, "before": 55, "after": 73, "gained": 18, "lost": 0, "benign_alarm_delta": 0}, {"comparison": "A3_vs_A1", "group": "effective", "cases": 162, "before": 162, "after": 162, "gained": 0, "lost": 0, "benign_alarm_delta": 0}, {"comparison": "A3_vs_A1", "group": "dormant", "cases": 78, "before": 55, "after": 73, "gained": 18, "lost": 0, "benign_alarm_delta": 0}].

Winning windows: {8: 22}; directions: {'nondirectional': 8, 'C/AB ambiguous': 14}. C/AB squared scores are identical; no faulty-member claims. Global equal common mode is unobservable to parity; any detected global case requires separate physical runtime evidence or a timing/alignment transient and is not proof of absolute common-mode observability.

All eight methods share physical cases. SVM receives cross-layer observations including250ms memory and raw parity; SVM-P also receives every parity statistic. Statistical and fault-origin uncertainty are preserved. UNKNOWN is not correct first-detection localization; wrong-origin promotion gate counts FAULT runs, while all-runtime and benign origin samples are also reported.

Window attribution (active means nonzero new parity strength): [{"method": "A1", "subgroup": "weak_steps", "window_and_parity_active": {"(8, True)": 22, "(2, False)": 15, "(8, False)": 1}}, {"method": "A1", "subgroup": "strong_steps", "window_and_parity_active": {"(8, False)": 7, "(2, True)": 17, "(2, False)": 4, "(1, False)": 2}}, {"method": "A1", "subgroup": "short_pulses", "window_and_parity_active": {"(2, False)": 2, "(8, False)": 1, "(1, False)": 1}}, {"method": "A1", "subgroup": "long_pulses", "window_and_parity_active": {"(2, False)": 22, "(8, False)": 4}}, {"method": "A1", "subgroup": "slow_drift", "window_and_parity_active": {"(8, False)": 9, "(8, True)": 39}}, {"method": "A3", "subgroup": "weak_steps", "window_and_parity_active": {"(8, True)": 22, "(2, False)": 15, "(8, False)": 1}}, {"method": "A3", "subgroup": "strong_steps", "window_and_parity_active": {"(8, False)": 7, "(2, True)": 17, "(2, False)": 4, "(1, False)": 2}}, {"method": "A3", "subgroup": "short_pulses", "window_and_parity_active": {"(2, False)": 2, "(8, False)": 1, "(1, False)": 1}}, {"method": "A3", "subgroup": "long_pulses", "window_and_parity_active": {"(2, False)": 22, "(8, False)": 4}}, {"method": "A3", "subgroup": "slow_drift", "window_and_parity_active": {"(8, False)": 9, "(8, True)": 39}}].

TRAIN/CAL/VALID performance is in validation_summary.csv; subgroup_summary.csv separates nearby amplitudes and fault families through subgroup definitions. Detailed amplitude/phase/duration/channel/benign-regime audits are embedded in thresholds.json. No tuning after validation. CIs/McNemar are descriptive for grouped deterministic campaigns; no statistical-method novelty claim. Regression and integrity results are recorded in calibration_record.md.

Final decision: parity rejected. A1/A3 benign alarms are6/300=2%, above the immutable1% ceiling; A0/A2 already have5/300=1.67%. A3 plant detection is581/641=90.64%, below98%. The preregistered first-localization preservation gate also fails:980/1038=94.41%, versus998/998 forA0. This stricter gate counts UNKNOWN as not correct; confident localization among FAULT alarm samples remains100%. All20 wrong confident runtime samples are on five benign runs, shared withA0; no FAULT run/sample has a wrong confident origin. There is no new startup failure or detected numerical instability.

The independent unchanged250ms memory extension is retained as the development selection A2: effective memory162/162 unchanged; dormant memory55/78 to73/78, +18 with no loss, no new benign alarm and no wrong confident fault origin. This does not qualify the overall architecture for unseen: A2 still has5/300benign alarms and572/641plant detection. Production Triplex source and controller remain unchanged; no parity provider is enabled there. The memory choice is independently reproducible from the registered A2 harness and existing multirate_memory.c.

A3 has40additional detections vsA0:22parity weak-step gains plus18memory gains. Parity adds no short-pulse,long-pulse,slow-drift,A-only or global common-mode detections. Gains are B8,C5,AB9; all22 useW8 and are UNKNOWN at first detection. Fourteen have tied C/AB maxima; eight lack sufficient directional separation. These are uncertainty-preserving anomaly detections, not new sensor-member localization. Another36 already-detected cases first alarm earlier with UNKNOWN. Runtime UNKNOWN rises to48434/348825=13.88% forA3. Parity-specific first-alarm/window records are in parity_gain_cases.csv.

Nearby-amplitude development checks show TRAIN gains at+.43 as well as signed.49, and CAL gains at+.46/+.52 as well as signed.49. All three unseen validation activation phases have gains. The result is therefore not confined to exactly+.49, but it is narrow in fault shape/channel: sustained weak steps on B/C/AB, with no pulse or A-only gain. Generalization of that sensitivity does not establish acceptable benign behavior.

The added benign alarm isparity_5084: legal-.32C reference excursion lasting1100ms. At31800ms, W8 G=162.374656 and parity strength=.25 caused an UNKNOWN alarm. This directly illustrates overlap with allowed persistent disagreement. It was retained in the denominator; no post-validation threshold change occurred.

SVM-P default wins raw detection1103/1200 versusA3 1038/1200, with65SVM-only and0A3-only cases (exact McNemar5.421e-20, descriptive). Its benign rate is166/300=55.33%. The frozen SVM-P matched operating point detects73/1200 with2/300benign alarms. A3 has965more detections (+80.42pp) than this operating point, but A3 violates the1% budget, so this is NOT matched-low-FPR superiority. SVM-R matched also exceeds its calibration target on validation(5/300). Among the compared fixed methods with actual validation benign<=1%, only SVM-P matched qualifies. No architecture simultaneously meets the requested detection, benign and plant-safety targets.

Full regression passed:348tests, build, Python compile, git diff --check,48legacy,64RTL, Triplex symmetry, Sensor-C independence, qualification/numerical/forbidden-input/UNKNOWN tests. Protected historical evidence and GUI unchanged. No final unseen, commit or push. Ready for new unseen: NO.
