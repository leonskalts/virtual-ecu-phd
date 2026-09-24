#include "clo_dsf_revised.h"
#include "ecu_types.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static runtime_observation_t normal(unsigned int t) {
 return (runtime_observation_t){.time_ms=t,.coolant_measured_c=92,.control_target_c=92,
 .target_register_c=92,.target_shadow_c=92,.target_shadow_valid=true,.control_execution_ms=(int)t,
 .source_valid=true,.source_ms=t,.source_c=92,.ambient_c=22,
 .sample_timestamp_ms=t,.sample_freshness_ok=true,.sample_expected_period_ms=100,
 .pump_command=.25f,.pump_actual=.25f,.timing={.period_ms=100,.relative_deadline_ms=100,.job_release_ms=(int)t,.actual_completion_ms=(int)t}};
}
int main(int argc,char **argv) {
 assert(argc==2);int test=atoi(argv[1]);clo_final_config_t c={1,.8,.35,.5,.55,.15,.5,1};
 clo_revised_t a,b;clo_revised_init(&a);clo_revised_init(&b);runtime_observation_t o=normal(0);
 if(test==0){for(unsigned t=0;t<10000;t+=100){o=normal(t);o.pump_actual*=.98f;clo_revised_step(&a,&c,&o);clo_final_step(&b.fusion,&c,&o);}assert(a.fusion.output.alarm&&a.fusion.output.estimated_origin==CLO_ACTUATOR);assert(!b.fusion.output.alarm);}
 if(test==1){for(unsigned t=0;t<100000;t+=100){o=normal(t);o.pump_command=o.pump_actual=(t%700)/700.0f;o.fan_command=o.fan_actual=(t%1100)/1100.0f;clo_revised_step(&a,&c,&o);assert(!a.fusion.output.alarm);}}
 if(test==2){clo_evidence_t e={0};for(int sign=-1;sign<=1;sign+=2){o.pump_actual=nextafterf(o.pump_command,sign<0?-INFINITY:INFINITY);clo_revised_extract(&e,&o);assert(e.strength[4]==0);o.pump_actual=nextafterf(o.pump_actual,sign<0?-INFINITY:INFINITY);clo_revised_extract(&e,&o);assert(e.strength[4]==1);}}
 if(test==3){clo_evidence_t e={0};o.pump_actual=NAN;clo_revised_extract(&e,&o);assert(!e.available[4]&&e.strength[4]==0);o=normal(50);o.pump_actual=0;clo_revised_extract(&e,&o);assert(!e.available[4]&&e.strength[4]==0);}
 if(test==4){clo_evidence_t e={0};o.pump_command=2;o.pump_actual=1;o.fan_command=-1;o.fan_actual=0;clo_revised_extract(&e,&o);assert(e.available[4]&&e.strength[4]==0);o.fan_command=.1f;clo_revised_extract(&e,&o);assert(e.strength[4]==1);}
 if(test==5){ecu_state_t x={0},y={0};for(unsigned t=0;t<10000;t+=100){x.time.time_ms=y.time.time_ms=t;x.control.active_control_target_c=y.control.active_control_target_c=92;x.sensors.coolant_temp_meas_c=y.sensors.coolant_temp_meas_c=92;x.control.pump_command=y.control.pump_command=.2f;x.actuators.pump_actual=y.actuators.pump_actual=.19f;y.cross_layer_fault.layer=FAULT_LAYER_MEMORY;y.cross_layer_runtime.active=true;y.faults.enabled=true;y.faults.active_mode=FAULT_FAN_STUCK_OFF;y.plant.coolant_temp_true_c=999;y.propagation.plant_ms=1;runtime_observation_t p,q;runtime_observation_capture(&x,&p);runtime_observation_capture(&y,&q);q.diagnostic_id=123;q.detector_alarm=true;q.safety_state=5;clo_revised_step(&a,&c,&p);clo_revised_step(&b,&c,&q);assert(!memcmp(&a,&b,sizeof(a)));}}
 if(test==6){for(unsigned t=0;t<10000;t+=100){o=normal(t);o.control_target_c=t<500?104:92;clo_revised_step(&a,&c,&o);clo_final_step(&b.fusion,&c,&o);assert(!memcmp(&a.fusion,&b.fusion,sizeof(a.fusion)));}}
 if(test==7){for(unsigned t=0;t<10000;t+=100){o=normal(t);if(t<300)o.pump_actual=.24f;clo_revised_step(&a,&c,&o);clo_revised_step(&b,&c,&o);clo_final_diagnostic(&a.fusion.evidence,t,3000);assert(!memcmp(&a.fusion.output,&b.fusion.output,sizeof(a.fusion.output)));}assert(!a.fusion.output.alarm&&a.fusion.output.alarm_timestamp_ms==0);}
 if(test==8){o.target_register_c=93;clo_revised_step(&a,&c,&o);assert(a.fusion.output.alarm&&a.fusion.output.estimated_origin==CLO_MEMORY);}
 if(test==9){for(unsigned t=0;t<5000;t+=100){o=normal(t);o.target_register_c=o.target_shadow_c=104;o.control_target_c=104;clo_revised_step(&a,&c,&o);assert(!a.fusion.output.alarm);}}
 if(test==10){for(unsigned t=0;t<5000;t+=100){o=normal(t);clo_revised_step(&a,&c,&o);assert(!a.fusion.output.alarm);}/* A non-effective stuck bit is not evidence. */}
 if(test==11){o.target_register_c=o.target_shadow_c=93;o.control_execution_ms=-1;clo_revised_step(&a,&c,&o);assert(!a.fusion.output.alarm);o=normal(100);o.target_shadow_valid=false;o.control_target_c=104;clo_revised_step(&a,&c,&o);assert(!a.fusion.output.alarm);}
 if(test==12){o=normal(100);o.source_valid=o.source_previous_valid=true;o.source_ms=100;o.source_previous_ms=0;o.source_previous_c=92;o.source_c=o.coolant_measured_c=98;clo_revised_step(&a,&c,&o);assert(a.fusion.output.alarm&&a.fusion.output.estimated_origin==CLO_SENSOR_CONTROL);}
 if(test==13){clo_revised_step(&a,&c,&o);o=normal(100);o.coolant_measured_c=98;o.source_valid=o.source_previous_valid=true;o.source_ms=100;o.source_previous_ms=0;o.source_c=o.source_previous_c=92;clo_revised_step(&a,&c,&o);assert(a.fusion.output.alarm&&!a.fusion.output.localization_valid);}
 if(test==14){clo_revised_step(&a,&c,&o);o=normal(100);o.coolant_measured_c=98;o.sample_freshness_ok=false;clo_revised_step(&a,&c,&o);assert(a.fusion.output.alarm&&a.fusion.output.estimated_origin==CLO_COMMUNICATION);}
 if(test==15){clo_revised_step(&a,&c,&o);o=normal(100);o.coolant_measured_c=98;o.source_valid=true;o.source_ms=200;o.source_c=200;clo_revised_step(&a,&c,&o);assert(a.fusion.output.alarm&&!a.fusion.output.localization_valid);}
 if(test==16){o.pump_actual=.2f;clo_revised_step(&a,&c,&o);assert(a.fusion.output.estimated_origin==CLO_ACTUATOR);for(unsigned t=100;t<5000;t+=100){o=normal(t);o.source_valid=o.source_previous_valid=true;o.source_ms=t;o.source_previous_ms=t-100;o.source_c=92+.0065f*t;o.source_previous_c=o.source_c-.65f;clo_revised_step(&a,&c,&o);assert(a.fusion.output.estimated_origin!=CLO_SENSOR_CONTROL);}assert(a.fusion.output.alarm&&!a.fusion.output.localization_valid);}
 if(test==17){o.pump_actual=.2f;clo_revised_step(&a,&c,&o);for(unsigned t=100;t<5000;t+=100){o=normal(t);clo_revised_step(&a,&c,&o);}assert(!a.direct_origins);o=normal(5000);o.source_valid=o.source_previous_valid=true;o.source_ms=5000;o.source_previous_ms=4900;o.source_c=98;o.source_previous_c=92;clo_revised_step(&a,&c,&o);assert(a.fusion.output.estimated_origin==CLO_SENSOR_CONTROL);}
 if(test==18){o=normal(100);o.pump_actual=.2f;o.source_valid=o.source_previous_valid=true;o.source_ms=100;o.source_previous_ms=0;o.source_c=98;o.source_previous_c=92;clo_revised_step(&a,&c,&o);assert(a.fusion.output.alarm&&!a.fusion.output.localization_valid&&a.ambiguous_onset);}
 if(test==19){for(unsigned t=0;t<5000;t+=100){o=normal(t);o.pump_actual=t<300?.2f:.25f;o.source_valid=o.source_previous_valid=true;o.source_ms=t;o.source_previous_ms=t?t-100:0;o.source_c=92+.0065f*t;o.source_previous_c=o.source_c-.65f;b.sensor_established_first=true;clo_revised_step(&a,&c,&o);clo_revised_step(&b,&c,&o);assert(!memcmp(&a.fusion.detection_mass,&b.fusion.detection_mass,sizeof(ds_mass_t)));assert(a.fusion.output.alarm==b.fusion.output.alarm);}}
 if(test==20){for(int origin=0;origin<3;origin++){clo_revised_init(&a);o=normal(0);if(origin==0)o.target_register_c=93;if(origin==1)o.sample_freshness_ok=false;if(origin==2)o.timing.deadline_exceeded=true;clo_revised_step(&a,&c,&o);assert(a.direct_origins);o=normal(100);o.source_valid=o.source_previous_valid=true;o.source_ms=100;o.source_previous_ms=0;o.source_c=98;o.source_previous_c=92;clo_revised_step(&a,&c,&o);assert(a.fusion.output.estimated_origin!=CLO_SENSOR_CONTROL);}}
 if(test==21){o.fan_command=.5f;o.fan_actual=0;clo_revised_step(&a,&c,&o);for(unsigned t=100;t<5000;t+=100){o=normal(t);clo_revised_step(&a,&c,&o);}assert(a.direct_origins&&a.actuator_unresolved==2&&!a.fusion.output.alarm);o=normal(5000);o.source_valid=o.source_previous_valid=true;o.source_ms=5000;o.source_previous_ms=4900;o.source_c=98;o.source_previous_c=92;clo_revised_step(&a,&c,&o);assert(a.fusion.output.alarm&&!a.fusion.output.localization_valid);for(unsigned t=5100;t<10000;t+=100){o=normal(t);o.fan_command=o.fan_actual=.5f;clo_revised_step(&a,&c,&o);}assert(!a.direct_origins&&!a.actuator_unresolved);}
 if(test==22){o.pump_actual=.2f;o.target_register_c=93;clo_revised_step(&a,&c,&o);assert(a.ambiguous_onset&&!a.fusion.output.localization_valid);o=normal(100);o.pump_actual=.2f;clo_revised_step(&a,&c,&o);assert(!a.fusion.output.localization_valid);}
 if(test==23){o.fan_command=.5f;o.fan_actual=0;clo_revised_step(&a,&c,&o);for(unsigned t=100;t<5000;t+=100){o=normal(t);o.fan_command=o.fan_actual=.5f;o.source_c=0;clo_revised_step(&a,&c,&o);}assert(a.direct_origins&&!a.fusion.output.alarm);for(unsigned t=5000;t<10000;t+=100){o=normal(t);o.fan_command=o.fan_actual=.5f;clo_revised_step(&a,&c,&o);}assert(!a.direct_origins);}
 if(test==24){o=normal(100);o.sample_timestamp_ms=0;o.sample_age_ms=100;clo_revised_step(&a,&c,&o);assert(a.fusion.output.alarm&&a.fusion.output.estimated_origin==CLO_COMMUNICATION);}
 if(test==25){for(int mode=0;mode<4;mode++){clo_revised_init(&a);o=normal(100);o.sample_timestamp_ms=0;o.sample_age_ms=100;if(mode==0)o.source_valid=false;if(mode==1)o.source_ms=0;if(mode==2)o.control_execution_ms=0;if(mode==3)o.source_ms=200;clo_revised_step(&a,&c,&o);assert(!a.fusion.output.alarm);}}
 if(test==26){float previous=92;bool detected=false;for(unsigned t=0;t<3000;t+=100){o=normal(t);float error=(t/100)%3==0?.5f:(t/100)%3==1?-.25f:0;o.source_c=o.coolant_measured_c=92+error;o.source_previous_valid=t>0;o.source_previous_ms=t?t-100:0;o.source_previous_c=previous;previous=o.source_c;clo_revised_step(&a,&c,&o);detected|=a.fusion.output.alarm;if(a.fusion.output.localization_valid)assert(a.fusion.output.estimated_origin==CLO_SENSOR_CONTROL);}assert(detected);}
 if(test==27){for(unsigned t=0;t<3000;t+=100){o=normal(t);o.source_c=o.coolant_measured_c=92+.005f*t;o.source_previous_valid=t>0;o.source_previous_ms=t?t-100:0;o.source_previous_c=o.source_c-.5f;clo_revised_step(&a,&c,&o);assert(!a.fusion.output.alarm);}}
 if(test==28){o=normal(100);o.source_previous_valid=true;o.source_previous_ms=0;o.source_previous_c=92;o.source_c=o.coolant_measured_c=92.5f;clo_revised_step(&a,&c,&o);o=normal(300);o.source_previous_valid=true;o.source_previous_ms=200;o.source_previous_c=92.5f;o.source_c=o.coolant_measured_c=92;clo_revised_step(&a,&c,&o);assert(a.fusion.evidence.strength[3]<=.125);}
 if(test==29){for(unsigned t=0;t<10000;t+=100){o=normal(t);o.source_c=o.coolant_measured_c=70+.002f*t;o.source_previous_valid=t>0;o.source_previous_ms=t?t-100:0;o.source_previous_c=o.source_c-.2f;clo_revised_step(&a,&c,&o);assert(!a.fusion.output.alarm);}}
 if(test>=30 && test<=34) {
  bool detected=false;float previous=92;
  for(unsigned t=0;t<5000;t+=100) {
   o=normal(t);float y=92+.0005f*t;
   if(test==30 && t>=1000)y+=1.1f;
   if(test==31)y+=((t*1103515245U+12345U)%201-100.0f)*.001f;
   if(test==32 && t>=1000)y-=1.1f;
   if(test==33 && t>=1000){y+=1.1f;o.source_valid=false;}
   if(test==34 && t>=1000){y+=1.1f;o.control_target_c=99;o.target_register_c=o.target_shadow_c=99;}
   o.source_c=o.coolant_measured_c=y;o.source_previous_valid=t>0;
   o.source_previous_ms=t?t-100:0;o.source_previous_c=previous;previous=y;
   clo_revised_step(&a,&c,&o);detected|=a.fusion.output.alarm;
   if(test==31 || test==33 || test==34)assert(a.response_strength==0);
   if(a.fusion.output.localization_valid)assert(a.fusion.output.estimated_origin==CLO_SENSOR_CONTROL);
  }
  if(test==30 || test==32)assert(detected);
  else assert(!detected);
 }
 return 0;
}
