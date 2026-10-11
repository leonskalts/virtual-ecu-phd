# Pre-evaluation observability qualification

This clarification is made before any secondary outcomes. It does not change any parameter, method, selection rule, input, cohort or execution.

There are two backend strata, not a claim of identical sufficient information for all algorithms:

1. **Full-runtime-input comparison:** CLOVER-ECU and frozen SVM-INT, Logistic Regression and Random Forest share the runtime sensing/integrity architecture. All three learned methods have the identical original 41-feature interface, including explicit integrity availability, status and held FAIL. CLOVER additionally maintains its documented runtime temporal/provenance state; this is part of its method, not injected metadata.
2. **Provider-strength comparison:** Threshold OR, Weighted Sum, Plain DS, EWMA and CUSUM use the frozen six-channel evidence interface. It includes digital integrity FAIL through the sensor provider and M2 through memory. However this reduction does **not** preserve every raw feature or explicit PASS/provenance field. These methods are legitimate classical algorithms on common provider evidence, but their comparison with CLOVER does not isolate decision mathematics under an identical sufficient feature representation. In particular benign-alarm differences may reflect discarded provenance, not an inherently inferior algorithm.

Original A0 remains a third, architectural-ablation stratum. No method is deprived of an entire sensing architecture in the backend comparisons, but "equal observability" must be qualified by the representation actually consumed. Do not call the strength-only comparisons strict full-information equality. Do not invent status-to-mass mapping or inject CLOVER's confirmation rule merely to increase comparator fairness on paper. No unseen outcome informs this qualification.

The preregistered Holm correction over eight backend comparisons is conservative regardless of this interpretation; it does not establish representation equivalence. Read any shorthand "equal-observability" in generated tables/protocol statistical labels subject to this qualification. For the strongest full-runtime comparison, use LR/RF/frozen SVM versus CLOVER. Negative findings and all classical outcomes remain reported.
