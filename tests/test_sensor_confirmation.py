import pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Confirmation(unittest.TestCase):
 def test_provenance_persistence_and_bypass(self):
  source=r'''
#include "sensor_confirmation.h"
#include <assert.h>
#include <math.h>
int main(void){sensor_confirmation_t s={0};
 assert(!sensor_confirmation_step(&s,0,true,false,1,true,3,.5));
 assert(!sensor_confirmation_step(&s,100,true,false,1,true,3,.5));
 assert(!sensor_confirmation_step(&s,100,true,false,1,true,3,.5));
 assert(sensor_confirmation_step(&s,200,true,false,1,true,3,.5));
 assert(!sensor_confirmation_step(&s,300,true,false,0,true,3,.5));
 assert(sensor_confirmation_step(&s,300,false,false,0,true,3,.5)); /* FAIL or UNKNOWN */
 assert(sensor_confirmation_step(&s,400,true,true,0,true,3,.5)); /* any other layer */
 assert(!sensor_confirmation_step(&s,500,true,false,1,true,3,.5));
 assert(!sensor_confirmation_step(&s,700,true,false,1,true,3,.5)); /* gap resets */
 assert(!sensor_confirmation_step(&s,800,true,false,NAN,true,3,.5));
 assert(!sensor_confirmation_step(&s,900,false,true,1,false,3,.5)); /* never invent alarm */
 assert(sensor_confirmation_step(&s,1000,true,false,0,true,0,0)); /* original endpoint */
 return 0;}
'''
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);(p/'test.c').write_text(source)
   subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-I'+str(ROOT/'include'),str(p/'test.c'),str(ROOT/'src/v7_3/sensor_confirmation.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
