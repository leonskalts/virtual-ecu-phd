# v7.3 validation record

PASS. One final full regression pass, with focused revision tests beforehand.
Frozen development candidate only. No final paper holdout created or executed.

- Baseline: 30e48538cc063cb62f3363c7075c0650c6a4642f. Initial git status/session identity retained.
- 18927 pre-existing tracked file identities verified; zero changes. User session byte-identical. Candidate 1/2/v7.2 manifests and v1–v6 accepted locks PASS; Hybrid/HETIA unchanged.
- Builds: original make and make -f clo_dsf_revised.mk PASS without warnings. Python compile PASS. git diff --check PASS. Nothing staged.
- Complete suite: 269 tests PASS, including new contract, finite/cadence/rounding boundaries, hidden-label invariance, unchanged-channel parity, diagnostic separation, group isolation and preregistration.
- Legacy regression: 48 cases against compiled accepted baseline, raw/summary bytes identical.
- RTL regression: 64 cases, all historical fields and comparison outcomes unchanged. Temporary replay artifacts were discarded after comparison; their hashes and verification records remain. No duplicate historical traces retained.
- Frozen comparator integration: six TRAIN cases spanning all origins/benign replayed through original v7.2. All seven common comparator metrics match exactly, including original Weighted Sum and v7.2.
- Registered new development cohort: 1,125 unique, TRAIN 735, VALIDATION 390; zero physical historical overlap and zero model/behavior group leakage. No parameter search. All C configurations validated before simulation; a pre-simulation duplicate-profile draft was corrected before registration.
- TRAIN passed the fixed contradiction gates; selection_record.json was written with validation_seen=false and unchanged source/configuration hashes before VALIDATION. All registered valid runs completed once. No post-validation scientific edits.
- Validation: 260/300 detection, 198/204 plant-propagating detection, six silent plant cases, zero benign alarms in 90, 200 correct localized outputs, 60 UNKNOWN, zero wrong origins at any runtime sample; latency 0/200 ms median/P95.
- Minimum ablation: v7.2 to revised changes only actuator evidence. Eight extra detections/correct origins and eight fewer silent plant cases; no detection losses, no extra false alarms. Nine cases detected only by revised versus frozen Weighted Sum, zero only by Weighted Sum.
- Scope: benefits are weak intermittent pump degradations, under the simulator's synchronous ideal response contract. No hardware/generalization/DS-superiority/statistical-significance claim. Remaining six pump misses have zero command during both injected intervals; all remaining silent plant misses are communication.
- Reporting refinement only: final findings explicitly distinguish those unexcited pump cases and narrow gain family. Frozen algorithm/configuration/registered generator were never edited after TRAIN/VALIDATION.
- Exact allowlisted inputs, per-run online metrics, commands and raw/summary/trace hashes retained; no screenshots, GUI modifications or unnecessary full trace copies. No embedded benchmark claim.

Frozen contract: docs/clo_dsf_revised_frozen_contract.md.
Config: clo_dsf_revised_config.json and revised.cfg.
Manifest: clo_dsf_revised_hashes.json includes complete historical dependencies and all new source/artifacts. Verify with python3 scripts/freeze_clo_dsf_revised.py --verify.
No git add, commit, push, reset, restore, checkout or clean was performed.
