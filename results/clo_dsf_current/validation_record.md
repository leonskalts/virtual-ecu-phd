# CURRENT development validation record

Registered before outcomes: 2026-09-20T12:54:38.683403+00:00

738 unique simulations; 492 TRAIN / 246 VALIDATION, disjoint operating families. All public C configurations validated. Zero profile/configuration overlap with previous development and holdout. No tuning or parameter search. Same physics stream for every observer. No accumulator selected: replay found no sustained bias discrepancy. Detector bytes identical to pre-change. Benign alternating jitter up to 0.10 C and triangular drift up to 1.2 C; no transport faults combined with variation. Temporary pre-change CURRENT core SHA256 cc5b709489580e4b77a023ccc1f908a711525b3b4bcb3d09e43717941cd4f6f7.

Protocol: [current runtime evidence](../../docs/clo_dsf_current.md).

Pre-execution identities:
```json
{
  "src/v7_3/clo_dsf_revised.c": "cc5b709489580e4b77a023ccc1f908a711525b3b4bcb3d09e43717941cd4f6f7",
  "src/v7_3/revised_runtime.c": "df14b1f2e0d188deb245b87fb89bee7ef8125ad8e2ee9113e0706ebb3251f23d",
  "src/sensors.c": "f19e601d68976a563a5edb031d76ca259689b32bef04958a81f6bd4a8947a352",
  "src/control.c": "39be6119817829cee8f068d2fc3fc74aa38a6c9f08bb98b94112c5dc8af6536a",
  "src/runtime_observation.c": "34690aa9b53e2257515890d1d2847c37ba24c1efb2188bade51c4a2a95877bc3",
  "include/runtime_observation.h": "ccd0f0bc1e5a7e1076645e395b3f6edc953d587ab477b0f31fb7638b81cf4293",
  "include/ecu_types.h": "c116b0f0e2831ea2f137b8ddaca48f112a8a105886d78517881b20e0a252da97",
  "include/clo_dsf_revised.h": "087f7bccf2ba3b4e25072bc06079005ab0b09571435e65a4e0366b7f992ce0d4",
  "results/cross_layer_safety_v7_3_dev/revised.cfg": "6f62e972a27c765cae6a24daf9b7b98fb1513cd46fc226a128d87a6431e73ac7",
  "python/virtual_ecu/clo_dsf_current.py": "4977a0134c15cc5502754d89cffa59317d03e215e8b0c2fa3a30bde9537ac91e",
  "results/clo_dsf_current/configuration_manifest.csv": "79b93c6d0da142eadbfe30f7779fd5b3214428eb79884c56ca41a66f5b6c82fe"
}
```

Pre-change CURRENT reconstruction patch (apply to the recorded current source in temporary storage; no maintained duplicate):
```diff
```

TRAIN gate PASS: unchanged detector preserves detections; no benign alarm, wrong origin, effective-memory miss or dormant alarm. Proceed with unchanged settings.

development-train: 492 simulations complete; no source/config change or tuning.

development-validation: 246 simulations complete; no source/config change or tuning.

## Final regression and preservation

Build PASS; Python compile PASS; git diff --check PASS; full tests **300/300**; legacy **48/48**; RTL **64/64**. Hybrid/HETIA source and historical evidence unchanged. Generated historical executables restored to verified pre-execution Git bytes. No commit/push.

All 738 paired CURRENT/pre-change rows are identical in every field except method name. Core and configuration retained unchanged; no improved detector is claimed. Eight prior weak misses remain documented, with eight corresponding misses in new validation. No unseen validation ran.

Protected SHA256 identities (all equal pre-execution):
```json
{
  "presets/gui_session_state.json": "3fdf2d807ea8661def7e447ff32be0ccf46d70e160e28390bff81aeffbab957a",
  "src/v7_3/clo_dsf_revised.c": "cc5b709489580e4b77a023ccc1f908a711525b3b4bcb3d09e43717941cd4f6f7",
  "include/clo_dsf_revised.h": "087f7bccf2ba3b4e25072bc06079005ab0b09571435e65a4e0366b7f992ce0d4",
  "src/control.c": "39be6119817829cee8f068d2fc3fc74aa38a6c9f08bb98b94112c5dc8af6536a",
  "src/sensors.c": "f19e601d68976a563a5edb031d76ca259689b32bef04958a81f6bd4a8947a352",
  "src/runtime_observation.c": "34690aa9b53e2257515890d1d2847c37ba24c1efb2188bade51c4a2a95877bc3",
  "src/detection_algorithm.c": "c4a024feb6eabc6d62bb6a4483d504cc39c3efa8fa64baf16c7c1fec13a7804d",
  "src/safety_monitor.c": "27412e114cd0cd22132b1a5b24e7a14e5c937df4ade5ac3f1b6029c6aec2fe4d",
  "src/timing_safety_monitor.c": "ffd160ccb9025ec9a03ea3526b0fdfe6450382005f7a41d81aa0d78c950e1b88",
  "src/cross_layer_fault.c": "5e3a807d89598615aa93cc9c3849eb6f8c4a44b1f25c4e56d6672ff5deb8e01f",
  "src/fault_injection.c": "52553d6d5b3e5f1d461dd52cf19be14941481581f1eb4613710dd0cee207d992",
  "src/sensor_delivery.c": "f3ea17440e15513808e77f3c8f41849da31f3504ea6441bca85b5c963e037d76",
  "results/cross_layer_safety_v7_3_dev/revised.cfg": "6f62e972a27c765cae6a24daf9b7b98fb1513cd46fc226a128d87a6431e73ac7"
}
```

Every initially tracked file outside the allowed adapter/makefile/current-binary changes matches its pre-execution hash, including existing GUI modifications. Eight compressed representative traces; no bulk trace archive.

Final git status:
```
 M clo_dsf_revised.mk
 M include/clo_dsf_revised.h
 M include/control.h
 M include/ecu_types.h
 M include/runtime_observation.h
 M presets/gui_session_state.json
 M src/control.c
 M src/runtime_observation.c
 M src/sensors.c
 M src/v7_3/clo_dsf_revised.c
 M src/v7_3/revised_runtime.c
 M tests/clo_revised_unit.c
 M tests/test_clo_dsf_candidate2.py
 M tests/test_clo_dsf_candidate2_development.py
 M tests/test_clo_dsf_final.py
 M tests/test_clo_dsf_final_confirmation.py
 M tests/test_clo_dsf_revised.py
 M virtual_ecu_v7_3
?? docs/clo_dsf_current.md
?? python/virtual_ecu/clo_dsf_current.py
?? python/virtual_ecu/clo_dsf_current_reporting.py
?? results/clo_dsf_current/
?? scripts/run_clo_dsf_current.py
?? tests/current_observation_unit.c
?? tests/historical_identity.py
?? tests/test_clo_dsf_current.py
```
