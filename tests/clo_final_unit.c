#include "clo_dsf_final.h"
#include "clo_final_observation_io.h"
#include "ecu_types.h" /* Hidden labels are used only by this harness. */
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static runtime_observation_t normal(unsigned int t) {
 return (runtime_observation_t){.time_ms=t,.coolant_measured_c=92,.control_target_c=92,.sample_timestamp_ms=t,.sample_freshness_ok=true,.sample_expected_period_ms=100,.timing={.period_ms=100,.relative_deadline_ms=100,.time_ms=t,.job_release_ms=(int)t,.actual_completion_ms=(int)t}};
}
static clo_final_config_t config(void) {return (clo_final_config_t){1,.8,.35,.5,.55,.15,.5,1};}
static void same_decision(const clo_final_t *s,const clo_final_t *z) {assert(!memcmp(&s->detection_mass,&z->detection_mass,sizeof(ds_mass_t)));assert(!memcmp(&s->origin_mass,&z->origin_mass,sizeof(ds_mass_t)));assert(!memcmp(&s->output,&z->output,sizeof(c2_output_t)));}
int main(int argc,char **argv) {
 assert(argc==2);int test=atoi(argv[1]);clo_final_config_t c=config();clo_final_t s,z;clo_final_init(&s);clo_final_init(&z);runtime_observation_t o=normal(0);
 if(test>=0&&test<=3) {unsigned int origin[]={CLO_TIMING,CLO_COMMUNICATION,CLO_MEMORY,CLO_ACTUATOR};if(test==0)o.timing.deadline_exceeded=true;if(test==1)o.sample_freshness_ok=false;if(test==2)o.control_target_c=104;if(test==3)o.pump_command=1;clo_final_step(&s,&c,&o);assert(s.output.alarm);assert(s.output.estimated_origin==origin[test]);assert(s.output.origin_score==1);}
 if(test==4){o.coolant_measured_c=160;clo_final_step(&s,&c,&o);assert(s.output.alarm);assert(!s.output.localization_valid);assert(s.output.origin_margin==0);}
 if(test==5){o.coolant_measured_c=115;clo_final_step(&s,&c,&o);assert(s.output.alarm);assert(s.output.origin_ignorance==1);assert(s.output.estimated_origin==0);}
 if(test==6){for(int t=0;t<10000;t+=100){o=normal(t);o.timing.deadline_exceeded=t<1000;o.pump_command=t>=100&&t<1000;clo_final_step(&s,&c,&o);clo_final_step(&z,&c,&o);clo_final_diagnostic(&s.evidence,t,3000);same_decision(&s,&z);if(t==100)assert(s.evidence.propagation_transitions!=0);}}
 if(test==7){for(int t=0;t<1000000;t+=100){o=normal(t);clo_final_step(&s,&c,&o);}assert(!s.output.alarm);assert(s.output.anomaly_ignorance==1);}
 if(test==8){for(int t=0;t<12000;t+=100){o=normal(t);o.control_target_c=t<500?104:92;clo_final_step(&s,&c,&o);}assert(s.output.alarm_timestamp_ms==0);assert(!s.output.alarm);assert(s.output.anomaly_belief<1e-8);}
 if(test==9){c.confirmation_persistence=2;o.timing.deadline_exceeded=true;clo_final_step(&s,&c,&o);assert(!s.output.alarm);o.time_ms=100;clo_final_step(&s,&c,&o);assert(s.output.alarm_timestamp_ms==100);}
 if(test==10){c.lambda_temporal=0;o.control_target_c=94;clo_final_step(&s,&c,&o);assert(s.output.anomaly_belief==.5);assert(s.output.alarm);c.confirmed_threshold=.500001;clo_final_step(&z,&c,&o);assert(!z.output.alarm);}
 if(test==11){c.localization_margin_threshold=.9;c.lambda_temporal=0;o.control_target_c=94;clo_final_step(&s,&c,&o);assert(s.output.alarm);assert(!s.output.localization_valid);}
 if(test==12){clo_final_step(&s,&c,&o);z=s;o.control_target_c=104;clo_final_step(&s,&c,&o);assert(!memcmp(&s,&z,sizeof(s)));}
 if(test==13){ecu_state_t a={0},b={0};a.cross_layer_fault.layer=FAULT_LAYER_MEMORY;b.cross_layer_fault.layer=FAULT_LAYER_ACTUATOR;b.cross_layer_runtime.active=true;b.plant.coolant_temp_true_c=999;b.faults.enabled=true;b.propagation.plant_ms=1;
 for(int t=0;t<1000;t+=100){a.time.time_ms=b.time.time_ms=t;a.sensors.coolant_temp_meas_c=b.sensors.coolant_temp_meas_c=92;a.control.active_control_target_c=b.control.active_control_target_c=104;runtime_observation_t x,y;runtime_observation_capture(&a,&x);runtime_observation_capture(&b,&y);y.diagnostic_id=999;y.safety_state=5;y.detector_alarm=true;clo_final_step(&s,&c,&x);clo_final_step(&z,&c,&y);same_decision(&s,&z);}}
 if(test==14){c2_state_t old;c2_init(&old);c2_config_t cfg;c2_config_default(&cfg);cfg.common.alarm_threshold_confirmed=.5;cfg.common.confirmation_persistence=1;cfg.common.propagation_bonus=0;
 for(int t=0;t<300000;t+=100){o=normal(t);o.coolant_measured_c=90+(t%700)*.07f;o.control_target_c=92+(t%900)*.005f;o.sample_age_ms=t%1100;o.pump_command=(t%3)*.2f;o.timing.deadline_exceeded=t%1700==0;clo_final_step(&s,&c,&o);c2_step(&old,&cfg,C2_FULL^C2_ORIGIN_RELIABILITY,&o);assert(!memcmp(&s.detection_mass,&old.detection_mass,sizeof(ds_mass_t)));assert(!memcmp(&s.origin_mass,&old.origin_mass,sizeof(ds_mass_t)));assert(!memcmp(&s.output,&old.output,sizeof(c2_output_t)));}}
 if(test==15){FILE *f=tmpfile();assert(f);o.coolant_measured_c=nextafterf(92,100);final_observation_header(f);final_observation_write(f,&o);rewind(f);char line[4096];assert(fgets(line,sizeof(line),f));runtime_observation_t copy;assert(final_observation_read(f,&copy)==1);assert(copy.coolant_measured_c==o.coolant_measured_c);clo_final_step(&s,&c,&o);clo_final_step(&z,&c,&copy);same_decision(&s,&z);fclose(f);}
 if(test==16){c.r_detection=NAN;assert(!clo_final_config_valid(&c));c=config();c.confirmation_persistence=0;assert(!clo_final_config_valid(&c));}
 assert(ds_valid(&s.detection_mass)&&ds_valid(&s.origin_mass));return 0;
}
