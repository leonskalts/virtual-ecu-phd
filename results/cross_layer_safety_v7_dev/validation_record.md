# Cross-Layer Safety v7 validation record

Baseline HEAD: `d757539df55ca5e93fe45c810d3e2c5d6fdf547b` (`main`, `origin/main`).
The preflight log showed only `presets/gui_session_state.json` modified. Its bytes
were hashed before implementation and repeatedly verified unchanged. No staging,
restore/reset/checkout/clean, commit or push was performed.

## Preflight and architectural inspection

- `git status --short`, last 12 commits, diff stat and exact HEAD recorded.
- Baseline `make`, Python compile and `git diff --check`: PASS.
- Complete baseline suite: **145 tests PASS**, log in validation/baseline_tests.log.
- Baseline scientific replays: **48 legacy / 64 RTL PASS** before implementation.
- All 141 accepted scientific source/config hashes and 5,866 accepted evidence
  hashes/file sets verified. Additional snapshot covers **16,352** pre-existing
  result files, including v1–v6, HETIA and RTL. v5/v6 locks remain available.
- Inspected runtime/ground-truth interfaces, scheduler ledger, sensor delivery,
  calibration/control, actuator feedback, thermal plant, diagnostics/detectors,
  timing/propagation monitors, hazard model, logger/metrics, campaign and GUI paths.
- The runtime/ground-truth allowlist and excluded legacy truth-derived signals are
  documented in docs/clo_dsf_algorithm.md. CLO-DSF does not consume diagnostic IDs,
  legacy alarm flags, true coolant, fault metadata or reference propagation.

## Final checks

- `make`: PASS, gcc C11 with `-Wall -Wextra -Wpedantic`, no new warnings.
- Python compile: PASS for GUI, package and new scripts.
- `git diff --check`: PASS.
- Complete suite: **193 tests PASS**, including **48 new tests**; C tests run with
  undefined-behavior sanitizer. Log: validation/complete_tests.log.
- Mathematical tests: hand-computable Dempster/Yager K and mass results, vacuity,
  discounting, belief, plausibility, BetP, invalid inputs and dense-mass properties.
- Channel/mapping tests, forward/incomplete/reverse/future/expired propagation,
  reliability cap, temporal transient/persistent/intermittent/benign/recovery,
  ambiguous/high-ignorance localization, and alarm/readout independence pass.
- Architectural transitive header allowlist and hidden-label runtime invariance
  pass. Old CSV is not fabricated into v7 runtime evidence.
- Post-implementation legacy regression: **48/48**, raw and summary bytes match
  accepted baseline. **64/64 RTL**, every historical field and metric unchanged.
- Eight v5 representative scheduler/fault/response traces reproduce exact bytes.
- Threshold, EWMA, CUSUM, Thermal Observer, Kalman, Hybrid, Timing Monitor,
  HT1–HT4, HETIA, frozen physics, safety, hazard/FTTI/containment unchanged.
- Original v6.2 desktop suite: **181 checks PASS**, 51 screenshots, all output
  redirected under v7. Old v1–v6 and 90-run Detector Study results load correctly.
- New v7 desktop suite: **14 checks PASS**; actual Advanced-mode and Detector Study
  examples execute the v7 binary and load sidecars, separate evaluation ground
  truth, retain Hybrid default, and preserve the session. Display socket access
  required running GUI checks outside the sandbox. Third-party font cache and all
  session writes were redirected to temporary storage. Initial test-harness
  main-loop failures were corrected; the clean final log has no thread exceptions.

## Study and audit

912 configured development simulations: 576 TRAIN, 336 DEVELOPMENT-VALIDATION;
720 faulty / 192 benign. Each monitored run includes an additional fault-free
reference trajectory (912 reference integrations, not independent data).
All algorithms run online on identical observe-only trajectories. The frozen
source/config hashes, methods, assumptions and no-ground-truth boundary remain
separate from evaluator truth.

312 TRAIN simulations completed in an interrupted first attempt before a legacy
CLI behavior error; they were re-executed, not counted as extra study evidence.
See execution_corrections.md. A later audit found 16 redundant TRAIN permanent
single-model deadline settings; **896 distinct physical configurations** remain.
All repeats stay in one split group; VALIDATION has none. Deduplicated TRAIN
selects the same candidate 1 and retains its 58.75% macro coverage. No source or
parameter was retuned after seeing DEVELOPMENT-VALIDATION results.

The final adapter-only pathname fix affects omitted-output-path CLI calls, not
study commands. A regression test covers it. Algorithm math and parameters remain
as evaluated. TRAIN archives contain initial candidate 0 runtime traces; selected
candidate-1 TRAIN metrics were actually computed by the online C bank. VALIDATION
and publication traces use selected candidate 1. Never mix these sidecar rules.

## Candidate and overhead

The preregistered continuation gate passes and candidate 1 is frozen for a new,
independent holdout. This does not establish alarm superiority: OR and plain DS
coverage are higher, propagation contributes no coverage gain, sensor/control
localization is UNKNOWN, and 56 plant-propagating validation cases stay silent.
The JSON, executable CFG and 25 source/config/study hashes are cross-checked by
`scripts/verify_clo_dsf_candidate.py`. No final holdout is created.

Detector state: **824 bytes**, including 512-byte mass function, 160-byte evidence
state, 144-byte output plus counters/alignment. Stack/config/stdio are excluded.
Binary text/data/bss deltas: **15,210 / 264 / 16,192 bytes**; the executable includes
the complete development comparison bank and CLI/evaluator adapter.
Final host medians: baseline 6.772 ms, candidate shadow 13.780 ms for 1,201 ticks;
**103.48% host-evaluated simulation overhead** (30 interleaved measurements,
sidecar formatting to /dev/null, same raw I/O, no reference simulation). An earlier
preliminary measurement was about 78%; host timing is load/cache-sensitive. Neither
measurement is an embedded WCET claim. Raw final samples are retained in
clo_dsf_overhead.json.

Preserved session SHA-256: `3fdf2d807ea8661def7e447ff32be0ccf46d70e160e28390bff81aeffbab957a`.

Final v7 regression: all six representative cases replay byte-identically with
the frozen adapter (raw CSV, C summary, runtime evidence and comparison metrics).
See validation/v7_representative_replay.json. Final accepted result hashes/file
sets rechecked after GUI execution: PASS, 16,352 files.
