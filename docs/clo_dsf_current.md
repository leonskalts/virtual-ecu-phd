# CURRENT final development pass protocol

Registered before the new campaign. No unseen validation or parameter search.
The eight prior isolated +/-1.2 C bias misses were replayed. Acquisition and
consumption agree exactly. Six cases have only onset/recovery excess-slew impulses;
two additionally have small legal-update/thermal residuals of opposite initial sign.
A diagnostic signed fresh-residual accumulator z=0.8*z+signed_excess peaks below
0.481. Constant offsets cancel from differences. Re-counting an old jump as fresh
persistent evidence is not justified. No accumulation mechanism is selected;
the current detector source, header and configuration stay byte-identical.
This rejects this simple mechanism, not all possible observers or noise models.

738 new configurations: four TRAIN operating families (492), two VALIDATION
families (246: 210 faults, 36 benign). Preserve difficult fault magnitudes and
legal calibration updates. Profiles and seeds are new. Audit uniqueness against
prior CURRENT and historical manifests before simulation. Compare actual pre-change
CURRENT, retained CURRENT and frozen Fair Weighted Sum on identical observations.
The retained method keeps the historical CSV name `Revised CLO-DSF`.

Benign workload variations: alternating jitter 0/.02/.05/.10 C, and triangular
variation .6 C over12s or1.2 C over18s with .02/.05 C jitter. Each mode has three
cases per family. This deterministic bounded envelope is not a population noise
model. An opt-in adapter perturbs existing acquisition and consumption values
identically, after the existing sensor step; no pristine value enters inference.
Used only on benign cases, not composed with transport faults. Default zero leaves
all existing simulations unchanged. Reference ECU receives identical workload.

TRAIN gate: no detection losses against pre-change, zero benign/wrong-origin alarms,
all effective memory detected and no dormant memory alarms. No tuning after TRAIN;
repeat reporting on VALIDATION. If no gain, retain eight misses as a documented
sensitivity limit. Report configured legacy behavior honestly: sensor events with
nonzero duration end at start+duration even when labeled permanent by the manifest
(`fault_event_is_active` in fault_injection.c); semantics are not changed here.

Keep aggregate/per-case summaries, inspection summary, validation record and eight
compressed representative traces only. Full regression once at the end: build,
Python compile, diff check, full tests, legacy48, RTL64. Verify GUI, detector core,
Hybrid/HETIA, providers and historical evidence against pre-execution hashes.
No commit or push.
