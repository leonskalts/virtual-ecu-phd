# Diagnostic-kernel host overhead

{
  "seconds_per_update": {
    "0": 3.4388009991673605e-09,
    "1": 9.102549958368027e-07,
    "2": 3.990424646128227e-09,
    "3": 9.083524146544546e-07
  },
  "cp_delta": 9.068161948376354e-07,
  "memory_delta": 5.516236469608662e-10,
  "combined_delta": 9.049136136552873e-07,
  "cp_state_bytes": 5752,
  "cp_config_bytes": 184,
  "memory_state_bytes": 16,
  "timing_repetitions": 7,
  "streams": 8,
  "repeats_per_timing": 100,
  "host_platform": "Linux-6.6.87.1-microsoft-standard-WSL2-x86_64-with-glibc2.35",
  "compiler": "gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0",
  "cdf_readonly_bytes": 27680460
}

H1:50 two-dimensional cumulative additions and squared norms/divisions (~300 floating operations),48 onset comparisons. H2:reuses first12 interval scores, scans534 fully populated recent intervals (comparisons and indexing); no recomputed interval sums. H3:70 weighted two-dimensional terms, two slope fits and two triangular solves (~300 floating operations). Empirical tails:three binary searches,≤ceil(log2(N+1)) comparisons each; combination/mapping includes logs, expm1 and fixed Cauchy terms. Finite recent interval history is not an alarm latch. CDF immutable storage is separate from bounded mutable rolling state. No runtime covariance fitting or inverse. Seven order-balanced host timings, not embedded WCET; excludes DS/simulation/CSV. Baseline memory121probes/120s;250mscandidate481probes, seven operations/probe, +2520operations. Candidate reuses existing memory state. Atomic save/test/restore; no actuation.

Compiled diagnostic state accounting (one retained core, two Triplex pair states, one memory state; excludes ECU plant/controller and immutable model/configuration):
```json
{
  "retained_core_state_bytes": 4304,
  "triplex_pair_state_bytes": 8656,
  "memory_state_bytes": 16,
  "cp_state_bytes": 5752,
  "baseline_diagnostic_state_bytes": 12976,
  "combined_diagnostic_state_bytes": 18728
}
```
