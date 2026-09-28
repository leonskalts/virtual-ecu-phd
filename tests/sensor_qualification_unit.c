#include "clo_dsf_revised.h"
#include <assert.h>
static clo_final_config_t config={1,.8,.35,.5,.55,.15,.5,1};
int main(void)
{
 for(int mode=0;mode<3;mode++) {
  clo_revised_t s;clo_revised_init(&s);runtime_observation_t o={0};int alarms=0;
  for(unsigned t=0;t<=1400;t+=100) {
   o.source_previous_c=o.source_c;o.source_previous_ms=o.source_ms;
   o.source_previous_valid=t>0;o.source_valid=true;
   o.time_ms=o.source_ms=o.reference_ms=t;
   o.reference_enabled=o.reference_valid=true;
   o.source_c=88-t*.007f;o.reference_c=o.source_c;
   o.control_target_c=92;o.control_execution_ms=-1;
   o.target_shadow_valid=true;o.target_register_c=o.target_shadow_c=92;
   if(mode==1 && t>=200)o.source_c+=1;
   if(mode==2 && t>=200)o.target_register_c=93;
   clo_revised_step(&s,&config,&o);
   if(s.fusion.output.alarm) {
    alarms++;
    if(!mode)assert(!s.fusion.output.localization_valid);
    if(mode==1 && t==300)assert(s.fusion.output.estimated_origin==CLO_SENSOR_CONTROL);
    if(mode==2)assert(s.fusion.output.estimated_origin==CLO_MEMORY);
   }
  }
  assert(mode ? alarms>0 : alarms==0);
 }
 return 0;
}
