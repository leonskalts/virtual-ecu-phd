import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MultiRateTests(unittest.TestCase):
 def test_runtime_symmetry_noise_and_probe_restore(self):
  code=r'''
#include "multirate_triplex.h"
#include "multirate_memory.h"
#include <assert.h>
#include <math.h>
static uint16_t value=93;
static uint16_t read_value(void*c){(void)c;return value;}
static void write_value(void*c,uint16_t x){(void)c;value=x;}
int main(void){
 for(unsigned p=25;p<=50;p+=25){
  mr_triplex_t a,b;mr_triplex_init(&a,p);mr_triplex_init(&b,p);
  for(unsigned ms=p;ms<3000;ms+=p){float v[3]={80,80,80};if(ms==1000)v[0]+=.9f;float w[3]={v[1],v[0],v[2]};mr_triplex_step(&a,ms,v,true);mr_triplex_step(&b,ms,w,true);assert(a.strength==0&&a.strength==b.strength);}
  bool detected=false;
  for(unsigned ms=3000;ms<3300;ms+=p){float v[3]={81,80,80};mr_triplex_step(&a,ms,v,true);detected=detected||a.strength>0;}
  assert(detected);
 }
 for(unsigned rate=250;rate<=500;rate+=250){memory_diagnostic_t m={0};for(unsigned now=0;now<=10000;now+=100){mr_memory_step(&m,now,rate,read_value,write_value,0);assert(value==93&&!m.failed);}assert(m.checks==(rate==250?41:21));assert(m.operations==7*m.checks);}
 return 0;
}'''
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'test.c').write_text(code)
   subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Iinclude',str(p/'test.c'),'src/v7_3/multirate_triplex.c','src/v7_3/multirate_memory.c','-lm','-o',str(p/'test')],cwd=ROOT,check=True)
   subprocess.run([str(p/'test')],check=True)
 def test_provider_has_no_truth_or_fault_metadata(self):
  for name in ['multirate_triplex.c','multirate_memory.c']:
   source=(ROOT/'src/v7_3'/name).read_text()
   for forbidden in ['ecu_types.h','cross_layer_fault','plant.','faults.','injection_','propagation']:self.assertNotIn(forbidden,source)
if __name__=='__main__':unittest.main()
