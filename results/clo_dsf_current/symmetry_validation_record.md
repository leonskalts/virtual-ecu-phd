# Symmetry audit validation record

HEAD: 1bc6b12d970acc702dea62ad2507f5709a5254cc

No detector source changes. Scientific source/header/config hashes and GUI bytes unchanged. Exact lock in symmetry_lock.json. TRAIN150 and CALIBRATION150 completed before validation generation/freeze. VALIDATION600 completed once with A0/A1 only; outcomes inspected after completion. No A2 campaign or unseen campaign. Case counts480fault+120benign. Historical validation findings/manifests retained unchanged.

Permutation test: PASS, nine scenarios; existing memory diagnostic checks7/7. Full regression PASS:339 tests, forced build, Python compile, git diff --check,48 legacy and64 RTL. Historical results including Hybrid/HETIA verified byte-for-byte unchanged before/after regression. Source and header integrity includes Hybrid/HETIA; preexisting runtime binaries restored after regression. No commit or push.

Retention gates all pass on new validation, including>=91% original and zero wrong confident origins. A1 is eligible to freeze; no post-outcome production integration or algorithm edits. Previous90.25% result is preserved and not invalidated by this new91.04% cohort. New reporting scripts and tests only; temporary raw work removed. Four preexisting compressed representative traces retained; none added.

Frozen validation manifest SHA256: 784b7f6a54a712b9a8de3103f0fc1ce834317b52e91121f3165f071779c0a1f2
