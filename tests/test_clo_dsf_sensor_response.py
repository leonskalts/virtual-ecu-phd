"""Scientific boundaries of the sensor-response development campaign."""
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_clo_dsf_sensor_response import design, command
class SensorResponseCampaignTests(unittest.TestCase):
    def test_disjoint_groupwise_design(self):
        rows=design();self.assertEqual(len(rows),900)
        train=[r for r in rows if r['partition']=='development-train']
        val=[r for r in rows if r['partition']=='development-validation']
        self.assertEqual((len(train),len(val)),(600,300))
        self.assertFalse({r['group'] for r in train}&{r['group'] for r in val})
        self.assertFalse({r['profile_semantic_sha256'] for r in train}&{r['profile_semantic_sha256'] for r in val})
        self.assertEqual(len({r['configuration_sha256'] for r in rows}),900)
    def test_ramp_is_explicit_experiment_input(self):
        r=next(r for r in design() if r['model']=='sensor_bias_ramp')
        args=command(r,Path('/tmp/unused-response-test'))
        self.assertIn('--revised-sensor-ramp',args)
        start=args.index('custom')
        self.assertEqual(args[start+1],'sensor_bias')
        self.assertEqual(float(args[start+5]),0)
        self.assertEqual(r['duration_ms'],0)
        core=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text()
        for hidden in ['sensor_ramp','sensor_variation','ground_truth','thermal_plant','faults.','propagation.plant']:
            self.assertNotIn(hidden,core)
    def test_benign_and_dormant_coverage(self):
        rows=design()
        self.assertEqual(sum(r['origin']=='NORMAL' for r in rows),180)
        for part in ['development-train','development-validation']:
            subset=[r for r in rows if r['partition']==part]
            self.assertEqual(len({r['sensor_variation'] for r in subset if r['origin']=='NORMAL'}),6)
            self.assertTrue(any(r['initially_latent_stuck'] and r['workload']=='static_target' for r in subset))
            self.assertEqual({r['sensor_ramp_rise_ms'] for r in subset if r['model']=='sensor_bias_ramp'},{2000,10000,30000})
