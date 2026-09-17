"""Candidate 2 frame algebra, observational invariance and additive integration."""
import pathlib
import re
import subprocess
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
CORE=['src/v7/ds_evidence.c','src/v7/clo_observability.c','src/v7/clo_dsf.c',
      'src/v7_1/candidate2_evidence.c','src/v7_1/candidate2_observability.c','src/v7_1/clo_dsf_candidate2.c']
class Candidate2Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='candidate2-tests-');cls.exe=pathlib.Path(cls.temp.name)/'unit'
  subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-Iinclude','tests/candidate2_unit.c',*CORE,'src/runtime_observation.c','-o',str(cls.exe)],cwd=ROOT,check=True)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_dependency_isolation(self):
  allowed={'clo_dsf_candidate2.h','clo_dsf.h','ds_evidence.h','runtime_observation.h','runtime_timing_observation.h','config.h'}
  pending=[ROOT/p for p in CORE];seen=set()
  while pending:
   p=pending.pop()
   if p in seen:continue
   seen.add(p);s=p.read_text()
   for name in re.findall(r'#include\s+"([^"]+)"',s):self.assertIn(name,allowed);pending.append(ROOT/'include'/name)
   if p.suffix=='.c':
    for word in ['diagnostic_id','detector_alarm','safety_state','fault_active','experiment_ground_truth','reference_observation','cross_layer_runtime']:self.assertNotIn(word,s)
 def test_disabled_compatibility(self):
  subprocess.run(['make'],cwd=ROOT,check=True,capture_output=True)
  paths=[pathlib.Path(self.temp.name)/f'{i}.csv' for i in range(2)]
  for exe,p in zip(['virtual_ecu','virtual_ecu_v7_1'],paths):subprocess.run([str(ROOT/exe),str(p),'baseline','--simulation-duration-ms','2000'],capture_output=True,check=True)
  self.assertEqual(paths[0].read_bytes(),paths[1].read_bytes())
 def test_candidate1_manifest_unchanged(self):subprocess.run(['python3','scripts/verify_clo_dsf_candidate.py'],cwd=ROOT,capture_output=True,check=True)
 def test_strict_complete_config(self):
  config=ROOT/'results/cross_layer_safety_v7_1_dev/selected_config.cfg'
  if not config.exists():self.skipTest('Development selection not available')
  base=config.read_text();path=pathlib.Path(self.temp.name)/'bad.cfg'
  for text in [base+'r_detection=1\n',base.replace('r_detection=1','r_detection=nan'),base.replace('r_detection=1\n',''),base+'unknown=1\n']:
   path.write_text(text)
   result=subprocess.run([str(ROOT/'virtual_ecu_v7_1'),str(pathlib.Path(self.temp.name)/'invalid.csv'),'baseline','--c2-config',str(path)],capture_output=True)
   self.assertNotEqual(result.returncode,0)
NAMES=['logical_frame_algebra','plant_alarm_unknown','timing_localizes','sensor_ambiguity','origin_cannot_gate_detection','forward_propagation','reversed_propagation','incomplete_propagation','long_benign','recovery','duplicate_time','hidden_label_invariance','candidate1_feature_parity','invalid_config','unavailable','threshold_boundary','ignorance_abstention','injector_truth_invariance','origin_hand_computation','confirmation_persistence','localization_threshold','localization_margin']
for i,name in enumerate(NAMES):
 def test(self,index=i):subprocess.run([str(self.exe),str(index)],capture_output=True,check=True)
 setattr(Candidate2Tests,'test_'+name,test)
