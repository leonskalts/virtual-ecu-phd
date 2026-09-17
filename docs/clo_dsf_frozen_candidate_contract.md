# CLO-DSF frozen candidate contract

Candidate 1 is frozen for the **next, independent holdout task**. No holdout dataset
or configuration was created here. This is a development candidate, not accepted
final safety evidence or a claim of superior detection. Do not change parameters,
mappings, sample cadence, mass rule, propagation graph, decision or localization
logic after this contract. Any such change invalidates this candidate identity.

## Required execution

```
make
python3 scripts/verify_clo_dsf_candidate.py
./virtual_ecu_v7 /tmp/example.csv baseline --detector clo_dsf --detector-action observe_only --clo-config results/cross_layer_safety_v7_dev/clo_dsf_candidate.cfg
```

The C convenience defaults are exploratory candidate 0 (Yager). The explicit CFG
above is mandatory for frozen candidate 1 (Dempster). The JSON and CFG parameters
are cross-checked by the verification script. The final legacy evidence lock must
also pass `virtual_ecu.final_evidence.verify_frozen()` before any future study.

## Frozen numerical parameters

```json
{
  "alarm_threshold_confirmed": 0.65,
  "alarm_threshold_suspect": 0.35,
  "confirmation_persistence": 2,
  "conflict_rule": "dempster",
  "ignorance_limit": 0.5,
  "lambda_temporal": 0.8,
  "localization_margin_threshold": 0.15,
  "localization_threshold": 0.55,
  "propagation_bonus": 0.1,
  "propagation_window_ms": 3000,
  "r_direct": 0.9,
  "r_indirect": 0.6
}
```

The full machine-readable contract is
`results/cross_layer_safety_v7_dev/clo_dsf_candidate_config.json`. It records every
evidence transform, subset, absence source, observability class, propagation edge,
activation threshold, cap, temporal cadence, confirmation/localization rule and
conflict fallback. Exact mathematical operations and pseudocode are in
`docs/clo_dsf_algorithm.md`; the static runtime map is in `clo_observability.c` and
its hashed CSV. No injector metadata or reference propagation is a detector input.

## Development justification and limitations

Training selected candidate 1 before validation. Validation: 152/240 detected,
0/96 benign false alarms; 110/166 plant-propagating faults detected, 56 silent;
136/152 correct origin estimates at first alarm, 16 UNKNOWN, zero wrong identified
origins. Sensor/control localization remains unresolved. Macro coverage 63.33%
trails OR (81.67%) and plain DS (65.00%); propagation changes no binary decisions.
There are 152 validation cases with at least one high-conflict step, which
is recorded instead of hidden (this cohort is not identical to the detected cohort). These findings justify testing abstention and
uncertainty on unseen data under the preregistered gate, NOT claiming a coverage
improvement over simple fusion. Weighted Sum is an uncalibrated strict baseline.

The study has 912 configuration executions, 896 distinct physical configurations:
16 redundant TRAIN deadline settings were disclosed in the semantic audit. There
are no equivalent VALIDATION configurations; deduplicated TRAIN selects the same
candidate. No repeated configurations are independent statistical evidence.
TRAIN sidecars show exploratory candidate 0; selected TRAIN candidate-1 scores
come from its actual online C bank. VALIDATION sidecars use frozen candidate 1.

Regression: 48 legacy cases, 64 RTL cases, 141 accepted source/configuration hashes,
5,866 accepted evidence-lock entries and all 16,352 pre-existing result files stay
unchanged. Hybrid/Timing Monitor/HETIA/HT1–HT4 are not retuned. Runtime integration
is additive; GUI labels mark the detector experimental and Hybrid remains default.
Host cost is in `clo_dsf_overhead.json`; embedded WCET claim: NONE.

## SHA-256 identity

