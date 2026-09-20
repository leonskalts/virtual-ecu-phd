"""Final reference numerics, observation isolation and preservation boundaries."""
import json,pathlib,re,subprocess,tempfile,unittest,hashlib
from historical_identity import historical_sha
ROOT=pathlib.Path(__file__).resolve().parents[1]
CORE=['src/v7/ds_evidence.c','src/v7/clo_observability.c','src/v7/clo_dsf.c','src/v7_1/candidate2_evidence.c','src/v7_1/candidate2_observability.c','src/v7_1/clo_dsf_candidate2.c','src/v7_2/clo_dsf_final.c']
class FinalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='clo-final-tests-');cls.exe=pathlib.Path(cls.temp.name)/'unit'
  subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-Iinclude','tests/clo_final_unit.c',*CORE,'src/runtime_observation.c','src/v7_2/final_observation_io.c','-o',str(cls.exe)],cwd=ROOT,check=True)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_dependency_isolation(self):
  allowed={'clo_dsf_final.h','clo_dsf_candidate2.h','clo_dsf.h','ds_evidence.h','runtime_observation.h','runtime_timing_observation.h','config.h'};pending=[ROOT/p for p in CORE];seen=set()
  while pending:
   p=pending.pop()
   if p in seen:continue
   seen.add(p);source=p.read_text()
   for name in re.findall(r'#include\s+"([^"]+)"',source):self.assertIn(name,allowed);pending.append(ROOT/'include'/name)
   if p.suffix=='.c':
    for word in ['diagnostic_id','detector_alarm','safety_state','fault_active','experiment_ground_truth','reference_observation','cross_layer_runtime']:self.assertNotIn(word,source)
 def test_historical_hashes(self):
  for name in ['results/cross_layer_safety_v7_dev/clo_dsf_candidate_hashes.json','results/cross_layer_safety_v7_1_dev/candidate2_development_hashes.json']:
   for path,digest in json.loads((ROOT/name).read_text())['sha256'].items():self.assertEqual(historical_sha(ROOT/path),digest,path)
 def test_removed_decision_parameters(self):
  source=(ROOT/'src/v7_2/clo_dsf_final.c').read_text().split('void clo_final_step',1)[1]
  for word in ['r_direct','r_indirect','propagation_bonus','propagation_transitions','propagation_window']:self.assertNotIn(word,source)
NAMES=['timing','communication','memory','actuator','sensor_unknown','plant_unknown','diagnostic_noninterference','long_benign','recovery','persistence','threshold','margin','duplicate_timestamp','hidden_truth_invariance','candidate2_no_discount_equivalence','observation_csv_roundtrip','invalid_config']
for i,name in enumerate(NAMES):
 def test(self,index=i):subprocess.run([str(self.exe),str(index)],check=True,capture_output=True)
 setattr(FinalTests,'test_'+name,test)
