"""Headless contracts for v6.1 presentation; original v6 commands are fixtures."""
import copy
import json
import sys
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.cross_layer_ui import (DEFAULTS, MODEL_TARGETS, UI_MODELS, CONTRACT, behaviors,
    visible_fields, backend_request, interpretation, propagation_states)
from virtual_ecu.gui_design import NAVIGATION, PAGE_LABELS, HELP, button_role, status_category
from virtual_ecu.gui_workflows import extrema, comparison_run_label


class GuiUXTests(unittest.TestCase):
    def test_original_v6_command_equivalence(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/gui_v6_commands.json').read_text())
        for case in fixture['cases']:
            with self.subTest(model=case['values']['Fault Model'],behavior=case['values']['Behavior']):
                positional,options=backend_request(case['values'])
                self.assertEqual(positional,case['positional'])
                self.assertEqual(options+['--detector','hybrid_adaptive_kalman','--detector-action','observe_only'],case['options'])

    def test_original_gui_execution_definitions_unchanged(self):
        from virtual_ecu.gui_execution import verify_gui_execution
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(verify_gui_execution(root),398)

    def test_gui_execution_guard_rejects_command_mutation(self):
        from virtual_ecu.gui_execution import verify_gui_execution
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/'scripts';destination.mkdir()
            source=(root/'scripts/virtual_ecu_gui.py').read_text()
            # Change an existing execution function, not a presentation method.
            source=source.replace('return load_existing_result_pair(selected_path)', 'return None',1)
            (destination/'virtual_ecu_gui.py').write_text(source)
            with self.assertRaisesRegex(ValueError,'execution/analysis'):
                verify_gui_execution(Path(directory))

    def test_final_reproducibility_controls_use_new_destination(self):
        from virtual_ecu import final_validation_gui as final_gui
        for mode in ('--quick-check','--analysis-only'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                captured=[]
                class Status:
                    def set(self,value):self.value=value
                status=Status()
                def background(title,detail,task,**kwargs):
                    result=task();kwargs['on_success'](result)
                panel=SimpleNamespace(directory=root/'results/cross_layer_safety_v6',status=status,
                    background_task=background,buttons=[],load=lambda path:captured.append(path))
                def run(command,**kwargs):
                    captured.append(command)
                    return SimpleNamespace(returncode=0,stdout='PASS',stderr='')
                with patch.object(final_gui,'ROOT',root),patch.object(final_gui.subprocess,'run',side_effect=run):
                    final_gui.FinalValidationPanel.run_mode(panel,mode)
                destination=root/'results/cross_layer_safety_v6_1/final_validation'
                self.assertEqual(captured[0][-3:],[mode,'--output-dir',str(destination)])
                self.assertEqual(captured[-1],destination)
                self.assertFalse(panel.directory.exists())
                self.assertTrue(status.value.startswith('Completed'))

    def test_frozen_guided_defaults(self):
        self.assertEqual([DEFAULTS[k] for k in ('FTTI (ms)','Warning Threshold (°C)','Critical Threshold (°C)','Max Critical Exposure (ms)','Timing Monitor','Communication Safety Response')],['5000','108','115','1000','Disabled','Observe Only'])
        self.assertEqual(DEFAULTS['Seed'],'42')

    def test_guided_memory_fields(self):
        fields=visible_fields(DEFAULTS)
        self.assertIn('Bit Index',fields)
        self.assertNotIn('Replay Age (ms)',fields)
        self.assertNotIn('Stuck Polarity',fields)
        self.assertNotIn('Seed',fields)
        self.assertNotIn('FTTI (ms)',fields)

    def test_stuck_polarity(self):
        self.assertIn('Stuck Polarity',visible_fields({**DEFAULTS,'Fault Model':'stuck_bit'}))

    def test_timing_task_fields(self):
        fields=visible_fields({**DEFAULTS,'Fault Model':'task_delay'})
        self.assertIn('Task Delay (ms)',fields)
        self.assertNotIn('Bit Index',fields)
        self.assertNotIn('Replay Age (ms)',fields)

    def test_replay_fields(self):
        fields=visible_fields({**DEFAULTS,'Fault Model':'replayed_sample'})
        self.assertIn('Replay Age (ms)',fields)
        self.assertNotIn('Communication Delay (ms)',fields)
        self.assertNotIn('Task Delay (ms)',fields)

    def test_drop_fields(self):
        fields=visible_fields({**DEFAULTS,'Fault Model':'dropped_update'})
        self.assertTrue({'Drop Count','Drop Every N Updates'}<=fields)
        self.assertNotIn('Replay Age (ms)',fields)

    def test_intermittent_controls(self):
        for model in MODEL_TARGETS:
            for behavior in behaviors(model):
                fields=visible_fields({**DEFAULTS,'Fault Model':model,'Behavior':behavior})
                self.assertEqual('Intermittent ON (ms)' in fields,behavior=='intermittent')
                self.assertEqual('Intermittent OFF (ms)' in fields,behavior=='intermittent')

    def test_permanent_and_single_deadline_hide_duration(self):
        self.assertNotIn('Duration (ms)',visible_fields({**DEFAULTS,'Behavior':'permanent'}))
        self.assertNotIn('Duration (ms)',visible_fields({**DEFAULTS,'Fault Model':'deadline_miss'}))

    def test_advanced_contract_access(self):
        self.assertTrue(set(CONTRACT)<=visible_fields(DEFAULTS,'Advanced'))
        self.assertIn('Seed',visible_fields(DEFAULTS,'Advanced'))
        self.assertTrue(set(CONTRACT)<=visible_fields(DEFAULTS,contract_open=True))

    def test_modes_do_not_mutate_values_or_commands(self):
        values={**DEFAULTS,'Seed':'92','FTTI (ms)':'7000','Replay Age (ms)':'1200'}
        original=copy.deepcopy(values);command=backend_request(values)
        for mode,expanded in [('Advanced',True),('Guided',False),('Guided',True)]:
            visible_fields(values,mode,expanded)
            self.assertEqual(values,original)
            self.assertEqual(backend_request(values),command)

    def test_every_field_remains_accessible(self):
        available=set()
        for model,(layer,_) in UI_MODELS.items():
            for behavior in behaviors(model):
                available.update(visible_fields({**DEFAULTS,'Fault Model':model,'Fault Layer':layer,'Behavior':behavior},'Advanced'))
        self.assertEqual(set(DEFAULTS)-available,set())

    def test_supported_layers_and_legacy_behavior(self):
        self.assertEqual({pair[0] for pair in UI_MODELS.values()},{'memory','timing','communication','sensing_control','actuator'})
        for model in ('sensor_bias','pump_degraded','fan_stuck_off'):
            self.assertEqual(behaviors(model),('transient','permanent'))
            positional,options=backend_request({**DEFAULTS,'Fault Model':model})
            self.assertEqual(positional[:2],['custom',model])
            self.assertIn('--cross-layer-monitor',options)

    def test_unsupported_model_and_behavior_rejected(self):
        for values in ({**DEFAULTS,'Fault Model':'invented'},{**DEFAULTS,'Fault Model':'sensor_bias','Behavior':'intermittent'}):
            with self.assertRaises(ValueError):backend_request(values)

    def test_navigation_ids_and_names(self):
        keys=[key for kind,_,key in NAVIGATION if kind=='page']
        self.assertEqual(len(keys),len(set(keys)))
        self.assertTrue({'dashboard','summary','figures','fault_path','research_analysis','rtl_security','cross_layer','exports','custom','final_validation'}==set(keys))
        self.assertEqual(PAGE_LABELS['runtime_study'],'Detector Study')
        self.assertEqual(PAGE_LABELS['custom'],'Advanced Experiment Builder')

    def test_semantic_actions(self):
        for text,role in [('Run Experiment','success'),('Compare All Algorithms','success'),('Compare vs Baseline','success'),('Regenerate Analysis','success'),('Export Snapshot','success'),('Load Results','primary'),('Open Final Report','secondary'),('Cancel','secondary'),('Delete preset','danger'),('Clear Results','danger')]:
            self.assertEqual(button_role(text),role)
        self.assertNotEqual(button_role('Inspect evidence','danger'),'danger')

    def test_status_vocabulary(self):
        for message,category in [('Ready','Ready'),('Running experiment','Running'),('Exported report','Completed'),('Loaded v5 evidence','Loaded'),('No results loaded','No Results'),('Warning: missing cohort','Warning'),('Load failed','Error')]:
            self.assertEqual(status_category(message),category)

    def test_tooltip_concepts(self):
        self.assertEqual(len(HELP),15)
        self.assertTrue(all(HELP.values()))

    def test_missing_evidence_not_inferred(self):
        self.assertIn('Hazard entered: N/A',interpretation({'plant_manifestation':True}))
        self.assertIn('Containment: N/A',interpretation({'safe_state_reached':True}))
        self.assertTrue(all(state=='N/A' for _,state,_ in propagation_states({})))

    def test_zero_timestamp_reached(self):
        self.assertEqual(propagation_states({'fault_injection_ms':0})[0],('Fault origin','reached','0'))

    def test_cross_layer_comparison_shows_recorded_fault(self):
        result={'raw_rows':[{'cross_layer_fault_enabled':'1','cross_layer_fault_model':'bit_flip'}],
                'summary_row':{'max_coolant_temp_c':'96.0','final_safe_state_label':'normal'}}
        text,is_cross_layer=comparison_run_label(result,'Baseline')
        self.assertTrue(is_cross_layer)
        self.assertIn('bit_flip (campaign: Baseline)',text)
        self.assertIn('96.0',text)
        self.assertEqual(comparison_run_label({'raw_rows':[{}]},'Legacy'),('Legacy',False))

    def test_sweep_ties_and_missing_values(self):
        rows=[{'detector_id':'Hybrid','coverage':'100'},{'detector_id':'baseline','coverage':'100'},{'detector_id':'missing','coverage':''}]
        self.assertEqual(extrema(rows,'coverage','detector_id',True),'100 · Hybrid, baseline (tie)')
        self.assertEqual(extrema(rows,'latency','detector_id'),'N/A')

if __name__=='__main__':unittest.main()
