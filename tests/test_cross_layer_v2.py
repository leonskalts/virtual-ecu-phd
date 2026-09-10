"""Temporal, data-path, scheduling, hazard and campaign contract tests."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
from virtual_ecu.cross_layer_safety import fault_options, read_rows, summarize_rows
from virtual_ecu.cross_layer_campaign import expand_runs, read_study, DEFAULT_STUDY, group_statistics


class CrossLayerV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vecu_v2_test_')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def run_fault(self, model, name='run', duration_ms=500, start_ms=1000, **kwargs):
        path = self.directory / (name+'.csv')
        command = [str(ROOT/'virtual_ecu'), str(path), 'baseline',
                   *fault_options(model, start_ms=start_ms, duration_ms=duration_ms, **kwargs),
                   '--simulation-duration-ms', '5000', '--hazard-monitor', 'on']
        subprocess.run(command, check=True, capture_output=True)
        return read_rows(path)

    def test_temporal_modes_and_bitflip_reactivation(self):
        for behavior, active in (
            ('transient', [1000,1100,1200,1300,1400]),
            ('intermittent', [1000,1100,1400]),
            ('permanent', list(range(1000,5100,100))),
        ):
            rows = self.run_fault('bit_flip', behavior=behavior, intermittent_on_ms=200,
                                  intermittent_off_ms=200, bit_index=5)
            self.assertEqual([int(r['time_ms']) for r in rows if r['fault_active']=='1'], active)
            self.assertEqual(rows[-1]['fault_activation_count'], '2' if behavior=='intermittent' else '1')
            for row in rows:
                self.assertEqual(float(row['active_control_target_c']), 124 if row['fault_active']=='1' else 92)
            self.assertEqual(rows[-1]['last_recovery_ms'], '' if behavior=='permanent' else '1500')

    def test_stuck_polarities_and_noncorrupting_stuck_bit(self):
        for bit, polarity, expected in ((3,0,84),(5,1,124),(3,1,92),(5,0,92)):
            for behavior in ('transient','intermittent','permanent'):
                with self.subTest(bit=bit,polarity=polarity,behavior=behavior):
                    rows=self.run_fault('stuck_bit',bit_index=bit,stuck_polarity=polarity,behavior=behavior,
                                        intermittent_on_ms=100,intermittent_off_ms=100)
                    for row in rows:
                        self.assertEqual(float(row['active_control_target_c']),expected if row['fault_active']=='1' else 92)
                    if expected==92:
                        self.assertEqual(rows[-1]['propagation_internal_ms'],'')
                        self.assertEqual(rows[-1]['max_propagation_stage'],'0')
                        self.assertEqual(rows[-1]['containment_success'],'')

    def test_intermittent_deadline_misses(self):
        rows=self.run_fault('deadline_miss',behavior='intermittent',intermittent_on_ms=100,intermittent_off_ms=100)
        self.assertEqual([r['time_ms'] for r in rows if r['execution_skipped']=='1'],['1000','1200','1400'])
        self.assertEqual([r['time_ms'] for r in rows if r['control_task_recovery']=='1'],['1100','1300','1500'])

    def test_delayed_job_executes_after_fault_recovers(self):
        rows=self.run_fault('task_delay',duration_ms=100,task_delay_ms=300)
        at={int(r['time_ms']):r for r in rows}
        for time in (1000,1100,1200):
            self.assertEqual(at[time]['actual_execution_ms'],'')
            self.assertEqual(at[time]['control_task_last_execution_ms'],'900')
        self.assertEqual(at[1100]['fault_active'],'0')
        self.assertEqual(at[1300]['nominal_release_ms'],'1000')
        self.assertEqual(at[1300]['actual_execution_ms'],'1300')
        self.assertEqual(at[1300]['task_delay_ms'],'300')
        self.assertEqual(at[1300]['deadline_ms'],'1100')
        self.assertEqual(at[1300]['deadline_missed'],'1')
        self.assertEqual(at[1300]['control_release_discarded'],'1')
        self.assertEqual(at[1400]['nominal_release_ms'],'1400')

    def test_intermittent_task_delay_and_exact_deadline_completion(self):
        rows=self.run_fault('task_delay',behavior='intermittent',duration_ms=1000,
                            intermittent_on_ms=100,intermittent_off_ms=300,task_delay_ms=100)
        completions=[r for r in rows if r['task_delay_ms']=='100']
        self.assertEqual([r['time_ms'] for r in completions],['1100','1500','1900'])
        self.assertTrue(all(r['deadline_missed']=='0' for r in completions))

    def test_delay_delivers_real_historical_generated_values(self):
        rows=self.run_fault('delayed_update',duration_ms=1000,communication_delay_ms=300)
        at={int(r['time_ms']):r for r in rows}
        for time in (1000,1100,1200): self.assertEqual(at[time]['update_delivered'],'0')
        for time in range(1300,2000,100):
            self.assertEqual(at[time]['delivered_value'],at[time-300]['current_generated_value'])
            self.assertEqual(at[time]['sample_delivered_ms'],str(time))
            self.assertEqual(at[time]['sample_age_ms'],'300')
        self.assertEqual(at[2000]['sample_age_ms'],'0')
        self.assertEqual(at[2000]['delivered_value'],at[2000]['current_generated_value'])

    def test_dropped_delivery_bursts_and_recovery(self):
        rows=self.run_fault('dropped_update',duration_ms=1000,drop_count=2,drop_every_n_updates=4)
        at={int(r['time_ms']):r for r in rows}
        self.assertEqual([r['time_ms'] for r in rows if r['update_dropped']=='1'],
                         ['1000','1100','1400','1500','1800','1900'])
        self.assertEqual(at[1100]['delivered_value'],at[900]['delivered_value'])
        self.assertEqual(at[1100]['consecutive_drops'],'2')
        self.assertEqual(at[1200]['consecutive_drops'],'0')
        self.assertEqual(at[2000]['update_delivered'],'1')
        once=self.run_fault('dropped_update',name='once',drop_count=2)
        self.assertEqual(sum(int(r['update_dropped']) for r in once),2)

    def test_replay_is_historical_packet_with_visible_acquisition_age(self):
        rows=self.run_fault('replayed_sample',replay_age_ms=500)
        at={int(r['time_ms']):r for r in rows}
        for time in range(1000,1500,100):
            self.assertEqual(at[time]['replay_source_timestamp_ms'],str(time-500))
            self.assertEqual(at[time]['delivered_value'],at[time-500]['current_generated_value'])
            self.assertEqual(at[time]['sample_age_ms'],'500')
            self.assertEqual(at[time]['coolant_sensor_last_update_ms'],str(time-500))
        self.assertEqual(at[1500]['replay_active'],'0')

    def test_reproducibility_and_changed_configuration(self):
        for model in ('stuck_bit','delayed_update','dropped_update','replayed_sample','task_delay'):
            self.run_fault(model,name='a',seed=17)
            self.run_fault(model,name='b',seed=17)
            self.assertEqual((self.directory/'a.csv').read_bytes(),(self.directory/'b.csv').read_bytes())
        a=self.run_fault('delayed_update',name='short',communication_delay_ms=100)
        b=self.run_fault('delayed_update',name='long',communication_delay_ms=400)
        self.assertNotEqual([r['delivered_value'] for r in a],[r['delivered_value'] for r in b])

    def test_new_paths_have_no_plant_mutation_at_injection(self):
        for model in ('delayed_update','dropped_update','replayed_sample','task_delay'):
            rows=self.run_fault(model)
            first=next(r for r in rows if r['time_ms']=='1000')
            self.assertEqual(first['plant_coolant_deviation_c'],'0.000000000')
            last=rows[-1]
            times=[int(last[k]) for k in ('fault_injection_ms','propagation_internal_ms','propagation_control_ms',
                'propagation_actuator_command_ms','propagation_actuator_realization_ms','propagation_plant_ms') if last[k]]
            self.assertEqual(times,sorted(times))

    def test_missing_v2_fields_in_v1_csv_are_not_zero(self):
        rows=self.run_fault('bit_flip')
        keys=list(rows[0]); end=keys.index('fault_active')
        legacy=[{k:r[k] for k in keys[:end]} for r in rows]
        report=summarize_rows(legacy)
        for key in ('hazard_entered','ftti_met','containment_time_ms','max_propagation_stage'):
            self.assertIsNone(report[key])
        self.assertFalse(report['hazard_telemetry_available'])

    def test_campaign_expansion_and_denominators(self):
        config=read_study(DEFAULT_STUDY)
        runs=expand_runs(config)
        self.assertEqual(len(runs),182)
        self.assertEqual(len({r['run_id'] for r in runs}),182)
        self.assertEqual({r['parameters']['seed'] for r in runs},{42})
        stats=group_statistics([{'injected':1,'detected':1,'cross_layer_detection_latency_ms':0},
                                {'injected':1,'detected':0,'cross_layer_detection_latency_ms':None},
                                {'injected':0,'detected':0}, {'injected':1,'detected':None}])
        self.assertEqual(stats['detection_coverage_numerator'],1)
        self.assertEqual(stats['detection_coverage_denominator'],2)
        self.assertEqual(stats['detection_latency_ms_mean'],0)
        self.assertEqual(stats['detection_latency_ms_n'],1)

    def test_invalid_v2_parameters(self):
        for model,options in (
            ('stuck_bit',['--stuck-polarity','2']),
            ('bit_flip',['--fault-behavior','intermittent','--intermittent-off-ms','0']),
            ('task_delay',['--task-delay-ms','150']),
            ('delayed_update',['--communication-delay-ms','25600']),
            ('replayed_sample',['--fault-start-ms','100','--replay-age-ms','500']),
            ('dropped_update',['--drop-count','4','--drop-every-n-updates','3']),
        ):
            result=subprocess.run([str(ROOT/'virtual_ecu'),str(self.directory/'bad.csv'),'baseline',
                '--cross-layer-fault',model,*options],capture_output=True)
            self.assertNotEqual(result.returncode,0,(model,options))


class HazardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='vecu_hazard_contract_')
        cls.directory=Path(cls.temp.name)
        source=cls.directory/'contract.c'
        source.write_text(r'''
#include <assert.h>
#include <string.h>
#include "ecu_types.h"
#include "cross_layer_fault.h"

static void tick(ecu_state_t *state, runtime_observation_t *o, experiment_ground_truth_t *t,
                 int now, float temperature) {
    o->time_ms=(unsigned int)now; t->coolant_true_c=temperature;
    hazard_model_step(&state->hazard_config,&state->hazard,o,t);
}
int main(int argc,char **argv) {
    (void)argc;
    ecu_state_t s={0}; runtime_observation_t o={0}; experiment_ground_truth_t t={0};
    hazard_config_default(&s.hazard_config); s.hazard_config.enabled=true;
    s.hazard_config.max_critical_exposure_ms=200; s.hazard_config.recovery_hold_ms=100;
    s.hazard_config.fault_tolerant_time_interval_ms=200;
    hazard_model_init(&s.hazard);
    t.propagation=(propagation_monitor_t){.injection_ms=100,.internal_ms=100,.control_ms=100,
        .actuator_command_ms=-1,.actuator_realization_ms=-1,.plant_ms=-1,.detector_ms=-1,
        .safety_response_ms=-1,.safe_state_ms=-1};
    t.fault.layer=FAULT_LAYER_MEMORY; t.fault_active=true;
    if (!strcmp(argv[1],"boundary")) {
        runtime_observation_t before,after;
        runtime_observation_capture(&s,&before);
        s.cross_layer_fault.fault_id=99; s.cross_layer_fault.start_ms=42;
        s.cross_layer_runtime.active=true; s.plant.coolant_temp_true_c=140;
        s.propagation.plant_ms=9; s.hazard.hazard_entered=true;
        runtime_observation_capture(&s,&after);
        assert(before.coolant_measured_c==after.coolant_measured_c);
        assert(before.sample_timestamp_ms==after.sample_timestamp_ms);
        assert(before.detector_alarm==after.detector_alarm);
        assert(before.control_target_c==after.control_target_c);
        return 0;
    }
    if (!strcmp(argv[1],"stuck_rewrite")) {
        s.cross_layer_fault=(fault_descriptor_t){.enabled=true,.layer=FAULT_LAYER_MEMORY,
            .model=FAULT_MODEL_STUCK_BIT,.behavior=FAULT_BEHAVIOR_PERMANENT,.bit_index=5,.stuck_polarity=1};
        s.control.target_register_c=92; cross_layer_fault_init(&s);
        cross_layer_fault_step(&s); assert(s.control.target_register_c==124);
        s.control.target_register_c=92; s.time.time_ms=100;
        cross_layer_fault_step(&s); assert(s.control.target_register_c==124);
        return 0;
    }
    if (!strcmp(argv[1],"hazard") || !strcmp(argv[1],"before") || !strcmp(argv[1],"after")) {
        t.propagation.detector_ms=100; o.safety_state=1;
        t.propagation.safe_state_ms=!strcmp(argv[1],"after") ? 400 : 100;
        tick(&s,&o,&t,100,116); assert(!s.hazard.hazard_entered);
        tick(&s,&o,&t,200,116); assert(!s.hazard.hazard_entered);
        tick(&s,&o,&t,300,116); assert(s.hazard.hazard_entered);
        tick(&s,&o,&t,400,100); tick(&s,&o,&t,500,100);
        assert(s.hazard.hazard_entry_ms==300); assert(s.hazard.hazard_exit_ms==400);
        assert(s.hazard.critical_exposure_ms==300);
        assert(s.hazard.containment_success==0 && s.hazard.ftti_met==0);
    } else if (!strcmp(argv[1],"short_crossing")) {
        tick(&s,&o,&t,100,116); tick(&s,&o,&t,200,100);
        assert(s.hazard.critical_entered && !s.hazard.hazard_entered);
        assert(s.hazard.critical_exposure_ms==100);
    } else if (!strcmp(argv[1],"pass") || !strcmp(argv[1],"fail")) {
        o.safety_state=1;
        if (!strcmp(argv[1],"fail")) s.hazard_config.fault_tolerant_time_interval_ms=50;
        tick(&s,&o,&t,100,100); tick(&s,&o,&t,200,100);
        assert(s.hazard.containment_success==1);
        assert(s.hazard.ftti_met==(!strcmp(argv[1],"pass")));
    } else if (!strcmp(argv[1],"recovery_invalidated")) {
        o.safety_state=1;
        tick(&s,&o,&t,100,100); tick(&s,&o,&t,200,100);
        assert(s.hazard.containment_success==1 && s.hazard.max_propagation_stage==6);
        tick(&s,&o,&t,300,110);
        assert(s.hazard.containment_success==0 && s.hazard.containment_ms==-1);
        assert(s.hazard.max_propagation_stage==6);
    } else if (!strcmp(argv[1],"silent_recovery")) {
        t.fault_active=false; t.reference_coolant_true_c=100;
        tick(&s,&o,&t,100,100); tick(&s,&o,&t,200,100);
        assert(s.hazard.containment_success==1 && t.propagation.detector_ms==-1);
    } else if (!strcmp(argv[1],"same_tick_hazard")) {
        s.hazard_config.max_critical_exposure_ms=0;
        tick(&s,&o,&t,100,116);
        assert(s.hazard.preexisting_hazard && s.hazard.containment_success==-1);
    } else if (!strcmp(argv[1],"preexisting")) {
        s.hazard_config.max_critical_exposure_ms=0;
        t.propagation.injection_ms=-1; tick(&s,&o,&t,0,116);
        t.propagation.injection_ms=100; tick(&s,&o,&t,100,116);
        assert(s.hazard.preexisting_hazard && s.hazard.ftti_met==-1);
    }
    s.propagation=t.propagation;
    printf("case"); hazard_csv_header(stdout); puts("");
    printf("%s",argv[1]); hazard_csv_row(stdout,&s); puts("");
    return 0;
}
''')
        cls.binary=cls.directory/'contract'
        subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Wpedantic','-I'+str(ROOT/'include'),
                        str(source),str(ROOT/'src/hazard_model.c'),str(ROOT/'src/runtime_observation.c'),
                        str(ROOT/'src/cross_layer_config.c'),str(ROOT/'src/cross_layer_fault.c'),
                        '-o',str(cls.binary)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def contract(self,name):
        completed=subprocess.run([str(self.binary),name],check=True,capture_output=True,text=True)
        return list(csv.DictReader(completed.stdout.splitlines()))

    def test_hazard_entry_exit_and_detection_not_containment(self): self.contract('hazard')
    def test_short_critical_crossing_is_not_sustained_hazard(self): self.contract('short_crossing')
    def test_ftti_pass(self): self.contract('pass')
    def test_ftti_fail_despite_eventual_containment(self): self.contract('fail')
    def test_silent_recovery_can_contain_without_detection(self): self.contract('silent_recovery')
    def test_later_thermal_change_invalidates_containment_but_preserves_max_stage(self): self.contract('recovery_invalidated')
    def test_preexisting_hazard_makes_fault_attribution_unavailable(self): self.contract('preexisting')
    def test_hazard_in_injection_tick_predates_physical_fault_effect(self): self.contract('same_tick_hazard')
    def test_new_observation_boundary(self): self.contract('boundary')
    def test_stuck_bit_is_reapplied_after_a_register_write(self): self.contract('stuck_rewrite')
    def test_safe_state_before_and_after_hazard(self):
        self.assertEqual(self.contract('before')[0]['safe_state_before_hazard'],'1')
        self.assertEqual(self.contract('after')[0]['safe_state_before_hazard'],'0')
