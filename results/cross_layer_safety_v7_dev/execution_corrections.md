# Execution corrections before selection

The first TRAIN execution stopped when the accepted legacy CLI rejected the
`intermittent` behavior token (312 completed TRAIN configurations; no selection or
validation outcomes inspected). The existing `custom_multi` facility now schedules
two transient events separated by a 1000 ms gap for legacy intermittent cohorts.
No injector semantics, evidence mapping, candidate parameters or selection rule
changed. The study is restarted from TRAIN and the failed attempt log is retained.
Benign hot-idle speed offsets were also shifted to nonnegative distinct values to
prevent clamping from duplicating profiles. Reported counts are unique study
configurations; attempted/repeated execution overhead is not additional evidence.

After study completion, the integration adapter's automatic sidecar pathname was
corrected for the legacy CLI form that omits an explicit output CSV. It now uses
`ECU_DEFAULT_LOG_PATH` and rejects truncation. All development commands specify
both output paths explicitly; no detector math, parameters, evidence or study
trajectory changed. This adapter-only fix is covered by a CLI regression test.

## Physical-equivalence audit after analysis

The 912 configuration rows contain **896 distinct physical configurations**.
Permanent deadline misses have no magnitude parameter and ignore finite duration;
three planned severity/duration settings therefore repeat each of eight TRAIN
trajectories (16 redundant runs). They are all in the SAME split group. Their
runtime sidecars are byte-identical, verified in physical_equivalence_groups.csv.
No VALIDATION configuration is redundant under this semantic audit.

The original preregistered tables remain intact. `deduplicated_sensitivity.csv`
recomputes every comparison with one member per equivalent configuration. TRAIN
has 560 distinct configurations instead of 576; VALIDATION remains 336. Removing
the redundant TRAIN runs selects the SAME candidate 1 and leaves its TRAIN macro
coverage at 58.75%. These are deterministic repeats, not independent evidence.
The earlier description of all 912 configurations as distinct was incorrect.
This correction changes no candidate parameters and does not rerun validation.
