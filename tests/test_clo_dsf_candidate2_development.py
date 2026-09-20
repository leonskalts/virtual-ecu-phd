"""Audit completed development evidence without executing or tuning validation."""
import csv,hashlib,json,pathlib,sys,unittest
from historical_identity import historical_sha
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_candidate2_development import key,readout,aggregate
OUT=ROOT/'results/cross_layer_safety_v7_1_dev'
def records(path):
 with path.open() as f:
  rows=list(csv.DictReader(f))
 for r in rows:
  for k,v in r.items():
   if not v:r[k]=None;continue
   try:r[k]=float(v) if '.' in v or 'e' in v else int(v)
   except ValueError:pass
 return rows
class Candidate2DevelopmentTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not (OUT/'candidate2_dev_runs.csv').exists():raise unittest.SkipTest('Completed development campaign unavailable')
  cls.rows=records(OUT/'candidate2_dev_runs.csv');cls.specs=records(OUT/'development_split_manifest.csv');cls.selection=json.loads((OUT/'selection_record.json').read_text())
 def test_group_separation_and_counts(self):
  a=[s for s in self.specs if s['partition']=='development-train'];b=[s for s in self.specs if s['partition']=='development-validation']
  self.assertEqual((len(a),len(b)),(744,396));self.assertFalse({s['group'] for s in a}&{s['group'] for s in b})
  self.assertEqual(len({s['run_id'] for s in self.specs}),1140)
 def test_predeclared_source_and_protocol_identity(self):
  pre=json.loads((OUT/'preregistered_protocol.json').read_text())
  for name,digest in pre['source_sha256'].items():self.assertEqual(historical_sha(ROOT/name),digest)
  self.assertEqual(hashlib.sha256((OUT/'selection_protocol.md').read_bytes()).hexdigest(),pre['protocol_sha256'])
  self.assertEqual(hashlib.sha256((OUT/'selected_config.cfg').read_bytes()).hexdigest(),self.selection['selected_config_sha256']);self.assertFalse(self.selection['validation_seen'])
 def test_semantic_duplicate_audit(self):
  audit=json.loads((OUT/'duplicate_audit.json').read_text())
  for key in ['duplicates','candidate1_validation_overlap','benign_profile_duplicates','group_overlap']:self.assertEqual(audit[key],0)
  self.assertEqual(audit['distinct_physical_configurations'],1140)
 def test_train_selection_reproducible(self):
  search=records(OUT/'candidate2_parameter_search.csv');self.assertEqual(len(search),96)
  off=min([r for r in search if r['propagation_bonus']==0],key=lambda r:(key(r,r['candidate']),r['localization_threshold'],r['localization_margin_threshold']))
  self.assertEqual(off['candidate'],self.selection['selected_candidate']);self.assertEqual(sum(r['selected'] for r in search),1)
  method=f"candidate_{off['candidate']}_no_prop";rows=[r for r in self.rows if r['partition']=='development-train' and r['method']==method]
  result=aggregate(readout(rows,off['localization_threshold'],off['localization_margin_threshold']))
  for k in ['detected','silent_plant','correct_localizations','wrong_localizations','unknown']:self.assertEqual(result[k],off[k])
 def test_weighted_selection_train_only(self):
  search=records(OUT/'weighted_sum_parameter_search.csv');self.assertEqual(len(search),12)
  chosen=min(search,key=lambda r:key(r,r['candidate'],False));self.assertEqual(chosen['candidate'],self.selection['weighted_choice'])
 def test_origin_ablation_cannot_change_alarms(self):
  val=[r for r in self.rows if r['partition']=='development-validation'];primary={r['run_id']:r for r in val if r['method']=='Candidate 2'}
  for r in val:
   if r['method'] in ['No origin reliability','Full propagation on','Full propagation off']:
    for field in ['first_alarm_ms','first_post_alarm_ms','alarm_samples','pre_alarm_samples']:self.assertEqual(r[field],primary[r['run_id']][field])
 def test_confusion_preserves_unknown_and_misses(self):
  for r in records(OUT/'candidate2_origin_confusion.csv'):
   self.assertEqual(sum(r[k] for k in ['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR','UNKNOWN','misses']),60)
 def test_runtime_traces_and_metrics_exist(self):
  for s in self.specs:
   for folder,suffix in [('raw','.csv.gz'),('traces','.candidate2.csv.gz'),('metrics','.csv'),('commands','.json')]:self.assertTrue((OUT/folder/(s['run_id']+suffix)).is_file())
 def test_zero_conflict_detection_and_complete_results(self):
  rows=[r for r in self.rows if r['partition']=='development-validation' and r['method']=='Candidate 2'];self.assertEqual(len(rows),396)
  for r in rows:self.assertEqual(r['mean_detection_conflict'],0);self.assertEqual(r['high_detection_conflict_samples'],0)
