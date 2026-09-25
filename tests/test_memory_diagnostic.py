"""Active readback contract, restoration, cadence and evidence freshness."""
import pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class MemoryDiagnosticTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='active-memory-unit-');cls.exe=pathlib.Path(cls.tmp.name)/'unit'
  objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
  objects += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_3/clo_dsf_revised.o']]
  subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Iinclude','tests/memory_diagnostic_unit.c',*objects,'-lm','-o',str(cls.exe)],cwd=ROOT,check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_no_truth_in_generic_checker(self):
  code=(ROOT/'src/memory_diagnostic.c').read_text()
  for token in ['ecu_types','cross_layer','fault_model','bit_index','reference','plant','target_shadow']:
   self.assertNotIn(token,code)
for i,name in enumerate(['all_clean_values_restore','all_stuck_polarities_and_recovery','period_and_legal_updates','bit_flip_is_not_stuck','evidence_freshness']):
 def test(self,index=i):subprocess.run([str(self.exe),str(index)],check=True,capture_output=True)
 setattr(MemoryDiagnosticTests,'test_'+name,test)
