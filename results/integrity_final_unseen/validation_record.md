# Execution and regression record

One frozen unseen cohort:1800 unique configurations,1200 faults/600 benign. No reruns or tuning. All source/config/model/generated-executable hashes verified before and after outcomes and regression. Historical files, Hybrid/HETIA and GUI unchanged.

HEAD: a340ca5cf0473d7dc572f7cd63e44fbc25b175a7

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
Ran 358 tests in 11.085s

OK
