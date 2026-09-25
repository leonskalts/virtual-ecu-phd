# Active diagnostic development

Registered 2026-09-25T13:41:19.064987+00:00 before outcomes. Baseline 20e705d0fd7af3d7994082094bdda2a9ce9b69f1.1200 unique new simulations:720 TRAIN(600 faults/120 benign),480 VALIDATION(400 faults/80 benign). Six TRAIN versus four VALIDATION operating families; all profiles distinct; no overlap with prior inline manifests. All public configurations validated. No parameter search.

Memory protocol:1000ms periodic atomic save/read,write0/read,write65535/read,restore/read. Seven memory accesses/check;16-byte per-ECU persistent state. Runtime checker receives only ordinary read/write callbacks. Virtual device backend enforces the already-active stuck-cell write constraint; inference/checker never sees bit identity or fault metadata. Normal scheduled injections and control writes unchanged. Transaction restores the actual saved word (not trusted shadow), never scrubs away a bit-flip or changes legal calibration metadata. Single-threaded scheduler excludes control/interrupt access during probes. Current plant simulator assigns no elapsed scheduler time to these accesses; hardware WCET is not measured. Results are conditional on this added storage-access contract.

Anchor feasibility: no engine-off/no-heat mode, persistent base heat even at zero load, startup not ambient-soaked, no trustworthy independent equilibrium/soak certificate. No sensor anchor invented or fitted; no hidden temperature/equation inversion. Half the families contain a zero-load/zero-speed interval; it is explicitly NOT a qualified anchor. With-anchor denominator0, without-anchor all cases. A2 is exactlyA0(no anchor); A3 exactlyA1(memory only); aliases are clearly recorded, not distinct implemented sensors. Existing short-horizon sensor channel unchanged.

A0 ignores added diagnostic observation; A1/A3 consume it as direct MEMORY/ABNORMAL support. All observers see the same physics stream. Weighted Sum remains choice6, unchanged. Effective/dormant labels use post-probe register-shadow mismatch only offline, so temporary diagnostic writes cannot fabricate effective corruption.

Retention per implemented diagnostic: validation detection and dormant-memory detection improve; no lost A0 detections, no added benign alarms, no wrong confident origins, preserved full effective-memory/timing/communication/actuator detection; silent plant coverage non-regressing. No source/config changes after VALIDATION other than removal if rejected. Ninety-percent target cannot select settings or cohorts. Memory period chosen before outcomes; no thermal contract exists to calibrate. Eight representative validation traces preselected, no bulk raw retention. No unseen holdout/commit/push.

Frozen identities:
```json
{
  "include/cross_layer_fault.h": "3a0a2df4a6b09ca7971447c92f4a6329d33605a6675685ba3bc9a0b8310bf518",
  "include/ecu_types.h": "5a4df8aba9a4c71f2710842d3bdf2ef5fedf4ddfa9fade4f44ca98937c655c33",
  "include/memory_diagnostic.h": "aefb15b66033f3db7022c717b61c57bfa7f047d6ef76afea45e649845486c892",
  "include/runtime_observation.h": "7630416543f7b9a0579f9c2822fabcc205714bce8df926e0bce4f88d6e014e41",
  "results/clo_dsf_current/campaign_manifest.csv": "97c7266f365824eddb84b8304eb7ec7cc6911cc1728f887a8cda116e487ad629",
  "results/cross_layer_safety_v7_3_dev/revised.cfg": "6f62e972a27c765cae6a24daf9b7b98fb1513cd46fc226a128d87a6431e73ac7",
  "scripts/run_clo_dsf_active_diagnostic.py": "2189dfd4ddab8b87d5b93ffcb9f74605a16fb4a857bf1b4efc439052fc505366",
  "src/control.c": "f2ccfbdde47db2ef483b1b64f4b83c9e6a48e9ae0b4f6450666686814dc839f7",
  "src/cross_layer_fault.c": "485d4b277f9734406ccef4020fe9edbe3d55d690d0b5daab254b69dc8991624f",
  "src/memory_diagnostic.c": "6b6fdea9cdef91abb836fffea60dc167739029e675dbb6e0431c2fe40e51208b",
  "src/runtime_observation.c": "a8e2bc1ec212f02019179d93fdb12bd02c821dad1e1995e30ecedefe210b390f",
  "src/v7_3/clo_dsf_revised.c": "dc13c1a29b9e4e82a5bc532de96944d34665334b36273bbf1971c5e36d1e5d86",
  "src/v7_3/revised_runtime.c": "cd0b32c48a92dbb3c1fe35ae540be9fa7db499a5e69e0ef2ba66d3fa76f76007"
}
```

