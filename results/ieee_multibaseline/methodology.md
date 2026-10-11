# Method and evidence scope

**CLOVER-ECU** is the publication name of the unchanged refined A2 architecture. Existing identifiers, source hashes, final-result names and the frozen SVM-INT model remain unchanged.

## Evidence separation

| Evidence | Role | What must not be inferred |
|---|---|---|
| `digital_integrity_development` TRAIN/CAL | Authorized fitting/operating-point selection for new baselines; original SVM training provenance | Not new independent test performance |
| Historical `comparative_benchmark` | Earlier architecture/backend context | Its SVM, features and false alarms are not frozen SVM-INT |
| `integrity_final_unseen` | Already frozen primary result, left untouched | Its per-case summaries cannot support new framewise replay |
| `frozen_robustness` | Separate fixed-profile stress evaluation, left untouched | Not additional independent primary test cases |
| This `ieee_multibaseline` cohort | One new locked secondary comparative evaluation | Not a replacement primary unseen result or new physical fault space |
| Original Triplex A0 in this cohort | Same-case architecture ablation | Not equal-observability evidence-fusion competition |

## Runtime input audit

The frozen `run_digital_integrity.features` extractor supplies 41 features:

| Columns (zero-based) | Input | Provenance |
|---|---|---|
| 0–5 | Six masked provider strengths | Frozen runtime providers, including M2 and integrity-enriched sensor evidence |
| 6–11 | Provider availability flags | Runtime validity, not fault labels |
| 12–17 | Ten-frame causal means | Available past/current provider samples only |
| 18–23 | Ten-frame causal maxima | Past/current provider samples only |
| 24–26 | Primary–C, reference–C residuals; alignment/qualification flag | Independent acquired values and runtime validity |
| 27–34 | Primary/reference/C values; load, pump/fan commands, speed, Triplex evidence | Runtime input/command and sensing fields |
| 35–40 | Integrity availability mask, bad-channel mask, three status fields and held violation evidence | Protected-record verifier output |

The source CSV also contains diagnostic alarm/origin fields and probe counts, but these are **excluded** by the feature slices. None of the learned classifiers receives CLOVER's final decision. Injected origin, activation interval and plant propagation labels enter only training targets or offline scoring. Classical fusion/sequential methods consume the six strengths and availability (and existing origin-subset provenance for OR/WS/DS localization). No integrity channel is counted twice as independent evidence. SVM, LR and RF use the same 41-feature representation. Availability of the same providers is not identical feature usage: this is explicitly a comparison on engineered runtime evidence, not a proof of backend independence from provider design.

## Reporting conventions

- New model fitting uses the original authorized TRAIN/CAL configuration identities, not validation/unseen/robustness identities. Retrieving those streams is training-data reconstruction, not rerunning a held-out benchmark.
- The SVM operating point remains frozen even if a newly calibrated classifier obtains different results. OR and Plain DS remain fixed; other new baselines are CAL-selected as preregistered.
- Binary-only methods have localization **N/A**, not zero accuracy and not synthetic origin attribution. OR/WS/DS use their pre-existing conventional origin rules; CLOVER retains causal precedence. First localization is conditional on detection; runtime localized accuracy excludes UNKNOWN, whose rate is separately reported.
- Precision is run-level detected faults / (detected faults + benign alarm runs), dependent on the cohort prevalence. Detection is the established post-onset rising-edge metric; latency is conditional on detection.
- Exact McNemar tables include ties and both-missed cases; Holm adjustment covers eight primary algorithm comparisons per endpoint. The A0 architecture comparison is separately marked. These are descriptive simulator results, not field reliability estimates.
- Computational measurements are host batch inference, without common evidence generation or feature construction. They include Python/library overhead and conventional origin rules where provided. Native A0/CLOVER final-core cost is unavailable from the unchanged adapter. No speed, embedded WCET or energy superiority is claimed.
- No coverage is established for physical pre-protection sensor failures, consistent data+witness compromise or idle mechanical actuator-health telemetry absent from the simulator.
