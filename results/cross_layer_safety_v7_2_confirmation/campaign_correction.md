# Invalid configuration attempt — retained and excluded

The first attempt stopped on final_0016: memory bit 6 is outside the existing injector range 0..5. Sixteen simulations had completed; their results were not inspected for scientific outcomes. The complete partial attempt, original study/protocol and failure log are retained under validation/invalid_attempt_01 and excluded from confirmation results.

Inspection of the unchanged C validator also found non-aligned proposed task delays (150/550 ms) and communication delays (150/850 ms). Before any further outcome inspection, the invalid settings were corrected to bit 5, task delays 200/600 ms, and communication delays 200/900 ms. Both base onsets were changed to 30500/72500 ms to avoid reusing any partially executed configuration. All other cohort rules remain fixed. This is correction of illegal injector configurations, not detector or baseline tuning.

The corrected cohort is checked with the unchanged C configuration parser/validator before registration/execution, and exact overlap with the 16 completed invalid-attempt configurations is checked. Scientific reference source, all detector parameters and Weighted Sum configuration remain byte-identical to the original preregistration. No final holdout is involved. This erratum is included in the corrected preregistration and final scientific record.