development-train completed with all frozen settings unchanged.

TRAIN gate PASS: no lost A0 detections, no benign alarms, no wrong origins; full memory/timing/communication/actuator detection; sensor outcomes unchanged. All settings remain originally frozen. Eight selected TRAIN scenarios produced byte-identical raw physics/control logs and C summaries against task-start baseline executable. Proceed to VALIDATION without changes.

development-validation completed with all frozen settings unchanged.

Post-run packaging before inspection of validation results: the two new virtual-storage callback functions moved verbatim from cross_layer_fault.c into a dedicated memory_diagnostic_backend.c/header. Their symbols, bodies, data layouts and call sites are unchanged; archived injector source/header restored byte-for-byte. This avoids modifying historical freeze identities and separates diagnostic device modeling from the unchanged original injector. Callback-body SHA256 28800c8bce7c621fc06fc0c39f909c1505f9890b0196d37ee59180e374fab4d8. No inference/diagnostic logic or parameters changed.

VALIDATION retention gatePASS for memory:362/400 vs340/400,22 added dormant detections, no lost detections,0/80 benign alarms,0 wrong origins; full80/80 memory/timing/communication/actuator. All sensor binary outcomes identical; silent plant misses37 unchanged. Memory retained, sensor anchor absent/not retained. No threshold/period/fusion/localization changes following validation.

CSV publication formatting only:CRLF converted toLF, parsed fields asserted identical. Manifest hashes:
```json
{
  "registered": "97c7266f365824eddb84b8304eb7ec7cc6911cc1728f887a8cda116e487ad629",
  "LF": "d68190161f4216e7cda9780e7cc5447e177b5e2276b8a1861bfdcfc6581cf7c9"
}
```

## Final retained implementation and regression

314 testsPASS; buildPASS; Python compilePASS; git diff --checkPASS; legacy48/48PASS; RTL64/64PASS. Six new diagnostic tests,308 existing tests. One full regression after retention. Unrelated tracked historical executables restored after verifying HEAD bytes match task-start hashes; CURRENT executable retained from fresh production build without A0 comparison object.

All initially tracked files outside CURRENT and the documented implementation/doc/executable changes match task-start hashes. GUI preserved. Original injector source/header restored unchanged. Hybrid/HETIA and all legacy/prior-unseen evidence unchanged. Final backend packaging verified again using eight TRAIN physics/control parity replays. No new VALIDATION or unseen campaign rerun. No commit/push.

