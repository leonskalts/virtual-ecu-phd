"""Independent reference and signed-window evidence contracts."""
import pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class RedundantTemperatureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='active-memory-unit-');cls.exe=pathlib.Path(cls.tmp.name)/'unit'
  objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
  objects += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_3/clo_dsf_revised.o']]
  subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Iinclude','tests/redundant_temperature_unit.c',*objects,'-lm','-o',str(cls.exe)],cwd=ROOT,check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_reference_model_has_no_primary_or_fault_dependency(self):
  code=(ROOT/'src/redundant_temperature.c').read_text()
  for token in ['ecu_types','coolant_source','cross_layer','faults.','control.']:
   self.assertNotIn(token,code)
for i,name in enumerate(['independent_state_noise_calibration','legal_disagreement_and_thermal_ramp','slow_drift','symmetric_evidence_and_missing_reset','common_mode_and_conversion_failure']):
 def test(self,index=i):subprocess.run([str(self.exe),str(index)],check=True,capture_output=True)
 setattr(RedundantTemperatureTests,'test_'+name,test)
