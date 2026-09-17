# Candidate 2 validation record

Status: PASS — completed development evaluation; no new candidate freeze and no final holdout.

- Committed baseline: d757539df55ca5e93fe45c810d3e2c5d6fdf547b.
- Initial Candidate 1 working tree, all its sources/configuration/evidence and user session are byte-identical. Final preservation audit: 21792 of 21794 existing files unchanged; only Makefile and scripts/virtual_ecu_gui.py receive additive Candidate 2 integration. The original Candidate 1 GNUmakefile and GUI modules remain unchanged.
- Accepted lock: 141 source/configuration entries and 5866 evidence entries pass; HETIA, v1–v6, Hybrid, timing and HT1–HT4 remain unchanged.
- Legacy regression: 48 cases against compiled accepted baseline, raw/summary bytes match.
- RTL regression: 64 cases, all historical fields/metrics match (relocated output paths excluded).
- Representative v5 replay: eight accepted cases, byte-identical raw/summary/event files.
- Candidate 1 replay: six origins/cohorts, byte-identical raw/summary/evidence/metrics. Six additional new-cohort comparisons verify the Candidate 1 bank matches its frozen executable.
- Build: make passes without warnings. Python compile of scripts/virtual_ecu_gui.py and python/virtual_ecu/*.py passes. git diff --check passes. No staged diff.
- Complete test suite: 228 tests PASS, including numerical frame algebra, temporal behavior, hidden injector-label invariance, independent detection/origin outputs, strict configuration parsing, feature parity and development selection audits.
- Desktop: 17 Candidate 2 checks PASS and 181 unchanged legacy desktop checks PASS. Advanced and Research examples execute C; historical and Candidate 1 results load; CONFIRMED + UNKNOWN displays normally. Session/history/export writes are redirected. Local display access required sandbox escalation; approved desktop checks did not alter user files.
- Runtime trace audit: 396 selected-validation runs, 475596 rows. Normalized masses, five-origin logical BetP/margin, binary positive support, state/timestamp consistency and online metric agreement pass. There are 1603 confirmed-UNKNOWN runtime rows.
- Campaign: 1140 unique configurations, TRAIN 744, VALIDATION 396. No semantic duplicates, no group leakage, no exact Candidate 1 validation overlap. Validation executed once after selection; raw commands and traces retained.
- Predeclared runtime source, study, protocol and selected-config hashes remain identical after validation. Weighted Sum and Candidate 2 selected before validation. No scientific parameter or algorithm changes after validation.
- Reporting correction only: selected TRAIN .55/.15 localization readout matches its online bank; actual later-localization timestamps were recovered from that bank (243 correct localizations before plant). This changes no selection objective, runtime or validation output. Historical search-table later-localization placeholders were not used for selection; see reporting_adjustments.json.
- Host overhead: 30 interleaved samples plus warmup per mode, recorded with raw samples. No embedded WCET claim.
- Final disposition: selected origin discounting is dominated on measured decision endpoints by the no-origin-discount ablation; fair Weighted Sum matches binary detection. Do not freeze or silently simplify using this validation. Candidate 1 remains frozen. candidate2_development_hashes.json seals reproducible evidence only, not a final-holdout candidate contract.

Commands and complete output are retained in validation/ and the scripts directory. The final git status is in validation/final_git_status.txt. No git add, commit, push, reset, restore, checkout or clean was run.
