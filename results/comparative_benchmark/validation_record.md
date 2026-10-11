# Comparative benchmark validation record

Frozen retained commit: a340ca5cf0473d7dc572f7cd63e44fbc25b175a7.
All 221 prior freeze scientific/GUI file hashes matched before any execution.
Previous final unseen artifacts remain untouched. No detector tuning, commit or push.

Protocol was written and hashed before TRAIN. TRAIN1200/CAL750 reuse was verified
against the legitimate development manifest, with its old validation excluded.
All 1950 reused executions match prior physical-output and CURRENT-trace hashes.
The frozen CURRENT full-state equality assertion passed on every sample.

The twelve Weighted Sum choices and three SVM choices were selected only on CAL.
The selection lock predates fresh VALIDATION750 (600fault/150benign). No configuration
change followed validation. C1 CURRENT524, OR509, DS509, WS444, SVM544 detections;
C2 TRIPLEX544, OR544, DS544, WS444, SVM558. All benign alarms0 except SVM16/150.
CLO wrong-origin runs0, OR/DS16, WS0; SVM localization not provided.

method_freeze.json seals selected settings, features, thresholds, model hashes,
TRAIN/CAL manifest hashes and implementation files. unseen_lock.json records the
subsequently generated manifest hash, seed formula and historical overlap audit.
The fresh unseen partition is disjoint from all benchmark train/cal/validation
profiles, configurations and seeds, separately from the historical audit.

No collection failure or outcome-triggered rerun occurred in TRAIN/CAL/VALIDATION.
One simulator experiment (including its normal scoring counterfactual) per case,
shared by every applicable method. No six-way duplicate physical executions.

Final regression and unseen completion records are appended after execution.

UNSEEN completed once:1500 cases=1200fault+300benign. All ten comparison rows per
case share physical/trace hashes and post-hoc plant/effect classifications.
No execution failures, retries, retuning or method changes. SHA256 and seed are in
unseen_lock.json. Post-hoc scoring qualification for SVM memory case0750 is documented
in findings.md; registered metric remains unchanged.

Final regression PASS:337tests,build,Python compile,diff check,48legacy,64RTL.
221 frozen scientific/GUI files, previous final unseen artifacts and37244 protected
historical files unchanged. Method lock unchanged. Binaries restored to initial bytes.
Execution counts:TRAIN1200,CAL750,VALID750,UNSEEN1500=4200, each physical case once.
Zero retained raw traces; no commit/push or staging. See regression.json and
execution_audit.json. Duplicate derived summaries removed after equivalent final
CSV creation; validation SVM localization is explicitly NOT PROVIDED.
