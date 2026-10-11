"""Contract tests for the standalone open-loop analytical provider."""
import subprocess,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AnalyticalThermalTest(unittest.TestCase):
 def test_independence_uncertainty_and_global_ambiguity(self):
    directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);tmp_path=Path(directory.name)
    source=tmp_path/'test.c'
    source.write_text(r'''
#include "analytical_thermal.h"
#include <assert.h>
#include <string.h>
int main(void){
 analytical_config_t c={.initial=88,.sigma=.5,.bound=1,.coefficient={2,9,-.025,-.08,0,0,-7,-6}};
 analytical_state_t a={0},b={0};bool valid[3]={true,true,true},unknown;
 for(unsigned ms=0;ms<120000;ms+=100){
  analytical_input_t u={ms,.6,20,40,.3,0};
  analytical_thermal_step(&a,&c,&u);analytical_thermal_step(&b,&c,&u);
  double sensors[3]={-9000+(double)ms,10000,-1};
  analytical_state_t before=a;(void)analytical_consistency(&a,&c,sensors,valid,&unknown);
  assert(!memcmp(&a,&before,sizeof a));assert(!memcmp(&a,&b,sizeof a));
 }
 analytical_state_t c0=a,c1=a;analytical_input_t command={120000,.6,20,40,0,0};
 analytical_thermal_step(&c0,&c,&command);command.pump=1;analytical_thermal_step(&c1,&c,&command);assert(c0.temperature==c1.temperature);
 command.ms+=100;analytical_thermal_step(&c0,&c,&command);analytical_thermal_step(&c1,&c,&command);assert(c0.temperature!=c1.temperature);
 double v[3]={a.temperature,a.temperature,a.temperature};
 assert(analytical_consistency(&a,&c,v,valid,&unknown)==0);
 v[0]+=3;assert(analytical_consistency(&a,&c,v,valid,&unknown)==1&&!unknown);
 v[1]+=3;v[2]+=3;assert(analytical_consistency(&a,&c,v,valid,&unknown)==1&&unknown);
 v[2]-=6;assert(analytical_consistency(&a,&c,v,valid,&unknown)==0);
 c.bound=100;assert(analytical_consistency(&a,&c,v,valid,&unknown)==0);
 c.bound=1;valid[0]=false;assert(analytical_consistency(&a,&c,v,valid,&unknown)==0);
 return 0;
}
''')
    exe=tmp_path/'test'
    subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'include'),str(source),str(ROOT/'src/v7_3/analytical_thermal.c'),'-lm','-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

if __name__=="__main__":unittest.main()
