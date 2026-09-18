"""Pre-outcome checks of holdout design and fixed statistical summaries."""
import csv,json,math,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_holdout import design,profile_identity,physical,ORIGINS,prepare_work,PROFILE_COLUMNS
from virtual_ecu.clo_dsf_holdout_reporting import pair,summary
from virtual_ecu.clo_dsf_final_reporting import wilson
class HoldoutTests(unittest.TestCase):
 def test_unique_balanced_design(self):
  rows=design();self.assertEqual(len(rows),1500);self.assertEqual(len({r['configuration_sha256'] for r in rows}),1500)
  for origin in ORIGINS:self.assertEqual(sum(r['origin']==origin for r in rows),240)
  self.assertEqual(sum(r['origin']=='NORMAL' for r in rows),300)
 def test_semantic_profile_not_spelling(self):
  self.assertEqual(profile_identity([dict(start_ms='0',value='1.00')]),profile_identity([dict(value=1,start_ms=0.0)]))
 def test_ignored_permanent_duration(self):
  s=dict(model='fan_stuck_off',behavior='permanent',start_ms=100,duration_ms=1,magnitude=0)
  self.assertEqual(physical(s,'same'),physical({**s,'duration_ms':999,'magnitude':77},'same'))
 def test_profile_materialization_keeps_c_column_order(self):
  spec=design()[0]
  with tempfile.TemporaryDirectory() as temp:
   work=Path(temp);prepare_work(work,[spec])
   with (work/'profiles'/(spec['profile']+'.csv')).open() as f:
    reader=csv.DictReader(f);self.assertEqual(reader.fieldnames,PROFILE_COLUMNS)
    actual=list(reader);expected=json.loads(spec['profile_json'])
    self.assertEqual([{k:float(v) for k,v in row.items()} for row in actual],expected)
 def test_wilson_known_bounds(self):
  lo,hi=wilson(0,100);self.assertAlmostEqual(lo,0);self.assertAlmostEqual(hi,.03699349820698568)
  lo,hi=wilson(100,100);self.assertAlmostEqual(lo,.9630065017930143);self.assertAlmostEqual(hi,1)
  self.assertEqual(wilson(0,0),(None,None))
 def test_paired_exact_and_sparse_discordance(self):
  def sample(n):return [dict(run_id=str(i),method=m,injected=1,detected=int(m=='Revised CLO-DSF')) for i in range(n) for m in ['Revised CLO-DSF','Weighted Sum']]
  self.assertIsNone(pair(sample(9),'Weighted Sum')['exact_mcnemar_p'])
  r=pair(sample(10),'Weighted Sum');self.assertEqual(r['only_clo_dsf'],10);self.assertEqual(r['only_comparator'],0);self.assertEqual(r['exact_mcnemar_p'],2/1024)
if __name__=='__main__':unittest.main()
