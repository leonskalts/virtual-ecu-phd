"""Qualification, direct-origin isolation and forbidden-input separation."""
import unittest,tempfile,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MLSensorWeakTests(unittest.TestCase):
 def test_qualification_and_bounded_mass(self):
  code=r'''
#include "ml_sensor_weak.h"
#include <assert.h>
#include <math.h>
int main(void){
 ml_sensor_state_t s={0};ml_sensor_config_t c={.alpha=.1,.gate=1};ml_sensor_input_t x={.time_ms=1000,.qualified=false,.physical=1};
 assert(ml_sensor_mass(&s,&c,&x,1)==0);x.qualified=true;x.physical=0;assert(ml_sensor_mass(&s,&c,&x,1)==0);
 x.physical=.01;assert(fabs(ml_sensor_mass(&s,&c,&x,.9)-.09)<1e-12);
 c.gate=2;assert(ml_sensor_mass(&s,&c,&x,.7)==0);c.gate=3;s=(ml_sensor_state_t){0};
 x.time_ms=1100;assert(ml_sensor_mass(&s,&c,&x,.9)==0);x.time_ms+=100;assert(ml_sensor_mass(&s,&c,&x,.9)==0);x.time_ms+=100;assert(ml_sensor_mass(&s,&c,&x,.9)>.08);
 x.qualified=false;x.time_ms+=100;assert(ml_sensor_mass(&s,&c,&x,.9)==0);x.qualified=true;x.time_ms+=100;assert(ml_sensor_mass(&s,&c,&x,.9)==0);
 assert(ml_sensor_mass(&s,&c,&x,NAN)==0);
 ml_sensor_model_t m={0};for(unsigned j=0;j<12;j++)m.scale[j]=1;m.weight[0]=2;m.platt_slope=1;double z[12]={.5};
 assert(fabs(ml_sensor_margin(&m,z)-1)<1e-12);assert(ml_sensor_confidence(&m,z)>0&&ml_sensor_confidence(&m,z)<1);
 double sv[12]={0},dual[1]={2};m.rbf=1;m.n_support=1;m.gamma=1;m.support=sv;m.dual=dual;assert(fabs(ml_sensor_margin(&m,z)-2*exp(-.25))<1e-12);
 return 0;
}'''
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'test.c').write_text(code);subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude',str(p/'test.c'),'src/v7_3/ml_sensor_weak.c','-lm','-o',str(p/'test')],cwd=ROOT,check=True);subprocess.run([str(p/'test')],check=True)
 def test_ml_alone_cannot_localize(self):
  source=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text();source='extern double ml_extra_mass;\n'+source
  source=source.replace('    { /* Temporal fusion is always part of the final algorithm. */','    if(ml_extra_mass>0){double ml_conflict=0;support(&channel,C2_D_ABNORMAL,ml_extra_mass);if(!combine(&detect,&channel,&ml_conflict,&v->detection_conflict))v->detection_fallback=true;}\n    { /* Temporal fusion is always part of the final algorithm. */')
  code=r'''
#include "clo_dsf_revised.h"
#include "config.h"
#include <assert.h>
#include <math.h>
double ml_extra_mass=.2;
int main(void){clo_revised_t s;clo_revised_init(&s);clo_final_config_t c={1,.8,.35,.5,.55,.15,.5,1};
 runtime_observation_t o={0};o.control_target_c=ECU_TARGET_COOLANT_TEMP_C;o.target_register_c=o.target_shadow_c=(unsigned)ECU_TARGET_COOLANT_TEMP_C;o.target_shadow_valid=true;o.source_valid=o.source_previous_valid=true;o.source_c=o.source_previous_c=o.coolant_measured_c=80;o.sample_freshness_ok=true;o.sample_expected_period_ms=100;
 for(unsigned i=1;i<=200;i++){o.time_ms=o.source_ms=o.sample_timestamp_ms=i*100;o.source_previous_ms=o.time_ms-100;o.control_execution_ms=(int)o.time_ms;clo_revised_step(&s,&c,&o);}
 assert(s.fusion.output.alarm);assert(!s.fusion.output.localization_valid);assert(s.fusion.output.estimated_origin==0);assert(s.fusion.output.origin_ignorance>.99);
 return 0;}
'''
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'core.c').write_text(source);(p/'test.c').write_text(code)
   objects=['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o']
   subprocess.run(['gcc','-std=c11','-O2','-Iinclude',str(p/'test.c'),str(p/'core.c'),*objects,'-lm','-o',str(p/'test')],cwd=ROOT,check=True);subprocess.run([str(p/'test')],check=True)
 def test_features_ignore_alarm_origin_and_metadata_columns(self):
  sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
  import numpy as np
  import run_ml_assisted_clodsf as d
  x=np.zeros((30,30));x[:,0]=np.arange(30)*100;x[:,9]=1
  y=x.copy();y[:,10:]=np.random.default_rng(417).normal(size=(30,20))
  a,q=d.features(x);b,r=d.features(y);self.assertTrue(np.array_equal(a,b));self.assertTrue(np.array_equal(q,r));self.assertEqual(a.shape[1],12)
 def test_features_do_not_use_future_samples(self):
  sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
  import numpy as np
  import run_ml_assisted_clodsf as d
  x=np.random.default_rng(917).normal(size=(100,24));x[:,0]=np.arange(100)*100;x[:,9]=1
  y=x.copy();y[50:,1:10]=777
  a,q=d.features(x);b,r=d.features(y)
  self.assertTrue(np.array_equal(a[:50],b[:50]));self.assertTrue(np.array_equal(q[:50],r[:50]))
if __name__=='__main__':unittest.main()
