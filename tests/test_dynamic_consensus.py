"""Native numerical/causal/qualification checks; no injected truth input."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DynamicConsensusTests(unittest.TestCase):
 def test_native_contract(self):
  code=r'''
#include "dynamic_consensus.h"
#include <assert.h>
#include <math.h>
#include <string.h>
int main(void){
 dc_config_t c={.variance={.01,.01,.01},.process_variance=1,.lambda=.9,.threshold=5,.alpha=.2,.healthy_margin=4.6,.consistency_bound=10,.common_bound=10,.origin_margin=6.9};
 dc_state_t s={0},prefix={0};
 for(unsigned i=0;i<1000;i++){
  dc_input_t u={.ms=i*100,.y={80+i*.01,80+i*.01,80+i*.01},.qualified=true};
  dynamic_consensus_step(&s,&c,&u);assert(s.stable);assert(s.mass==0);
  if(i==500)prefix=s;
 }
 assert(s.q_healthy>.99);assert(s.filter[0].x[0]>89);assert(s.margin<1e-8);
 dc_state_t causal={0};for(unsigned i=0;i<=500;i++){dc_input_t u={.ms=i*100,.y={80+i*.01,80+i*.01,80+i*.01},.qualified=true};dynamic_consensus_step(&causal,&c,&u);}assert(!memcmp(&prefix,&causal,sizeof causal));
 for(unsigned i=1000;i<1020;i++){dc_input_t u={.ms=i*100,.y={92,90,90},.qualified=true};dynamic_consensus_step(&s,&c,&u);assert(s.stable);}assert(s.D>c.threshold);assert(s.best==1);assert(s.q_healthy==0);
 dc_state_t ab={0},ba={0};c.robust=0;
 for(unsigned i=0;i<400;i++){
  dc_input_t u={.ms=i*100,.y={80+sin(i*.1)*.2,80+cos(i*.13)*.1,80},.qualified=true},v=u;
  v.y[0]=u.y[1];v.y[1]=u.y[0];dynamic_consensus_step(&ab,&c,&u);dynamic_consensus_step(&ba,&c,&v);
  assert(fabs(ab.D-ba.D)<1e-9);assert(fabs(ab.filter[1].ell-ba.filter[2].ell)<1e-9);
 }
 dc_state_t unchanged=ab;dc_input_t old={.ms=100,.y={0,1000,-1000},.qualified=true};dynamic_consensus_step(&ab,&c,&old);assert(!memcmp(&ab,&unchanged,sizeof ab));
 dc_input_t bad={.ms=102000,.y={NAN,0,0},.qualified=true};dynamic_consensus_step(&s,&c,&bad);assert(s.count==0&&s.mass==0&&s.stable);
 for(unsigned i=0;i<10000;i++){dc_input_t u={.ms=i*100,.y={80+sin(i*.2),80+sin(i*.2)+.01,80+sin(i*.2)-.01},.context={i%2,0,0,0},.qualified=true};c.robust=1;dynamic_consensus_step(&s,&c,&u);assert(s.stable);}
 return 0;
}
'''
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'test.c').write_text(code)
   subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'include'),str(p/'test.c'),str(ROOT/'src/v7_3/dynamic_consensus.c'),'-lm','-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
 def test_allowlist(self):
  text=(ROOT/'include/dynamic_consensus.h').read_text();self.assertNotIn('fault_origin',text);self.assertNotIn('plant',text);self.assertNotIn('injection',text)
 def test_actual_probe_callback_integrity(self):
  import sys
  sys.path.insert(0,str(ROOT/'scripts'))
  import run_dynamic_consensus as d
  function=d.FRONT[d.FRONT.index('static void dc_probe'):]
  code=r'''#include "memory_diagnostic.h"
#include <stdlib.h>
#include <assert.h>
typedef struct {void *log_file;struct {unsigned time_ms;} time;struct {uint16_t target_register_c;} control;} ecu_state_t;
static memory_diagnostic_t dc_memory;
static bool stuck;
static unsigned reads,writes;
static uint16_t cross_layer_memory_read(void *p){reads++;return ((ecu_state_t*)p)->control.target_register_c;}
static void cross_layer_memory_write(void *p,uint16_t v){writes++;((ecu_state_t*)p)->control.target_register_c=stuck?(v&~1U):v;}
'''+function+r'''
int main(void){
 ecu_state_t state={.log_file=(void*)1,.control={94}};memory_diagnostic_t baseline={0};
 for(unsigned now=0;now<=120000;now+=100){
  state.time.time_ms=now;unsigned phase=(now/100)%100;stuck=phase%11==0;
  memory_diagnostic_step(&baseline,now,cross_layer_memory_read,cross_layer_memory_write,&state);dc_probe(&state);
  assert(state.control.target_register_c==94);
  if(baseline.checked_ms==now){assert(dc_memory.checked_ms==now);assert(baseline.failed==dc_memory.failed);}
 }
 assert(baseline.checks==121);assert(dc_memory.checks==481);assert(reads+writes==7*(121+481));
 return 0;
}
'''
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'test.c').write_text(code)
   subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'include'),str(p/'test.c'),str(ROOT/'src/memory_diagnostic.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
 def test_phase_superset(self):
  phases=set(range(0,100,11))
  for _ in range(30):
   pairs=[]
   for begin in sorted(phases):
    gap=1
    while (begin+gap)%100 not in phases:gap+=1
    pairs.append((gap,-begin,begin))
   gap,_,begin=max(pairs);phases.add((begin+gap//2)%100)
  self.assertEqual(len(phases),40);self.assertTrue(set(range(0,100,11))<=phases)
if __name__=='__main__':unittest.main()
