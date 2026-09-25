# Multi-timescale redundant sensor development

Registered before outcomes 2026-09-25T14:39:37.864845+00:00. Git baseline 67bcc337532d968c8458cf1d226015025e02c549 plus retained uncommitted redundant-sensor implementation (A0 core SHA256 b44cc1300d2381300595c5322deefd47ccaf7660de904da8322ac91a514a7579).

1560 simulations: TRAIN936(816 faults/120 benign), VALIDATION624(544 faults/80 benign); six versus four disjoint operating families. Per family:20 each MEMORY/TIMING/COMMUNICATION/ACTUATOR,56 SENSOR_CONTROL,20 benign. Sensors:12 slow drifts/8 steps/6 pulses per chain;2 reference conversion failures;2 common-mode limitation controls. Positive/negative weak offsets;300ms or permanent steps;900ms or permanent pulse trains; new magnitudes, seeds, onsets and profiles. Same physics stream for all observers. Prior inline manifests audited before replacing CURRENT.

A0=SLOW only, an explicit identical alias. FAST only removes only the slow averaging feature, retaining all inherited local sensor evidence and direct conversion-failure status. FAST+SLOW is the proposed current detector. Temporary ablation objects only, no maintained candidate tree.

FAST contract fixed before TRAIN: two-sample noise difference<=0.40C and legal differential slew<=1.2C/s. Edge violation abs(delta[k]-delta[k-1])>0.52C at100ms cadence. Freeze pre-event disagreement for<=300ms; require two consecutive same-sign residuals beyond0.40+1.2*h, OR three excessive edges in a ten-acquisition(1s) rolling window. One isolated spike plus recovery supplies at most two edges. Confirmation supplies direct SENSOR_CONTROL contract evidence1, max-merged with existing sensor evidence; no extra DS source. No global threshold, slow window, causal precedence, memory, timing, communication, actuator or sensor model change. Sensor-member attribution remains UNKNOWN. No hidden truth/labels in inference.

Benign tests retain independent noise/calibration and legal triangular disagreement; additionally reference-only isolated +/-0.9C100ms spikes and +/-0.35C300/900ms transients. Repeated large out-of-contract impulsive noise is not promised distinguishable from fault pulse trains. Common-mode not targeted.

No parameter search planned. TRAIN may reject; settings lock before VALIDATION. Retain only substantial new weak abrupt-fault validation detections, preserved slow-drift and other-origin detections, no lost A0 cases, near-zero benign alarms and wrong origins. Desired percentages never select cohorts/parameters. Latency comparison reports full detected populations and paired common detections, recognizing changed denominators. Eight compressed representative traces preselected; raw run artifacts discarded immediately after scoring. No unseen holdout/commit/push.

A0 reconstruction from current core (temporary only):
```diff
--- current.c
+++ baseline.c
@@ -146,53 +146,6 @@
     if(s->reference_count==320)
         s->reference_strength=fmin(1.0,fmax(0.0,(fabs(s->reference_mean)-.90)/2.0));
     return s->reference_strength;
-}
-
-/* Fast redundancy contract: independent-chain calibration cancels in changes.
- * Combined bounded sample noise is <=0.20 C; two samples permit 0.40 C.
- * Legal differential ramps up to 1.2 C/s add 1.2*dt. Freeze the last
- * pre-event acquisition for at most 300 ms. Two consecutive same-direction
- * out-of-envelope residuals certify persistence; one isolated spike cannot.
- * Recurrent alternating pulses instead require >=3 excessive edges in 1 s:
- * an isolated spike and its recovery supply at most two edges. Both tests
- * are one short-history consistency provider, not independent DS sources.
- * A confirmed contract violation supplies direct sensor evidence (as other
- * runtime contract providers do), not a calibrated fault probability.
- */
-static double fast_redundant_sensor(clo_revised_t *s,const runtime_observation_t *o)
-{
-    s->fast_strength=0;
-    bool valid=o->reference_enabled && o->reference_valid && !o->reference_failed &&
-        o->source_valid && o->source_ms==o->time_ms && o->reference_ms==o->source_ms &&
-        isfinite(o->source_c) && isfinite(o->reference_c);
-    if(!valid || (s->fast_valid && o->time_ms!=s->fast_last_ms+ECU_SENSOR_PERIOD_MS)) {
-        s->fast_valid=false;s->fast_active=false;s->fast_count=0;
-        s->fast_index=0;s->fast_edges=0;
-        for(unsigned int i=0;i<10;i++)s->fast_edge_history[i]=0;
-    }
-    if(!valid)return 0;
-    double delta=(double)o->source_c-o->reference_c;
-    bool edge=s->fast_valid && fabs(delta-s->fast_previous)>.40+1.2*ECU_SENSOR_PERIOD_MS/1000.;
-    s->fast_edges-=s->fast_edge_history[s->fast_index];
-    s->fast_edge_history[s->fast_index]=edge;s->fast_edges+=edge;
-    s->fast_index=(s->fast_index+1)%10;
-    if(s->fast_active && o->time_ms-s->fast_anchor_ms>300)s->fast_active=false;
-    if(edge && !s->fast_active) {
-        s->fast_anchor=s->fast_previous;s->fast_anchor_ms=s->fast_last_ms;
-        s->fast_active=true;s->fast_count=0;s->fast_sign=0;
-    }
-    if(s->fast_active) {
-        double h=(o->time_ms-s->fast_anchor_ms)/1000.;
-        double residual=delta-s->fast_anchor;
-        int sign=residual>0?1:-1;
-        if(fabs(residual)>.40+1.2*h) {
-            s->fast_count=sign==s->fast_sign?s->fast_count+1:1;s->fast_sign=sign;
-            if(s->fast_count>=2)s->fast_strength=1;
-        } else {s->fast_active=false;s->fast_count=0;}
-    }
-    if(s->fast_edges>=3)s->fast_strength=1;
-    s->fast_previous=delta;s->fast_last_ms=o->time_ms;s->fast_valid=true;
-    return s->fast_strength;
 }

 #include <string.h>
@@ -247,7 +200,6 @@
     state->previous_local_ms=o->source_ms;
     local=fmax(local,sensor_response(state,o));
     local=fmax(local,redundant_sensor(state,o));
-    local=fmax(local,fast_redundant_sensor(state,o));
     s->evidence.strength[3] = fmax(s->evidence.strength[3], local);
     s->evidence.available[3] = s->evidence.available[3] || local > 0;
     /* Establish precedence only from a directly observed contract violation,
```

