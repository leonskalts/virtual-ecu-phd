"""Legal scheduler behavior, frozen rules, statistical and paired endpoints."""
import csv,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.validation_v5_design import expand,load_config,source_hashes,OUTPUT
from virtual_ecu.validation_v5_metrics import wilson,duration,intervention_cost,NativeAblation,paired,percentile
from virtual_ecu.validation_v5_recovery import horizon_row

class ValidationV5Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)
 def simulate(self,kind='legal',**options):
  path=self.path/'trace.csv';cmd=[str(ROOT/'virtual_ecu'),str(path),'baseline','--v5-policy',options.pop('policy','observe_only'),'--scheduler-stress',kind,'--scheduler-events',str(self.path/'events.csv'),'--simulation-duration-ms','6000']
  for k,v in options.items():cmd+=['--scheduler-'+k.replace('_','-'),str(v)]
  subprocess.run(cmd,check=True,capture_output=True)
  with path.open() as f:return list(csv.DictReader(f))
 def test_legal_seeded_jitter_is_quiet(self):
  for seed in [11,29,47]:
   trace=self.simulate(seed=seed,release_jitter_ms=25,start_jitter_ms=25,execution_ms=30)
   self.assertEqual(trace[-1]['timing_monitor_detected'],'0');self.assertEqual(trace[-1]['scheduler_first_violation_ms'],'')
   self.assertEqual(trace[-1]['runtime_safety_first_request_ms'],'')
 def test_near_and_exact_deadline_are_legal(self):
  for execution in [99,100]:
   trace=self.simulate(execution_ms=execution)
   self.assertEqual(trace[-1]['timing_monitor_detected'],'0')
   self.assertEqual(trace[0]['scheduler_minimum_completion_margin_ms'],'')
   with (self.path/'events.csv').open() as f:self.assertTrue(all(int(r['contract_margin_ms'])>=0 for r in csv.DictReader(f)))
 def test_queue_conservation_and_real_completions(self):
  trace=self.simulate('overload',overload_execution_ms=550,stress_start_ms=1000,stress_duration_ms=2100)
  for r in trace:
   self.assertEqual(int(r['scheduler_release_count']),int(r['scheduler_completion_count'])+int(r['scheduler_rejected_count'])+int(r['scheduler_queue_count']))
  self.assertGreater(int(trace[-1]['scheduler_rejected_count']),0)
  with (self.path/'events.csv').open() as f:events=list(csv.DictReader(f))
  done=[e for e in events if e['rejected']=='0']
  for e in events:
   if e['rejected']=='1':self.assertEqual(e['actual_release_ms'],'');self.assertEqual(e['actual_start_ms'],'');self.assertEqual(e['completion_ms'],'')
  self.assertEqual(len(done),int(trace[-1]['scheduler_completion_count']))
  for e in done:self.assertLessEqual(int(e['actual_release_ms']),int(e['actual_start_ms']));self.assertEqual(int(e['completion_ms'])-int(e['actual_start_ms']),int(e['execution_duration_ms']))
 def test_short_overrun_separates_deadline_from_age(self):
  trace=self.simulate('overload',overload_execution_ms=101,stress_start_ms=1000,stress_duration_ms=100)
  alarms=NativeAblation(self.path/'bridge').replay(trace)
  self.assertEqual(alarms['combined'],1100);self.assertEqual(alarms['deadline_only'],1100);self.assertIsNone(alarms['execution_age_only'])
  self.assertEqual(trace[-1]['scheduler_rejected_count'],'0')
 def test_overload_is_not_injected_fault(self):
  trace=self.simulate('overload');self.assertEqual(trace[-1]['cross_layer_fault_enabled'],'0')
  self.assertEqual(trace[-1]['fault_injection_ms'],'');self.assertEqual(trace[-1]['timing_monitor_detected'],'1')
 def test_invalid_legal_envelope(self):
  with self.assertRaises(subprocess.CalledProcessError):self.simulate(execution_ms=101)
 def test_different_seeds_change_real_jitter(self):
  self.simulate(seed=11,release_jitter_ms=25);a=(self.path/'events.csv').read_bytes()
  self.simulate(seed=29,release_jitter_ms=25);self.assertNotEqual(a,(self.path/'events.csv').read_bytes())
 def test_frozen_manifest_matches_sources(self):
  manifest=json.loads((OUTPUT/'timing_monitor_contract.json').read_text())
  self.assertEqual(manifest['source_sha256'],source_hashes());self.assertEqual(manifest['primary_monitor'],'combined')
 def test_holdout_combinations_and_no_fake_legal_seed_replicates(self):
  config=load_config();runs=expand(config)
  self.assertEqual(len(runs),1833)
  self.assertTrue(all(p['id'].startswith('holdout_') for p in config['profiles']))
  self.assertTrue(set(config['injection_times_ms']).isdisjoint({20100,60100,90100,150100,220100}))
  timing=[r for r in runs if r['study_kind']=='timing' and r['policy']=='observe_only'];self.assertEqual(len(timing),714)
  signatures={(r['profile']['id'],r['model'],json.dumps(r['parameters'],sort_keys=True),json.dumps(r.get('stress',{}),sort_keys=True)) for r in timing}
  self.assertEqual(len(signatures),714)
  self.assertEqual(sum(r.get('stress_kind')=='legal' for r in timing),156)
  self.assertTrue(all(r['parameters']['duration_ms']==100 for r in runs if r['model']=='deadline_miss' and r['parameters']['behavior']=='transient'))
 def test_matched_temporal_grid(self):
  rows=[r for r in expand(load_config()) if r['study_kind']=='matched'];self.assertEqual(len(rows),135)
  for match in {r['match_id'] for r in rows}:
   group=[r for r in rows if r['match_id']==match];self.assertEqual(len(group),5)
   self.assertEqual(len({r['parameters']['bit_index'] for r in group}),1)
   self.assertEqual(len({r['parameters']['start_ms'] for r in group}),1)
 def test_wilson_boundaries_and_known_values(self):
  self.assertEqual(wilson(0,0),(None,None));lo,hi=wilson(0,100);self.assertAlmostEqual(lo,0);self.assertAlmostEqual(hi,.0369935,places=6)
  lo,hi=wilson(100,100);self.assertAlmostEqual(lo,.9630065,places=6);self.assertAlmostEqual(hi,1)
  lo,hi=wilson(5,10);self.assertAlmostEqual(lo,.2365931,places=6);self.assertAlmostEqual(hi,.7634069,places=6)
  with self.assertRaises(ValueError):wilson(2,1)
 def test_duration_uses_completed_intervals(self):
  trace=[{'time_ms':str(t),'safe_state_id':str(s)} for t,s in [(0,0),(100,2),(250,2),(400,0)]]
  self.assertEqual(duration(trace,lambda r:r['safe_state_id']=='2'),300)
  self.assertEqual(duration(trace,lambda r:r['safe_state_id']=='2',200,300),100)
  self.assertEqual(intervention_cost(trace)['safe_state_activations'],1)
 def test_recovery_horizon_na_and_stable_tail(self):
  trace=[{'time_ms':str(t),'hazard_warning_active':'0','containment_success':'1' if t>=1000 else '0','containment_time_ms':'1000' if t>=1000 else '', 'hazard_entered':'0','critical_exposure_time_ms':'0','safe_state_id':'1','coolant_temp_true_c':'95'} for t in range(0,2100,100)]
  self.assertEqual(horizon_row(trace,0,1500)['stable_below_warning_latency_ms'],1000)
  self.assertEqual(horizon_row(trace,0,1500)['containment_success'],1)
  self.assertIsNone(horizon_row(trace,None,1000)['containment_success']);self.assertIsNone(horizon_row(trace,0,3000)['containment_success'])
 def test_percentile_missing_is_na(self):
  self.assertIsNone(percentile([]));self.assertAlmostEqual(percentile([0,100]),95)
 def test_graded_policy_does_not_access_ground_truth(self):
  source=(ROOT/'src/safety_policy_v5.c').read_text()
  for forbidden in ['ecu_types','fault','hazard','scenario','scheduler_stress']:self.assertNotIn(forbidden,source)
 def test_graded_legal_workload_no_false_request(self):
  trace=self.simulate(policy='graded',release_jitter_ms=1,start_jitter_ms=1,execution_ms=98)
  self.assertEqual(trace[-1]['timing_monitor_detected'],'0');self.assertEqual(trace[-1]['runtime_safety_first_request_ms'],'')
 def test_frozen_design_hash_and_legacy_domain(self):
  import hashlib
  from virtual_ecu.validation_v5_design import STUDY
  manifest=json.loads((OUTPUT/'timing_monitor_contract.json').read_text())
  self.assertEqual(manifest['study_sha256'],hashlib.sha256(STUDY.read_bytes()).hexdigest())
  for r in expand(load_config()):
   if r['model'] in ['sensor_bias','pump_degraded','fan_stuck_off']:self.assertIn(r['parameters']['behavior'],['transient','permanent'])
 def test_v5_unnecessary_cost_counts_release_hysteresis(self):
  common={'pair_id':'p','is_perturbed':1,'plant_manifestation':0,'attributable_hazard':0,'actuator_any_effect':0,'preexisting_hazard':0,'fault_recovered':1,'runtime_safety_first_action_ms':None}
  base={**common,'policy':'observe_only','policy_intervention':0,'safe_state_duration_ms':100,'policy_requested_duration_ms':0}
  action={**common,'policy':'graded','policy_intervention':1,'safe_state_duration_ms':1100,'policy_requested_duration_ms':500,'runtime_safety_first_action_ms':100}
  paired([base,action]);self.assertEqual(action['unnecessary_intervention_duration_ms'],1000);self.assertEqual(action['unnecessary_requested_duration_ms'],500)
  self.assertEqual(action['intervention_class'],'UNNECESSARY_NO_ACTUATOR_PLANT')
 def test_old_result_numeric_loader_preserves_na(self):
  from virtual_ecu.validation_v5_report import records
  p=self.path/'old.csv';p.write_text('run_id,endpoint,value\nold,,0\n')
  r=records(p)[0];self.assertIsNone(r['endpoint']);self.assertEqual(r['value'],0)
 def test_overhead_report_generation_is_labeled_host(self):
  from virtual_ecu.validation_v5_overhead import measure
  rows=measure(self.path,repetitions=2)
  monitor=next(r for r in rows if r['metric']=='monitor_state');self.assertGreater(monitor['value'],0)
  host=next(r for r in rows if r['metric']=='host_runtime_observe_only');self.assertEqual(host['n'],2);self.assertIn('host',host['scope'])
  self.assertTrue((self.path/'monitor_overhead_summary.csv').is_file())
 def test_graded_gate_and_escalation_native(self):
  source=self.path/'policy.c';binary=self.path/'policy'
  source.write_text('''#include <assert.h>
#include "safety_policy_v5.h"
int main(void){runtime_safety_status_t s;runtime_safety_policy_init(&s);safety_policy_v5_state_t v={-1};runtime_safety_config_t c={.enabled=true,.communication_protective_action=true,.timing_mode=TIMING_PROTECTIVE_ACTION};runtime_observation_t o={.timing={.period_ms=100},.sample_freshness_ok=false};timing_monitor_status_t t={0};
safety_policy_v5_step(&s,&v,&c,V5_GRADED,&o,&t);assert(s.requested_state==0);
o.detector_alarm=true;safety_policy_v5_step(&s,&v,&c,V5_GRADED,&o,&t);assert(s.requested_state==1);
o.time_ms=499;safety_policy_v5_step(&s,&v,&c,V5_GRADED,&o,&t);assert(s.requested_state==1);
o.time_ms=500;safety_policy_v5_step(&s,&v,&c,V5_GRADED,&o,&t);assert(s.requested_state==2);
o.detector_alarm=false;safety_policy_v5_step(&s,&v,&c,V5_GRADED,&o,&t);assert(s.requested_state==0);
o.detector_alarm=true;o.time_ms=600;safety_policy_v5_step(&s,&v,&c,V5_GRADED,&o,&t);assert(s.requested_state==1);
o.detector_alarm=false;t.alarm=true;t.severity=TIMING_CRITICAL_ABSENCE;o.timing.execution_age_ms=300;safety_policy_v5_step(&s,&v,&c,V5_GRADED,&o,&t);assert(s.requested_state==1);
o.timing.execution_age_ms=500;safety_policy_v5_step(&s,&v,&c,V5_GRADED,&o,&t);assert(s.requested_state==2);return 0;}''')
  subprocess.run(['gcc','-std=c11','-I'+str(ROOT/'include'),str(source),str(ROOT/'src/safety_policy_v5.c'),str(ROOT/'src/runtime_safety_policy.c'),'-o',str(binary)],check=True)
  subprocess.run([str(binary)],check=True)

if __name__=='__main__':unittest.main()
