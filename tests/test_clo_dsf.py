"""Mathematics, runtime dynamics, isolation and additive build regression."""
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE = ['src/v7/ds_evidence.c', 'src/v7/clo_observability.c', 'src/v7/clo_dsf.c']


class CloDsfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='clo-tests-')
        cls.exe = pathlib.Path(cls.temp.name) / 'test'
        subprocess.run(['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1',
                        '-fsanitize=undefined', '-Iinclude', 'tests/clo_dsf_unit.c',
                        *CORE, 'src/runtime_observation.c', '-o', str(cls.exe)], cwd=ROOT, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_transitive_runtime_dependency_allowlist(self):
        allowed = {'clo_dsf.h', 'ds_evidence.h', 'runtime_observation.h', 'runtime_timing_observation.h', 'config.h'}
        pending = [ROOT / p for p in CORE]
        visited = set()
        while pending:
            path = pending.pop()
            if path in visited:
                continue
            visited.add(path)
            source = path.read_text()
            for name in re.findall(r'#include\s+"([^"]+)"', source):
                self.assertIn(name, allowed)
                pending.append(ROOT / 'include' / name)
            if path.suffix == '.c':
                for forbidden in ['diagnostic_id', 'detector_alarm', 'safety_state', 'experiment_ground_truth',
                                  'cross_layer_runtime', 'fault_active', 'reference_observation', 'propagation_monitor']:
                    self.assertNotIn(forbidden, source)

    def test_v7_disabled_is_byte_identical(self):
        subprocess.run(['make'], cwd=ROOT, check=True, capture_output=True)
        paths = [pathlib.Path(self.temp.name) / 'old.csv', pathlib.Path(self.temp.name) / 'new.csv']
        for exe, path in zip(['virtual_ecu', 'virtual_ecu_v7'], paths):
            subprocess.run([str(ROOT / exe), str(path), 'baseline', '--simulation-duration-ms', '2000'], check=True, capture_output=True)
        self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
        self.assertEqual(paths[0].with_name('old_summary.csv').read_bytes(), paths[1].with_name('new_summary.csv').read_bytes())


_NAMES = ['empty_normalize', 'vacuous', 'vacuous_combination', 'dempster_hand_example', 'yager_hand_example',
          'total_conflict', 'discounting', 'belief_plausibility_pignistic', 'invalid_mass', 'timing_channel',
          'communication_channel', 'memory_channel', 'sensor_channel', 'actuator_channel', 'plant_subset',
          'reliability_unavailable', 'forward_propagation', 'incomplete_propagation', 'reversed_propagation',
          'future_propagation', 'single_transient', 'persistent_and_localization', 'intermittent', 'long_benign',
          'ambiguous_localization', 'high_ignorance_localization', 'duplicate_timestamp', 'hidden_label_invariance',
          'config_validation', 'future_packet_unavailable', 'recovery', 'localization_does_not_change_alarms',
          'dense_mass_properties', 'propagation_cap', 'propagation_expiry']
for _index, _name in enumerate(_NAMES):
    def _test(self, index=_index):
        subprocess.run([str(self.exe), str(index)], check=True, capture_output=True)
    setattr(CloDsfTests, 'test_' + _name, _test)