| Artifact | SHA-256 |
|---|---|
| `src/v7/clo_dsf.c` | `88908647de871270ebfbcfa7fb13cb3da3371c33c42a41cce0a33dd984655854` |
| `src/v7/clo_observability.c` | `420160ef18797024bf72ceafa4c7f888ff21f15d65cf4326279102a61c64dd1b` |
| `src/v7/clo_runtime.c` | `3f5e1b9ea9710f30029cc404d3bcc0b130e22d4e250c5c2d8540d951bc247079` |
| `src/v7/ds_evidence.c` | `c763e3eb722629779b46b569badb3301cc8accf348b787e9d939f6af60854c92` |
| `include/clo_dsf.h` | `fb8895897690205ade67bb72474fda72a8bb9397a13bcf054009b8004b2152d7` |
| `include/ds_evidence.h` | `b9798ed2445e3db970bd6e6a23a2a7af12752d908fdf05511fe062bcd515a65c` |
| `src/main.c` | `ce81833c12f36aca454251121efc18b835b30fe99cf2e434afd7370ed977e032` |
| `src/scheduler.c` | `80d924e069d55926f6f2485db853ce8de06744c55c0119b640510e7641ec30d9` |
| `src/runtime_observation.c` | `7d61be2aa13aa55438b7112837c9a83bb1c13e67f7341a5192fb44f88cc38b60` |
| `include/runtime_observation.h` | `1c0e3c6dd79fa2ba5534c3647efcf3df8de009f6ba385f1ce52ede3f363bd410` |
| `include/runtime_timing_observation.h` | `93abae40373360d6fc824b887b459a33e830ced88951838b8489a7a95bb09565` |
| `include/config.h` | `eb481dc6fe5bca46e1c4a4fef773be421933c33b43ca385c8c88f8e013e16aa7` |
| `GNUmakefile` | `d889389ab8aed71c84ba9a2e55e012966f266a309aa745d69b092c6afd6b7fae` |
| `studies/clo_dsf_development_v1.yaml` | `e7946c69e6711f6b4c2842b7f6237cb89978c6c068361ea2643933a5d05c59bd` |
| `studies/cross_layer_final_evidence_lock.json` | `0f79878065ffdd4919db2ff635552786ebf4d45a74085600762d548456248466` |
| `docs/clo_dsf_development_protocol.md` | `f1e0a899ddea1dd9fd1f346cc108f7624f2102eb10b2287f57a0617dd33180c8` |
| `docs/clo_dsf_algorithm.md` | `533a4ca5e2f545bbba63bd93b98231fa7dbf24503c0dbb9da2f7c9d2a978680f` |
| `results/cross_layer_safety_v7_dev/runtime_observability_mapping.csv` | `4472f4d5a9c3213d3df65e8835c4e0c7c1ad31cad24fac58e59aaeb656e10337` |
| `results/cross_layer_safety_v7_dev/clo_dsf_candidate_config.json` | `defd37a925420845de974f45aeea519b97199734dfecffe88c7eb7ca20c3f380` |
| `results/cross_layer_safety_v7_dev/clo_dsf_candidate.cfg` | `2a678bb72a8ffb69ee010dd253448faa87d04a1e92b38c6e6d066227077b8293` |
| `results/cross_layer_safety_v7_dev/selected_config.cfg` | `2a678bb72a8ffb69ee010dd253448faa87d04a1e92b38c6e6d066227077b8293` |
| `results/cross_layer_safety_v7_dev/development_split_manifest.csv` | `883db228df066b4689cc02c5564596515d8e58e0f07f746358892bd823e2af22` |
| `results/cross_layer_safety_v7_dev/selection_record.json` | `4a6917b03944e4348961566ea3d16188f016900c2a0c2832fe79a78be253da6e` |
| `python/virtual_ecu/clo_dsf_development.py` | `821d85b42b511be02ac502cb66c9aa1cfa39de16a0d6b60c68c8e5c85e6afc03` |
| `scripts/audit_clo_dsf_development.py` | `9d510d1151bb71219c98a6dae1513fe1b35b6944056d00a322bc19a9f83bea11` |

All changes are intentionally unstaged. No commit or push was performed.
