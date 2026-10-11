# Analytical-reference independence: PASS

`tests/test_analytical_thermal.py` compiles the C module with gcc C11, `-O2 -Wall -Wextra -Werror`. Across 1,200 updates, two states receive identical non-coolant inputs while one is subjected to arbitrary A/B/C consistency readouts. Their entire state bytes remain identical; consistency evaluation does not mutate prediction. The predictor input structure has no coolant sensor, physical state, fault label or injection fields.

The same test checks zero evidence for model-consistent readings, single-member abnormal support, UNKNOWN for coherent global discrepancy, ignorance for conflicting all-member residuals, increased-bound suppression and invalid-readout suppression. The production Triplex/core/controller/plant sources remain untouched. This tests direct independence; later control-command effects remain physically legitimate.

Command: `python3 tests/test_analytical_thermal.py` — 1 test passed.

Causal command timing additionally tested: changing a newly issued pump command does not change the current prediction; its effect appears on the following update. Stored previous commands increase predictor state from16 to32bytes.
