# Final unseen redundant CLO-DSF findings

Exact scientific implementation: `e8126d9f3da261a210f1d16c83d4af57245036e2`. One1500-case campaign (1200 faults/300 benign),240 faults per origin. Protocol and configurations frozen before outcomes; zero exact overlap with all recovered historical campaign identities. No tuning, exclusions, replacement cases or second evaluation.

**Detection: 1080/1200 (90.00%), Wilson95% 88.17–91.57%.** Desired >90% was not observed; this is the final result regardless. Intervals are descriptive at case level and do not correct for correlated operating families.

| Method | Detection | Silent plant | Benign alarms | Median/P95(s) |
|---|---:|---:|---:|---:|
| Hybrid | 808/1200 | 171/756 | 210/300 | 14.6/30.62499999999999 |
| Plain DS | 868/1200 | 155/756 | 150/300 | 0.2/21.964999999999996 |
| Pre-change CLO-DSF | 977/1200 | 83/756 | 0/300 | 0.0/0.6199999999999932 |
| Revised CLO-DSF | 1080/1200 | 51/756 | 1/300 | 0.0/14.134999999999968 |
| Simple OR | 884/1200 | 140/756 | 150/300 | 0.15/21.884999999999994 |
| Timing Monitor | 240/240 | 0/157 | 0/0 | 0.05/0.1 |
| Weighted Sum | 922/1200 | 104/756 | 150/300 | 0.1/21.79499999999999 |

Timing Monitor is restricted to240 timing cases. Every other method observes the identical1500 simulations. Pre-redundancy is the committed67bcc337 active-memory core. Frozen baselines do not gain the newly engineered reference evidence. Comparison therefore includes added observability; it is not a controlled comparison of fusion rules alone.

| CURRENT subgroup | Detection |
|---|---:|
| MEMORY | 235/240 |
| TIMING | 240/240 |
| COMMUNICATION | 240/240 |
| SENSOR_CONTROL | 138/240 |
| ACTUATOR | 227/240 |
| primary/sensor_bias_ramp | 20/30 |
| primary/sensor_bias | 30/40 |
| primary/sensor_interface_intermittent | 20/30 |
| reference/sensor_bias_ramp | 20/30 |
| reference/sensor_bias | 28/40 |
| reference/sensor_interface_intermittent | 20/30 |
| common_mode/sensor_bias_ramp | 0/40 |
| effective_memory | 163/163 |
| dormant_memory | 72/77 |
| legal-update benign alarms | 0/150 |

Plant-propagating detection705/756; silent51; pre/same/post-plant649/30/26. Precision0.999075; recall0.900000. Latency includes detected faults only; misses are not assigned zero latency. Reference-only sensor faults do not affect control and can be detectable without plant propagation.

## Localization

First-detection correct1080/1080 localized (1080 detections). All-alarm runtime coverage387881/390679; correct387877/387881; UNKNOWN2798/390679. Wrong confident origins across all cases:1 runs/4 samples. Fault-only wrong origins:0 runs/0 samples. Benign localized alarms are false diagnoses, and are not hidden by reporting only fault localization. Sensor-member attribution remains unresolved; SENSOR_CONTROL is a broad origin.

## Paired comparison

{'group': 'ALL', 'both': 863, 'only_clo': 217, 'only_weighted_sum': 59, 'neither': 61, 'mcnemar_exact_two_sided_p': 2.082075981973603e-22, 'discordant': 276, 'clo_faster': 287, 'same_latency': 546, 'clo_slower': 30}

Exact McNemar is an exploratory paired case-level result; operating families are correlated. Frozen Weighted Sum retains its nominal-calibration assumption and may alarm on authorized target updates. Some post-onset baseline detections can therefore be incidental. Higher paired coverage alone does not establish universal superiority or isolate a DS advantage.

## Post-hoc limitations

The sensor allocation deliberately includes small/short signals below the documented amplitude/persistence envelope, both sensor chains, multiple unseen drift rates and40 common-mode cases. Full sensitivity rows are reported without changing denominators. Identical common-mode drift cannot be diagnosed through disagreement alone. Slow detection latency reflects the unchanged32s accumulation and when residual becomes observable. The physical independent/co-located sensor and bounded-noise assumptions still require hardware qualification.

Miss counts by origin/chain/model:
```json
{
  "MEMORY/none/stuck_bit": 5,
  "SENSOR_CONTROL/primary/sensor_bias_ramp": 10,
  "SENSOR_CONTROL/primary/sensor_bias": 10,
  "SENSOR_CONTROL/primary/sensor_interface_intermittent": 10,
  "SENSOR_CONTROL/reference/sensor_bias_ramp": 10,
  "SENSOR_CONTROL/reference/sensor_bias": 12,
  "SENSOR_CONTROL/reference/sensor_interface_intermittent": 10,
  "SENSOR_CONTROL/common_mode/sensor_bias_ramp": 40,
  "ACTUATOR/none/pump_degraded": 13
}
```

Benign alarm cases (all retained, no exclusions):
```json
[
  {
    "run_id": "final_redundant_1469",
    "sensor_variation": "0.033:1.1:16300",
    "reference_noise": 0.085,
    "reference_offset": -0.117,
    "benign_reference_magnitude": 0.75,
    "benign_reference_duration": 100,
    "first_alarm_ms": 19900,
    "alarm_samples": 4,
    "wrong_localized_runtime_samples": 4
  }
]
```

These post-hoc findings were never passed to detector inference and caused no scientific source/configuration changes. No parameter selection or holdout repeat is authorized by these results.

### Specific final limitations

All five memory misses were dormant intermittent stuck faults:800ms ON/1200ms OFF windows never coincided with a1000ms diagnostic probe. The registered schedules yield zero active-probe opportunities for these cases. Effective corruption remains163/163; dormant coverage72/77. This exposes a diagnostic sampling-phase limit; no probe period was changed.

All13 actuator misses had zero observed actuator/plant effect and no positive runtime feature in the recorded summary. They remain in the detection denominator; no hidden-truth alarm was added.

The one benign false alarm was final_redundant_1469: a legal+0.75C reference excursion lasting100ms, combined with independent noise and benign primary variation. Excursion start19700ms; first alarm19900ms. Four alarm samples confidently named SENSOR_CONTROL. This demonstrates that the FAST channel does not universally reject isolated benign excursions across noise phases. No rerun or repair was performed. Fault-only causal localization remained0 wrong runs/0 samples; all-case counts deliberately include this false diagnosis.

Primary and reference slow drift each detected20/30: all1.65/2.75C cases and no0.85C cases. FAST-related abrupt coverage improved primary35/70 to50/70 and reference0/70 to48/70. Thus both channels show benefit on new configurations, with retained sensitivity limits and a measured false-alarm cost. The gain must not be described as complete generalization of development100% sensor coverage.

The paired counts favor CURRENT over frozen Weighted Sum on these cases (+217/-59), but do not isolate a fusion-rule advantage; calibration-update false alarms and unequal evidence access remain confounds. Runtime-sample Wilson intervals also do not imply independent temporal samples.

**Final interpretation:** exactly90.00% is not >90%; that desired outcome did not generalize. The result is usable as final manuscript evidence, including the negative findings, not as support for an above90% claim or deployment qualification.

Regression and integrity: PASS (325 tests,48 legacy,64 RTL,build/compile/diff); scientific hashes unchanged; GUI, Hybrid/HETIA and CURRENT development evidence preserved. No commit/push.
