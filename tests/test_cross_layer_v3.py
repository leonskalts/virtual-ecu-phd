"""Scientific analysis contracts; synthetic cases are never campaign evidence."""
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.cross_layer_analysis import (hazard_states, interval, ftti_result,
    classify_consequence, containment_classification, diagnose_miss, metric_summary,
    sensitivity, analyze_campaign, analyze_run, DEFAULT_INPUT, typed)
from virtual_ecu.cross_layer_observability import observability_matrix, coverage_matrix
from virtual_ecu.cross_layer_safety import read_rows, summarize_rows


def case(**changes):
    row=dict(injected=1, internal_corruption=1, control_effect=0,
             actuator_any_effect=0, plant_manifestation=0, sensing_visible_effect=0,
             attributable_hazard=0, post_injection_critical=0, detected=0,
             propagation_detector_ms=None, hazard_entry_ms=None, fault_layer='memory',
             fault_model='bit_flip', fault_behavior='transient', operating_profile='test',
             preexisting_hazard=0, first_safety_relevant_manifestation_ms=None,
             legacy_v2_containment=1, containment_time_ms=2000, fault_injection_ms=1000,
             observation_end_ms=12000, protective_response_active_end=0, fault_recovered=1,
             detector='hybrid_adaptive_kalman', max_runtime_detection_score=.3)
    row.update(changes)
    return row


class HazardAnalysisTests(unittest.TestCase):
    def states(self,samples,allowance=1000):
        return list(hazard_states(samples,allowance))

    def test_hazard_state_transitions_and_exit(self):
        result=self.states([(0,False,False),(100,True,False),(200,True,True),
                            (1200,True,True),(1300,True,False),(1400,False,False)])
        self.assertEqual([r['hazard_state'] for r in result],['NORMAL','WARNING','CRITICAL_TRANSIENT','HAZARD_SUSTAINED','WARNING','RECOVERED'])
        self.assertEqual(result[-1]['critical_exposure_ms'],1100)
        self.assertEqual(result[-1]['consecutive_critical_ms'],0)

    def test_short_critical_crossing_is_not_sustained(self):
        result=self.states([(0,True,True),(900,True,True),(1000,False,False)])
        self.assertNotIn('HAZARD_SUSTAINED',[r['hazard_state'] for r in result])
        # Exactly 1000 cumulative ms on exit does not imply active sustained hazard.
        self.assertEqual(result[-1]['critical_exposure_ms'],1000)

    def test_simulation_ending_hazard_and_no_extra_interval(self):
        result=self.states([(0,True,True),(1000,True,True)])
        self.assertEqual(result[-1]['hazard_state'],'HAZARD_SUSTAINED')
        self.assertEqual(result[-1]['critical_exposure_ms'],1000)
        self.assertEqual(self.states([(0,False,False),(1000,True,True)])[-1]['critical_exposure_ms'],0)

    def test_reentry_resets_consecutive_clock(self):
        result=self.states([(0,True,True),(1000,True,True),(1100,False,False),
                            (1200,True,True),(2100,True,True)])
        self.assertEqual(result[-1]['hazard_state'],'CRITICAL_TRANSIENT')
        self.assertEqual(result[-1]['consecutive_critical_ms'],900)

    def test_zero_allowance_and_invalid_clock(self):
        self.assertEqual(self.states([(0,True,True)],0)[0]['hazard_state'],'HAZARD_SUSTAINED')
        with self.assertRaises(ValueError):self.states([(0,False,False),(0,True,True)])
        with self.assertRaises(ValueError):self.states([(0,False,True)])


class TimingMetricTests(unittest.TestCase):
    def test_injection_and_manifestation_clocks(self):
        self.assertEqual(interval(1000,3000),2000)
        self.assertEqual(interval(3500,3000),-500)
        self.assertEqual(ftti_result(1000,7000,0,10000,5000),0)
        self.assertEqual(ftti_result(2000,7000,0,10000,5000),1)

    def test_missing_origin_and_endpoint_are_na(self):
        self.assertIsNone(interval(None,3000))
        self.assertIsNone(interval(1000,None))
        self.assertIsNone(ftti_result(None,3000,0,5000,5000))
        self.assertEqual(interval(1000,1000),0)

    def test_deadline_horizon_and_hazard(self):
        self.assertIsNone(ftti_result(1000,None,0,5999,5000))
        self.assertEqual(ftti_result(1000,None,0,6000,5000),0)
        self.assertEqual(ftti_result(1000,2000,1,12000,5000),0)
        self.assertIsNone(ftti_result(1000,2000,None,12000,5000))

    def test_global_sensitivity_and_denominators(self):
        a=case(first_safety_relevant_manifestation_ms=1500,hardened_containment=1,hardened_containment_time_ms=2500,containment_time_ms=2500)
        b=case(legacy_v2_containment=None,hardened_containment=None)
        result=[r for r in sensitivity([a,b],budgets=(1000,2000)) if r['dimension']=='overall']
        self.assertEqual([(r['numerator'],r['denominator']) for r in result],[(0,1),(1,1),(1,1),(1,1)])


