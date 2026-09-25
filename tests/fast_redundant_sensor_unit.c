#include "clo_dsf_revised.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
static clo_final_config_t config={1,.8,.35,.5,.55,.15,.5,1};
static void sample(clo_revised_t *s,runtime_observation_t *o,unsigned t,double d,int swap)
{
 o->time_ms=o->source_ms=o->reference_ms=t;
 o->source_valid=o->reference_valid=o->reference_enabled=true;
 o->source_c=(float)(70+t*.001+(swap?0:d));o->reference_c=(float)(70+t*.001+(swap?d:0));
 clo_revised_step(s,&config,o);
}
int main(int argc,char **argv)
{
 assert(argc==2);int mode=atoi(argv[1]);
 if(mode==0)for(int swap=0;swap<2;swap++)for(int sign=-1;sign<=1;sign+=2){
  clo_revised_t s;clo_revised_init(&s);runtime_observation_t o={0};
  for(unsigned t=0;t<2000;t+=100){sample(&s,&o,t,t>=1000?sign*.95:0,swap);if(t==1000)assert(!s.fast_strength);if(t==1100)assert(s.fast_strength==1 && s.fusion.output.estimated_origin==CLO_SENSOR_CONTROL);}
 }
 if(mode==1)for(int swap=0;swap<2;swap++){
  clo_revised_t s;clo_revised_init(&s);runtime_observation_t o={0};
  for(unsigned t=0;t<5000;t+=100){sample(&s,&o,t,t==1000?.9:0,swap);assert(!s.fast_strength);}
 }
 if(mode==2){clo_revised_t s;clo_revised_init(&s);runtime_observation_t o={0};int alarms=0;
  for(unsigned t=0;t<5000;t+=100){int phase=(t/100)%3;double d=t>=1000&&t<3000?(phase==0?.5:phase==1?-.25:0):0;sample(&s,&o,t,d,1);alarms+=s.fast_strength>0;if(t>=4100)assert(!s.fast_strength);}
  assert(alarms>0);
 }
 if(mode==3){clo_revised_t s;clo_revised_init(&s);runtime_observation_t o={0};
  for(unsigned t=0;t<120000;t+=100){double p=(t%8000)/8000.;double tri=p<.25?4*p:p<.75?2-4*p:4*p-4;double noise=.2*((t/100)%2?1:-1);sample(&s,&o,t,2.3*tri+noise,1);assert(!s.fast_strength);}
 }
 if(mode==4){clo_revised_t s;clo_revised_init(&s);runtime_observation_t o={0};
  sample(&s,&o,0,0,0);sample(&s,&o,100,.9,0);sample(&s,&o,300,.9,0);assert(!s.fast_strength&&s.fast_edges==0);
  o.time_ms=400;o.reference_valid=false;clo_revised_step(&s,&config,&o);assert(!s.fast_strength&&!s.fast_valid);
 }
 return 0;
}
