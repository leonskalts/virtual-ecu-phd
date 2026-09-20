"""Runtime provider boundaries and current group-wise scientific design."""
import subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_current import design
from historical_identity import SUPERSEDED, historical_sha
class CurrentTests(unittest.TestCase):
    def test_provider_contains_sensor_errors_and_no_hidden_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'provider'
            sources=[str(p) for p in sorted((ROOT/'src').glob('*.c')) if p.name!='main.c']
            subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-Iinclude','tests/current_observation_unit.c',*sources,'-o',str(exe)],cwd=ROOT,check=True,capture_output=True)
            subprocess.run([str(exe)],check=True,capture_output=True)
    def test_groupwise_unique_design(self):
        specs=design();self.assertEqual(len(specs),738)
        self.assertEqual(len({s['configuration_sha256'] for s in specs}),738)
        train=[s for s in specs if s['partition']=='development-train'];valid=[s for s in specs if s['partition']=='development-validation']
        self.assertEqual((len(train),len(valid)),(492,246))
        self.assertFalse({s['group'] for s in train}&{s['group'] for s in valid})
        self.assertEqual(sum(s['initially_latent_stuck'] for s in specs),90)
        for part in [train,valid]:
            for origin in ['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR','NORMAL']:
                self.assertEqual({s['workload'] for s in part if s['origin']==origin},{'static_target','authorized_updates'})
    def test_historical_exceptions_do_not_include_evidence_or_legacy(self):
        self.assertFalse(any(p.startswith('results/') for p in SUPERSEDED))
        for name in ['src/detection_algorithm.c','src/safety_monitor.c','src/timing_safety_monitor.c','src/cross_layer_fault.c','src/sensor_delivery.c']:
            self.assertNotIn(name,SUPERSEDED)
            self.assertEqual(historical_sha(ROOT/name),__import__('hashlib').sha256((ROOT/name).read_bytes()).hexdigest())
