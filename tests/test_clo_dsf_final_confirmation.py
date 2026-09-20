"""Frozen confirmation integrity, exact optimization and paired-analysis checks."""
import csv,hashlib,json,pathlib,subprocess,tempfile,unittest,sys
from historical_identity import historical_sha
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_final_reporting import records,paired,wilson
OUT=ROOT/'results/cross_layer_safety_v7_2_confirmation'
class FinalConfirmationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not (OUT/'final_candidate_runs.csv').exists():raise unittest.SkipTest('Confirmation not available')
  cls.rows=records(OUT/'final_candidate_runs.csv')
 def test_fixed_source_hashes(self):
  for name in ['preregistered_confirmation.json','clo_dsf_final_scientific_hashes.json']:
   manifest=json.loads((OUT/name).read_text());hashes=manifest.get('sha256',manifest.get('source_sha256'))
   for p,h in hashes.items():self.assertEqual(historical_sha(ROOT/p),h,p)
 def test_authoritative_parameters(self):
  p=json.loads((OUT/'parameter_provenance.json').read_text());c2=dict(line.split('=') for line in (ROOT/p['source']).read_text().splitlines())
  for k,v in p['copied_exact_lexical_values'].items():self.assertEqual(v,c2[k])
  self.assertEqual(p['weighted_choice'],json.loads((ROOT/'results/cross_layer_safety_v7_1_dev/selection_record.json').read_text())['weighted_choice'])
 def test_no_physical_overlap(self):
  for r in records(OUT/'configuration_overlap_audit.csv'):self.assertEqual(r['exact_overlap'],0)
  self.assertEqual(len(records(OUT/'confirmation_configuration_manifest.csv')),900)
 def test_simplification_all_runs(self):
  final={r['run_id']:r for r in self.rows if r['method']=='Final CLO-DSF'}
  for r in self.rows:
   if r['method']=='Candidate 2 no origin discount':
    for key in ['first_alarm_ms','first_post_alarm_ms','first_localization_ms','origin_at_alarm','first_origin','alarm_samples','mean_anomaly_ignorance','mean_origin_ignorance']:self.assertEqual(r[key],final[r['run_id']][key])
 def test_replay_complete_bit_identical(self):
  r=json.loads((OUT/'benchmark/equivalence.json').read_text());self.assertEqual(r['runs'],900);self.assertEqual(r['observations'],1080900);self.assertTrue(r['bit_identical_complete_state']);self.assertEqual(r['decision_discrepancies'],0)
 def test_paired_denominators(self):
  for name in ['Weighted Sum','Simple OR','Candidate 2']:
   p=paired(self.rows,name);self.assertEqual(sum(p[k] for k in ['both_detect','only_a','only_b','neither']),720)
 def test_confusion_denominators(self):
  for r in records(OUT/'final_candidate_origin_confusion.csv'):self.assertEqual(sum(r[k] for k in ['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR','UNKNOWN','misses']),144)
 def test_wilson_extremes(self):
  low,high=wilson(0,180);self.assertEqual(low,0);self.assertGreater(high,0)
  low,high=wilson(462,462);self.assertLess(low,1);self.assertAlmostEqual(high,1)
  self.assertEqual(wilson(0,0),(None,None))
 def test_exact_sparse_generic_math(self):
  with tempfile.TemporaryDirectory(prefix='final-sparse-test-') as t:
   exe=pathlib.Path(t)/'test';subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-O2','-fsanitize=undefined','-Iinclude','tests/final_sparse_unit.c','src/v7_2/final_sparse_math.c','src/v7/ds_evidence.c','src/v7_1/candidate2_observability.c','-o',str(exe)],cwd=ROOT,check=True);subprocess.run([str(exe)],check=True)
 def test_excluded_attempt_disclosed(self):
  p=OUT/'validation/invalid_attempt_01';self.assertTrue((p/'failure.log').exists());self.assertEqual(len(list((p/'commands').glob('*.json'))),16);self.assertTrue((OUT/'campaign_correction.md').exists())
