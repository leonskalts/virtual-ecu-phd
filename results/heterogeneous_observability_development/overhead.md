# Host diagnostic-kernel overhead

{
  "seconds_per_update": {
    "0": 3.857202331390508e-09,
    "1": 4.996877601998334e-09,
    "2": 1.5910699417152374e-08,
    "3": 1.7708159866777685e-08
  },
  "analytical_delta": 1.2053497085761866e-08,
  "memory_delta": 1.1396752706078265e-09,
  "combined_delta": 1.3850957535387178e-08,
  "predictor_state_bytes": 32,
  "config_bytes": 96,
  "memory_state_bytes": 16,
  "scope": "matched diagnostic kernels on 8 seen TRAIN benign streams, 5 order-balanced repetitions, 100 repeats per timing; excludes DS/simulation/CSV; no embedded WCET"
}

10Hz updates. Predictor: bounded eight multiply-accumulates plus input transformations/Euler update; consistency: three normalized residuals and bounded comparisons, no matrix solver at runtime. Parameters identified offline. Baseline memory mean1000ms/max1100ms; candidate mean250ms/max300ms. Over120s baseline121probes847operations; candidate481probes3367operations, +2520operations. Four reads/three writes per atomic probe, including restoration verification. Existing memory state is reused; analytical mutable state is additional. Config is read-only. This is incremental host diagnostic-kernel timing, not full-controller timing or embedded WCET.
