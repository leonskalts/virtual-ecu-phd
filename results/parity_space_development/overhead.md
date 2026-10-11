# Diagnostic-kernel host overhead

{
  "seconds_per_update": {
    "0": 3.173397169025812e-09,
    "1": 5.617298084929225e-08,
    "2": 3.861365528726062e-09,
    "3": 5.8257701915070775e-08
  },
  "parity_delta": 5.299958368026644e-08,
  "memory_delta": 6.879683597002498e-10,
  "combined_delta": 5.5084304746044964e-08,
  "parity_state_bytes": 224,
  "parity_config_bytes": 72,
  "memory_state_bytes": 16,
  "timing_repetitions": 7,
  "streams": 8,
  "repeats_per_timing": 100
}

Four window scores share an eight-element ring. Two-dimensional triangular Cholesky solves; fewer than220 floating adds/multiplies/divides per fully populated update, excluding comparisons/integer bookkeeping. No runtime covariance fitting or matrix inverse. Includes existing memory diagnostic kernel; excludes DS/simulation/CSV. Seven order-balanced host timings, not embedded WCET. Baseline memory121probes/120s;250mscandidate481probes, seven operations/probe, +2520operations. Candidate reuses existing memory diagnostic state; combined incremental mutable state is parity_state_bytes. Memory model writes are atomic, restore verified; no actuation.
