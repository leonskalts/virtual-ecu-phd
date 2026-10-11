# Digital integrity development findings

Promotion gates: {'gain_ge_2pp': True, 'no_losses': True, 'zero_wrong_fault_origins': True, 'incremental_integrity_benign_le_005': True, 'plant_not_worse': True}; retained development candidate: A2. Strong raw SVM success: False.

| Method | Fault detections | Benign | Plant | Precision | Median/P95 ms |
|---|---|---|---|---|---|
| A0 | 1014/1200 | 55/1200 | 583/639 | 0.9485500467726847 | 0.0/900.0 |
| A1 | 1103/1200 | 55/1200 | 639/639 | 0.9525043177892919 | 0.0/300.0 |
| A2 | 1125/1200 | 55/1200 | 639/639 | 0.9533898305084746 | 0.0/178.0 |
| SVM-INT default | 1125/1200 | 0/1200 | 639/639 | 1.0 | 0.0/178.0 |
| SVM-INT CAL1 | 1125/1200 | 0/1200 | 639/639 | 1.0 | 0.0/178.0 |

Prior90: {'integrity_observable': 82, 'A0': 0, 'A1': 82, 'A2': 82, 'unsampled': 8, 'svm_default': 82, 'svm_only': 0, 'both_missed': 8}. Original detections lost: 0. Incremental integrity benign runs: 0.
The witness is a simulated isolated acquisition driver mailbox. In ordinary unisolated C memory it has no guaranteed independent fault containment. No plant temperature, sensor model internals, labels or fault timing enters its checks. Channel values and producer timestamps are the protected payload. Legitimate reference calibration and primary sensor variation update the protected value through explicit authorized transformations, never by resealing consumer data.
Value-only corruption, replay, valid recomputed data tag, and witness-tag upset have executable boundary tests. Consistent data+witness corruption and pre-protection error intentionally pass: no coverage claim. Simultaneous ABC value mutation in the original campaign does not mutate the isolated witness; this is digital integrity coverage, not physical common-mode sensor coverage. Unsampled pulses have no sample to authenticate.
SVM has the same integrity flags/status, cross-layer/M2 evidence, sensor values and context. Default and CAL-selected empirical1% operating points are separate; report actual VALID false alarms. Binary SVM does not localize. No validation tuning or unseen execution. Only TRAIN/CAL selected comparator; integrity mapping fixed before outcomes.
Original detector thresholds, DS algebra, Triplex sensing, controller/plant and injection semantics unchanged. Development-only adapter; no production default silently enabled.
