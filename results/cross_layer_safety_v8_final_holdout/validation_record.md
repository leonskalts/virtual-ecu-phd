# Final holdout validation record

Pre-outcome registration (immutable):
```json
{
  "frozen_manifest_sha256": "12f1d4253bc46608b6568ef95fc1d5821b829b829afdd21956d525fbddec8eaf",
  "outcomes_seen": false,
  "protocol_sha256": "60aa2e99234940eeb70dc7baec871d2d87df1c7237eba4d0a51d4f6d9d9445e3",
  "registered_utc": "2026-09-18T14:36:08.985670+00:00",
  "source_and_design_sha256": {
    "python/virtual_ecu/clo_dsf_holdout.py": "25ebafd477f27f1df4a997017931e06df8483a5d134b791e1d35b2198a2c3294",
    "python/virtual_ecu/clo_dsf_holdout_reporting.py": "587b20d69958c7cf01685e1967f94d520f2198375fe27e14c81691fd9bdd8c16",
    "results/cross_layer_safety_v8_final_holdout/configuration_overlap_audit.csv": "f02e5393d01f0dd3d25cd45c704f7211fc1828b28c43784f295f46d2c7ecac68",
    "results/cross_layer_safety_v8_final_holdout/final_holdout_manifest.csv": "883efd805752747cabd795452b758aa8b274ea472c317ba52e7c8361bd4a97c8",
    "scripts/run_clo_dsf_final_holdout.py": "343c48024d52e3f0bdda2ce04a6b800f1bd496d280da29630058adde14613102",
    "scripts/validate_clo_dsf_final_holdout.py": "cea15f198d40614b2b3971969a8964337a982ed7a0d96d2dce2a03dd87452a90",
    "tests/test_clo_dsf_holdout.py": "e3c46035b422d210cb3e83853bcad5b331d1aba961a91253f85dd62b9699ea97"
  }
}
```

Execution pending.

EXECUTION STOPPED at holdout_0000 after 0 completed cases: RuntimeError('holdout_0000 failed: Driving profile line 2: road_slope_percent must be in [-20, 20].\n'). No rerun or tuning.

Pre-outcome amendment registration (initial registration retained above):
```json
{
  "completed_simulations_before_amendment": 0,
  "frozen_manifest_sha256": "12f1d4253bc46608b6568ef95fc1d5821b829b829afdd21956d525fbddec8eaf",
  "outcomes_seen": false,
  "protocol_sha256": "866ae1b766a0e150ac2efcd90b3886493001770227ed6cff988658e499dffec2",
  "registered_utc": "2026-09-18T14:38:32.984785+00:00",
  "source_and_design_sha256": {
    "python/virtual_ecu/clo_dsf_holdout.py": "e3900214dbbeb2df5bfcf8e033e0798515321398f0adca4bf5fff1c9f86a8d69",
    "python/virtual_ecu/clo_dsf_holdout_reporting.py": "587b20d69958c7cf01685e1967f94d520f2198375fe27e14c81691fd9bdd8c16",
    "results/cross_layer_safety_v8_final_holdout/configuration_overlap_audit.csv": "f02e5393d01f0dd3d25cd45c704f7211fc1828b28c43784f295f46d2c7ecac68",
    "results/cross_layer_safety_v8_final_holdout/final_holdout_manifest.csv": "883efd805752747cabd795452b758aa8b274ea472c317ba52e7c8361bd4a97c8",
    "results/cross_layer_safety_v8_final_holdout/paper_tables/pre_outcome_registration_history.csv": "af69e95d6d37392828b7f5cd74bddd86380734110cc3bc5b0031feeafe95a0a6",
    "scripts/run_clo_dsf_final_holdout.py": "2c32ce0ae453896500dc644b67a9af330b487e858e6b02cbf6c084527e8505a0",
    "scripts/validate_clo_dsf_final_holdout.py": "66cdf58a14b3b435437633f35d3d7b66fab5034dff87fc4c4675f00cc13ea403",
    "tests/holdout_configuration_check.c": "d152c979bbfeb69f880d6a39a6dbcd651e7d6197fae2d54ea8808c7ce97a9867",
    "tests/test_clo_dsf_holdout.py": "f07045688399f1395aab3b4a7f9a3026c5a6f0b35d68afc90c3b12928674d491"
  }
}
```

