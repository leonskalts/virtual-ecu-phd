"""Headless tests for formatting loaded evidence and research navigation state."""
import json
import sys
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.final_validation_gui import format_final_metric, read_final_summary
from virtual_ecu.gui_design import NAVIGATION, PAGE_LABELS, RESEARCH_VIEWS
from virtual_ecu.gui_workflows import comparison_key_difference, sweep_metric_values
from virtual_ecu.research_analysis_gui import ResearchAnalysisWorkspace


class ConsolidationTests(unittest.TestCase):
    def test_final_loaded_formatting(self):
        root=Path(__file__).resolve().parents[1]
        values=read_final_summary(root/'results/cross_layer_safety_v6')
        expected=[('558 / 558','100.00%'),('99.32–100.00%',''),('0 / 156',''),('0.00–2.40%',''),('33 / 33','33 / 33 detected pre-plant'),('394 / 540','72.96%'),('188 / 216','87.04%'),('28 / 216','')]
        self.assertEqual([format_final_metric(v) for v in list(values.values())[:8]],expected)

    def test_formatting_uses_input_not_frozen_constants(self):
        self.assertEqual(format_final_metric('17/31 (54.84%)'),('17 / 31','54.84%'))
        self.assertEqual(format_final_metric('2/9; pre-plant 1/9'),('2 / 9','1 / 9 detected pre-plant'))
        for value in ('N/A','Unavailable','7.4–19.6%'):
            self.assertEqual(format_final_metric(value),(value,''))
        self.assertEqual(format_final_metric(''),('N/A',''))

    def test_sidebar_and_legacy_aliases(self):
        keys={key for kind,_,key in NAVIGATION if kind=='page'}
        self.assertEqual(len(keys),10)
        self.assertTrue({'research_analysis','rtl_security','final_validation','custom'}<=keys)
        self.assertTrue({'batch','runtime_study','parameter_sweep'}.isdisjoint(keys))
        self.assertEqual(PAGE_LABELS['batch'],'Aggregate Analysis')
        self.assertEqual(len(RESEARCH_VIEWS),4)

    def test_research_selection_survives_other_pages(self):
        workspace=ResearchAnalysisWorkspace.__new__(ResearchAnalysisWorkspace)
        workspace.selected='research_analysis'
        workspace.selection=tk.StringVar(tk.Tcl(),value=workspace.selected)
        self.assertEqual(workspace.record('parameter_sweep'),'research_analysis')
        self.assertEqual(workspace.record('rtl_security'),'rtl_security')
        self.assertEqual(workspace.selected,'parameter_sweep')
        self.assertEqual(workspace.selection.get(),'parameter_sweep')
        seen=[];workspace.app=SimpleNamespace(_navigate_to_page=seen.append)
        workspace.show('research_analysis')
        self.assertEqual(workspace.selected,'research_analysis')
        self.assertEqual(seen,['research_analysis'])

    def test_sweep_preserves_all_ties_and_unavailable(self):
        interp=tk.Tcl()
        summary={name:tk.StringVar(interp,value=value) for name,value in [('Hybrid Coverage','83.0%'),('Hybrid Median Latency','4.0 ms'),('Clean Alarms','0/2')]}
        rows=[{'detector_id':name,'detector_name':label,'coverage_percent':coverage,'median_latency_ms':latency} for name,label,coverage,latency in [('a','Baseline A','90','0'),('b','Baseline B','90','0'),('hybrid_adaptive_kalman','Hybrid Adaptive Kalman','83','4'),('missing','Unavailable','nan','-1')]]
        result=sweep_metric_values(rows,summary)
        self.assertEqual(result['Best Coverage'],'90%\nBaseline A / Baseline B')
        self.assertEqual(result['Best Median Latency'],'0 ms\nBaseline A / Baseline B')
        self.assertEqual(result['Hybrid Coverage'],'83.0%')
        self.assertEqual(result['Clean Alarms'],'0/2')
        self.assertEqual(set(sweep_metric_values([],summary).values()),{'N/A'})

    def test_comparison_reuses_verdict_and_recorded_evidence(self):
        self.assertEqual(comparison_key_difference('Higher recorded temperature.\nLonger details.'),'Higher recorded temperature.')
        results={'left':{'summary_row':{'max_coolant_temp_c':'101.20'}},'right':{'summary_row':{'max_coolant_temp_c':'109.80'}}}
        before=json.dumps(results)
        self.assertEqual(comparison_key_difference('Legacy verdict',results),'Recorded maximum coolant: left 101.20 °C; right 109.80 °C.')
        self.assertEqual(json.dumps(results),before)
        self.assertIn('N/A',comparison_key_difference(''))
