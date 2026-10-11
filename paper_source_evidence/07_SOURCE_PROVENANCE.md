# 07 — Source provenance and reproducibility limits

Evidence labels used throughout: **VERIFIED FROM SOURCE** (literal implemented behavior); **VERIFIED FROM EXPERIMENT ARTIFACT** (recorded outcomes/protocol); **DERIVED MATHEMATICALLY FROM VERIFIED SOURCE** (algebra or deterministic accounting, not a new experiment); **NOT RECOVERABLE / REQUIRES CONFIRMATION** (missing/limited evidence). Source paths are repository-relative unless explicitly absolute. Line numbers refer to the hashes in 07, not an assumed future HEAD.

Repository HEAD at extraction: `a340ca5cf0473d7dc572f7cd63e44fbc25b175a7`. This does **not** identify the full frozen executable by itself. Some scientific files are untracked, generated adapters live outside Git, and retained records independently hash exact build inputs. `data/source_index.json` reports current source hashes, Git tracking and matching historical manifests. A source without a matching recorded freeze hash is labeled as a current extraction, not silently promoted to frozen provenance.

## Evidence-to-source map

| Claim / procedure | Actual implementation and range source | Applicable evidence/version |
|---|---|---|
| Discrete thermal/controller equations | 01 exact numbered excerpts; thermal_plant_step, control_step, scheduler_run | Final protected_hashes.json; case profiles from each distinct manifest |
| Sensor A/B/C conversion and sampling | sensors_step, redundant_temperature_sample, diagnostic_temperature_sample and generated wrappers | Primary frozen adapter/source/object hashes; no inference-side physical truth |
| Evidence, DS and causal localization | Generated extended.c, c2_extract, ds_combine, c2_origin_betp | Final freeze.json plus protected C/config hashes; 02 full technical source appendix |
| Independent-C pair channel | triplex_consistency_step plus generated bridge.c exported clo_existing_pair_strength | Primary generated bridge.o and provider object freeze entries |
| Integrity record ownership and qualification | di_publish/di_transform/di_verify, generated di_source/di_finish/di_strength | Primary source and generated adapter hashes; development boundary parity/failure-mode tests |
| Final active memory source | Generated dc_probe and z.memory_check assignments | Primary final adapter.c; not merely mr_memory_step by filename |
| Final three-sample gate | sensor_confirmation_step, ba_capture, collect(q[:,25]) | Benign selection G2 and final frozen assembly; selected runtime-data readout |
| Offline plant label | propagation_monitor_step, separate reference scheduler | Threshold .01°C reporting-only; not an online feature |
| Multi-baseline comparison | ieee_baselines/comparative_backends and run_ieee_multibaseline | Separate secondary locked selection/protocol; qualification retained |
| Origin-RF common schema / inference | origin_rf.py; run_origin_rf.py | input_schema, model lock, logging-only instrumentation/object hashes; authentic confusion CSV |
| RTL | digital_integrity_monitor.v, timing.tcl, synthesis.ys | rtl_integrity_poc record source/library hashes, statistics and logs |
| Native resources | tools/native_resource and tools/native_memory, generated payload maps | Separate verified replay build provenance, not final ECU deployment image |

## Exact files, ranges, hashes and Git coverage

All line ranges below are current bytes at extraction; numbered function-level excerpts in01–05 bind each principal rule. Original paths can include `/tmp`; their fragility is a reproducibility limitation, not a reason to replace them with a different standalone implementation.

