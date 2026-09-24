"""Narrow scientific revision checks; historical suite is run once at completion."""
import hashlib,json,pathlib,re,subprocess,tempfile,unittest
from historical_identity import historical_sha
ROOT=pathlib.Path(__file__).resolve().parents[1]
class RevisedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='clo-revised-tests-');cls.exe=pathlib.Path(cls.temp.name)/'test'
  core=['src/v7/ds_evidence.c','src/v7/clo_observability.c','src/v7/clo_dsf.c','src/v7_1/candidate2_evidence.c','src/v7_1/candidate2_observability.c','src/v7_1/clo_dsf_candidate2.c','src/v7_2/clo_dsf_final.c','src/v7_3/clo_dsf_revised.c','src/runtime_observation.c']
  subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-Iinclude','tests/clo_revised_unit.c',*core,'-lm','-o',str(cls.exe)],cwd=ROOT,check=True)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_core_isolation(self):
  source=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text()
  for forbidden in ['ecu_types.h','experiment_ground_truth','cross_layer_fault','faults.','reference_observation','propagation.plant','diagnostic_id','detector_alarm','safety_state']:
   self.assertNotIn(forbidden,source)
  self.assertIn("ds_combine(current,channel,DS_DEMPSTER",source)
 def test_frozen_v72_identity(self):
  path=ROOT/'results/cross_layer_safety_v7_2_confirmation/clo_dsf_final_scientific_hashes.json'
  for name,digest in json.loads(path.read_text())['sha256'].items():
   self.assertEqual(historical_sha(ROOT/name),digest,name)
NAMES=['weak_actuator_contract','varying_healthy_commands','one_ulp_boundary','unavailable_or_unsynchronized','clamping_and_fan','hidden_truth_invariance','unaffected_channel_parity','temporal_recovery_and_diagnostics','small_memory_integrity','authorized_unusual_calibration','dormant_not_evidence','unavailable_and_stale_use','independent_sensor_origin','delivered_jump_abstains','communication_origin_preserved','future_source_abstains','downstream_suppression_and_abstention','quiet_episode_reset','simultaneous_onsets_ambiguous','anomaly_independent_of_precedence','all_direct_provenance_sources','unexcited_actuator_not_recovery','simultaneous_direct_sources_abstain','subambient_excursion_not_recovery','fresh_consumption_provenance','provenance_requires_synchronous_observation','weak_opposing_pulses','monotonic_excess_not_pulse','gapped_acquisitions_not_pulse','legal_slew_and_fresh_consumption','response_positive_step','response_bounded_noise','response_negative_step','response_missing_provenance','response_operating_transition']
for i,name in enumerate(NAMES):
 def test(self,index=i):subprocess.run([str(self.exe),str(index)],check=True,capture_output=True)
 setattr(RevisedTests,'test_'+name,test)

def campaign_integrity(self):
 out=ROOT/'results/cross_layer_safety_v7_3_dev'
 if not (out/'selection_record.json').exists():self.skipTest('Campaign not executed')
 import csv
 with (out/'development_split_manifest.csv').open() as f:rows=list(csv.DictReader(f))
 self.assertEqual(len(rows),1125)
 train={r['group'] for r in rows if r['partition']=='development-train'};val={r['group'] for r in rows if r['partition']=='development-validation'}
 self.assertFalse(train&val)
 self.assertFalse(json.loads((out/'selection_record.json').read_text())['validation_seen'])
 for name,digest in json.loads((out/'preregistered_development.json').read_text())['source_sha256'].items():self.assertEqual(historical_sha(ROOT/name),digest,name)
 self.assertEqual((out/'revised.cfg').read_bytes(),(ROOT/'results/cross_layer_safety_v7_2_confirmation/final_reference.cfg').read_bytes())
RevisedTests.test_campaign_isolation_and_preregistration=campaign_integrity
