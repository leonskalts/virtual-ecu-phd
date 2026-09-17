#include "clo_dsf_candidate2.h"
#include "ecu_types.h" /* Test harness only; never a detector dependency. */
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define NEAR(a,b) assert(fabs((a)-(b))<1e-8)
static runtime_observation_t normal(unsigned int t) {
 return (runtime_observation_t){.time_ms=t,.coolant_measured_c=92,.control_target_c=92,
 .sample_timestamp_ms=t,.sample_freshness_ok=true,.sample_expected_period_ms=100,
 .timing={.period_ms=100,.relative_deadline_ms=100,.time_ms=t,.job_release_ms=(int)t,.actual_completion_ms=(int)t}};
}
int main(int argc,char **argv) {
 assert(argc==2);int test=atoi(argv[1]);c2_state_t s,z;c2_init(&s);c2_init(&z);
 c2_config_t c,d;c2_config_default(&c);d=c;runtime_observation_t o=normal(0);
 if(test==0) {double p[5];c2_origin_betp(&s.origin_mass,p);for(int i=0;i<5;i++)NEAR(p[i],.2);
 for(unsigned int a=1;a<32;a++)for(unsigned int b=1;b<32;b++) {assert((c2_encode_origin_subset(a)&c2_encode_origin_subset(b))==c2_encode_origin_subset(a&b));assert((c2_encode_origin_subset(a)|c2_encode_origin_subset(b))==c2_encode_origin_subset(a|b));}
 ds_empty(&s.origin_mass);s.origin_mass.mass[33]=1;c2_origin_betp(&s.origin_mass,p);NEAR(p[0],1);for(int i=1;i<5;i++)NEAR(p[i],0);}
 if(test==1) {o.coolant_measured_c=115;for(int t=0;t<1000;t+=100){o.time_ms=t;c2_step(&s,&c,C2_FULL,&o);}assert(s.output.alarm);assert(!s.output.localization_valid);NEAR(s.output.origin_ignorance,1);NEAR(s.detection_mass.mass[1],0);}
 if(test==2) {for(int t=0;t<1000;t+=100){o=normal(t);o.timing.deadline_exceeded=true;c2_step(&s,&c,C2_FULL,&o);}assert(s.output.alarm);assert(s.output.estimated_origin==CLO_TIMING);}
 if(test==3) {for(int t=0;t<1000;t+=100){o=normal(t);o.coolant_measured_c=160;c2_step(&s,&c,C2_FULL,&o);}assert(s.output.alarm);assert(!s.output.localization_valid);NEAR(s.output.origin_margin,0);}
 if(test==4) {d.common.r_direct=.01;d.common.r_indirect=0;d.common.propagation_bonus=0;d.common.localization_threshold=.99;d.common.ignorance_limit=0;
 for(int t=0;t<5000;t+=100){o=normal(t);o.timing.deadline_exceeded=t<2000;o.pump_command=t>=200&&t<1000;c2_step(&s,&c,C2_FULL,&o);c2_step(&z,&d,C2_FULL,&o);assert(!memcmp(&s.detection_mass,&z.detection_mass,sizeof(ds_mass_t)));assert(s.output.alarm==z.output.alarm);}}
 if(test>=5 && test<=7) {o.timing.deadline_exceeded=test!=6;o.pump_command=test==6;c2_step(&s,&c,C2_FULL,&o);o=normal(100);o.timing.deadline_exceeded=true;o.pump_command=test!=7;c2_step(&s,&c,C2_FULL,&o);assert(s.output.propagation_support==(test==5));if(test==5)NEAR(s.origin_reliability[0],.99);}
 if(test==8) {for(int t=0;t<1000000;t+=100){o=normal(t);c2_step(&s,&c,C2_FULL,&o);}assert(!s.output.alarm);NEAR(s.output.anomaly_belief,0);NEAR(s.output.origin_ignorance,1);}
 if(test==9) {for(int t=0;t<10000;t+=100){o=normal(t);o.control_target_c=t<500?104:92;c2_step(&s,&c,C2_FULL,&o);}assert(s.output.alarm_timestamp_ms>=0);assert(!s.output.alarm);assert(s.output.anomaly_belief<1e-8);}
 if(test==10) {c2_step(&s,&c,C2_FULL,&o);z=s;o.control_target_c=104;c2_step(&s,&c,C2_FULL,&o);assert(!memcmp(&s,&z,sizeof(s)));}
 if(test==11) {for(int t=0;t<3000;t+=100){o=normal(t);o.control_target_c=104;runtime_observation_t q=o;q.diagnostic_id=999;q.safety_state=9;q.detector_alarm=true;c2_step(&s,&c,C2_FULL,&o);c2_step(&z,&c,C2_FULL,&q);assert(!memcmp(&s,&z,sizeof(s)));}}
 if(test==12) {clo_dsf_t old;clo_dsf_init(&old);for(int t=0;t<5000;t+=100){o=normal(t);o.coolant_measured_c=90+t%700*.05;o.control_target_c=92+t%400*.02;o.sample_age_ms=t%1000;o.pump_command=(t%3)*.2;c2_step(&s,&c,C2_FULL,&o);clo_dsf_step(&old,&c.common,CLO_FULL,&o);for(int i=0;i<6;i++){NEAR(s.evidence.strength[i],old.evidence.strength[i]);assert(s.evidence.available[i]==old.evidence.available[i]);}assert(s.evidence.propagation_transitions==old.evidence.propagation_transitions);}}
 if(test==13) {c.r_detection=NAN;assert(!c2_config_valid(&c));c.r_detection=1;c.common.conflict_rule=DS_YAGER;assert(!c2_config_valid(&c));}
 if(test==14) {o.control_target_c=NAN;o.coolant_measured_c=NAN;o.pump_actual=NAN;o.timing.period_ms=0;o.sample_timestamp_ms=100;c2_step(&s,&c,C2_FULL,&o);NEAR(s.output.anomaly_belief,0);NEAR(s.output.origin_ignorance,1);}
 if(test==15) {o.control_target_c=94;c.common.confirmation_persistence=1;c.common.alarm_threshold_confirmed=.5;c2_step(&s,&c,0,&o);assert(s.output.alarm);NEAR(s.output.anomaly_belief,.5);NEAR(s.output.detection_conflict,0);}
 if(test==16) {c.common.confirmation_persistence=1;c.common.r_direct=.1;c.common.alarm_threshold_confirmed=.5;o.control_target_c=104;c2_step(&s,&c,C2_ORIGIN_RELIABILITY,&o);assert(s.output.alarm);assert(!s.output.localization_valid);NEAR(s.output.origin_ignorance,.9);}
 if(test==17) {ecu_state_t left={0},right={0};left.cross_layer_fault.layer=FAULT_LAYER_MEMORY;right.cross_layer_fault.layer=FAULT_LAYER_ACTUATOR;
 right.cross_layer_runtime.active=true;right.cross_layer_fault.bit_index=5;right.plant.coolant_temp_true_c=999;right.faults.enabled=true;right.propagation.plant_ms=1;
 for(int t=0;t<1000;t+=100){left.time.time_ms=right.time.time_ms=t;left.sensors.coolant_temp_meas_c=right.sensors.coolant_temp_meas_c=92;left.control.active_control_target_c=right.control.active_control_target_c=104;
 runtime_observation_t a,b;runtime_observation_capture(&left,&a);runtime_observation_capture(&right,&b);c2_step(&s,&c,C2_FULL,&a);c2_step(&z,&c,C2_FULL,&b);assert(!memcmp(&s,&z,sizeof(s)));}}
 if(test==18) {ds_mass_t a,b,result;double conflict,p[5];ds_vacuous(&a);a.mass[33]=.6;a.mass[63]=.4;ds_vacuous(&b);b.mass[2]=.5;b.mass[63]=.5;assert(ds_combine(&a,&b,DS_DEMPSTER,&result,&conflict));NEAR(conflict,.3);NEAR(result.mass[33],3./7);NEAR(result.mass[2],2./7);c2_origin_betp(&result,p);NEAR(p[0],3./7+2./35);NEAR(p[1],2./7+2./35);}
 if(test==19) {o.timing.deadline_exceeded=true;c2_step(&s,&c,C2_FULL,&o);assert(!s.output.alarm);o.time_ms=100;c2_step(&s,&c,C2_FULL,&o);assert(s.output.alarm);assert(s.output.alarm_timestamp_ms==100);}
 if(test==20 || test==21) {c.common.confirmation_persistence=d.common.confirmation_persistence=1;c.common.lambda_temporal=d.common.lambda_temporal=0;
 if(test==20)d.common.localization_threshold=.99;else d.common.localization_margin_threshold=.95;
 o.control_target_c=104;c2_step(&s,&c,C2_FULL,&o);c2_step(&z,&d,C2_FULL,&o);assert(s.output.alarm && z.output.alarm);assert(s.output.localization_valid && !z.output.localization_valid);}
 assert(ds_valid(&s.detection_mass));assert(ds_valid(&s.origin_mass));return 0;
}
