"""V4 trusted scheduler contracts, independent alarms and paired responses."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.cross_layer_safety import fault_options,read_rows,summarize_rows
from virtual_ecu.cross_layer_campaign import read_study
from virtual_ecu.runtime_safety_study import (expand_cases,TIMING_STUDY,COMMUNICATION_STUDY,
    runtime_summary,mechanism_attribution,intervention_classification,pair_outcomes)


class RuntimeSafetyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='vecu_v4_test_');self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)

    def run_case(self,model=None,mode='observe_only',evidence='combined',name='case',**parameters):
        path=self.path/(name+'.csv')
        options=fault_options(model,start_ms=1000,duration_ms=parameters.pop('duration_ms',100),**parameters) if model else []
        subprocess.run([str(ROOT/'virtual_ecu'),str(path),'baseline',*options,'--hazard-monitor','on',
            '--simulation-duration-ms','6000','--detector','hybrid_adaptive_kalman','--detector-action','observe_only',
            '--timing-monitor',mode,'--timing-evidence',evidence],check=True,capture_output=True)
        return read_rows(path)

    def test_no_fault_no_alarm_or_action(self):
        for mode in ('disabled','observe_only','protective_action'):
            rows=self.run_case(mode=mode)
            self.assertTrue(all(r['timing_contract_violation']=='0' and r['timing_monitor_alarm']=='0' for r in rows))
            self.assertEqual(rows[-1]['runtime_safety_first_action_ms'],'')

    def test_single_missed_release_and_deadline_ablation(self):
        combined=self.run_case('deadline_miss')
        deadline=self.run_case('deadline_miss',evidence='deadline_only')
        age=self.run_case('deadline_miss',evidence='execution_age_only')
        self.assertEqual(combined[-1]['timing_monitor_first_alarm_ms'],'1000')
        self.assertEqual(age[-1]['timing_monitor_first_alarm_ms'],'1000')
        self.assertEqual(deadline[-1]['timing_monitor_first_alarm_ms'],'1100')
        self.assertEqual(deadline[-1]['timing_first_violation_ms'],'1000')
        self.assertEqual(combined[-1]['runtime_safety_first_request_ms'],'')

    def test_task_delay_is_not_known_before_contract_violation(self):
        rows=self.run_case('task_delay',task_delay_ms=200)
        at={int(r['time_ms']):r for r in rows}
        self.assertEqual(at[1000]['trusted_job_release_ms'],'1000')
        self.assertEqual(at[1000]['trusted_actual_start_ms'],'')
        self.assertEqual(at[1000]['timing_monitor_alarm'],'0')
        self.assertEqual(at[1100]['timing_monitor_alarm'],'1')
        self.assertEqual(at[1200]['trusted_actual_start_ms'],'1200')
        self.assertEqual(at[1200]['trusted_actual_completion_ms'],'1200')
        self.assertEqual(at[1200]['trusted_job_release_ms'],'1000')

    def test_exact_deadline_completion_is_not_overrun_but_discard_is_visible(self):
        rows=self.run_case('task_delay',task_delay_ms=100)
        at={int(r['time_ms']):r for r in rows}
        self.assertEqual(at[1100]['trusted_deadline_exceeded'],'0')
        self.assertEqual(at[1100]['trusted_missed_expected_execution'],'1')
        self.assertEqual(at[1200]['trusted_deadline_exceeded'],'1')

    def test_intermit_confirmation_and_protective_action(self):
        rows=self.run_case('deadline_miss',mode='protective_action',behavior='intermittent',duration_ms=1000,
                           intermittent_on_ms=100,intermittent_off_ms=100)
        self.assertEqual(rows[-1]['timing_monitor_first_alarm_ms'],'1000')
        self.assertGreater(int(rows[-1]['runtime_safety_first_request_ms']),1000)
        self.assertEqual(rows[-1]['runtime_safety_first_action_ms'],rows[-1]['runtime_safety_first_request_ms'])
        self.assertTrue(any(r['timing_monitor_severity']=='repeated' for r in rows))
        self.assertTrue(any(int(r['safe_state_id'])>0 for r in rows))

    def test_isolated_single_anomaly_does_not_force_action(self):
        rows=self.run_case('deadline_miss',mode='protective_action')
        self.assertEqual(rows[-1]['timing_monitor_detected'],'1')
        self.assertEqual(rows[-1]['runtime_safety_first_request_ms'],'')

    def test_permanent_absence_and_critical_execution_age(self):
        rows=self.run_case('deadline_miss',mode='protective_action',behavior='permanent')
        self.assertEqual(rows[-1]['timing_monitor_severity'],'critical_execution_absence')
        self.assertEqual(rows[-1]['runtime_safety_requested_state'],'2')
        self.assertGreater(int(rows[-1]['trusted_execution_age_ms']),300)

    def test_scheduler_ledger_accounts_for_every_real_execution(self):
        for model,parameters in (('deadline_miss',{}),('task_delay',{'task_delay_ms':2000}),
                                  ('deadline_miss',{'behavior':'permanent'})):
            rows=self.run_case(model,**parameters)
            completed=0
            for r in rows:
                completed+=int(r['control_task_last_execution_ms']==r['time_ms'])
                self.assertEqual(int(r['trusted_execution_sequence']),completed)
                self.assertEqual(int(r['trusted_release_sequence']),completed+int(r['trusted_cancelled_releases'])+int(r['trusted_job_outstanding']))

    def test_observe_only_preserves_every_legacy_field_and_hybrid_waveform(self):
        a=self.run_case('task_delay',mode='disabled',task_delay_ms=2000)
        b=self.run_case('task_delay',mode='observe_only',task_delay_ms=2000)
        fields=list(a[0]);legacy=fields[:fields.index('runtime_safety_enabled')]
        for x,y in zip(a,b):
            self.assertEqual({k:x[k] for k in legacy},{k:y[k] for k in legacy})
        self.assertEqual(b[-1]['runtime_safety_first_action_ms'],'')

    def test_communication_existing_alarm_with_and_without_action(self):
        source=ROOT/'results/cross_layer_safety_v2/commands.json'
        if not source.is_file():self.skipTest('Accepted local campaign not installed')
        commands=json.loads(source.read_text())
        for index in (63,81):
            results=[]
            for mode in ('observe_only','protective_action'):
                command=list(commands[index]);command[0]=str(ROOT/'virtual_ecu');command[1]=str(self.path/f'comm_{index}_{mode}.csv')
                command+=['--communication-safety-response',mode]
                subprocess.run(command,check=True,capture_output=True)
                results.append(read_rows(Path(command[1])))
            a,b=results
            self.assertEqual(a[-1]['hazard_entered'],'1')
            self.assertEqual(b[-1]['hazard_entered'],'0')
            self.assertEqual(b[-1]['critical_exposure_time_ms'],'0')
            self.assertEqual(a[-1]['runtime_safety_first_action_ms'],'')
            action=int(b[-1]['runtime_safety_first_action_ms'])
            self.assertEqual(action,int(b[-1]['existing_detector_first_alarm_ms']))
            self.assertLess(action,int(a[-1]['hazard_entry_ms']))
            # No retuning: the entire existing detector waveform agrees up to action.
            for x,y in zip(a,b):
                if int(x['time_ms'])<=action:
                    for key in ('runtime_detection_alarm','runtime_detection_score','runtime_detection_label'):
                        self.assertEqual(x[key],y[key])
            self.assertEqual(b[-1]['containment_success'],'0') # Hazard avoidance is not stable-tail containment.

    def test_invalid_new_modes_rejected(self):
        for option,value in (('--timing-monitor','hybrid'),('--timing-evidence','fault_flag'),('--communication-safety-response','auto')):
            path=self.path/'invalid.csv'
            result=subprocess.run([str(ROOT/'virtual_ecu'),str(path),'baseline',option,value],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(path.exists())


class RuntimeSafetyAnalysisTests(unittest.TestCase):
    def test_balanced_matrix_and_no_stochastic_duplicates(self):
        cases=expand_cases(read_study(TIMING_STUDY))
        faults=[r for r in cases if r['model']!='baseline']
        self.assertEqual(len(cases),74)
        for model in ('deadline_miss','task_delay'):self.assertEqual(sum(r['model']==model for r in faults),36)
        for behavior in ('transient','intermittent','permanent'):self.assertEqual(sum(r['parameters']['behavior']==behavior for r in faults),24)
        signatures={(r['model'],r['profile']['id'],json.dumps(r['parameters'],sort_keys=True)) for r in faults}
        self.assertEqual(len(signatures),72)
        self.assertEqual(len(expand_cases(read_study(COMMUNICATION_STUDY))),50)

    def test_mechanism_attribution_including_ties(self):
        self.assertEqual(mechanism_attribution(100,200),('existing_detector',100))
        self.assertEqual(mechanism_attribution(200,100),('timing_safety_monitor',100))
        self.assertEqual(mechanism_attribution(100,100),('SIMULTANEOUS',100))
        self.assertEqual(mechanism_attribution(None,None),('NONE',None))

    def test_false_unnecessary_and_true_protective_interventions(self):
        benign={'policy_intervention':1,'injected':0}
        self.assertEqual(intervention_classification(benign,{}),'FALSE_INTERVENTION')
        fault={'policy_intervention':1,'injected':1,'attributable_hazard':0,'critical_exposure_time_ms':0}
        self.assertEqual(intervention_classification(fault,{'actuator_any_effect':0,'plant_manifestation':0}),'UNNECESSARY_NO_DOWNSTREAM')
        hazardous={'attributable_hazard':1,'actuator_any_effect':1,'plant_manifestation':1,'critical_exposure_time_ms':1000}
        self.assertEqual(intervention_classification(fault,hazardous),'TRUE_PROTECTIVE_HAZARD_MITIGATED')
        self.assertEqual(intervention_classification(fault,{**hazardous,'attributable_hazard':0}),'RESPONSE_TO_PROPAGATING_FAULT_BENEFIT_UNPROVEN')

    def test_old_v1_v2_v3_rows_keep_missing_v4_values_na(self):
        for row in ({'time_ms':'0'}, {'time_ms':'0','cross_layer_monitor_enabled':'1'}, {'run_id':'v3','detected':'0'}):
            summary=runtime_summary([row])
            self.assertIsNone(summary['timing_monitor_detected'])
            self.assertIsNone(summary['policy_intervention'])
            self.assertEqual(summary['first_detection_mechanism'],'N/A')

    def test_monitor_and_policy_have_no_ground_truth_type_access(self):
        for name in ('timing_safety_monitor.c','runtime_safety_policy.c','runtime_timing_observation.c'):
            source=(ROOT/'src'/name).read_text()
            for forbidden in ('ecu_types.h','experiment_ground_truth','faults.','cross_layer_runtime','propagation.'):
                self.assertNotIn(forbidden,source)


class TrustedEventContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='vecu_timing_contract_')
        cls.addClassCleanup(cls.temp.cleanup)
        directory=Path(cls.temp.name);source=directory/'contract.c';cls.binary=directory/'contract'
        source.write_text(r'''
#include <assert.h>
#include <string.h>
#include "runtime_safety_policy.h"
static void check(runtime_timing_recorder_t *r,timing_monitor_status_t *m,unsigned now) {
    runtime_timing_observe(r,now);
    timing_safety_monitor_step(m,&r->observation,TIMING_OBSERVE_ONLY,TIMING_COMBINED);
    assert(!m->alarm);
}
int main(int argc,char **argv) {
    (void)argc;
    runtime_timing_recorder_t r;timing_monitor_status_t m;
    runtime_timing_init(&r,100);timing_safety_monitor_init(&m);
    if (!strcmp(argv[1],"legal_jitter")) {
        for (unsigned t=0;t<1000;t+=100) {
            runtime_timing_release(&r,t);runtime_timing_admit(&r);check(&r,&m,t);
            runtime_timing_start(&r,t+25);runtime_timing_complete(&r,t+99);check(&r,&m,t+99);
        }
    } else if (!strcmp(argv[1],"deadline_boundary")) {
        runtime_timing_release(&r,0);runtime_timing_admit(&r);
        runtime_timing_start(&r,99);runtime_timing_complete(&r,100);check(&r,&m,100);
        assert(!r.observation.deadline_exceeded);
    } else if (!strcmp(argv[1],"policy_gate")) {
        runtime_safety_status_t p;runtime_safety_policy_init(&p);
        runtime_safety_config_t c={.enabled=true,.communication_protective_action=true};
        runtime_observation_t o={.time_ms=100,.sample_freshness_ok=false};
        runtime_safety_policy_step(&p,&c,&o,&m);assert(!p.communication_request);
        o.detector_alarm=true;o.sample_freshness_ok=true;
        runtime_safety_policy_step(&p,&c,&o,&m);assert(!p.communication_request);
        o.sample_freshness_ok=false;runtime_safety_policy_step(&p,&c,&o,&m);
        assert(p.communication_request && p.requested_state==2 && p.first_request_ms==100);
    } else if (!strcmp(argv[1],"overrun_without_cancel")) {
        runtime_timing_release(&r,0);runtime_timing_admit(&r);
        runtime_timing_observe(&r,100);
        timing_safety_monitor_step(&m,&r.observation,TIMING_OBSERVE_ONLY,TIMING_DEADLINE_ONLY);
        assert(m.alarm && m.first_alarm_ms==100);
    }
    return 0;
}
''')
        subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Wpedantic','-I'+str(ROOT/'include'),str(source),
            str(ROOT/'src/runtime_timing_observation.c'),str(ROOT/'src/timing_safety_monitor.c'),str(ROOT/'src/runtime_safety_policy.c'),'-o',str(cls.binary)],check=True,capture_output=True)

    def test_legal_jitter_is_quiet_in_synthetic_contract_fixture(self):
        subprocess.run([str(self.binary),'legal_jitter'],check=True)

    def test_completion_exactly_at_deadline_is_legal(self):
        subprocess.run([str(self.binary),'deadline_boundary'],check=True)

    def test_policy_requires_both_existing_alarm_and_failed_freshness(self):
        subprocess.run([str(self.binary),'policy_gate'],check=True)

    def test_deadline_channel_can_observe_overrun_without_injector_or_cancellation(self):
        subprocess.run([str(self.binary),'overrun_without_cancel'],check=True)