Scientific identities:
```json
{
  "src/cross_layer_config.c": "0ac07cf90296a041f82973ad754337c9c8ae9fc9f58dff6104e2a828dfe38457",
  "src/runtime_safety_logger.c": "aff426aefcbe42b4e1c83ecd036d94ac8dc91acac6bcec1b4c7933982c9d36dc",
  "src/timing_safety_monitor.c": "ffd160ccb9025ec9a03ea3526b0fdfe6450382005f7a41d81aa0d78c950e1b88",
  "src/validation_v5_config.c": "67ddfb3421720339b33404e835790a93c877f22ce7d8debe619c63fcf829b4dc",
  "src/thermal_plant.c": "162cff8f8729f524716f96836f78f3ebd5ae6b61818a461c7ca152c5e53aa106",
  "src/metrics.c": "b15690d244ba59b75532e299e53bd74f2bd946268e6b0b0d1c6c8f10d510c20a",
  "src/diagnostics.c": "e20a16a34c8b2238a89d3363c40c15794fca5c37b5b7854524e1cbb383e448e6",
  "src/experiment.c": "f6334c4fb6d71bd1fbfec067434722d9c38d4f6bb525fb10ea17cf1fffbaeadf",
  "src/safety_monitor.c": "27412e114cd0cd22132b1a5b24e7a14e5c937df4ade5ac3f1b6029c6aec2fe4d",
  "src/scheduler.c": "80d924e069d55926f6f2485db853ce8de06744c55c0119b640510e7641ec30d9",
  "src/control.c": "f2ccfbdde47db2ef483b1b64f4b83c9e6a48e9ae0b4f6450666686814dc839f7",
  "src/cross_layer_fault.c": "5e3a807d89598615aa93cc9c3849eb6f8c4a44b1f25c4e56d6672ff5deb8e01f",
  "src/detection_algorithm.c": "c4a024feb6eabc6d62bb6a4483d504cc39c3efa8fa64baf16c7c1fec13a7804d",
  "src/actuator_trace.c": "066e91642cef22759a918d3797e613d3d8ed1f373abb96ff9838ce090861cc99",
  "src/memory_diagnostic.c": "6b6fdea9cdef91abb836fffea60dc167739029e675dbb6e0431c2fe40e51208b",
  "src/runtime_timing_observation.c": "5d6f4cbe3d097136ed7f5883057388e0ed4dc6b84aff28a051386c68c7d84ac0",
  "src/validation_v5_logger.c": "2d1c35b32c8420c1a097b657c4928d04436836bb6299bbc4b5b821ccc590efb2",
  "src/redundant_temperature.c": "176da3fafddaf219b0515492be7225c72e59498ef1d3c10a74e771669d42a6d1",
  "src/hazard_model.c": "c531b742fa8c639dfd515afcba00d136398d953f9cd2873a9ba57b19f2146b03",
  "src/propagation_monitor.c": "1bf34f5ea6fa748844d8c3353fc13ce07d679574178e3b1f051861c684a920e3",
  "src/actuators.c": "5b1fcad84453fce451aa7d08cb23dc744fa2ff484c0fb22e0cfe72d234641ce3",
  "src/sensors.c": "f19e601d68976a563a5edb031d76ca259689b32bef04958a81f6bd4a8947a352",
  "src/memory_diagnostic_backend.c": "a6d0ece226c89b8f9b5fa1d7809927ccad63eefbd2c50f02d5e608c565c8a5ed",
  "src/fault_injection.c": "52553d6d5b3e5f1d461dd52cf19be14941481581f1eb4613710dd0cee207d992",
  "src/sensor_delivery.c": "f3ea17440e15513808e77f3c8f41849da31f3504ea6441bca85b5c963e037d76",
  "src/main.c": "ce81833c12f36aca454251121efc18b835b30fe99cf2e434afd7370ed977e032",
  "src/runtime_safety_policy.c": "ac6761caa9480effa52f3f721a980ed0ffaa02dbe44c46492788acb34eeaecb3",
  "src/runtime_safety_config.c": "3af95ba0188b9ab123269d4aec2451f335589399f2ab79c8cbc6b59b9e1d870a",
  "src/sensor_trace.c": "2e4663115e93ce7e95ba42ae51cd49b8c8612aea100fb617bbb9ccea257de8d6",
  "src/safety_policy_v5.c": "8a1c55d9bc265d3e36bcb9a4074d3c75a47d188e016221d987acc6cb96c421d6",
  "src/calibration_trace.c": "e537ce9a6884d4c1a22efa59a6f154d84d6bf0c51359e7180b0da5f1fa4d230f",
  "src/scheduler_stress.c": "b9e4ca5013a90c6b639dcebaf1921beec07def11e443576bf36ba852534f66b0",
  "src/logger.c": "3f30449d70bca3d2dd1f473853b875f195c67062a4f6775205f621e83aea760c",
  "src/runtime_observation.c": "cae3370319989b38c52832293215d678444eedcf20dba9b93dc04f2444c323ea",
  "src/v7/clo_runtime.c": "3f5e1b9ea9710f30029cc404d3bcc0b130e22d4e250c5c2d8540d951bc247079",
  "src/v7/clo_observability.c": "420160ef18797024bf72ceafa4c7f888ff21f15d65cf4326279102a61c64dd1b",
  "src/v7/ds_evidence.c": "c763e3eb722629779b46b569badb3301cc8accf348b787e9d939f6af60854c92",
  "src/v7/clo_dsf.c": "88908647de871270ebfbcfa7fb13cb3da3371c33c42a41cce0a33dd984655854",
  "src/v7_2/final_runtime.c": "d7f7262861914c20e2527cf19883968c1ea8fd0ebe315c33f9e39b5b8df3c4fb",
  "src/v7_2/clo_dsf_final_optimized.c": "0b748efd16ad75c2f836f36740f9d6da80776d053ee1f5f0a7c6936681df10f6",
  "src/v7_2/clo_dsf_final.c": "7a8aa323d0d744f2d80559ce8880ca29028979fe54176fdab4fde42505ff1f15",
  "src/v7_2/final_observation_io.c": "19446a5c5726dd650da092c634e8c7ade7f4101401ad152e73fae41afb3d9145",
  "src/v7_2/final_sparse_math.c": "25be89984a88c16b8ca98f96493212dcd802904ad5c521e82c486e8af1f1775b",
  "src/v7_3/clo_dsf_revised.c": "684f025ef5f28e0d890767f20756a34964239ad38d89e9d7750c3f5180f2f1b5",
  "src/v7_3/revised_runtime.c": "1febac2b4044a5ea67a16e53ab1acc71332b228f3add33365167761a25424d2f",
  "src/v7_1/candidate2_evidence.c": "8c486e59666e603f8423f8e0bc23d47551ce8a676f8045702a28cda3bbbbcab7",
  "src/v7_1/clo_dsf_candidate2.c": "4f2be33b1cb63180be9e2508b013b80a70546c0cb9d3b1e406a3f5fc4f0c15e4",
  "src/v7_1/candidate2_runtime.c": "34fd68804a6e4977feebf02952cdf473a6a8d6d15b957223a7f0fbe7d854c77a",
  "src/v7_1/candidate2_observability.c": "d7b55e3db75e217dcf322b778511f47de8ccaf2b288b180b7b5761d65854ddb0",
  "include/clo_dsf_revised.h": "ceb615c0c7fdcca62e9d354e9ce9d438a616360c82555d34271bfb70e2314a23",
  "include/scheduler_stress.h": "fad142d4ec73101839e28fe6614b04169860bde690135750bb2ef796fdb72281",
  "include/clo_final_sparse_math.h": "461cdd57bf792d53efe75dc29cef6d441f24bfb64392052c9421801bac286bc8",
  "include/calibration_trace.h": "af4341b1e6ebc1a1c715ddb9e68e388a4a57354bf15858504932b52380cf2e90",
  "include/logger.h": "a9cbcff8b36a1ca75594a5f283a63dfadcf2fb3460c88345c89ce5fe2ab7eb57",
  "include/clo_final_observation_io.h": "af3df00c1262e63246e2b10ae5d180e5c9f9b7dcbe4caac241159a9cdca99142",
  "include/timing_safety_monitor.h": "b30c251737a0ce06fd320ee8684d5557ed7de984ecb04cc22cd53781083f6e9c",
  "include/diagnostics.h": "7cf690e3de1e183153a0e4518881ca9aa180983481e5bbc951b149f08259999b",
  "include/sensors.h": "b429f6bfaa51d386ea557648fb82dfef391d45cc771b5e832956a8ef3b0f37fa",
  "include/ds_evidence.h": "b9798ed2445e3db970bd6e6a23a2a7af12752d908fdf05511fe062bcd515a65c",
  "include/fault_injection.h": "e2dc9375f400d3505b0bf84cb5938e9c9547c0417efe7ffcbe5ae377168d1789",
  "include/cross_layer_fault.h": "7865bcb55c7bec755aaf4a28073de8aa2b6b687cfa1d336a5bbd597c2fb1dd0f",
  "include/runtime_timing_observation.h": "93abae40373360d6fc824b887b459a33e830ced88951838b8489a7a95bb09565",
  "include/fault_model.h": "0ea6dacb24bbffa5192a252f12fec5fa9ffc73d9c46309fe84e7758a8e0bb56b",
  "include/memory_diagnostic_backend.h": "0ec43b9c0ef43c987e0c95d9ce9151c8c97573688107dde0d0e449ec8f82e095",
  "include/safety_policy_v5.h": "42a78c6ea7893185ea33446b1f039a6640acc4a2bfc0a83782ec56f3c114fcb5",
  "include/safety_monitor.h": "48757ad24c41d5434c1b424f13190ab56f373a812843c249ae9bb6dfef202111",
  "include/experiment.h": "37a13975880f1d259dea1e67d2cf31e4fa49df539bbfd38d75bddb8e3528a3c5",
  "include/redundant_temperature.h": "fdece6f4c7f8abd02f5547413370e80389f8f38e10bfa678b4dd72524e73cf2e",
  "include/clo_dsf_candidate2.h": "921e4caa96c824c72953261cd0bea5a29d0de357e69a9e972f372fe0f1a4bae3",
  "include/detection_algorithm.h": "8230c347415e40d98c7c35f7f3c47654c0bc1257504c60b17d248c5de9431150",
  "include/control.h": "87f885fa76e0d9b3b1bc047323339622e61300588135c2bdd1e92e32a869b7e3",
  "include/clo_dsf_final.h": "151475b2ccbd2b3dd50b06cd64bb6a5932b4b2a74834e59b78c0d4cae421f954",
  "include/runtime_safety_policy.h": "0bd2ef517faa18e28bf0aa451d9417d5ee542cdc6ab3dd15c911667add9cda65",
  "include/ecu_types.h": "9db75d0b7e0c98ec54783eb8bf9491c6b154f5afd2f3a0ae16360ad713066ce4",
  "include/runtime_observation.h": "7fd084b6a4c6e05372858a9ad2c81a42872afae5e2704903c478089c9c8fad91",
  "include/experiment_ground_truth.h": "9d01ad1c5abb042bc8a928f6e369dbbbffe8bea452677a2ed805b835dc393e6c",
  "include/clo_dsf.h": "fb8895897690205ade67bb72474fda72a8bb9397a13bcf054009b8004b2152d7",
  "include/thermal_plant.h": "d8cb4973679426d61d5c22938d3ffbbfd8583e86c62f554fb95734a0c352926b",
  "include/memory_diagnostic.h": "aefb15b66033f3db7022c717b61c57bfa7f047d6ef76afea45e649845486c892",
  "include/actuator_trace.h": "2b630d3b60f6d707d04b40c45670992e028efae548f8bd227db4870e68f0e091",
  "include/config.h": "eb481dc6fe5bca46e1c4a4fef773be421933c33b43ca385c8c88f8e013e16aa7",
  "include/metrics.h": "7dbbfaf3f6781df79c88a8616f3cce046904c15664c2c82d90fa837d35f73c31",
  "include/scheduler.h": "23c91cdec90e92acfd3e04f56cb4a937f1e9c30ea4f19186a306ba8f4ed3d9ea",
  "include/sensor_trace.h": "75da9edb7f8489d59b948807def7d46599b37babf8fe73cb799aa4bdbd816369",
  "include/propagation_monitor.h": "eadcc4c103956b1204ea1c6923da31369b4bf501db8bb2c9c158b0cc14576b1d",
  "include/hazard_model.h": "540ec063274e629312b7d3d777d35c57c901342ef936a41502f8b488f98983da",
  "include/actuators.h": "bafed89c18baf80ad51ff513fc5f95da38831a3407b6d0b78f6afb0c9fd4b461",
  "scripts/run_clo_dsf_fast_redundancy.py": "0c4272f6a608724f827ed053b5bd8edd9c37bf018236d60d0dcafa05e9359de4",
  "results/cross_layer_safety_v7_3_dev/revised.cfg": "6f62e972a27c765cae6a24daf9b7b98fb1513cd46fc226a128d87a6431e73ac7",
  "results/clo_dsf_current/campaign_manifest.csv": "d319b14d975e1bec57749c92d504a79d40bb9ee401c0469b8adb81c8545652da"
}
```

