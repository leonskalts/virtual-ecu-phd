# Frozen diagnostic benchmark

The benchmark adds Python replay backends around the existing C observer harness;
it does not replace a production detector. `scripts/run_comparative_benchmark.py`
uses the frozen Triplex builder with a read-only export callback in temporary build
sources. No repository scientific C source is changed. The observer's existing
full-state CURRENT-versus-historical equality assertion remains enabled.

`virtual_ecu.comparative_backends.Evidence` is the interface: monotone runtime
sample timestamps and six-channel strength, availability and origin-subset arrays.
Backends return one alarm and origin subset per sample. They cannot access a case
specification, injection parameters, fault label, hidden plant state or future
sample. Only the scoring/training layer receives case metadata. CURRENT and
TRIPLEX remain online C executions; conventional methods safely replay the same
causal evidence. Deduplicating identical feature rows for an instantaneous SVM
changes cost, not predictions. There is no interpolation or look-ahead in inference.

| Method | Provider temporal preprocessing | Additional temporal fusion | Localization | Supervised |
|---|---|---|---|---|
| OR | Shared frozen providers | None | Single qualified origin; ambiguous abstention | No |
| Weighted Sum | Shared frozen providers | None | Dominant singleton contribution | No |
| Plain classical DS | Shared frozen providers | None | Conventional pignistic decision | No |
| SVM | Shared frozen providers | None | Not provided | TRAIN only |
| CURRENT | Frozen pre-Triplex providers | Frozen temporal DS and causal provenance | Frozen | No |
| TRIPLEX | Frozen final providers including C | Frozen temporal DS and causal provenance | Frozen | No |

The two comparisons must remain separate. C1 exposes pre-Triplex providers to all
applicable methods; C2 exposes final providers to all applicable methods. Neither
comparison is a claim that raw measurements alone suffice for the conventional
baselines: they inherit the substantial provider engineering. No correlated C pair
is counted as an extra DS source. C1/C2 WS and SVM are calibrated independently;
their cross-input difference therefore includes calibration. OR and Plain DS have
identical parameters across C1/C2, and CURRENT/TRIPLEX use identical frozen fusion.

The detailed predeclared grid, selection criterion, qualification and statistical
semantics are in `results/comparative_benchmark/protocol.md`. Scikit-learn is an
experiment-only dependency (SVC/StandardScaler). This run uses the existing isolated
installation `/tmp/clo-ml-deps`; exact observed versions are recorded in
`svm_fit_record.json`. No dependency is added to the ECU build.

Execution order (each phase is guarded against accidental repeated execution):

```sh
python3 scripts/run_comparative_benchmark.py setup
python3 scripts/run_comparative_benchmark.py run TRAIN
python3 scripts/run_comparative_benchmark.py fit
python3 scripts/run_comparative_benchmark.py run CALIBRATION
python3 scripts/run_comparative_benchmark.py select
python3 scripts/run_comparative_benchmark.py run VALIDATION
python3 scripts/freeze_comparative_benchmark.py
python3 scripts/run_comparative_benchmark.py run UNSEEN
python3 scripts/report_comparative_benchmark.py
```

The existing completed final-unseen directories are never regenerated or replaced.
New validation and unseen manifests are audited against current files, Git history,
archived campaign identities and explicit benchmark TRAIN/CAL/VALID identities.
Raw files are deleted after every case. A compact sufficient-statistics CSV supports
paired and localization audits. Pickled SVM models are local trusted artifacts;
loading a model is not a supported interface for untrusted external input.
