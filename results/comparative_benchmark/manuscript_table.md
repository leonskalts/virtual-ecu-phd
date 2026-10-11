# Comparative unseen: frozen methods, one physical execution per case

C1 excludes Sensor C; C2 includes C-derived evidence. All methods share frozen temporal evidence preprocessing. SVM localization is not provided. CIs and paired tests are descriptive for grouped deterministic scenarios.

| Method | Supervised | Extra C | Detection | Wilson 95% | Plant detection | Benign FPR | Precision | Median/P95 | First localized accuracy (coverage) | Runtime localized accuracy | Wrong runs/samples | Runtime UNKNOWN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 CURRENT | no | no | 1051/1200 (87.58%) | 85.60–89.33% | 679/730 | 0/300 (0.00%) | 100.00% | 0/13.1 s | 100.00% (100.00%) | 100.00% | 0/0 | 0.65% |
| C1 OR | no | no | 1022/1200 (85.17%) | 83.04–87.07% | 650/730 | 0/300 (0.00%) | 100.00% | 0/31.9 s | 100.00% (100.00%) | 99.97% | 33/82 | 0.01% |
| C1 Plain DS | no | no | 1022/1200 (85.17%) | 83.04–87.07% | 650/730 | 0/300 (0.00%) | 100.00% | 0/31.9 s | 100.00% (100.00%) | 99.97% | 33/82 | 0.00% |
| C1 SVM | yes | no | 1090/1200 (90.83%) | 89.07–92.34% | 703/730 | 46/300 (15.33%) | 95.95% | 0/1.96 s | NOT PROVIDED | — | — | — |
| C1 Weighted Sum | no | no | 888/1200 (74.00%) | 71.44–76.40% | 584/730 | 0/300 (0.00%) | 100.00% | 0/0.4 s | 100.00% (100.00%) | 100.00% | 0/0 | 0.00% |
| C2 OR | no | yes | 1089/1200 (90.75%) | 88.98–92.26% | 716/730 | 0/300 (0.00%) | 100.00% | 0/43.6 s | 100.00% (100.00%) | 99.97% | 33/82 | 0.01% |
| C2 Plain DS | no | yes | 1089/1200 (90.75%) | 88.98–92.26% | 716/730 | 0/300 (0.00%) | 100.00% | 0/43.6 s | 100.00% (100.00%) | 99.97% | 33/82 | 0.00% |
| C2 SVM | yes | yes | 1118/1200 (93.17%) | 91.60–94.46% | 730/730 | 49/300 (16.33%) | 95.80% | 0/29.8 s | NOT PROVIDED | — | — | — |
| C2 TRIPLEX | no | yes | 1089/1200 (90.75%) | 88.98–92.26% | 716/730 | 0/300 (0.00%) | 100.00% | 0/33.7 s | 100.00% (100.00%) | 100.00% | 0/0 | 0.62% |
| C2 Weighted Sum | no | yes | 888/1200 (74.00%) | 71.44–76.40% | 584/730 | 0/300 (0.00%) | 100.00% | 0/0.4 s | 100.00% (100.00%) | 100.00% | 0/0 | 0.00% |