class SeverityAndContainmentTests(unittest.TestCase):
    def test_sc0_internal_only(self):
        self.assertEqual(classify_consequence(case()),('S1_INTERNAL_ONLY','SC0'))

    def test_sc1_control_and_sensing_visible(self):
        self.assertEqual(classify_consequence(case(control_effect=1)),('S2_ECU_VISIBLE','SC1'))
        self.assertEqual(classify_consequence(case(sensing_visible_effect=1)),('S2_ECU_VISIBLE','SC1'))

    def test_sc2_plant_and_actuator(self):
        self.assertEqual(classify_consequence(case(plant_manifestation=1)),('S3_ACTUATOR_OR_PLANT','SC2'))
        self.assertEqual(classify_consequence(case(actuator_any_effect=1)),('S3_ACTUATOR_OR_PLANT','SC2'))

    def test_sc3_late_same_tick_and_absent_alarm(self):
        for alarm in (None,3000,4000):
            self.assertEqual(classify_consequence(case(attributable_hazard=1,hazard_entry_ms=3000,
                propagation_detector_ms=alarm,detected=int(alarm is not None))),('S5_SUSTAINED_HAZARD','SC3'))
        self.assertEqual(classify_consequence(case(attributable_hazard=1,hazard_entry_ms=3000,
            propagation_detector_ms=2000,detected=1))[1],'DETECTED')

    def test_severity_no_effect_transient_and_na(self):
        self.assertEqual(classify_consequence(case(internal_corruption=0)),('S0_NO_EFFECT','NO_EFFECT'))
        self.assertEqual(classify_consequence(case(plant_manifestation=1,post_injection_critical=1))[0],'S4_CRITICAL_TRANSIENT')
        self.assertEqual(classify_consequence(case(injected=0)),('NOT_APPLICABLE','NOT_APPLICABLE'))
        self.assertEqual(classify_consequence(case(internal_corruption=None)),('UNAVAILABLE','UNAVAILABLE'))
        self.assertEqual(classify_consequence(case(attributable_hazard=None)),('UNAVAILABLE','UNAVAILABLE'))

    def test_no_containment_required_despite_legacy_success(self):
        self.assertEqual(containment_classification(case(control_effect=1)),(None,'NO_CONTAINMENT_REQUIRED'))

    def test_containment_before_and_after_plant(self):
        row=case(first_safety_relevant_manifestation_ms=1000,containment_time_ms=2000)
        self.assertEqual(containment_classification(row),(1,'CONTAINED_BEFORE_PLANT'))
        self.assertEqual(containment_classification({**row,'propagation_plant_ms':1500}),(1,'CONTAINED_AFTER_PLANT_BEFORE_HAZARD'))

    def test_hazard_overrides_eventual_recovery(self):
        self.assertEqual(containment_classification(case(first_safety_relevant_manifestation_ms=1000,attributable_hazard=1)),(0,'FAILED_CONTAINMENT_HAZARD'))

    def test_protection_detection_and_recovery_are_not_success(self):
        base=case(first_safety_relevant_manifestation_ms=1000,legacy_v2_containment=0)
        self.assertEqual(containment_classification({**base,'protective_response_active_end':1}),(0,'PROTECTIVE_RESPONSE_ACTIVE'))
        self.assertEqual(containment_classification({**base,'detected':1}),(0,'DETECTED_NOT_CONTAINED'))
        self.assertEqual(containment_classification(base),(0,'FAULT_RECOVERED'))

    def test_preexisting_and_early_confirmation_na(self):
        self.assertEqual(containment_classification(case(preexisting_hazard=1)),(None,'NOT_APPLICABLE'))
        self.assertEqual(containment_classification(case(first_safety_relevant_manifestation_ms=3000)),(None,'UNRESOLVED_CONTAINMENT'))


