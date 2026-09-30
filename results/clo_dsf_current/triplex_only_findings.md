# Final triplex-only validation: promotion rejected

All 480 previously locked fault-validation cases completed once, A0/A1 only, with identical physical observations. The completed 120 benign cases were reused. Outcomes were inspected only after completion. No scientific source, thresholds, sensor model, fusion, localization, locked manifest or GUI bytes changed. A2 remains permanently rejected and was neither linked nor evaluated. No unseen holdout, commit or push.

Original space: A0 347/400 (86.75%, Wilson 83.08–89.73%); A1 361/400 (90.25%, Wilson 86.95–92.79%). Expanded space: A0 383/480 (79.79%, Wilson 75.97–83.14%); A1 426/480 (88.75%, Wilson 85.61–91.27%). The primary >=91% gate fails: three further original detections would have been required. No automatic promotion at >90%.

Original paired comparison: both347, A0-only0, A1-only14, neither39; exact two-sided McNemar p=0.0001220703125. All fourteen gains are AB common-mode; weak-step/pulse subgroup gains overlap this category and are not independent additional gains. No original detections lost. Expanded: both383, A0-only0, A1-only43, neither54; p=2.2737367544323206e-13.

AB common-mode improves 10/24 to24/24. Original plant-propagating detection improves170/180 to180/180, silent misses10 to0. Expanded plant detection185/204 to195/204, silent misses19 to9. Both methods have0/120 benign alarms, zero wrong confident origins, and100% first and localized-runtime accuracy. UNKNOWN runtime samples653 for each method, from existing uncertainty semantics. Timing80/80, communication80/80 and effective memory54/54 unchanged.

Limitations: original actuator detection50/80, including33/33 initially excited and17/47 initially unexcited; memory75/80; sensor76/80. Global ABC remains4/16, C-only29/32. Original P95 latency increases29.9s to34.6s when additional detections are included; this does not demonstrate latency improvement. Expanded P95 increases39.6s to42s.

No further refinement. A1 is not promoted; CURRENT A0 remains retained. Not ready to freeze triplex for a new unseen holdout. Full regression was conditional on passing retention and was therefore not run. Detailed original/expanded metrics and subgroup denominators are in triplex_only_summary.csv and triplex_only_subgroups.csv. Per-case sufficient statistics are retained without raw trajectories. Previous development and rejected-latch artifacts remain untouched.