Final source hashes:
```json
{
  "docs/clo_dsf_current.md": "50ede0858d8d6f573d8cf1daabe50f78e5df129f74841fb26db4d6046f311e81",
  "include/ecu_types.h": "5a4df8aba9a4c71f2710842d3bdf2ef5fedf4ddfa9fade4f44ca98937c655c33",
  "include/memory_diagnostic.h": "aefb15b66033f3db7022c717b61c57bfa7f047d6ef76afea45e649845486c892",
  "include/memory_diagnostic_backend.h": "0ec43b9c0ef43c987e0c95d9ce9151c8c97573688107dde0d0e449ec8f82e095",
  "include/runtime_observation.h": "7630416543f7b9a0579f9c2822fabcc205714bce8df926e0bce4f88d6e014e41",
  "results/cross_layer_safety_v7_3_dev/revised.cfg": "6f62e972a27c765cae6a24daf9b7b98fb1513cd46fc226a128d87a6431e73ac7",
  "scripts/run_clo_dsf_active_diagnostic.py": "4beda59e1eedef095960a4312a7ea2da96d62734c2917310459f80bbb5a6fa60",
  "src/control.c": "f2ccfbdde47db2ef483b1b64f4b83c9e6a48e9ae0b4f6450666686814dc839f7",
  "src/memory_diagnostic.c": "6b6fdea9cdef91abb836fffea60dc167739029e675dbb6e0431c2fe40e51208b",
  "src/memory_diagnostic_backend.c": "a6d0ece226c89b8f9b5fa1d7809927ccad63eefbd2c50f02d5e608c565c8a5ed",
  "src/runtime_observation.c": "a8e2bc1ec212f02019179d93fdb12bd02c821dad1e1995e30ecedefe210b390f",
  "src/v7_3/clo_dsf_revised.c": "dc13c1a29b9e4e82a5bc532de96944d34665334b36273bbf1971c5e36d1e5d86",
  "src/v7_3/revised_runtime.c": "01f42027e5ff07ae26f39f82aaf7f1529675b97ebec72ccdaea566992d6e9523",
  "tests/memory_diagnostic_unit.c": "46aa588f80d0a1d001d41ff35a721aab8378376ab0c153052d688739ef02e3fd",
  "tests/test_memory_diagnostic.py": "c25515557d8ea8d380aeedb00390355e8b27650b712254b705d666a68a8a1c25"
}
```

Physics/control parity checks:
```json
[
  {
    "run_id": "active_0000",
    "raw_sha256": "6eded5c9c204bd899638f25afda474e3e22602dd5fd96a5e95bd128753b615c1",
    "summary_sha256": "3e9c1dab692b7bda7187d693e66b65d841b2967c8c797f1cf5bce1fadd41db2a",
    "parity": true
  },
  {
    "run_id": "active_0020",
    "raw_sha256": "d23520fd11f6444c4d132312ee4acf72f8abbd336aa3cefb306027d1c0d61f6c",
    "summary_sha256": "54b28a64d3c4b38506a5dcc7493e8298f81c4207a82db11824af1354f48a113d",
    "parity": true
  },
  {
    "run_id": "active_0040",
    "raw_sha256": "2c63a9d5988bad5741c5166ad9a451a49f240c093fa0d38f8ff73fce14edd4df",
    "summary_sha256": "117b72f7802160c29b1f4813a8e4cf01ffff93aa495ae5390aad47ac6cdc6e40",
    "parity": true
  },
  {
    "run_id": "active_0060",
    "raw_sha256": "76185cb0975e623a5a34b8eed56339e4e290dbffdbabb457d6a9464ad00fdefb",
    "summary_sha256": "8ef25076ebbea21e75c6ac41bb13de3b4b24f8f7c4733d3cd91ef28e4798ae7b",
    "parity": true
  },
  {
    "run_id": "active_0080",
    "raw_sha256": "ce1e71b6abc5c615ff95d73089ccd5e92b5b6685632ba995f11322e1a58f7848",
    "summary_sha256": "3138e3a812bc0a27a084787658de4ad059eab74eccc5387927fbca3b4810bf88",
    "parity": true
  },
  {
    "run_id": "active_0100",
    "raw_sha256": "4dcf6d17c129d15cafb5f58642b8806db35bf383aeb6a10c25e32ad1960b8d5a",
    "summary_sha256": "7cd853ac5bdba8c72669a922abf22dba6b8d30635f8aa62f3073fcf2effd19db",
    "parity": true
  },
  {
    "run_id": "active_0001",
    "raw_sha256": "f862dbe3440d4e626f9634cf8b2aa74ec3982871151dad85497aec74cedf8e8a",
    "summary_sha256": "ec1703eae62881c6f16e16bc374f31c425a192b0352f740903e7ecb4611986d5",
    "parity": true
  },
  {
    "run_id": "active_0016",
    "raw_sha256": "dcd7b33c32119b1c19f8f13684babc0fb56869dfcc59fc3416e1c428e1c5b304",
    "summary_sha256": "59aa8b478268113117adb60bf329611c8796ddb669445d71ebddc23a83eb811c",
    "parity": true
  }
]
```

