"""Development-evaluation boundaries, data integrity and additive GUI behavior."""
import csv
import gzip
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_development import design,command,OUTPUT,ORIGINS,candidate,selection_key
from virtual_ecu.clo_dsf_gui import read_evidence,run_experimental


class CloDevelopmentTests(unittest.TestCase):
    def test_design_counts_group_separation_and_balance(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);specs=design(root)
            self.assertEqual(len(specs),912)
            for o in ORIGINS:self.assertEqual(sum(s['origin']==o for s in specs),144)
            self.assertEqual(sum(s['origin']=='NORMAL' for s in specs),192)
            parts={p:{s['group'] for s in specs if s['partition']==p} for p in ['development-train','development-validation']}
            self.assertFalse(parts['development-train']&parts['development-validation'])
            profiles=[p.read_bytes() for p in (root/'profiles').glob('benign*.csv')]
            self.assertEqual(len(profiles),len(set(profiles)))

    def test_legacy_intermittent_uses_existing_sequence(self):
        spec=dict(run_id='example',model='sensor_bias',start_ms=25000,duration_ms=2000,behavior='intermittent',magnitude=4,profile='urban',simulation_duration_ms=120000)
        cmd=command(spec,OUTPUT,'train',OUTPUT/'initial_config.cfg')
        self.assertIn('custom_multi',cmd);self.assertNotIn('intermittent',cmd)
        self.assertIn('28000',cmd)

    def test_candidate_space_is_eight_global_configs(self):
        configs=[candidate(i) for i in range(8)]
        self.assertEqual(len({json.dumps(c,sort_keys=True) for c in configs}),8)
        for c in configs:self.assertEqual(set(c),set(configs[0]))
        for key in configs[0]:
            if key not in ['conflict_rule','lambda_temporal','alarm_threshold_confirmed']:
                self.assertEqual(len({c[key] for c in configs}),1)

    def test_false_alarms_outrank_coverage(self):
        common=dict(silent_plant=0,localization_accuracy=1,latency_median_ms=0,high_conflict_runs=0)
        clean=dict(common,benign_false_alarms=0,macro_coverage=.1)
        noisy=dict(common,benign_false_alarms=1,macro_coverage=1)
        self.assertLess(selection_key(clean,0),selection_key(noisy,1))

    def test_runtime_gui_allowlist_drops_truth(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'e.csv'
            path.write_text('time_ms,detector_state,estimated_origin,origin_score,ignorance_mass,conflict_mass,propagation_support,true_origin\n0,NORMAL,UNKNOWN,0,1,0,0,MEMORY\n')
            row=read_evidence(path)[0]
            self.assertNotIn('true_origin',row);self.assertEqual(row['estimated_origin'],'UNKNOWN')

    def test_old_csv_is_not_fabricated_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'old.csv';path.write_text('time_ms,coolant\n0,92\n')
            with self.assertRaises(ValueError):read_evidence(path)

    def test_experimental_command_is_separate_and_observe_only(self):
        with tempfile.TemporaryDirectory() as d,patch('virtual_ecu.clo_dsf_gui.subprocess.run') as run:
            run.return_value.returncode=0
            run_experimental(pathlib.Path(d)/'r.csv',['baseline'],[])
            cmd=run.call_args.args[0]
            self.assertEqual(pathlib.Path(cmd[0]).name,'virtual_ecu_v7')
            self.assertIn('clo_dsf',cmd);self.assertIn('observe_only',cmd)

    def test_study_evidence_denominators_and_candidates_train_only(self):
        path=OUTPUT/'clo_dsf_dev_runs.csv'
        if not path.exists():self.skipTest('Development package not generated')
        rows=list(csv.DictReader(path.open()))
        val=[r for r in rows if r['method']=='CLO-DSF' and r['partition']=='development-validation']
        self.assertEqual(len(val),336)
        self.assertFalse(any(r['method'].startswith('candidate_') and r['partition']=='development-validation' for r in rows))
        self.assertTrue(all(int(r['detected'])+int(r['silent_plant'])==1 for r in val if r['plant_manifestation']=='1' and r['injected']=='1'))
        for r in val:
            self.assertTrue(0<=float(r['mean_ignorance'])<=1)
            self.assertTrue(0<=float(r['mean_conflict'])<=1)
        selected=json.loads((OUTPUT/'selection_record.json').read_text())
        self.assertFalse(selected['validation_seen'])

    def test_archived_runtime_csv_contains_no_evaluation_fields(self):
        paths=list((OUTPUT/'traces').glob('dev_*.gz'))
        if not paths:self.skipTest('Development package not generated')
        for path in paths[::100]:
            with gzip.open(path,'rt') as f: header=next(csv.reader(f))
            for forbidden in ['true_origin','fault_layer','fault_active','fault_model','propagation_plant_ms','injection_ms']:
                self.assertNotIn(forbidden,header)
            self.assertTrue(all(f'conflict_step_{i}' in header for i in range(8)))

    def test_cli_default_sidecar_path_and_invalid_config(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'logs').mkdir()
            subprocess.run(['make'],cwd=ROOT,check=True,capture_output=True)
            result=subprocess.run([str(ROOT/'virtual_ecu_v7'),'baseline','--simulation-duration-ms','1000','--detector','clo_dsf'],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((root/'logs/thermal_run.csv.clo_dsf.csv').is_file())
            self.assertFalse((root/'baseline.clo_dsf.csv').exists())
            bad=root/'bad.cfg';bad.write_text('lambda_temporal=nan\n')
            result=subprocess.run([str(ROOT/'virtual_ecu_v7'),str(root/'r.csv'),'baseline','--clo-config',str(bad)],cwd=root,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((root/'r.csv').exists())

    def test_physical_equivalence_audit_has_no_validation_repeats(self):
        path=OUTPUT/'physical_equivalence_audit.json'
        if not path.exists():self.skipTest('Development audit not generated')
        data=json.loads(path.read_text())
        self.assertEqual(data['configured_simulations'],912)
        self.assertEqual(data['distinct_physical_configurations'],896)
        self.assertEqual(data['validation_redundant_executions'],0)
        self.assertTrue(data['same_selected_candidate'])