| Path | Lines | SHA-256 | Git tracked | Matching recorded freeze/source manifest |
|---|---:|---|---|---|
| `docs/cross_layer_observability_model.md` | 1–193 | `52135f5df9e9aada974ee439bdfafe3e4ed23a034b09be45796bf760011e6f72` | False | Current extraction; no matching entry in inspected locks |
| `docs/paper_blueprint.md` | 1–215 | `1f5f2eed01dc8f58cb46d5ded6dc4140678f8d35e102d41e4e12c86a0855ff06` | False | Current extraction; no matching entry in inspected locks |
| `include/clo_dsf_candidate2.h` | 1–47 | `921e4caa96c824c72953261cd0bea5a29d0de357e69a9e972f372fe0f1a4bae3` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `include/clo_dsf_final.h` | 1–22 | `151475b2ccbd2b3dd50b06cd64bb6a5932b4b2a74834e59b78c0d4cae421f954` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `include/clo_dsf_revised.h` | 1–42 | `206fa839cdb9c008a319ef22f3d0fe3081f179feeef809086c8cf7baa15247b2` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `include/config.h` | 1–46 | `eb481dc6fe5bca46e1c4a4fef773be421933c33b43ca385c8c88f8e013e16aa7` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `include/cross_layer_fault.h` | 1–22 | `7865bcb55c7bec755aaf4a28073de8aa2b6b687cfa1d336a5bbd597c2fb1dd0f` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `include/digital_sensor_integrity.h` | 1–11 | `3d0518aa54b9e51b45f533423fad23d77cc8f70ac6827ebdd78cc4c412a3bdff` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `include/memory_diagnostic.h` | 1–18 | `7d66530fcbbcfaab612ad9f01a2fe57b3ad20da9cf9ce4216127fde6443e306c` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `include/runtime_observation.h` | 1–38 | `7fd084b6a4c6e05372858a9ad2c81a42872afae5e2704903c478089c9c8fad91` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `include/runtime_timing_observation.h` | 1–28 | `93abae40373360d6fc824b887b459a33e830ced88951838b8489a7a95bb09565` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `python/virtual_ecu/comparative_backends.py` | 1–98 | `49736a4ba235118f3fb6704d0018213a200d5990f43a68aef4bebe61a0e81c88` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `python/virtual_ecu/ieee_baselines.py` | 1–45 | `d60e7e861e22c031dbae50657286673f2fb55bf73dc0a079c07867accf28f284` | False | results/ieee_origin_rf/scientific_hashes.json |
| `python/virtual_ecu/origin_rf.py` | 1–60 | `820e7e1fb1c247831a702ada2c1449db6cf437748db0d398fab695417825cab3` | False | results/ieee_origin_rf/scientific_hashes.json |
| `results/benign_alarm_development/protocol.md` | 1–15 | `221be3f4ff1476bb25c103463a21488480ed913e4575c3085d83578798c9296c` | False | results/integrity_final_unseen/protected_hashes.json; results/benign_alarm_development/artifact_hashes.json |
| `results/clo_dsf_current/symmetry_findings.md` | 1–33 | `103b22790d869b9b51a7ef56d4b233c4a67b178d5368416185670f9d7c60f18a` | True | results/integrity_final_unseen/protected_hashes.json |
| `results/clo_dsf_current/triplex_freeze_record.md` | 1–13 | `ff11ee6d32115bbfa636ba62fbae34ac0a85c02a61aa2e21f676f354808c37fc` | True | results/integrity_final_unseen/protected_hashes.json |
| `results/clo_dsf_current/triplex_only_findings.md` | 1–13 | `4f9690aa9579b25e44950f367e6b3ce04c545eae4f004dbf3a03c351a9f3a621` | True | results/integrity_final_unseen/protected_hashes.json |
| `results/cross_layer_safety_v7_3_dev/revised.cfg` | 1–8 | `6f62e972a27c765cae6a24daf9b7b98fb1513cd46fc226a128d87a6431e73ac7` | True | results/integrity_final_unseen/protected_hashes.json |
| `results/digital_integrity_development/boundary_parity.json` | 1–18 | `be3a7c90eb1bc660764caafc36ea2868e4de60341f6df652b1048f3d8a0f5890` | False | results/integrity_final_unseen/protected_hashes.json; results/digital_integrity_development/artifact_hashes.json |
| `results/digital_integrity_development/protocol.md` | 1–11 | `65269234c89dbc07f764c062e67bcdf53caf1542132aed2dbeae9801eed60096` | False | results/integrity_final_unseen/protected_hashes.json; results/digital_integrity_development/artifact_hashes.json |
| `results/frozen_robustness/protocol.md` | 1–26 | `9ccd0744abdf04ae1f58716bd88499306f74172c2b04afe77235d04f3c5b2bd9` | False | results/frozen_robustness/artifact_hashes.json; results/frozen_robustness/freeze.json |
| `results/ieee_multibaseline/methodology.md` | 1–40 | `fe5abeee61009989d934150aaebd908ef35dded1a3ee4e1b142734e9cdc58515` | False | results/ieee_multibaseline/artifact_hashes.json |
| `results/ieee_multibaseline/observability_scope.md` | 1–12 | `514d48856961f7429b30532adb591939b1da14ab7185307ec4fb04dd6987e0ac` | False | results/ieee_multibaseline/artifact_hashes.json; results/ieee_multibaseline/registration_lock.json |
| `results/ieee_multibaseline/protocol.md` | 1–41 | `9205ee82d48105314e3df8ca374b15aaf847613ac70503158ff75e396fe5508a` | False | results/ieee_multibaseline/artifact_hashes.json; results/ieee_multibaseline/registration_lock.json |
| `results/ieee_multibaseline/rf_only_posthoc.csv` | 1–6 | `7b01d678e872cb05b0bd7cec768f2f4874a46917c968bd6b7d37a35ee13a6771` | False | results/ieee_multibaseline/artifact_hashes.json |
| `results/ieee_origin_rf/findings.md` | 1–67 | `3eb8a91ba6889e6738d3ffb4ada2e7c7105341fca7a9b031a914888366c8c585` | False | results/ieee_origin_rf/artifact_hashes.json |
| `results/ieee_origin_rf/input_schema.json` | 1–89 | `88956ad6a41b651ff0715a76dfcbaeff00ae5146b082c1ef13f5290255a27458` | False | results/ieee_origin_rf/artifact_hashes.json; results/ieee_origin_rf/registration_lock.json |
| `results/ieee_origin_rf/instrumentation.json` | 1–123 | `676a7e4b5fc20e43d6f77c1aeb1c30377ccfcd165ec350cd8846327f9a48dc9d` | False | results/ieee_origin_rf/artifact_hashes.json; results/ieee_origin_rf/registration_lock.json |
| `results/ieee_origin_rf/methodology.md` | 1–15 | `94e7f2f860812f55f04805c67f5ec08db732b52c603dd8cc84ed98cc6edcbaa8` | False | results/ieee_origin_rf/artifact_hashes.json |
| `results/ieee_origin_rf/protocol.md` | 1–37 | `1ad549c71ad6dce95057b13f0729dcb70b0e677007f9f74cb75b66c3f2cfa18a` | False | results/ieee_origin_rf/artifact_hashes.json; results/ieee_origin_rf/registration_lock.json |
| `results/integrity_final_unseen/freeze.json` | 1–1823 | `9dfe00fc25a89f1a7381fb35a1284156c05f6a87bdbc06956e8e76c930a0cda1` | False | results/integrity_final_unseen/artifact_hashes.json |
| `results/integrity_final_unseen/protected_hashes.json` | 1–38038 | `cab196bcc0c9fd50be2fd54d065f02eedd888bf018f636a36caccc767da2ebc1` | False | results/integrity_final_unseen/freeze.json; results/integrity_final_unseen/artifact_hashes.json; results/integrity_final_unseen/freeze.json |
| `results/integrity_final_unseen/protocol.md` | 1–13 | `f4366f3c83419483d28a54440bd5578f267788e541bca6f0bae4b0cbc3c73bc7` | False | results/integrity_final_unseen/freeze.json; results/integrity_final_unseen/artifact_hashes.json; results/integrity_final_unseen/freeze.json |
| `results/integrity_final_unseen/registration.json` | 1–233 | `c0a4247521e14cbb8c5e6142659f5106c9c1f9021960b63565621eeb7c955149` | False | results/integrity_final_unseen/freeze.json; results/integrity_final_unseen/artifact_hashes.json; results/integrity_final_unseen/freeze.json |
| `results/native_memory_footprint/findings.md` | 1–59 | `8c009fbedc187bd6c720457e1fe5fa2a0885037d844c1deb3bd255077cb56f45` | False | results/native_memory_footprint/artifact_hashes.json |
| `results/native_resource_benchmark/findings.md` | 1–36 | `d85eaf56f3c37b914533b6ce6b0ae13c4513ae9106fd12d94d396d9a1acc15a3` | False | results/native_resource_benchmark/artifact_hashes.json |
| `results/rtl_integrity_poc/record.json` | 1–21 | `978eb5f908c4418c6db58b6c389e86b51e144f1c8508f36b8fdca19ca9b50046` | False | Current extraction; no matching entry in inspected locks |
| `results/rtl_integrity_poc/simulation.log` | 1–1 | `2e1750f4cac236a2a52019ec4561645d950b13a6f659bc06bac18992f971a48b` | False | Current extraction; no matching entry in inspected locks |
| `results/rtl_integrity_poc/statistics.json` | 1–93 | `2577fe4b129b2a8214df303c1e002ac31c68c9f91bc2ef9904b612e904382564` | False | Current extraction; no matching entry in inspected locks |
| `results/rtl_integrity_poc/synthesis.ys` | 1–9 | `f396e02f4e14d8e3213cd966861f809f165062b48f6899b5edd023bbdd8c5224` | False | Current extraction; no matching entry in inspected locks |
| `results/rtl_integrity_poc/timing.log` | 1–386 | `836d9bb7bf2715a7f02f4ad0ee8f53339169d5f2949b302971c2c0cd701a9a6f` | False | Current extraction; no matching entry in inspected locks |
| `results/rtl_integrity_poc/timing.tcl` | 1–10 | `aba9dc20310a9fb037cebf302c10ca6f501175fb8da9f3725a9dd60daa026e98` | False | Current extraction; no matching entry in inspected locks |
| `rtl/integrity/digital_integrity_monitor.v` | 1–62 | `93b6c2f47e02f0447cda354964d8ea558a957ece0329910e5adceb78483f3a6c` | False | results/rtl_integrity_poc/record.json |
| `scripts/report_comparative_benchmark.py` | 1–88 | `834422d6ceb5cae6b98c11c7c29b1ccb70e56339d5543c822d08e4cedac5755c` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_benign_alarm.py` | 1–169 | `a4b95304ab100fb6d4e82e609dd42b811dc498daa79bcc598a4e16bb76326315` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_clo_dsf_multirate.py` | 1–230 | `a7a1cd13b5e45b4a49345a22a693be46cc6c27aa68bdb5b57d4a415d38e0d104` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_digital_integrity.py` | 1–170 | `63fa7f99fcd770e6e7be4666abaa4ab5a8a47d455a6b25d989929669c175a16f` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_dynamic_consensus.py` | 1–178 | `ed6cdda1862b8c934622ff5963c80d0c7c20a3db212030501203ea83c176e32d` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_frozen_robustness.py` | 1–133 | `e4b86ef1f351b6ad6d9628b8007a28fd5688b1ccf32556005ccc4b809a027c63` | False | results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_ieee_multibaseline.py` | 1–242 | `19b31017149dcef39ac110d75b292b8f25acb97885ab72567a7e59ce338ba00c` | False | results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_integrity_final_unseen.py` | 1–159 | `a86d4954bf943460c98d97edeb74b946ef84cefe0bdf8b1003a0f79871ced4fa` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_origin_rf.py` | 1–212 | `7140f3e38439045dd2e5d08a66f4e703f369fb80ce63306323394f282c50a336` | False | results/ieee_origin_rf/scientific_hashes.json |
| `scripts/run_rtl_integrity_poc.py` | 1–39 | `1cf782d998dd6542da79604bbc0536461bacace7938c593c24efb8fab7c354be` | False | results/ieee_origin_rf/scientific_hashes.json; results/rtl_integrity_poc/record.json |
| `scripts/run_triplex_plus.py` | 1–218 | `5e04f3896dd4c6f9f988ff96f2fdd9eabfb784238ccedb6f6cf2a7b3f9fab141` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/actuators.c` | 1–117 | `5b1fcad84453fce451aa7d08cb23dc744fa2ff484c0fb22e0cfe72d234641ce3` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/control.c` | 1–78 | `f2ccfbdde47db2ef483b1b64f4b83c9e6a48e9ae0b4f6450666686814dc839f7` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/cross_layer_config.c` | 1–201 | `0ac07cf90296a041f82973ad754337c9c8ae9fc9f58dff6104e2a828dfe38457` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/cross_layer_fault.c` | 1–206 | `5e3a807d89598615aa93cc9c3849eb6f8c4a44b1f25c4e56d6672ff5deb8e01f` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/experiment.c` | 1–669 | `f6334c4fb6d71bd1fbfec067434722d9c38d4f6bb525fb10ea17cf1fffbaeadf` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/fault_injection.c` | 1–168 | `52553d6d5b3e5f1d461dd52cf19be14941481581f1eb4613710dd0cee207d992` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/memory_diagnostic_backend.c` | 1–26 | `a6d0ece226c89b8f9b5fa1d7809927ccad63eefbd2c50f02d5e608c565c8a5ed` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/propagation_monitor.c` | 1–153 | `1bf34f5ea6fa748844d8c3353fc13ce07d679574178e3b1f051861c684a920e3` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/redundant_temperature.c` | 1–22 | `176da3fafddaf219b0515492be7225c72e59498ef1d3c10a74e771669d42a6d1` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/runtime_observation.c` | 1–62 | `cae3370319989b38c52832293215d678444eedcf20dba9b93dc04f2444c323ea` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/scheduler.c` | 1–175 | `80d924e069d55926f6f2485db853ce8de06744c55c0119b640510e7641ec30d9` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/sensor_delivery.c` | 1–59 | `f3ea17440e15513808e77f3c8f41849da31f3504ea6441bca85b5c963e037d76` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/sensors.c` | 1–137 | `f19e601d68976a563a5edb031d76ca259689b32bef04958a81f6bd4a8947a352` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/thermal_plant.c` | 1–205 | `162cff8f8729f524716f96836f78f3ebd5ae6b61818a461c7ca152c5e53aa106` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/v7/ds_evidence.c` | 1–85 | `c763e3eb722629779b46b569badb3301cc8accf348b787e9d939f6af60854c92` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/v7_1/candidate2_evidence.c` | 1–63 | `8c486e59666e603f8423f8e0bc23d47551ce8a676f8045702a28cda3bbbbcab7` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/v7_1/candidate2_observability.c` | 1–21 | `d7b55e3db75e217dcf322b778511f47de8ccaf2b288b180b7b5761d65854ddb0` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/v7_3/diagnostic_temperature.c` | 1–27 | `b4cd951328299da10fa5b4c0a504e79f9cf8a252b861304e38e77546be4e7be9` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/v7_3/digital_sensor_integrity.c` | 1–34 | `10c0c9edf054003470e0b06ebfb0d2503341f71dfe1042efa1cad7774b2b7949` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/v7_3/sensor_confirmation.c` | 1–15 | `5cc7c433a4c93242f4678a363c0e54cb8e3344d7c404e92dafb7a6066818deae` | False | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `src/v7_3/triplex_consistency.c` | 1–31 | `be679e4184818f6c679ddb7af0dfe7d4d7342fa3eb76958f71ab06fa297f5bd4` | True | results/integrity_final_unseen/protected_hashes.json; results/ieee_origin_rf/scientific_hashes.json |
| `tools/native_memory/build.py` | 1–57 | `511762c61f7cf645856de22549a2e2f35304de894bbf8f5f8c054e4dde52754d` | False | results/native_memory_footprint/artifact_hashes.json |
| `tools/native_memory/build_pipeline.py` | 1–47 | `1e850bc0a137bebfa31251729b7150e3f4fef4875968f26dbabf6795ad578903` | False | results/native_memory_footprint/artifact_hashes.json |
| `tools/native_memory/stack_call.S` | 1–19 | `6c0102a5d1450d09ad7c531d7a8a429f09e0051550124d4977e8ec51f6d59a38` | False | results/native_memory_footprint/artifact_hashes.json |
| `tools/native_memory/stack_driver.c` | 1–14 | `c983316c638ba8812f7d4a1fc93acf6b06616746d116ce739fb4f09ffb16f71a` | False | results/native_memory_footprint/artifact_hashes.json |
| `/tmp/clo-integrity-final-unseen/work/adapter.c` | 1–560 | `061c050ab29046f6d1d8336002037cbf2c0c7d9c1df5615e9f61c2ab6ede303f` | False | results/integrity_final_unseen/freeze.json; results/integrity_final_unseen/freeze.json |
| `/tmp/clo-integrity-final-unseen/work/bridge.c` | 1–410 | `d48249de80d3c60f05c4ef2c1cd224a24ed7335a19bd96f9d38919c998b52039` | False | results/integrity_final_unseen/freeze.json; results/integrity_final_unseen/freeze.json |
| `/tmp/clo-integrity-final-unseen/work/extended.c` | 1–419 | `71b21a98d0b490749af22192d3c7d572529d3fcba824bf7fe4fd90d8abc92a91` | False | results/integrity_final_unseen/freeze.json; results/integrity_final_unseen/freeze.json |

