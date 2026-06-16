# Runtime Custom Scenario Matrix

This matrix uses the virtual ECU research simulator. Runtime detectors run inside the C simulation loop, and detector actions are optional research interventions. `observe_only` preserves baseline simulator behavior.

- Scenario: Custom Kalman Fan Test (`custom_kalman_fan_test`)
- Fault events: 1
- Runtime detectors: 6
- Detector actions: 3
- Simulator runs: 18

## Key Findings

- Fastest detected runtime response: cusum at 800.0 ms.
- Lowest descriptive mean maximum coolant: precautionary_cooling / limp_home at 91.71 C (-0.54 C versus observe_only).
- Missed observe-only detection: none.
- Active detector actions changed the final safe-state outcome in 0 of 12 intervention runs.
- Observe-only preserves the virtual ECU simulator's built-in safety behavior.

## Limitations

- Results are deterministic outcomes for one configured custom scenario.
- This is not production ECU validation or real-vehicle validation.
- Thermal differences are descriptive and do not establish statistical significance.

## Reproduction

Use the Runtime Study page's **Run Matrix for Latest Custom Scenario** button to reproduce this exact 5 x 3 comparison from the latest custom configuration.
