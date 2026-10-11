# Host overhead

{
  "seconds_per_update": {
    "0": 3.681307243963364e-09,
    "1": 2.1317235636969192e-07,
    "2": 4.309950041631973e-09,
    "3": 2.1990840965861781e-07
  },
  "dynamic_delta": 2.0949104912572854e-07,
  "memory_delta": 6.286427976686089e-10,
  "combined_delta": 2.1622710241465444e-07,
  "dynamic_state_bytes": 344,
  "config_bytes": 120,
  "memory_bytes": 16,
  "core_bytes": 4304,
  "triplex_bytes": 8656,
  "baseline_state_bytes": 12976,
  "combined_state_bytes": 13320,
  "M2_phase_storage_bytes": 101,
  "integration_scalar_bytes": 24,
  "total_persistent_including_integration_bytes": 13445,
  "filters": 5,
  "state_dimension": 2,
  "host": "Linux-6.6.87.1-microsoft-standard-WSL2-x86_64-with-glibc2.35",
  "compiler": "gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0",
  "repetitions": 7,
  "streams": 8,
  "repeats": 100,
  "initial_unmatched_seconds_per_update": {
    "0": 3.708368026644463e-09,
    "1": 2.1369275603663613e-07,
    "2": 1.7745628642797668e-09,
    "3": 2.142797668609492e-07
  },
  "benchmark_correction": "M0/M1/M2 diagnostic functions compiled in separate translation units with identical callback visibility and no LTO; prevents optimizer removal/inlining of only the M2 callback transaction. Diagnostic algorithm and selected schedule unchanged."
}

Five2D predict/update filters; each uses three scalar measurement likelihood contributions, one rank-one determinant/solve and one healthy-set scalar update. No dense matrix inverse, dynamic allocation or temporal history arrays. Per update:15 residual/variance contributions,5 two-state predictions/covariance predictions,5 scalar posterior updates,15 variance logs and5 log1p; four fault exp terms and one logsumexp. Robust choice adds up to10 bounded healthy innovation weights/square roots. qhealthy/mass use two exponentials. Three symmetric covariance scalars/filter. Constant-velocity scalarized operations, not a physical-temperature predictor. M0 121probes/120s; M1/M2 481,7 operations/probe,+2520operations. M2 adds100boolean phase table plus one initialization flag and first-call deterministic construction, excluded from steady per-update comparison only when initialization amortized. Host timings include callback tests/state updates, exclude DS/simulation/CSV; no embedded WCET claim.


The primary timing values use the matched separate-translation-unit benchmark. Initial unmatched timings are retained transparently and are not evidence of a negative memory cost. Corrected benchmark source/command and all28 timing rows are embedded in calibration.json. This is a measurement correction, not a detector or parameter change.