All 1500 runtime executions completed. Registered identities and all 9494 frozen v7.3 identities verified after execution. Final regression pending.

## FINAL REGRESSION PASS

- PASS: 9494 frozen revision/dependency/artifact identities. No final holdout.
- Registered protocol, generator, reporting, validator, tests, manifest and overlap identities unchanged after evaluation. No scientific tuning or configuration changes.
- All 1,500 simulations completed once; 1,801,500 observations audited for normalized masses and agreement between trace alarms/origins and online metrics.
- Build PASS; Python compile PASS; git diff --check PASS; nothing staged. Full tests: 275 tests PASS.
- Legacy 48 and RTL 64 PASS. Accepted immutable lock: {"accepted_evidence_files": 5866, "baseline_commit": "0da05ccc7c20e9913194fcd2a718a7412f2a5f1a", "scientific_behavior_changed": false, "source_files": 141}. Hybrid/HETIA and all historical candidate sources/evidence unchanged.
- 21462 pre-existing tracked-file SHA256 identities unchanged, including the pre-existing user session edit. Initial status: M presets/gui_session_state.json.
- Temporary raw holdout/replay files discarded after checks; compact outputs, exact commands/profile manifests and artifact hashes retained. No screenshots or duplicate historical raw logs.
- Full tests/regressions were run once for this final pass. Focused new evaluator tests ran before holdout registration.
- Only reporting/evaluation support files and the new holdout result directory were added. No detector, threshold, mapping, temporal/localization rule, baseline or fault semantics changed.
- Ready for manuscript evidence with the simulator, family-dependence, nominal-interval and evidence-versus-fusion limitations stated in the findings. No production or hardware-transfer claim.
- No git add, commit, push, reset, restore, checkout or clean was run.

Final git status:
```
 M presets/gui_session_state.json
?? python/virtual_ecu/clo_dsf_holdout.py
?? python/virtual_ecu/clo_dsf_holdout_reporting.py
?? results/cross_layer_safety_v8_final_holdout/
?? scripts/run_clo_dsf_final_holdout.py
?? scripts/validate_clo_dsf_final_holdout.py
?? tests/holdout_configuration_check.c
?? tests/test_clo_dsf_holdout.py
```

## Final editorial audit

Paper figures visually checked for readable labels and matching counts. Findings
clarify the narrow pump-only gain, remaining short-delay communication blind spot,
the cross-fault versus fault/benign collision groups, and the disclosed zero-outcome
serialization amendment. These are interpretations of unchanged tables; no
registered source, protocol, detector, parameters or results changed after execution.
The historical verifier's literal "No final holdout" suffix describes the archived
v7.3 development freeze, not the current completed 1500-case holdout.
Raw/summary hashes include discarded temporary paths; path-independent input,
evidence and metric hashes plus commands identify scientific replay outputs.

## Final artifact SHA256 identities