Regression:
```json
{
  "build": {
    "exit": 0
  },
  "python_compile": {
    "exit": 0
  },
  "diff_check": {
    "exit": 0
  },
  "full_tests": {
    "exit": 0
  },
  "legacy_cases": 48,
  "rtl_cases": 64
}
```

Final git status:
```text
 M docs/clo_dsf_current.md
 M include/ecu_types.h
 M include/runtime_observation.h
 M presets/gui_session_state.json
 D results/clo_dsf_current/ablation_comparison.csv
 D results/clo_dsf_current/benign_contract_dataset_manifest.csv
 M results/clo_dsf_current/case_summary.csv
 D results/clo_dsf_current/characterization_summary.csv
 M results/clo_dsf_current/confusion_summary.csv
 D results/clo_dsf_current/contract_0000_trace.csv.gz
 D results/clo_dsf_current/contract_0024_trace.csv.gz
 D results/clo_dsf_current/contract_0042_trace.csv.gz
 D results/clo_dsf_current/contract_0060_trace.csv.gz
 D results/clo_dsf_current/contract_0072_trace.csv.gz
 D results/clo_dsf_current/contract_0090_trace.csv.gz
 D results/clo_dsf_current/contract_0102_trace.csv.gz
 D results/clo_dsf_current/contract_benign_0240_trace.csv.gz
 M results/clo_dsf_current/findings.md
 M results/clo_dsf_current/localization_summary.csv
 D results/clo_dsf_current/thermal_contract.cfg
 M results/clo_dsf_current/validation_record.md
 D results/clo_dsf_current/validation_summary.csv
 M src/control.c
 M src/runtime_observation.c
 M src/v7_3/clo_dsf_revised.c
 M src/v7_3/revised_runtime.c
 M virtual_ecu_v7_3
?? include/memory_diagnostic.h
?? include/memory_diagnostic_backend.h
?? results/clo_dsf_current/ablation_summary.csv
?? results/clo_dsf_current/active_0720_trace.csv.gz
?? results/clo_dsf_current/active_0740_trace.csv.gz
?? results/clo_dsf_current/active_0760_trace.csv.gz
?? results/clo_dsf_current/active_0780_trace.csv.gz
?? results/clo_dsf_current/active_0788_trace.csv.gz
?? results/clo_dsf_current/active_0794_trace.csv.gz
?? results/clo_dsf_current/active_0800_trace.csv.gz
?? results/clo_dsf_current/active_0820_trace.csv.gz
?? results/clo_dsf_current/baseline_comparison.csv
?? results/clo_dsf_current/campaign_manifest.csv
?? results/clo_dsf_current/event_detection_summary.csv
?? results/clo_dsf_current/memory_integrity_summary.csv
?? results/clo_dsf_current/sensor_anchor_summary.csv
?? scripts/analyze_clo_dsf_complementarity.py
?? scripts/run_clo_dsf_active_diagnostic.py
?? scripts/run_clo_dsf_integrity_event.py
?? src/memory_diagnostic.c
?? src/memory_diagnostic_backend.c
?? tests/memory_diagnostic_unit.c
?? tests/test_memory_diagnostic.py
```
Status counts {" M": 14, " D": 13, "??": 23}. Eight compressed traces. No commit/push.
