# Validation record

HEAD unchanged: a340ca5cf0473d7dc572f7cd63e44fbc25b175a7.
37994 original files unchanged; GUI, integrity/M2, Hybrid/HETIA, physics/control/fault and old results preserved.
1255seen historical reconstruction runs only for root-cause audit; exact original A2 metric parity. Seven preselected new TRAIN cases additionally exercised native gate smoke checks before the registered campaign. NEW TRAIN2400/CAL2400 selected one predefined configuration; VALID3600(1200fault/2400benign) untouched until source/model/selection lock. No validation retuning or alternate-candidate scoring. Frozen SVM unchanged.
No raw traces retained. No unseen, commit or push.
{
  "retained_candidate": true,
  "build": 0,
  "compile": 0,
  "tests": 0,
  "diff_check": 0,
  "legacy": 48,
  "rtl": 64,
  "Hybrid_HETIA_unchanged": true,
  "GUI_unchanged": true,
  "old_scientific_and_results_unchanged": true
}
....................................................................................../home/leonskal/code/virtual-ecu-phd/tests/test_clo_dsf_development.py:71: ResourceWarning: unclosed file <_io.TextIOWrapper name='/home/leonskal/code/virtual-ecu-phd/results/cross_layer_safety_v7_dev/clo_dsf_dev_runs.csv' mode='r' encoding='UTF-8'>
  rows=list(csv.DictReader(path.open()))
ResourceWarning: Enable tracemalloc to get the object allocation traceback
................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 358 tests in 11.981s

OK

