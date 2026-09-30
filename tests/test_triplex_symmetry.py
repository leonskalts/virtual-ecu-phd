"""Permutation checks on runtime-equivalent observations; no injection metadata."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SymmetryTests(unittest.TestCase):
 def test_pair_and_triplex_permutations(self):
  code=r'''
#include "triplex_consistency.h"
#include <assert.h>
#include <math.h>
static unsigned swap_pattern(unsigned p){return p==1?2:p==2?1:p;}
int main(void){
 for(unsigned scenario=0;scenario<9;scenario++){
  triplex_consistency_t t,u;triplex_consistency_init(&t);triplex_consistency_init(&u);
  clo_revised_t pairs[6];for(unsigned j=0;j<6;j++)clo_revised_init(&pairs[j]);
  for(unsigned k=1;k<900;k++){
   unsigned ms=100*k;float base=70+.002f*k;
   float effect=k<100?0:scenario==0?.013f*(k-100):scenario==1?.8f:scenario==2?-1.1f:scenario==3?(k<107?.9f:0):scenario==4?(k%2?.2f:-.2f):scenario==5?(k==130?1.f:0):scenario==6?3.f:0;
   float v[3]={base+effect,base+.05f,base-.03f};
   if(scenario==6)v[1]=base-3.f;
   runtime_observation_t o={0};o.time_ms=o.source_ms=o.reference_ms=ms;o.source_valid=o.reference_valid=o.reference_enabled=true;o.source_c=v[0];o.reference_c=v[1];
   diagnostic_readout_t c={.value_c=v[2],.previous_c=v[2]-.002f,.sample_ms=ms,.previous_ms=ms-100,.valid=true,.previous_valid=true};
   if(scenario==8&&ms>=200){c.sample_ms-=37;c.previous_ms-=37;c.value_c-=.00074f;c.previous_c-=.00074f;}
   if(scenario==7&&k%17==0){o.source_ms-=100;o.source_valid=false;}
   runtime_observation_t p=o;p.source_c=o.reference_c;p.reference_c=o.source_c;p.source_ms=o.reference_ms;p.reference_ms=o.source_ms;p.source_valid=o.reference_valid;p.reference_valid=o.source_valid;
   triplex_consistency_step(&t,&o,&c);triplex_consistency_step(&u,&p,&c);
   assert(fabs(t.strength-u.strength)<1e-12);assert(fabs(t.ac_strength-u.bc_strength)<1e-12);assert(fabs(t.bc_strength-u.ac_strength)<1e-12);
   assert(t.qualified==u.qualified&&t.ambiguous==u.ambiguous);assert(swap_pattern(t.member_pattern)==u.member_pattern);
   /* Every pair, reversed endpoints: identical strength at EVERY timestamp,
      hence identical threshold crossings and detection-provider timing. */
   unsigned ends[3][2]={{0,1},{0,2},{1,2}};
   for(unsigned j=0;j<3;j++){
    runtime_observation_t a={0};a.time_ms=a.source_ms=a.reference_ms=ms;a.source_valid=a.reference_valid=a.reference_enabled=true;a.source_c=v[ends[j][0]];a.reference_c=v[ends[j][1]];
    runtime_observation_t b=a;b.source_c=a.reference_c;b.reference_c=a.source_c;
    double x=clo_existing_pair_strength(&pairs[2*j],&a),y=clo_existing_pair_strength(&pairs[2*j+1],&b);assert(fabs(x-y)<1e-12);
   }
  }
 }
 return 0;
}'''
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);(d/'test.c').write_text(code)
   (d/'bridge.c').write_text((ROOT/'src/v7_3/clo_dsf_revised.c').read_text()+'\ndouble clo_existing_pair_strength(clo_revised_t*s,const runtime_observation_t*o){return fmax(redundant_sensor(s,o),fast_redundant_sensor(s,o));}\n')
   objects=['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o']
   subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude',str(d/'test.c'),str(d/'bridge.c'),'src/v7_3/triplex_consistency.c',*objects,'-lm','-o',str(d/'test')],cwd=ROOT,check=True)
   subprocess.run([str(d/'test')],check=True)
if __name__=='__main__':unittest.main()