development-train complete; all scientific hashes unchanged.

TRAIN gate PASS: A0 704/816; FAST+SLOW803/816; +99/-0; both slow drift72/72 each, all four preserved origins120/120; benign0/120; wrong0/0. No parameter selection/search/tuning performed. Lock unchanged FAST parameters and proceed to VALIDATION. Overall P95 only modestly reduced,47.645s to45.99s; slow drift still governs tail.

development-validation complete; all scientific hashes unchanged.

VALIDATION retention PASS: A0 468/544; FAST+SLOW535/544 (+67/-0), abrupt111/112 versus44/112; primary/reference slow48/48 each. Four other origins80/80 each; benign0/80; wrong0 runs/0 samples. Silent plant20 to9. Common-mode0/8 remains a limitation; one weak primary step remains missed. No parameter changes after TRAIN/VALIDATION. Overall P95 improves modestly47.40 to45.93s; slow drift itself is unchanged. Retain FAST; both detection margins exceeded.

## Final regression and integrity verification

PASS:325 tests, gcc build, Python compile, git diff --check,48 legacy cases and64 RTL cases. Scientific hashes identical before TRAIN, before VALIDATION, after execution and after regression. Strip only the FAST function and its max-merge call and the entire detector core is byte-identical to the retained A0 snapshot. SLOW, active memory, other-origin contracts, acquisition/consumption consistency and causal precedence unchanged. The adapter changes only append FAST strength/edge-count trace columns. Hybrid/HETIA, sensor model and historical results outside CURRENT are unchanged; all pre-task protected source/document/config/result files verified against captured hashes. GUI session preserved SHA256 3fdf2d807ea8661def7e447ff32be0ccf46d70e160e28390bff81aeffbab957a.

