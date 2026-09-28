import pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class QualificationTests(unittest.TestCase):
 def test_shared_startup_and_early_direct_faults(self):
  with tempfile.TemporaryDirectory() as tmp:
   exe=pathlib.Path(tmp)/'unit'
   core=['src/v7/ds_evidence.c','src/v7/clo_observability.c','src/v7/clo_dsf.c','src/v7_1/candidate2_evidence.c','src/v7_1/candidate2_observability.c','src/v7_1/clo_dsf_candidate2.c','src/v7_2/clo_dsf_final.c','src/v7_3/clo_dsf_revised.c','src/runtime_observation.c']
   subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Iinclude','tests/sensor_qualification_unit.c',*core,'-lm','-o',str(exe)],cwd=ROOT,check=True)
   subprocess.run([str(exe)],check=True)
