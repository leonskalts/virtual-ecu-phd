import unittest,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TriplexTests(unittest.TestCase):
 def test_independent_nonideal_sensor_and_runtime_pair_provider(self):
  code=r'''
#include "triplex_consistency.h"
#include <assert.h>
#include <math.h>
int main(void){
 diagnostic_temperature_t a,b;diagnostic_temperature_init(&a,19,.1,.001,.02,.02,.0003,100,37,0);diagnostic_temperature_init(&b,29,-.1,-.001,.03,.025,-.0002,100,67,0);
 assert(!diagnostic_temperature_sample(&a,0,80));assert(diagnostic_temperature_sample(&a,100,80.1));assert(a.output.sample_ms==37);assert(a.output.value_c!=80.1f);
 assert(diagnostic_temperature_sample(&a,200,80.2));assert(a.output.previous_valid&&a.output.previous_ms==37&&a.output.sample_ms==137);
 diagnostic_temperature_sample(&b,200,80.2);assert(b.output.sample_ms==167&&a.output.value_c!=b.output.value_c);
 triplex_consistency_t t;triplex_consistency_init(&t);runtime_observation_t o={0};diagnostic_readout_t c={0};
 o.source_valid=o.reference_valid=o.reference_enabled=true;
 for(unsigned ms=0;ms<60000;ms+=100){o.time_ms=o.source_ms=o.reference_ms=ms;o.source_c=o.reference_c=80;
 c=(diagnostic_readout_t){.value_c=80,.previous_c=80,.sample_ms=ms,.previous_ms=ms>=100?ms-100:0,.valid=true,.previous_valid=ms>=100};triplex_consistency_step(&t,&o,&c);assert(t.strength==0);}
 /* A+B matching drift versus C is detectable without assuming which side failed. */
 for(unsigned ms=60000;ms<100000;ms+=100){o.time_ms=o.source_ms=o.reference_ms=ms;o.source_c=o.reference_c=84;c.sample_ms=ms;c.previous_ms=ms-100;triplex_consistency_step(&t,&o,&c);}
 assert(t.strength>.5&&t.member_pattern==3&&!t.ambiguous);
 o.source_c=75;o.reference_c=85;triplex_consistency_step(&t,&o,&c);assert(t.ambiguous);
 /* All three equal common drift gives no differential evidence after settling. */
 triplex_consistency_init(&t);
 for(unsigned ms=100;ms<40000;ms+=100){float v=80+.00001f*ms;o.time_ms=o.source_ms=o.reference_ms=ms;o.source_c=o.reference_c=v;c.value_c=v;c.previous_c=v-.001f;c.sample_ms=ms;c.previous_ms=ms-100;triplex_consistency_step(&t,&o,&c);assert(t.strength==0);}
 return 0;
}'''
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);p=d/'test.c';p.write_text(code)
   core=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text()+'\ndouble clo_existing_pair_strength(clo_revised_t *s,const runtime_observation_t *o){return fmax(redundant_sensor(s,o),fast_redundant_sensor(s,o));}\n';q=d/'bridge.c';q.write_text(core)
   objects=['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o']
   subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude',str(p),str(q),'src/v7_3/diagnostic_temperature.c','src/v7_3/triplex_consistency.c',*objects,'-lm','-o',str(d/'test')],cwd=ROOT,check=True);subprocess.run([str(d/'test')],check=True)