class ScientificAggregationTests(unittest.TestCase):
    def test_conditional_plant_and_hazard_denominators(self):
        rows=[case(detected=1,plant_manifestation=1,attributable_hazard=1),
              case(detected=0,plant_manifestation=1),case(detected=1),case(detected=None,plant_manifestation=None)]
        result={r['metric']:r for r in metric_summary(rows) if r['dimension']=='overall'}
        self.assertEqual((result['detection_coverage_given_plant_propagation']['numerator'],result['detection_coverage_given_plant_propagation']['denominator']),(1,2))
        self.assertEqual((result['detection_coverage_given_hazard']['numerator'],result['detection_coverage_given_hazard']['denominator']),(1,1))

    def test_absent_hazard_denominator_is_na(self):
        result={r['metric']:r for r in metric_summary([case()]) if r['dimension']=='overall'}
        self.assertIsNone(result['detection_coverage_given_hazard']['percent'])

    def test_observability_is_not_consumption_or_coverage(self):
        result={r['fault_model']:r for r in observability_matrix()}
        self.assertEqual(result['deadline_miss']['scheduler_last_execution'],'DIRECT')
        self.assertEqual(result['deadline_miss']['scheduler_release_deadline_contract'],'NOT AVAILABLE')
        self.assertEqual(result['replayed_sample']['sensor_freshness_age'],'DIRECT')
        self.assertEqual(result['sensor_bias']['sensor_value_residual'],'NOT AVAILABLE')
        self.assertEqual(result['bit_flip']['actuator_command_actual_mismatch'],'NOT APPLICABLE')
        coverage=coverage_matrix([case(fault_model='deadline_miss')])
        self.assertEqual(next(r for r in coverage if r['fault_model']=='deadline_miss' and r['mechanism']=='hybrid_adaptive_kalman')['classification'],'MISSED')
        self.assertEqual(next(r for r in coverage if r['mechanism']=='other_detectors_not_exercised')['classification'],'NOT APPLICABLE')

    def test_miss_diagnosis_is_deterministic_and_unresolved_when_needed(self):
        a=case(fault_layer='timing',scheduler_event_seen=1)
        self.assertEqual(diagnose_miss(a),diagnose_miss(dict(reversed(list(a.items())))))
        self.assertEqual(diagnose_miss(a)[0],'TIMING_EVENT_NOT_EXPOSED_TO_CURRENT_DETECTOR')
        self.assertEqual(diagnose_miss(case(max_runtime_detection_score=1.1))[0],'UNRESOLVED')
        self.assertEqual(diagnose_miss(case())[0],'COMBINED_SCORE_BELOW_CURRENT_CONFIRMATION_FLOOR')

    def test_protected_output_rejected_before_any_write(self):
        for path in (DEFAULT_INPUT,DEFAULT_INPUT/'new',ROOT/'results/cross_layer_safety_v1',ROOT/'results'):
            with self.assertRaises(ValueError):analyze_campaign(output=path)

    def test_old_csv_missing_fields_remain_na(self):
        old=summarize_rows([{'time_ms':'0'}])
        self.assertIsNone(old['ftti_met'])
        self.assertIsNone(old['containment_success'])
        self.assertIsNone(old['propagation_plant_ms'])


@unittest.skipUnless((DEFAULT_INPUT/'campaign_runs.csv').is_file(),'Accepted local v2 evidence not installed')
class AcceptedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campaign=read_rows(DEFAULT_INPUT/'campaign_runs.csv')

    def test_v2_raw_metrics_and_bytes_reproduce_representative_cases(self):
        commands=json.loads((DEFAULT_INPUT/'commands.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            for index in (1,37,63,113,155):
                original=DEFAULT_INPUT/'raw'/Path(commands[index][1]).name
                command=list(commands[index]);command[0]=str(ROOT/'virtual_ecu');command[1]=str(Path(temp)/original.name)
                subprocess.run(command,check=True,capture_output=True)
                self.assertEqual(hashlib.sha256(original.read_bytes()).digest(),hashlib.sha256(Path(command[1]).read_bytes()).digest())
                current=summarize_rows(read_rows(original))
                for key in ('containment_success','ftti_met','silent_corruption','propagation_detector_ms'):
                    self.assertEqual(current[key],typed(self.campaign[index])[key])

    def test_real_hazard_trace_audit_and_legacy_fields_unchanged(self):
        original=self.campaign[63]
        raw=read_rows(DEFAULT_INPUT/'raw'/Path(original['raw_csv']).name)
        baseline=read_rows(DEFAULT_INPUT/'raw'/Path(self.campaign[0]['raw_csv']).name)
        analyzed,events=analyze_run(original,raw,{int(r['time_ms']):r for r in baseline})
        for key,value in typed(original).items():self.assertEqual(analyzed[key],value)
        self.assertEqual(analyzed['hazard_entry_ms'],100400)
        self.assertEqual(analyzed['hardened_containment'],0)
        self.assertEqual(analyzed['silent_corruption_class'],'DETECTED')
        self.assertIn('HAZARD_SUSTAINED',[r['hazard_state'] for r in events])
        self.assertEqual(analyzed['remaining_time_to_hazard_at_detection_ms'],10100)

    def test_v1_and_v2_readers(self):
        old=ROOT/'results/cross_layer_safety_v1/raw/memory_bit_flip.csv'
        if old.is_file():
            self.assertIsNone(summarize_rows(read_rows(old))['ftti_met'])
        self.assertEqual(summarize_rows(read_rows(DEFAULT_INPUT/'raw'/Path(self.campaign[63]['raw_csv']).name))['ftti_met'],0)
