import pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Integrity(unittest.TestCase):
 def test_boundary_and_failures(self):
  code=r'''
#include "digital_sensor_integrity.h"
#include <assert.h>
#include <string.h>
int main(void){
 di_witness_t w={0};di_record_t r,old;float v=42.125f;
 di_publish(&w,&r,1,v,100);assert(!di_verify(&w,&r,v,100));old=r;
 assert(di_verify(&w,&r,v+.42f,100)&1); /* value only */
 di_publish(&w,&r,1,v,200);assert(di_verify(&w,&old,v,100)&2); /* replay */
 v+=.3f;memcpy(&r.bits,&v,4);r.tag=di_tag(&r);assert(di_verify(&w,&r,v,200)&1); /* valid forged tag */
 w.protected_record.tag^=1;assert(di_verify(&w,&r,v,200)&4); /* witness upset */
 di_publish(&w,&r,1,v,300); /* pre-protection error is authenticated */
 assert(!di_verify(&w,&r,v,300));
 v+=.7f;memcpy(&r.bits,&v,4);r.tag=di_tag(&r);w.protected_record=r;
 assert(!di_verify(&w,&r,v,300)); /* consistent common failure is NOT covered */
 di_transform(&w,&r,.21f);v+=.21f;assert(!di_verify(&w,&r,v,300));
 return 0;
}'''
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);(p/'test.c').write_text(code)
   subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-I'+str(ROOT/'include'),str(p/'test.c'),str(ROOT/'src/v7_3/digital_sensor_integrity.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