Eight raw/summary CSV parity cases match retained A0 byte-for-byte, spanning all origins, both sensing chains and common-mode. Five focused FAST tests pass: signed/swapped steps; isolated-spike rejection; recurring pulse confirmation and recovery; bounded noise/ramp rejection; missing/gapped acquisition resets.

Production executable rebuilt without temporary ablation objects. Unrelated tracked legacy executables restored to task-start HEAD bytes. Temporary per-run raw data deleted; eight compressed representative traces retained. No commit, push, algorithm-version tree or unseen holdout. Additional state64B, no sensor/hardware changes.

Remaining validation misses: eight common-mode drifts plus fast_redundant_1517, a -0.765C permanent primary offset which did not satisfy FAST confirmation and lies inside SLOW tolerance. No parameter adjustment was made to repair it. Memory effective59/59 (stuck43/43), dormant21/21 retained.

Reproduction of A0: apply the recorded reverse core patch to the current source in temporary storage and verify SHA256 recorded above. Header only gains unused FAST state for A0; A0 initialization/layout uses that shared header. scripts/run_clo_dsf_fast_redundancy.py constructs temporary FAST-only/A0 objects, records a manifest before outcomes, refuses accidental repeat of this completed campaign, and gates validation through /tmp/clo-fast-redundancy/validation_go. Blank context lines in the Markdown reconstruction patch have whitespace normalized for diff hygiene.