## Frozen assembly, not a clean-HEAD assumption

**VERIFIED FROM EXPERIMENT ARTIFACT.** Primary freeze lists generated adapter.c/extended.c/bridge.c/frozen.c, linked objects, compare executable, profiles, specs, protocol and registration. The source-index checks recoverable relevant files against those records. Origin-RF instrumentation adds logging only and links frozen objects; its recorded link command and object hashes—not model filenames alone—identify the evaluated input path. Native memory reparses/recompiles the verified export and core with its own build flags, then empirically verifies exact output equivalence. It does not replace the primary frozen binary.

**NOT RECOVERABLE / REQUIRES CONFIRMATION.** The ZIP is an evidence package, not a standalone reproduction environment. It intentionally excludes raw replay archives, trained model binaries, toolchains and whole source trees. Exact rerunning would need the referenced repository plus frozen models/build inputs; some models/build adapters and generator ancestors rely on `/tmp` paths. The recovered generated source excerpts are authoritative for explanation, but portability of all historical generator dependencies is not demonstrated here. No experiments or builds were run during extraction.

Primary unseen/robustness raw traces were deleted by their original protocol; per-case sufficient statistics and summary tables cannot support new waveform plots or a proof of trace indistinguishability. Origin-RF alone retained full replayable packets, which are intentionally omitted from this compact package. Do not claim all studies support strict identical-information replay.

The protected producer domain, independent sensor C, synchronous actuator response and calibrated legal signal envelope are **modeling assumptions**, not physical automotive validation. Pre-protection/common-witness sensor corruption, independent idle mechanical-health telemetry, scheduler jitter, full ECU producer cost, MCU memory placement, WCET and post-layout RTL timing remain outside demonstrated coverage. G2 sensitivity to physical integrity-PASS anomalies outside the sampled fault space is not established.

The current export's RF model padding and unused provider struct members are measured, not lower bounds. Pure CLOVER decision-only A memory is not cleanly allocated separately from its local provider state; do not fabricate a subtraction. Zero observed errors/false alarms are finite-cohort results, not zero-probability safety guarantees.

## Package validation

`data/package_validation.json` records structural/numerical checks. `data/copy_manifest.json` permits byte-for-byte comparison of authentic summary/confusion files to originals. `data/cohort_inventory.json` is explicitly a deterministic extraction from manifests, not new experiment data. No source, model, GUI, RTL or original result was changed; no commit/push.
