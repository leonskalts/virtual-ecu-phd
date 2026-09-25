# Multi-timescale redundant-sensor development

One new development campaign: **1560 simulations**, TRAIN936 and VALIDATION624 (544 faults/80 benign), six/four disjoint operating families. No unseen holdout. All FAST parameters were fixed before TRAIN and locked unchanged for VALIDATION; no search/tuning was needed. The existing32s SLOW channel, other origins, physical sensor architecture and global thresholds remain unchanged.

## Validation ablation

| Method | Detection | Silent plant | Benign | Median/P95 |
|---|---:|---:|---:|---:|
| A0 retained redundant sensor | 468/544 (86.03%) | 20/347 | 0/80 | 0/47.4 s |
| FAST only | 439/544 (80.70%) | 57/347 | 0/80 | 0/0.51 s |
| SLOW only | 468/544 (86.03%) | 20/347 | 0/80 | 0/47.4 s |
| FAST+SLOW (A1) | 535/544 (98.35%) | 9/347 | 0/80 | 0.1/45.93 s |

**A0 and SLOW-only are identical aliases**, verified case-by-case, not independent experiments. FAST-only retains all inherited primary checks, other origins and reference conversion-failure status; only the slow averaging feature is removed. Every observer receives the same simulation stream.

Combined detection **98.35%**, Wilson95% **96.89–99.13%**. These descriptive case-level intervals do not model within-family dependence. All retained tests and cohorts are reported; none excluded to reach a target.

| Origin | Detection |
|---|---:|
| MEMORY | 80/80 |
| TIMING | 80/80 |
| COMMUNICATION | 80/80 |
| SENSOR_CONTROL | 215/224 |
| ACTUATOR | 80/80 |

## Sensor outcomes

| Chain/model | Detection | Median/P95 |
|---|---:|---:|
| primary/sensor_bias_ramp | 48/48 | 37.4/58.165 s |
| primary/sensor_bias | 31/32 | 0.1/0.1 s |
| primary/sensor_interface_intermittent | 24/24 | 0.2/0.3849999999999998 s |
| reference/sensor_bias_ramp | 48/48 | 36.55/60.9 s |
| reference/sensor_bias | 32/32 | 0.1/0.1 s |
| reference/sensor_interface_intermittent | 24/24 | 0.35/0.8849999999999998 s |
| reference/sensor_dropout | 8/8 | 0.0/0.0 s |
| common_mode/sensor_bias_ramp | 0/8 | NA/NA s |

FAST adds **67** validation detections and loses **0** relative toA0. On their 468 common detections it is faster in8, equal in460, slower in0. Both slow-drift chains remain48/48. Common-mode controls remain0/8 and are deliberately not targeted.

Plant-propagating detection338/347; silent misses9. Pre/same/post-plant detections247/39/52. Benign alarms0/80, including independent noise/calibration, legal triangles/updates, isolated +/-0.9C reference spikes and small300/900ms transients. Zero observed alarms is not proof of zero population risk (Wilson95% upper4.58%).

First-detection localization535/535. Runtime localized accuracy193409/193409; coverage193409/194487 (99.4457%); UNKNOWN1078 (0.5543%). Wrong origins0 runs/0 samples. Disagreement still identifies only SENSOR_CONTROL; sensor-member identity remains unresolved.

## Interpretation and limitations

FAST is a short-history contract provider. With d=primary-reference, bounded noise permits0.40C change and legal differential slew permits1.2C/s. It requires two persistent same-direction departures from the pre-event acquisition within300ms, or at least three excessive edges in1s. This rejects a single spike plus recovery while allowing recurring pulse evidence. Confirmed violations produce direct evidence1; this is an explicit metrology-contract decision, not a calibrated probability. The correlated features are max-merged in the original sensor mass and never multiplied as independent DS channels.

The 1.2C/s slope/noise contract must be qualified for real sensor placement, lag and wiring. Multiple large out-of-contract benign spikes may be observationally indistinguishable from faults; the campaign does not establish immunity to arbitrary burst noise. Simulated physical independence remains the previously documented assumption, and hidden plant truth/fault labels remain outside detector inference.

The overall P95 is still governed by slow drift. Adding fast-detected cases changes the latency population; an overall percentile decrease alone does not mean slow-drift detection accelerated. Consult paired common detections and separate abrupt/slow latency in latency_summary.csv. No slow-channel retuning or claim of common-mode observability is made.

The prior14/48 weak-step/pulse result and current campaign have different cohorts and denominators. The proper improvement comparison is A0 versusA1 on these exact new cases; do not interpret raw counts across campaigns as a paired result.

Retention follows preserved slow/other-origin capability, no lost A0 detections, robust primary/reference abrupt detection, lower silent plant misses and zero observed false/wrong-origin alarms. Eight physics-parity checks against the retained baseline yielded identical plant/control raw and summary CSVs. Extra persistent detector state64B (4208 to4272B), O(1) arithmetic per100ms acquisition; no extra sensor, dependency or physical hardware WCET claim.

## Final decision

**Retain FAST.** Validation overall535/544=98.35% (Wilson95%96.89–99.13%), SENSOR_CONTROL215/224=95.98%; both requested detection margins reached. Weak steps63/64 and pulses48/48, versus A0 abrupt44/112. Primary steps31/32, reference steps32/32. Effective memory59/59 and dormant21/21 preserved. Nine remaining misses: eight common-mode drifts and one -0.765C permanent primary offset (fast_redundant_1517), not adjusted after validation.

**Material overall latency goal not reached:** P9547.40s to45.93s is only3.10% lower on the same campaign; slow-only and combined slow-drift timings are identical. Eight common detections improve,460 are unchanged, none worsen. The earlier50s value came from a different campaign and is not the paired baseline.

Ready for ONE new unseen holdout within the explicitly documented independent-sensor/noise contract; no unseen data were run here. All regression checks passed:325 tests, build/compile/diff,48 legacy and64 RTL. Preserved GUI and Hybrid/HETIA; no commit/push.
