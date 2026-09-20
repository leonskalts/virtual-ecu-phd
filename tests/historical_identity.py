"""Historical identities after the explicitly authorized CURRENT in-place revision.

Only these superseded implementation files use the pre-change Git snapshot.
Archived results and all protected legacy algorithms still check working bytes.
This is not a claim that the current working tree satisfies historical freezes.
"""
import hashlib
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PRECHANGE = 'ee51591d749fbe212cfcf5c0ac95addea96c5549'
SUPERSEDED = frozenset({
    'include/clo_dsf_revised.h', 'include/ecu_types.h', 'include/control.h', 'include/runtime_observation.h',
    'src/control.c', 'src/sensors.c', 'src/runtime_observation.c',
    'tests/test_clo_dsf_candidate2.py', 'tests/test_clo_dsf_candidate2_development.py',
    'tests/test_clo_dsf_final.py', 'tests/test_clo_dsf_final_confirmation.py',
    'tests/test_clo_dsf_revised.py',
    'src/v7_3/clo_dsf_revised.c', 'src/v7_3/revised_runtime.c', 'clo_dsf_revised.mk',
})
def historical_sha(path):
    name = str(Path(path).relative_to(ROOT))
    data = subprocess.check_output(['git', 'show', f'{PRECHANGE}:{name}'], cwd=ROOT) if name in SUPERSEDED else Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()
