"""Numerical parity, ambiguity, qualification and forbidden-input tests."""
import unittest,subprocess,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ParityTests(unittest.TestCase):
 def test_geometry_qualification_and_numerics(self):
  source=r'''
#include "triplex_parity.h"
#include <assert.h>
#include <math.h>
int main(void){
 parity_config_t c={{0,0},1,.2,1,.1,2,.5,2};parity_state_t s={0};
 parity_input_t u={1000,.5,.5,true};triplex_parity_step(&s,&c,&u);
 /* whitened r=(.5,.4), vA=(1,-.2), vB=(0,1),vC=(-1,-.8). */
 assert(fabs(s.current_m-.41)<1e-12);assert(fabs(s.directional[0]-(.42*.42)/1.04)<1e-12);assert(fabs(s.directional[1]-.16)<1e-12);
 assert(s.directional[2]==s.directional[3]);assert(s.direction==0);assert(s.origin_mass==0);assert(s.mass>0&&s.mass<=.5);
 for(unsigned i=1;i<8;i++){u.ms+=100;triplex_parity_step(&s,&c,&u);}assert(s.count==8&&s.window==8);assert(fabs(s.m-8*.41)<1e-12);
 u.qualified=false;u.ms+=100;triplex_parity_step(&s,&c,&u);assert(!s.qualified&&s.count==0&&s.mass==0);
 u.qualified=true;u.ms+=100;triplex_parity_step(&s,&c,&u);assert(s.count==1&&s.window==1);
 u.ms+=200;triplex_parity_step(&s,&c,&u);assert(s.count==1);
 u.ac=u.bc=0;u.ms+=200;triplex_parity_step(&s,&c,&u);assert(s.g==0&&s.mass==0); /* equal ABC shift is absent in parity */
 u.ac=NAN;triplex_parity_step(&s,&c,&u);assert(s.mass==0&&!s.qualified);
 u.ac=1e308;u.bc=1e308;triplex_parity_step(&s,&c,&u);assert(!s.stable&&s.mass==0);
 c.l11=0;u.ac=u.bc=0;triplex_parity_step(&s,&c,&u);assert(!s.stable&&s.mass==0);
 return 0;}
'''
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'test.c').write_text(source);subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude',str(p/'test.c'),'src/v7_3/triplex_parity.c','-lm','-o',str(p/'test')],cwd=ROOT,check=True);subprocess.run([str(p/'test')],check=True)
 def test_runtime_features_exclude_alarm_and_metadata(self):
  sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
  import numpy as np
  import select_parity_space as p
  n=30;a=dict(input=np.zeros((n,15)),values=np.zeros((n,6)),available=np.ones((n,6),bool),subset=np.ones((n,6),int));a['input'][:,0]=np.arange(n)*100;a['input'][:,3]=1;v=np.zeros((n,23));x=p.features(a,v,True)
  a['input'][:,4:]=997;v[:,11:]=991;y=p.features(a,v,True);self.assertTrue(np.array_equal(x,y));self.assertEqual(x.shape[1],34)
 def test_future_parity_does_not_change_past(self):
  sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
  import numpy as np
  import select_parity_space as p
  a=np.zeros((50,4));a[:,0]=np.arange(50)*100;a[:,3]=1;a[:,1:3]=np.random.default_rng(19).normal(size=(50,2));b=a.copy();b[25:,1:3]=999
  c=dict(mean=[0,0],covariance=[[1,.2],[.2,2]])
  with tempfile.TemporaryDirectory() as folder:
   old=p.B;p.B=Path(folder)
   try:
    x=p.series(a,c);y=p.series(b,c);self.assertTrue(np.array_equal(x[:25],y[:25]))
   finally:p.B=old
 def test_ambiguous_provider_cannot_name_origin_in_ds(self):
  source=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text()
  source='extern double parity_mass,parity_origin_mass;\n'+source
  source=source.replace('    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);','    local=fmax(local,parity_mass);origin_local=fmax(origin_local,parity_origin_mass);\n    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);')
  code=r'''#include "clo_dsf_revised.h"
#include "config.h"
#include <assert.h>
double parity_mass=.5,parity_origin_mass=0;
int main(void){clo_revised_t s;clo_revised_init(&s);clo_final_config_t c={1,.8,.35,.5,.55,.15,.5,1};runtime_observation_t o={0};o.control_target_c=ECU_TARGET_COOLANT_TEMP_C;o.target_register_c=o.target_shadow_c=(unsigned)ECU_TARGET_COOLANT_TEMP_C;o.target_shadow_valid=true;o.source_valid=o.source_previous_valid=true;o.source_c=o.source_previous_c=o.coolant_measured_c=80;o.sample_freshness_ok=true;o.sample_expected_period_ms=100;
for(unsigned i=1;i<=100;i++){o.time_ms=o.source_ms=o.sample_timestamp_ms=i*100;o.source_previous_ms=o.time_ms-100;o.control_execution_ms=(int)o.time_ms;clo_revised_step(&s,&c,&o);}assert(s.fusion.output.alarm);assert(!s.fusion.output.localization_valid);assert(s.fusion.output.estimated_origin==0);return 0;}
'''
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'core.c').write_text(source);(p/'test.c').write_text(code)
   objects=['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o']
   subprocess.run(['gcc','-std=c11','-O2','-Iinclude',str(p/'test.c'),str(p/'core.c'),*objects,'-lm','-o',str(p/'test')],cwd=ROOT,check=True);subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
