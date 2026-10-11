"""Sequential runtime state and qualification contracts; no fault labels."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SequentialTests(unittest.TestCase):
 def test_bounded_accumulation_and_unavailable_decay(self):
  code=r'''
#include "triplex_plus_sequential.h"
#include <assert.h>
#include <math.h>
int main(void){
 plus_oq_t s;plus_oq_init(&s);double table[60],e[6]={.02,0,0,0,0,0};unsigned char available[6]={1,0,0,0,0,0};
 for(unsigned i=0;i<60;i++)table[i]=2;
 assert(!plus_oq_step(&s,e,available,table,.8,4));assert(s.score[0]==2);
 assert(!plus_oq_step(&s,e,available,table,.8,4));assert(fabs(s.score[0]-3.6)<1e-12);
 assert(plus_oq_step(&s,e,available,table,.8,4));
 available[0]=0;assert(!plus_oq_step(&s,e,available,table,.8,4));
 for(unsigned i=0;i<20;i++)plus_oq_step(&s,e,available,table,.8,4);
 assert(s.score[0]<.1);available[0]=1;
 for(unsigned i=0;i<60;i++)table[i]=100;
 for(unsigned i=0;i<100;i++)plus_oq_step(&s,e,available,table,1,4);
 assert(s.score[0]==32);e[0]=NAN;assert(!plus_oq_step(&s,e,available,table,.8,4));
 assert(e[1]==0&&available[1]==0);
 return 0;
}'''
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);(d/'test.c').write_text(code)
   subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude',str(d/'test.c'),'src/v7_3/triplex_plus_sequential.c','-lm','-o',str(d/'test')],cwd=ROOT,check=True)
   subprocess.run([str(d/'test')],check=True)
if __name__=='__main__':unittest.main()
