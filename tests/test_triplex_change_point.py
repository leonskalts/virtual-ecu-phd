"""Causal CP formulas, exact empirical tails, failure and origin qualification."""
import unittest,subprocess,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ChangePointTests(unittest.TestCase):
 def module(self):
  sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
  import select_change_point as p
  return p
 def test_statistics_causality_and_qualification(self):
  p=self.module();np=p.np
  a=np.zeros((80,4));a[:,0]=np.arange(80)*100;a[:,3]=1;a[:,1:3]=np.random.default_rng(19).normal(size=(80,2));c=dict(mean=[0,0],covariance=[[1,0],[0,1]])
  with tempfile.TemporaryDirectory() as folder:
   old=p.B;p.B=Path(folder);p.lib=None
   try:
    v=p.series(a,c);b=a.copy();b[40:,1:3]=999;self.assertTrue(np.array_equal(v[:40],p.series(b,c)[:40]))
    for t in [2,19,49,79]:
     lo=max(0,t-49);z=a[lo:t+1,1:3];step=max(np.sum(z[-n:],axis=0)@np.sum(z[-n:],axis=0)/n for n in range(3,len(z)+1));trans=max(np.sum(z[k:l+1],axis=0)@np.sum(z[k:l+1],axis=0)/(l-k+1) for k in range(len(z)) for l in range(k,min(len(z),k+12)))
     self.assertAlmostEqual(v[t,1],step,places=10);self.assertAlmostEqual(v[t,2],trans,places=10)
     slopes=[]
     for kk,w in enumerate([20,50]):
      if len(z)<w:continue
      time=np.arange(w)*.1;time-=time.mean();slope=time@z[-w:]/(time@time);self.assertTrue(np.allclose(slope,v[t,16+2*kk:18+2*kk]));slopes.append(slope@slope)
     if slopes:self.assertAlmostEqual(v[t,3],max(slopes),places=10)
    self.assertEqual(v[0,20],0);self.assertEqual(v[18,22],0);self.assertEqual(v[19,22],1)
    b=a.copy();b[30,3]=0;v=p.series(b,c);self.assertEqual(v[30,8],0);self.assertEqual(v[31,20],0);self.assertEqual(v[49,22],0);self.assertEqual(v[50,22],1)
    b=a.copy();b[30:,0]+=100;v=p.series(b,c);self.assertEqual(v[30,20],0);self.assertEqual(v[48,22],0)
    cdf=[np.array([0.,1.,1.,2.])]*3;v=p.series(a,dict(c,threshold=0,gamma=.25),cdf)
    for j in range(3):
     for i in np.flatnonzero(v[:,20+j]):self.assertEqual(v[i,4+j],(1+np.sum(cdf[j]>=v[i,1+j]))/5)
    self.assertTrue(np.all((v[:,8]>=0)&(v[:,8]<=.25)))
   finally:p.B=old;p.lib=None
 def test_features_exclude_labels_output_and_future(self):
  p=self.module();np=p.np;n=50;a=dict(input=np.zeros((n,10)),values=np.zeros((n,6)),available=np.ones((n,6),bool),subset=np.ones((n,6),int));a['input'][:,0]=np.arange(n)*100;a['input'][:,3]=1;c=dict(mean=[0,0],covariance=[[1,0],[0,1]]);a['svm_parity']=p.comparator_parity(a,c);v=np.zeros((n,44));x=p.features(a,v,True)
  a['input'][:,4:]=997;v[:,23:]=991;self.assertTrue(np.array_equal(x,p.features(a,v,True)));self.assertEqual(x.shape[1],38)
  b={k:z.copy() for k,z in a.items()};b['input'][25:,1:3]=999;self.assertTrue(np.array_equal(a['svm_parity'][:25],p.comparator_parity(b,c)[:25]))
 def test_extreme_values_and_singular_covariance(self):
  source=r'''
#include "triplex_change_point.h"
#include <assert.h>
#include <math.h>
int main(void){cp_state_t s={0};cp_config_t c={.chol={1,0,1},.slope_chol={{1,0,1},{1,0,1}},.gamma=.5};cp_input_t u={1000,NAN,0,true};triplex_cp_step(&s,&c,&u);assert(s.mass==0&&s.count==0);u.ac=1e308;triplex_cp_step(&s,&c,&u);assert(!s.stable&&s.mass==0);u.ac=0;c.chol[2]=0;triplex_cp_step(&s,&c,&u);assert(!s.stable&&s.mass==0);double p[3]={1,1,1};bool q[3]={true,true,true};for(unsigned i=0;i<3;i++)assert(isfinite(cp_combine(p,q,i)));return 0;}
'''
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'test.c').write_text(source);subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude',str(p/'test.c'),'src/v7_3/triplex_change_point.c','-lm','-o',str(p/'test')],cwd=ROOT,check=True);subprocess.run([str(p/'test')],check=True)
 def test_provider_cannot_name_origin(self):
  source=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text();source='extern double cp_mass;\n'+source;source=source.replace('    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);','    local=fmax(local,cp_mass);\n    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);')
  code=r'''#include "clo_dsf_revised.h"
#include "config.h"
#include <assert.h>
double cp_mass=.5;
int main(void){clo_revised_t s;clo_revised_init(&s);clo_final_config_t c={1,.8,.35,.5,.55,.15,.5,1};runtime_observation_t o={0};o.control_target_c=ECU_TARGET_COOLANT_TEMP_C;o.target_register_c=o.target_shadow_c=(unsigned)ECU_TARGET_COOLANT_TEMP_C;o.target_shadow_valid=true;o.source_valid=o.source_previous_valid=true;o.source_c=o.source_previous_c=o.coolant_measured_c=80;o.sample_freshness_ok=true;o.sample_expected_period_ms=100;for(unsigned i=1;i<=100;i++){o.time_ms=o.source_ms=o.sample_timestamp_ms=i*100;o.source_previous_ms=o.time_ms-100;o.control_execution_ms=(int)o.time_ms;clo_revised_step(&s,&c,&o);}assert(s.fusion.output.alarm);assert(!s.fusion.output.localization_valid);assert(s.fusion.output.estimated_origin==0);return 0;}
'''
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'core.c').write_text(source);(p/'test.c').write_text(code);objects=['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o'];subprocess.run(['gcc','-std=c11','-O2','-Iinclude',str(p/'test.c'),str(p/'core.c'),*objects,'-lm','-o',str(p/'test')],cwd=ROOT,check=True);subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