```json
{
  "results/cross_layer_safety_v8_final_holdout/configuration_overlap_audit.csv": "f02e5393d01f0dd3d25cd45c704f7211fc1828b28c43784f295f46d2c7ecac68",
  "results/cross_layer_safety_v8_final_holdout/final_baseline_comparison.csv": "2f8a0836af8821874a3bbf4755ed3cb1c03313b768c061c3f35fd4e66080753d",
  "results/cross_layer_safety_v8_final_holdout/final_detection_summary.csv": "7de4688ddd935af6679f32856030257d34a63321cd3455ded85edf6481325d0c",
  "results/cross_layer_safety_v8_final_holdout/final_holdout_findings.md": "e201973c452179d784c28d3d9d3b5b61e25acb103aebd735e7215f70b949443d",
  "results/cross_layer_safety_v8_final_holdout/final_holdout_manifest.csv": "883efd805752747cabd795452b758aa8b274ea472c317ba52e7c8361bd4a97c8",
  "results/cross_layer_safety_v8_final_holdout/final_holdout_protocol.md": "866ae1b766a0e150ac2efcd90b3886493001770227ed6cff988658e499dffec2",
  "results/cross_layer_safety_v8_final_holdout/final_localization_summary.csv": "5c383185c8177dc63f60143dac05f8ca635af17cb34824e42d04d8aae8d707f2",
  "results/cross_layer_safety_v8_final_holdout/final_origin_confusion.csv": "dba1c21174d3c185c53f134a42cddccde3ed94743c4f8a19a7d8b0e2546574f4",
  "results/cross_layer_safety_v8_final_holdout/final_paired_comparison.csv": "d21bc9baa19dcf8f4b26d0e825e8304ba30c4324e3067ace4d524316075a6ffb",
  "results/cross_layer_safety_v8_final_holdout/paper_figures/actuator_generalization.pdf": "5bd61826a4a90d882ca55ef6e072dd9b552ba230d3d680266d34b453ec9aeb99",
  "results/cross_layer_safety_v8_final_holdout/paper_figures/actuator_generalization.png": "20d74ed4b20653011b7d56682445f22a567930fbd9843c952237066e0cdda026",
  "results/cross_layer_safety_v8_final_holdout/paper_figures/baseline_detection_and_silent_plant.pdf": "497dd0c75b5e8cf607950327d03ab7d0ba4aa914a63e803b391a09fdaa0e2b5d",
  "results/cross_layer_safety_v8_final_holdout/paper_figures/baseline_detection_and_silent_plant.png": "cdd87435fe4e3cf86f262c7148d9692b757b97d8d8d18f6defa60ad419725b2a",
  "results/cross_layer_safety_v8_final_holdout/paper_figures/detection_by_origin.pdf": "d153275ec921daa3f30c59b535f4b2bb58339be59cf2db5fd23a32947717b1d4",
  "results/cross_layer_safety_v8_final_holdout/paper_figures/detection_by_origin.png": "15b50c8b1b801cf5d8f829b548c530164409888d63634627a273e092dac8f2cb",
  "results/cross_layer_safety_v8_final_holdout/paper_figures/origin_confusion.pdf": "ab2b68b13c685264d7db2e6fa766cad2beddba0731dd9d5e2c690adfd3dc7d72",
  "results/cross_layer_safety_v8_final_holdout/paper_figures/origin_confusion.png": "5ea0f594bbb803aa3f96465f8cb6513a07083ba4406ffba96a972dd7f4bdd08f",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/holdout_conclusions.csv": "e6a3a4197bd2c748994394de9667694bee72ab2a4d10bacaff517caedbdabcb7",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/identifiability_groups.csv": "732361232524202963cc466f74045b7158b2dfce4390b9810e3795345e3f0a26",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/integrity_checks.csv": "86d9125d695e46f4ede2d1f18908326c6084ac6b932add27c725cb9f3b79695c",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/latent_stuck_patterns.csv": "0a38d32d26ed456f6a0e88b17a408dac5b7053176d6685e284c6385f64ce8c94",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/paired_by_model_behavior.csv": "5eba17330040a7161c93a74e14fffa975d1775ba785d9f81566dd8cab2a1bdb8",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/paired_by_severity.csv": "309d1c701c30e430d02545cccc0796f288348bfb772cd361dd943a9e83cf56a9",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/per_origin_comparison.csv": "5c0f927c95194243e526a41c41f109f336e16bfabc0d214fd2fe2ac5951337e3",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/per_run_outcomes.csv": "f3e809dc76f4d1de320442a91461aa653626f5078c404c46aa1d8621e7e1d904",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/pre_outcome_registration_history.csv": "af69e95d6d37392828b7f5cd74bddd86380734110cc3bc5b0031feeafe95a0a6",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/run_provenance.csv": "7afabe48b5c5bba31ee2489c4a547400cd4f08a794978a4f49c40615ce8a944e",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/runtime_signatures.csv": "705898b18876f2a3056939d703350437a6c5a57dd541f9ee70693678107d83dd",
  "results/cross_layer_safety_v8_final_holdout/paper_tables/subtype_performance.csv": "d36eb248369826da46b1f9ae893e4cad0d9b07f533ee7f97966ab11db1d152e4"
}
```
