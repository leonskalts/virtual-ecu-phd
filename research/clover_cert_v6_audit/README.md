# CLOVER-CERT v6 source provenance and temporal audit

This is a source audit, not a diagnostic/synthesis implementation. All new files
are under `research/clover_cert_v6_audit/`; existing source and results are read-only.
Start with [audit_verdict.md](audit_verdict.md), then inspect the anchors and cases.

| File | Purpose |
|---|---|
| [source_inventory.md](source_inventory.md) | Commit/build scope, source hashes, paths, functions, exact tokens and 1-based lines |
| [fault_provenance_manifest.json](fault_provenance_manifest.json) | CLOVER_CERT_V6 provenance/evidence/timing/domain/case model |
| [runtime_oracle_boundary.md](runtime_oracle_boundary.md) | Published model data versus labels/truth and oracle-derived outputs |
| [temporal_paths.md](temporal_paths.md) | Actual scheduling/propagation paths and all five ambiguity analyses |
| [unresolved_assumptions.md](unresolved_assumptions.md) | Explicit VERIFIED/INFERRED/UNVERIFIED obligations |
| [audit_verdict.md](audit_verdict.md) | Findings, modeling candidates and claim limits |
| [validate_manifest.py](validate_manifest.py) | Dependency-free structural/source validator, mutation tests and preservation check |
| [validation_report.json](validation_report.json) | Actual validation errors, unresolved findings, tests and preservation result |
| [workspace_baseline.json](workspace_baseline.json) | Hash/size inventory of every pre-existing outside-audit file, including ignored outputs |
| [git_status_before.txt](git_status_before.txt) / [git_status_after.txt](git_status_after.txt) | Working-tree context, including existing user changes |

From the repository root:

```bash
python3 research/clover_cert_v6_audit/validate_manifest.py --self-test --check-preservation
```

The full preservation check streams about 13.6 GB locally. It neither executes nor
imports production code, compiles binaries, runs experiments, or rewrites source.
The baseline and status files preserve the audit snapshot; do not replace them
merely to make a later comparison pass. A newly changed checkout should be reported
as a different snapshot.

Default exit 0 means the manifest is structurally/source consistent, even when
its qualified research conclusion is UNKNOWN. Exit 1 means a structural/source,
self-test or requested preservation failure. `--strict-unresolved` returns exit 2
when unresolved findings remain. Validation reports are written only in this audit
directory. Exact tokens are literal substrings on the specified source line;
function/context names were reviewed during the source inspection. Their presence
does not constitute a formal proof of C semantics or hardware trust.

The manifest covers 19 confirmed source/template paths and five critical cases.
It is not a universal audit of every untracked development algorithm, nor a proof
that optional templates were linked into a particular historical executable. No
novelty or publication-readiness claim follows from this audit.
