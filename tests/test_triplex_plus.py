"""Readout-only alignment and no-repeat-persistence contracts."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TriplexPlusTests(unittest.TestCase):
 def test_alignment_freshness_and_legal_excursion(self):
  code=r'''
#include "triplex_plus.h"
#include <assert.h>
#include <math.h>
int main(void){
 for(unsigned scenario=0;scenario<4;scenario++){
  plus_stagger_t s;plus_stagger_init(&s);double peak=0;
  for(unsigned now=0;now<5000;now++){
   unsigned member=now%100==0?0:now%100==33?1:now%100==66?2:3;
   if(member==3)continue;
   float value=70+.001f*now;
   if(scenario==1&&member==1&&now==1033)value+=.83f;
   if(scenario==2&&member==1&&now>=1033)value+=1.2f;
   if(scenario==3&&member==2&&now==1066)value-=.83f;
   diagnostic_readout_t r={.value_c=value,.sample_ms=now,.valid=true};
   plus_stagger_readout(&s,member,&r);s.strength=0;plus_stagger_pairs(&s,now);peak=fmax(peak,s.strength);
   unsigned accepted=s.accepted_pairs;plus_stagger_pairs(&s,now);assert(accepted==s.accepted_pairs);
   double v,u;if(plus_stagger_align(&s,member,now,&v,&u)){assert(fabs(v-value)<1e-5);assert(u==0);}
  }
  if(scenario!=2)assert(peak==0);else assert(peak>=.5);
  double v,u;assert(!plus_stagger_align(&s,0,4000,&v,&u));assert(!plus_stagger_align(&s,0,6000,&v,&u));
 }
 assert(plus_conservative_difference(.1,.2)==0);
 assert(fabs(plus_conservative_difference(-.8,.1)+.7)<1e-9);
 return 0;
}'''
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);(d/'test.c').write_text(code)
   (d/'bridge.c').write_text((ROOT/'src/v7_3/clo_dsf_revised.c').read_text()+'\ndouble clo_existing_pair_strength(clo_revised_t*s,const runtime_observation_t*o){return fmax(redundant_sensor(s,o),fast_redundant_sensor(s,o));}\n')
   objects=['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o']
   subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude',str(d/'test.c'),str(d/'bridge.c'),'src/v7_3/triplex_plus.c',*objects,'-lm','-o',str(d/'test')],cwd=ROOT,check=True)
   subprocess.run([str(d/'test')],check=True)
if __name__=='__main__':unittest.main()
