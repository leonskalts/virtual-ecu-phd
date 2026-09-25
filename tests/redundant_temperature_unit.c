#include "redundant_temperature.h"
#include "clo_dsf_revised.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
static clo_final_config_t config={1,.8,.35,.5,.55,.15,.5,1};
static void sample(clo_revised_t *s,runtime_observation_t *o,unsigned int t,float primary,float reference)
{
 o->time_ms=o->source_ms=o->reference_ms=t;
 o->source_c=primary;o->reference_c=reference;
 o->source_valid=o->reference_valid=o->reference_enabled=true;
 clo_revised_step(s,&config,o);
}
int main(int argc,char **argv)
{
 assert(argc==2);int mode=atoi(argv[1]);
 if(mode==0){redundant_temperature_t a,b,c;redundant_temperature_init(&a,17,.12,.08);redundant_temperature_init(&b,29,-.12,.08);redundant_temperature_init(&c,17,.12,.08);
  unsigned int different=0;
  for(unsigned int t=0;t<100000;t+=100){float physical=30+t*.001f;redundant_temperature_sample(&a,t,physical);redundant_temperature_sample(&b,t,physical);redundant_temperature_sample(&c,t,physical);assert(a.value_c==c.value_c);assert(fabs(a.value_c-physical-.12)<.086);different+=a.value_c!=b.value_c;}
  assert(different>900);float old=b.value_c;a.value_c+=50;assert(b.value_c==old);
 }
 if(mode==1 || mode==2){clo_revised_t s;clo_revised_init(&s);runtime_observation_t o={0};
  for(unsigned int t=0;t<=120000;t+=100){double p=(t%24200)/24200.;double triangle=p<.25?4*p:p<.75?2-4*p:4*p-4;
   float physical=40+.2f*(t/1000.f);float delta=mode==1?(float)(2.3*triangle+.097*((t/100)%2?1:-1)):(t>25000?1.8f*fminf(1,(t-25000)/41000.f):0);
   sample(&s,&o,t,physical+delta,physical-.1f+.08f*sinf(t));
   if(mode==1)assert(s.reference_strength==0);
  }
  if(mode==2)assert(s.fusion.output.alarm && s.fusion.output.estimated_origin==CLO_SENSOR_CONTROL);
 }
 if(mode==3){clo_revised_t a,b;clo_revised_init(&a);clo_revised_init(&b);runtime_observation_t x={0},y={0};
  for(unsigned int t=0;t<=50000;t+=100){sample(&a,&x,t,80,82);sample(&b,&y,t,82,80);assert(a.reference_strength==b.reference_strength);}
  assert(a.fusion.output.alarm&&b.fusion.output.alarm);
  x.reference_valid=false;x.time_ms+=100;clo_revised_step(&a,&config,&x);assert(a.reference_count==0&&a.reference_strength==0);
 }
 if(mode==4){clo_revised_t s;clo_revised_init(&s);runtime_observation_t o={0};
  for(unsigned int t=0;t<60000;t+=100)sample(&s,&o,t,80+t*.0001f,80+t*.0001f);
  assert(!s.fusion.output.alarm&&s.reference_strength==0);
  o.time_ms+=100;o.reference_ms=o.time_ms;o.reference_failed=true;o.reference_valid=false;clo_revised_step(&s,&config,&o);assert(s.reference_strength==1&&s.fusion.output.alarm);
 }
 return 0;
}
