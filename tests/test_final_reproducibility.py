"""V6 provenance, denominator and deterministic-presentation regression tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu import final_evidence as evidence
from virtual_ecu.final_reporting import generate, validate_traceability
from virtual_ecu.final_reproducibility import relocate, compare_historical_csv
from virtual_ecu.final_validation_gui import read_final_summary


class FinalEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='vecu-v6-test-')
        cls.out=Path(cls.temporary.name)
        generate(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_output_protection_including_ancestor_and_symlink(self):
        for i in range(1,6):
            with self.assertRaises(ValueError):evidence.safe_output(ROOT/f'results/cross_layer_safety_v{i}/new')
        with self.assertRaises(ValueError):evidence.safe_output(ROOT/'results')
        link=self.out/'accepted-link'
        link.symlink_to(ROOT/'results/cross_layer_safety_v5',target_is_directory=True)
        with self.assertRaises(ValueError):evidence.safe_output(link/'write')
        link.unlink()

    def test_frozen_source_and_evidence_mutations_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'src').mkdir();(root/'src/a.c').write_text('accepted')
            result=root/'results/cross_layer_safety_v5/a.csv';result.parent.mkdir(parents=True);result.write_text('a\n1\n')
            lock={'baseline_commit':'test','source_sha256':{'src/a.c':evidence.sha256(root/'src/a.c')},
                  'accepted_evidence_sha256':{'results/cross_layer_safety_v5/a.csv':evidence.sha256(result)}}
            with patch.object(evidence,'ROOT',root),patch.object(evidence,'read_lock',return_value=lock):
                evidence.verify_frozen()
                result.write_text('a\n2\n')
                with self.assertRaisesRegex(ValueError,'evidence missing or changed'):evidence.verify_frozen()
                result.write_text('a\n1\n');(root/'src/a.c').write_text('retuned')
                with self.assertRaisesRegex(ValueError,'scientific source'):evidence.verify_frozen()

    def test_configuration_uses_accepted_sources(self):
        cfg=evidence.final_configuration()
        self.assertFalse(cfg['scientific_behavior_modified'])
        self.assertEqual(cfg['hazard']['fault_tolerant_time_interval_ms'],5000)
        self.assertEqual(cfg['timing_contract']['period_ms'],100)
        self.assertEqual(cfg['recommended_monitor'],'combined')
        self.assertEqual(cfg['default_research_action'],'observe_only')

    def test_claim_sources_and_artifact_columns_resolve(self):
        self.assertEqual(validate_traceability(self.out),13)
        rows=evidence.records(self.out/'paper_artifact_traceability.csv')
        self.assertEqual(len(rows),19) # Four figures and five tables in three forms.

    def test_denominators_are_preserved(self):
        c={r['claim_id']:r for r in evidence.records(self.out/'claim_evidence_matrix.csv')}
        for cid,k,n in [('C1',558,558),('C2',0,156),('C3',33,33),('C5',394,540),('C6',188,216),('C7',28,216),('C9',5,5),('C13',11,558)]:
            self.assertEqual((c[cid]['numerator'],c[cid]['denominator']),(k,n))
        self.assertIn('prevention is N/A',c['C8']['limitations'])
        self.assertIn('hazard_prevention=N/A (empty cohort)',c['C8']['confidence_interval_95'])

    def test_layer_aggregates_match_accepted_summary(self):
        rows=evidence.records(self.out/'paper_tables/table_3_observability_by_consequence.csv')
        total=rows[0]
        for key in ['runs','detected','plant_propagation','detected_given_plant','silent_plant_propagation']:
            self.assertEqual(total[key],sum(r[key] for r in rows[1:]))
        self.assertEqual(total['plant_propagation'],total['detected_given_plant']+total['silent_plant_propagation'])

    def test_unqualified_claims_rejected_bounded_claims_retained(self):
        audit=evidence.records(self.out/'claim_audit.csv')
        self.assertEqual(sum(r['classification']=='NOT SUPPORTED' for r in audit),9)
        self.assertEqual(sum(r['classification']=='SUPPORTED' for r in audit),2)
        self.assertEqual(sum(r['classification']=='SUPPORTED WITH LIMITATION' for r in audit),11)
        self.assertTrue(all(r['defensible_wording'] and r['evidence'] for r in audit))

    def test_old_or_partial_summary_never_invents_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'research_summary.json'
            path.write_text(json.dumps({'schema_version':6,'fields':{'Legal Timing Alarms':'0/156'}}))
            fields=read_final_summary(Path(directory))
            self.assertEqual(fields['Timing Holdout Coverage'],'N/A')
            self.assertEqual(fields['Legal Timing Alarms'],'0/156')
            path.write_text(json.dumps({'schema_version':5,'fields':{}}))
            with self.assertRaises(ValueError):read_final_summary(Path(directory))

    def test_relocation_keeps_input_profile_but_moves_all_outputs(self):
        cmd=['/old/repo/virtual_ecu','/old/repo/results/a.csv','baseline','--driving-profile','/old/repo/profiles/driving/v5/profile_1.csv','--scheduler-events','/old/repo/results/a_events.csv']
        dest=self.out/'new.csv';new=relocate(cmd,dest)
        self.assertEqual(new[1],str(dest))
        self.assertEqual(new[-1],str(self.out/'new_events.csv'))
        self.assertEqual(new[4],str(ROOT/'profiles/driving/v5/profile_1.csv'))

    def test_manifest_detects_artifact_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);source=path/'source.csv';source.write_text('value\n1\n')
            evidence.write_csv(path/'manifests/artifact_manifest.csv',[{'relative_path':str(source),'sha256':evidence.sha256(source)}])
            self.assertEqual(evidence.verify_artifact_manifest(path),1)
            source.write_text('value\n2\n')
            with self.assertRaises(ValueError):evidence.verify_artifact_manifest(path)

    def test_historical_csv_allows_only_appended_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            a=Path(directory)/'old.csv';b=Path(directory)/'new.csv'
            a.write_text('time,value\n0,1.000\n');b.write_text('time,value,new\n0,1.000,\n')
            compare_historical_csv(a,b)
            b.write_text('time,value,new\n0,1.001,\n')
            with self.assertRaises(ValueError):compare_historical_csv(a,b)
            b.write_text('time,value,new\n0,1.000,\n1,1.000,\n')
            with self.assertRaises(ValueError):compare_historical_csv(a,b)

    def test_external_output_keeps_v6_provenance(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root=Path(directory);preset=root/'studies/index.yaml';preset.parent.mkdir();preset.write_text('version: 6\n')
            out=Path(external);(out/'report.md').write_text('final report')
            with patch.object(evidence,'ROOT',root),patch.object(evidence,'PRESET',preset),patch.object(evidence,'read_lock',return_value={'accepted_evidence_sha256':{},'source_sha256':{}}):
                rows=evidence.artifact_manifest(out)
            row=next(r for r in rows if r['relative_path']==str(out/'report.md'))
            self.assertEqual(row['study_version'],'v6')
            self.assertEqual(row['generated_by_script'],evidence.GENERATOR)

    def test_analysis_is_byte_reproducible(self):
        before={str(p.relative_to(self.out)):evidence.sha256(p) for p in self.out.rglob('*') if p.is_file()}
        generate(self.out)
        after={str(p.relative_to(self.out)):evidence.sha256(p) for p in self.out.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_no_unstable_timestamps_or_embedded_overhead_claim(self):
        report=(self.out/'final_report.md').read_text()
        self.assertIn('Embedded runtime/WCET', (self.out/'claim_audit.md').read_text())
        self.assertIn('within measurement noise',report)
        self.assertNotIn('Generated at ',report)


if __name__=='__main__':unittest.main()
