#include "clo_dsf_revised.h"
#include "ecu_types.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static runtime_observation_t normal(unsigned int t) {
 return (runtime_observation_t){.time_ms=t,.coolant_measured_c=92,.control_target_c=92,
 .sample_timestamp_ms=t,.sample_freshness_ok=true,.sample_expected_period_ms=100,
 .pump_command=.25f,.pump_actual=.25f,.timing={.period_ms=100,.relative_deadline_ms=100,.job_release_ms=(int)t,.actual_completion_ms=(int)t}};
}
int main(int argc,char **argv) {
 assert(argc==2);int test=atoi(argv[1]);clo_final_config_t c={1,.8,.35,.5,.55,.15,.5,1};
 clo_final_t a,b;clo_final_init(&a);clo_final_init(&b);runtime_observation_t o=normal(0);
 if(test==0){for(unsigned t=0;t<10000;t+=100){o=normal(t);o.pump_actual*=.98f;clo_revised_step(&a,&c,&o);clo_final_step(&b,&c,&o);}assert(a.output.alarm&&a.output.estimated_origin==CLO_ACTUATOR);assert(!b.output.alarm);}
 if(test==1){for(unsigned t=0;t<100000;t+=100){o=normal(t);o.pump_command=o.pump_actual=(t%700)/700.0f;o.fan_command=o.fan_actual=(t%1100)/1100.0f;clo_revised_step(&a,&c,&o);assert(!a.output.alarm);}}
 if(test==2){clo_evidence_t e={0};for(int sign=-1;sign<=1;sign+=2){o.pump_actual=nextafterf(o.pump_command,sign<0?-INFINITY:INFINITY);clo_revised_extract(&e,&o);assert(e.strength[4]==0);o.pump_actual=nextafterf(o.pump_actual,sign<0?-INFINITY:INFINITY);clo_revised_extract(&e,&o);assert(e.strength[4]==1);}}
 if(test==3){clo_evidence_t e={0};o.pump_actual=NAN;clo_revised_extract(&e,&o);assert(!e.available[4]&&e.strength[4]==0);o=normal(50);o.pump_actual=0;clo_revised_extract(&e,&o);assert(!e.available[4]&&e.strength[4]==0);}
 if(test==4){clo_evidence_t e={0};o.pump_command=2;o.pump_actual=1;o.fan_command=-1;o.fan_actual=0;clo_revised_extract(&e,&o);assert(e.available[4]&&e.strength[4]==0);o.fan_command=.1f;clo_revised_extract(&e,&o);assert(e.strength[4]==1);}
 if(test==5){ecu_state_t x={0},y={0};for(unsigned t=0;t<10000;t+=100){x.time.time_ms=y.time.time_ms=t;x.control.active_control_target_c=y.control.active_control_target_c=92;x.sensors.coolant_temp_meas_c=y.sensors.coolant_temp_meas_c=92;x.control.pump_command=y.control.pump_command=.2f;x.actuators.pump_actual=y.actuators.pump_actual=.19f;y.cross_layer_fault.layer=FAULT_LAYER_MEMORY;y.cross_layer_runtime.active=true;y.faults.enabled=true;y.faults.active_mode=FAULT_FAN_STUCK_OFF;y.plant.coolant_temp_true_c=999;y.propagation.plant_ms=1;runtime_observation_t p,q;runtime_observation_capture(&x,&p);runtime_observation_capture(&y,&q);q.diagnostic_id=123;q.detector_alarm=true;q.safety_state=5;clo_revised_step(&a,&c,&p);clo_revised_step(&b,&c,&q);assert(!memcmp(&a,&b,sizeof(a)));}}
 if(test==6){for(unsigned t=0;t<10000;t+=100){o=normal(t);o.control_target_c=t<500?104:92;clo_revised_step(&a,&c,&o);clo_final_step(&b,&c,&o);assert(!memcmp(&a,&b,sizeof(a)));}}
 if(test==7){for(unsigned t=0;t<10000;t+=100){o=normal(t);if(t<300)o.pump_actual=.24f;clo_revised_step(&a,&c,&o);clo_revised_step(&b,&c,&o);clo_final_diagnostic(&a.evidence,t,3000);assert(!memcmp(&a.output,&b.output,sizeof(a.output)));}assert(!a.output.alarm&&a.output.alarm_timestamp_ms==0);}
 return 0;
}
