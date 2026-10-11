# TRAIN / CALIBRATION record

Source: the existing `clo_dsf_current/multirate_manifest.csv`, SHA256
`e84ba3b6eb319b579f1da5c8504bf7b5acd69195df9c775ef5ced326efd6516b`.
Only its TRAIN1200 (960fault/240benign) and CALIBRATION750 (600/150) partitions
were reused, with original group separation. Its VALIDATION partition was excluded.
All 1950 configuration identities were checked against the repository manifest.
No previous final unseen outcome was used for selection or training.

Replay uses the frozen retained 100ms architecture, not the rejected multi-rate
providers. All 1200 TRAIN physical-output and CURRENT-trace hashes exactly match
the prior development execution; `replay_equivalence.json` records the check.
Every C sample also passes the original frozen CURRENT full-state equality assertion.
One simulation per case supplied both evidence contracts and all replay baselines.

SVM: 16,275 TRAIN frames, 9,600 inactive/benign and 6,675 active fault frames.
Uniform-within-case/time-stratum sampling was predeclared; class_weight=balanced
handles frame-count imbalance. StandardScaler fitted separately on TRAIN C1/C2.
The predeclared linear C=.1, linear C=1 and RBF C=1 gamma=scale family was evaluated
on complete CALIBRATION traces. Selected linear C=.1 independently for C1 and C2;
zero decision threshold. SVM localization intentionally NOT PROVIDED.
Software/model hashes and actual installed versions are recorded in svm_fit_record.json.

Weighted Sum independently selected [2,2,2,1,2,1], threshold .14 in both C1 and C2.
Weights normalize over AVAILABLE inputs. Selection followed the preregistered order:
minimum benign alarm runs, maximum macro recall, minimum P95 latency, candidate order.
The benign-first criterion is conservative: it can prefer loss of weak standalone
sensor detection to even one benign alarm. No claim is made that this is a universal
optimal operating point. Full candidate results are in calibration_selection.csv.

CALIBRATION selected-method results (fault600,benign150):

| Input/method | Detected | Benign alarm runs | Wrong-origin runs |
|---|---:|---:|---:|
| C1 CURRENT | 517 | 1 | 1 |
| C1 OR | 505 | 1 | 13 |
| C1 Plain DS | 505 | 1 | 13 |
| C1 Weighted Sum | 442 | 0 | 0 |
| C1 SVM | 535 | 35 | NOT PROVIDED |
| C2 TRIPLEX | 538 | 1 | 1 |
| C2 OR | 537 | 1 | 13 |
| C2 Plain DS | 537 | 1 | 13 |
| C2 Weighted Sum | 442 | 0 | 0 |
| C2 SVM | 548 | 35 | NOT PROVIDED |

No threshold rescue was attempted for SVM benign alarms. These are findings under
the predeclared limited model family, not a claim that every SVM operating point
would behave this way. Baseline settings were locked BEFORE the fresh validation.
The post-validation freeze will seal those same settings, not select alternatives.
