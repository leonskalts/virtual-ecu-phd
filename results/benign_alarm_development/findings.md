# Benign-alarm elimination findings

Retained development refinement: True; selected G2 using NEW TRAIN/CAL only. Gates: {'benign_le_005': True, 'no_plant_losses': True, 'no_wrong_fault_origins': True, 'no_integrity_losses': True, 'loss_le_0025': True}.

| Method | Fault detection | Benign | Plant detection | Precision | Median/P95 ms |
|---|---|---|---|---|---|
| A2 original | 1124/1200 | 49/2400 | 641/641 | 0.9582267689684569 | 0.0/131.0 |
| Refined | 1124/1200 | 0/2400 | 641/641 | 1.0 | 0.0/131.0 |
| SVM-INT default | 1124/1200 | 0/2400 | 641/641 | 1.0 | 0.0/131.0 |
| SVM-INT CAL1 | 1124/1200 | 0/2400 | 641/641 | 1.0 | 0.0/131.0 |

Detections lost: []; gained: []; benign removed: 49; new benign: 0; remaining: [].
Historical55: all witnessPASS and no other-layer evidence.42 had AB_FAST,20Triplex,7overlap. Strength1 bursts lasted1–2consecutive qualified samples; DS carry-over produced4–9alarm samples.53legal_offset cases plus2authorized_update cases. Weak slew<=.100434 accompanied5; no trajectory-response or slow-redundant contribution at alarms. No correctly detected historical fault depended exclusively on PASS-only legacy evidence;52sensor fault runs had eligible recovery-tail samples.1255historical reconstructions matched original A2 detection/alarm/localization metrics exactly. These old cases did NOT select the refinement.
The gate verifies complete PASS and absence of any other evidence/current retained direct-origin provenance. IntegrityFAIL or unavailable witness bypasses; all non-sensor layers bypass. DS mass, combination, thresholds, Triplex, M2, integrity provider and causal origins are unchanged. Final confirmation is a runtime provenance rule, not an injected-label classifier. Frozen SVM41features/scaler/model and both previous thresholds are untouched.
Per-origin changes, first/runtime localization, UNKNOWN and benign origins are separate tables. This is development validation; no unseen. No claim of preserved sensitivity to unmodeled pre-protection physical faults: a genuine PASS-only sensor anomaly can incur extra confirmation delay or be missed if too brief. Current post-conversion faults with witnessFAIL are never suppressed.
Benign diversity includes legal offsets/calibrations, independent noise/quantization and thermal/load/speed changes. Groups/configurations/profiles/seeds are disjoint, but this remains shared simulator-family development evidence, not a field false-alarm guarantee.
