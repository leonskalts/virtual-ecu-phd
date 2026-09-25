/* Adapter/evaluator: scoring metadata is never passed to a runtime detector. */
#include "clo_dsf_revised.h"
#include "clo_final_observation_io.h"
#include "ecu_types.h"
#include "control.h"
#include "memory_diagnostic_backend.h"
#include "memory_diagnostic.h"
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
int clo_accepted_main(int argc,char **argv);
void __real_detection_algorithm_step(struct ecu_state *state);
#define METHODS 8
/* Optional pre-change CURRENT core, compiled only in temporary storage. */
void clo_prechange_step(clo_revised_t *, const clo_final_config_t *, const runtime_observation_t *) __attribute__((weak));
static clo_revised_t prechange;
static const char *names[METHODS]={"Revised CLO-DSF","Candidate 2","v7.2 CLO-DSF","Plain DS","Simple OR","Weighted Sum","Hybrid","Timing Monitor"};
static clo_revised_t detector;
static clo_final_t previous;
static clo_final_config_t config;
static c2_state_t candidate2;
static c2_config_t c2_config;
static clo_dsf_t plain;
static clo_config_t plain_config;
static detection_algorithm_state_t hybrid;
static FILE *trace,*observations;
static bool enabled,comparison,primary;
static unsigned int evaluation_start;
static struct { unsigned int time_ms; uint16_t target; } target_updates[16];
static unsigned int target_update_count;
void __real_cross_layer_fault_step(ecu_state_t *state);
void __wrap_cross_layer_fault_step(ecu_state_t *state)
{
 /* Authorized workload input, identically applied to live and reference ECUs.
  * No activation, model or fault state is consulted. */
 for (unsigned int i=0;i<target_update_count;i++)
  if (state->time.time_ms==target_updates[i].time_ms)
   control_commit_target(state,target_updates[i].target);
 __real_cross_layer_fault_step(state);
 /* Synchronous scheduler: no control/sensor task runs inside this transaction.
  * Snapshot is restored before returning; the legal shadow is never modified. */
 if(enabled && state->log_file)
  memory_diagnostic_step(&state->control.memory_diagnostic,state->time.time_ms,
                         cross_layer_memory_read,cross_layer_memory_write,state);
}
/* Optional benign measurement workload. Defaults to exactly zero; not evidence.
 * Identical timestamp-keyed perturbations reach live and reference observations.
 * Intended for fault-free noise experiments, not transport fault composition. */
static double sensor_jitter, sensor_drift;
static unsigned int sensor_variation_period=6000;
/* Experiment-only ramp injection. Never passed to runtime inference; reference
 * ECU receives no ramp, so existing propagation scoring remains independent. */
static unsigned int sensor_ramp_start, sensor_ramp_rise;
static double sensor_ramp_offset;
void __real_sensors_step(ecu_state_t *state);
static float sensor_variation(unsigned int ms)
{
 double p=(double)(ms%sensor_variation_period)/sensor_variation_period;
 double triangle=p<.25 ? 4*p : p<.75 ? 2-4*p : 4*p-4;
 return (float)(sensor_drift*triangle+sensor_jitter*((ms/100)%2 ? 1 : -1));
}
void __wrap_sensors_step(ecu_state_t *state)
{
 __real_sensors_step(state);
 if(sensor_ramp_rise && state->log_file && state->time.time_ms>=sensor_ramp_start) {
  double elapsed=state->time.time_ms-sensor_ramp_start;
  float offset=(float)(sensor_ramp_offset*fmin(1.0,elapsed/sensor_ramp_rise));
  state->sensors.coolant_source_c+=offset;
  state->sensors.coolant_temp_meas_c+=offset;
 }
 if(sensor_jitter==0 && sensor_drift==0)return;
 state->sensors.coolant_source_c+=sensor_variation(state->sensors.coolant_source_ms);
 state->sensors.coolant_temp_meas_c+=sensor_variation(state->sensors.coolant_sensor_last_update_ms);
}
static const char *metrics_path;
static int weighted_choice;
static const double ws_thresholds[6]={.04,.06,.08,.10,.14,.18};
static const double ws_weights[2][6]={{1./6,1./6,1./6,1./6,1./6,1./6},{.2,.2,.2,.1,.2,.1}};
typedef struct {
    int first_alarm,first_post_alarm,first_localization;
    unsigned int origin_at_alarm,leading_at_alarm,first_origin;
    double score_at_alarm,margin_at_alarm,ignorance_at_alarm;
    unsigned int samples,alarm_samples,pre_alarm_samples,propagation_samples,high_detection,high_localization;
    double anomaly_ignorance_sum,origin_ignorance_sum,detection_conflict_sum,localization_conflict_sum;
    bool previous_alarm;
    unsigned int origin_alarm_samples[6];
} score_t;
static score_t scores[METHODS];

static void score_step(int index,unsigned int now,bool alarm,unsigned int origin,unsigned int leading,
    double confidence,double margin,double origin_ignorance,double anomaly_ignorance,
    double detection_conflict,double localization_conflict,bool prop)
{
    score_t *s=&scores[index];s->samples++;s->alarm_samples+=alarm;
    if(alarm){unsigned int k=0;for(unsigned int j=0;j<5;j++)if(origin==(1U<<(j+1)))k=j+1;s->origin_alarm_samples[k]++;}
    s->pre_alarm_samples+=alarm && now<evaluation_start;
    if(alarm&&!s->previous_alarm) {
        if(s->first_alarm<0)s->first_alarm=(int)now;
        if(now>=evaluation_start && s->first_post_alarm<0) {
            s->first_post_alarm=(int)now;s->origin_at_alarm=origin;s->leading_at_alarm=leading;
            s->score_at_alarm=confidence;s->margin_at_alarm=margin;s->ignorance_at_alarm=origin_ignorance;
        }
    }
    if(alarm && origin && now>=evaluation_start && s->first_post_alarm>=0 && s->first_localization<0) {
        s->first_localization=(int)now;s->first_origin=origin;
    }
    s->previous_alarm=alarm;s->anomaly_ignorance_sum+=anomaly_ignorance;s->origin_ignorance_sum+=origin_ignorance;
    s->detection_conflict_sum+=detection_conflict;s->localization_conflict_sum+=localization_conflict;
    s->high_detection+=detection_conflict>=.5;s->high_localization+=localization_conflict>=.5;s->propagation_samples+=prop;
}
static void log_header(FILE *f)
{
    fprintf(f,"time_ms,detector_state,anomaly_belief,anomaly_plausibility,anomaly_decision_score,anomaly_ignorance,detection_conflict,estimated_origin,origin_score,origin_belief,origin_plausibility,origin_margin,origin_ignorance,localization_conflict,propagation_support,observed_evidence_path,alarm,localization_valid,alarm_timestamp_ms,localization_timestamp_ms,detection_fallback,localization_fallback");
    for(int i=0;i<6;i++)fprintf(f,",%s_evidence,%s_detection_reliability,%s_origin_reliability",clo_channel_names[i],clo_channel_names[i],clo_channel_names[i]);
    for(int i=0;i<7;i++)fprintf(f,",detection_K_%d,localization_K_%d",i,i);
    for(unsigned int i=1;i<32;i++)fprintf(f,",origin_mass_%u",i);
    fprintf(f,",detection_mass_normal,detection_mass_abnormal,detection_mass_ignorance,target_register_c,target_shadow_c,target_shadow_valid,control_target_c,control_execution_ms,source_c,source_previous_c,source_ms,source_previous_ms,source_valid,source_previous_valid,direct_origin_onset_ms,direct_origin_sources,sensor_established_first,ambiguous_onset,actuator_unresolved,delivered_sample_ms,delivered_sample_age_ms,response_residual_c,response_strength,memory_check_ms,memory_check_valid,memory_check_failed\n");
}
static void log_row(FILE *f,unsigned int now,const clo_revised_t *provenance,const runtime_observation_t *o)
{
    const clo_final_t *s=&provenance->fusion;
    const c2_output_t *v=&s->output;
    fprintf(f,"%u,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d,%u,%d,%d,%d,%d,%d,%d",now,
        clo_state_name(v->state),v->anomaly_belief,v->anomaly_plausibility,v->anomaly_decision_score,v->anomaly_ignorance,v->detection_conflict,
        clo_origin_name(v->estimated_origin),v->origin_score,v->origin_belief,v->origin_plausibility,v->origin_margin,v->origin_ignorance,v->localization_conflict,
        v->propagation_support,s->evidence.propagation_transitions,v->alarm,v->localization_valid,v->alarm_timestamp_ms,v->localization_timestamp_ms,v->detection_fallback,v->localization_fallback);
    for(int i=0;i<6;i++)fprintf(f,",%.17g,%.17g,%.17g",s->evidence.strength[i],s->evidence.available[i]?config.r_detection:0,s->evidence.available[i]?1.:0.);
    for(int i=0;i<7;i++)fprintf(f,",%.17g,%.17g",v->detection_conflict_steps[i],v->localization_conflict_steps[i]);
    for(unsigned int i=1;i<32;i++)fprintf(f,",%.17g",s->origin_mass.mass[c2_encode_origin_subset(i)]);
    fprintf(f,",%.17g,%.17g,%.17g,%u,%u,%d,%.9g,%d,%.9g,%.9g,%u,%u,%d,%d,%u,%u,%d,%d,%u,%u,%u,%.17g,%.17g,%u,%d,%d\n",s->detection_mass.mass[C2_D_NORMAL],s->detection_mass.mass[C2_D_ABNORMAL],s->detection_mass.mass[DS_THETA],o->target_register_c,o->target_shadow_c,o->target_shadow_valid,o->control_target_c,o->control_execution_ms,o->source_c,o->source_previous_c,o->source_ms,o->source_previous_ms,o->source_valid,o->source_previous_valid,provenance->direct_onset_ms,provenance->direct_origins,provenance->sensor_established_first,provenance->ambiguous_onset,provenance->actuator_unresolved,o->sample_timestamp_ms,o->sample_age_ms,provenance->response_residual,provenance->response_strength,o->memory_check_ms,o->memory_check_valid,o->memory_check_failed);
}
static void old_score(int index,unsigned int now,const clo_dsf_t *s)
{
    const clo_output_t *v=&s->output;double p[6];ds_pignistic(&s->fused,p);
    unsigned int leading=2;double best=p[1];
    for(unsigned int i=2;i<6;i++)if(p[i]>best){best=p[i];leading=1U<<i;}
    score_step(index,now,v->alarm,v->estimated_origin,leading,v->origin_score,v->origin_margin,
        v->ignorance_mass,v->ignorance_mass,v->conflict_mass,v->conflict_mass,v->propagation_support);
}
static void simple_score(int index,unsigned int now,bool alarm)
{
    score_step(index,now,alarm,0,0,0,0,1,1,0,0,false);
}

static void final_score(int index,unsigned int now,const c2_output_t *v)
{
 score_step(index,now,v->alarm,v->estimated_origin,v->leading_origin,v->origin_score,v->origin_margin,v->origin_ignorance,v->anomaly_ignorance,v->detection_conflict,v->localization_conflict,false);
}
void __wrap_detection_algorithm_step(struct ecu_state *state)
{
 if(!enabled || !state->log_file){__real_detection_algorithm_step(state);return;}
 runtime_observation_t o;runtime_observation_capture(state,&o);
 if(observations)final_observation_write(observations,&o);
 clo_revised_step(&detector,&config,&o);
 clo_final_diagnostic(&detector.fusion.evidence,o.time_ms,3000);
 final_score(0,o.time_ms,&detector.fusion.output);
 if(trace)log_row(trace,o.time_ms,&detector,&o);
 if(comparison) {
  if(clo_prechange_step){clo_prechange_step(&prechange,&config,&o);final_score(1,o.time_ms,&prechange.fusion.output);}
  else {c2_step(&candidate2,&c2_config,C2_FULL,&o);final_score(1,o.time_ms,&candidate2.output);}
  clo_final_step(&previous,&config,&o);final_score(2,o.time_ms,&previous.output);
  clo_dsf_step(&plain,&plain_config,CLO_PLAIN,&o);old_score(3,o.time_ms,&plain);
  /* Baselines keep the ORIGINAL extractor, never revised evidence. */
  double peak=0,ws=0;for(int i=0;i<6;i++){double e=previous.evidence.strength[i];if(e>peak)peak=e;ws+=ws_weights[weighted_choice/6][i]*e;}
  simple_score(4,o.time_ms,peak>=.5);simple_score(5,o.time_ms,ws>=ws_thresholds[weighted_choice%6]);
  ecu_state_t shadow=*state;shadow.detection=hybrid;__real_detection_algorithm_step(&shadow);hybrid=shadow.detection;
  simple_score(6,o.time_ms,hybrid.alarm_active);simple_score(7,o.time_ms,state->timing_monitor.alarm);
 }
 if(primary){state->detection.current_score=(float)detector.fusion.output.anomaly_decision_score;state->detection.alarm_active=detector.fusion.output.alarm;state->detection.detected=detector.fusion.output.alarm_timestamp_ms>=0;state->detection.first_detection_time_ms=detector.fusion.output.alarm_timestamp_ms;snprintf(state->detection.runtime_label,sizeof(state->detection.runtime_label),"clo_dsf_revised");}
 else __real_detection_algorithm_step(state);
}
static int number(const char *value,unsigned int *out)
{
    errno=0;char *end;unsigned long n=strtoul(value,&end,10);
    if(*value<'0'||*value>'9'||*end||errno||n>UINT_MAX)return -1;
    *out=(unsigned int)n;return 0;
}
static int historical_config_read(const char *path,c2_config_t *c)
{
    FILE *f=fopen(path,"r");if(!f)return -1;
    const char *keys[]={"r_detection","r_origin_direct","r_origin_indirect","lambda_temporal","propagation_bonus","suspect_threshold","confirmed_threshold","localization_threshold","localization_margin_threshold","ignorance_limit"};
    double *values[]={&c->r_detection,&c->common.r_direct,&c->common.r_indirect,&c->common.lambda_temporal,&c->common.propagation_bonus,&c->common.alarm_threshold_suspect,&c->common.alarm_threshold_confirmed,&c->common.localization_threshold,&c->common.localization_margin_threshold,&c->common.ignorance_limit};
    unsigned int seen=0;char line[256],key[100],value[100],extra;
    while(fgets(line,sizeof(line),f)) {
        if(line[0]=='#'||line[0]=='\n')continue;
        if(sscanf(line,"%99[^=]=%99s %c",key,value,&extra)!=2){fclose(f);return -1;}
        int index=-1;
        for(int i=0;i<10;i++)if(!strcmp(key,keys[i])) {
            index=i;errno=0;char *end;*values[i]=strtod(value,&end);
            if(errno||*end){fclose(f);return -1;}
        }
        if(!strcmp(key,"propagation_window_ms")){index=10;if(number(value,&c->common.propagation_window_ms)){fclose(f);return -1;}}
        if(!strcmp(key,"confirmation_persistence")){index=11;if(number(value,&c->common.confirmation_persistence)){fclose(f);return -1;}}
        if(index<0 || (seen&(1U<<index))){fclose(f);return -1;}
        seen|=1U<<index;
    }
    bool ok=!ferror(f);fclose(f);return ok&&seen==4095&&c2_config_valid(c)?0:-1;
}

static int final_config_read(const char *path,clo_final_config_t *c)
{
 FILE *f=fopen(path,"r");if(!f)return -1;
 const char *keys[]={"r_detection","lambda_temporal","suspect_threshold","confirmed_threshold","localization_threshold","localization_margin_threshold","ignorance_limit"};
 double *values[]={&c->r_detection,&c->lambda_temporal,&c->suspect_threshold,&c->confirmed_threshold,&c->localization_threshold,&c->localization_margin_threshold,&c->ignorance_limit};
 char line[256],key[100],value[100],extra;unsigned int seen=0;
 while(fgets(line,sizeof(line),f)) {
  if(line[0]=='#'||line[0]=='\n')continue;
  if(sscanf(line,"%99[^=]=%99s %c",key,value,&extra)!=2){fclose(f);return -1;}
  int index=-1;
  for(int i=0;i<7;i++)if(!strcmp(key,keys[i])) {index=i;errno=0;char *end;*values[i]=strtod(value,&end);if(errno||*end){fclose(f);return -1;}}
  if(!strcmp(key,"confirmation_persistence")){index=7;if(number(value,&c->confirmation_persistence)){fclose(f);return -1;}}
  if(index<0||(seen&(1U<<index))){fclose(f);return -1;}seen|=1U<<index;
 }
 bool ok=!ferror(f);fclose(f);return ok&&seen==255&&clo_final_config_valid(c)?0:-1;
}
static int metrics_write(void)
{
    if(!metrics_path)return 0;
    FILE *f=fopen(metrics_path,"w");if(!f)return -1;
    fprintf(f,"method,first_alarm_ms,first_post_alarm_ms,origin_at_alarm,leading_at_alarm,origin_score_at_alarm,origin_margin_at_alarm,origin_ignorance_at_alarm,first_localization_ms,first_origin,samples,alarm_samples,pre_alarm_samples,mean_anomaly_ignorance,mean_origin_ignorance,mean_detection_conflict,mean_localization_conflict,high_detection_conflict_samples,high_localization_conflict_samples,propagation_samples,alarm_UNKNOWN,alarm_MEMORY,alarm_TIMING,alarm_COMMUNICATION,alarm_SENSOR_CONTROL,alarm_ACTUATOR\n");
    for(int i=0;i<METHODS;i++)if(comparison||i==0) {
        score_t *s=&scores[i];double n=s->samples?s->samples:1;
        fprintf(f,"%s,%d,%d,%s,%s,%.12g,%.12g,%.12g,%d,%s,%u,%u,%u,%.12g,%.12g,%.12g,%.12g,%u,%u,%u",names[i],s->first_alarm,s->first_post_alarm,
            clo_origin_name(s->origin_at_alarm),clo_origin_name(s->leading_at_alarm),s->score_at_alarm,s->margin_at_alarm,s->ignorance_at_alarm,
            s->first_localization,clo_origin_name(s->first_origin),s->samples,s->alarm_samples,s->pre_alarm_samples,
            s->anomaly_ignorance_sum/n,s->origin_ignorance_sum/n,s->detection_conflict_sum/n,s->localization_conflict_sum/n,
            s->high_detection,s->high_localization,s->propagation_samples);
        for(int j=0;j<6;j++)fprintf(f,",%u",s->origin_alarm_samples[j]);
        fputc('\n',f);
    }
    bool bad=ferror(f);return fclose(f)||bad?-1:0;
}

int main(int argc,char **argv)
{
 int write=1;const char *trace_path=NULL,*config_path=NULL,*c2_path=NULL,*observation_path=NULL;bool ws_set=false;
 for(int i=1;i<argc;i++) {
  if(!strcmp(argv[i],"--revised-comparison")){comparison=true;enabled=true;continue;}
  if(!strncmp(argv[i],"--revised-",10)) {
   const char *key=argv[i];if(++i>=argc){fprintf(stderr,"Missing %s value\n",key);return 1;}
   if(!strcmp(key,"--revised-target-update")) {
    unsigned int t,v;char extra;
    if(target_update_count>=16 || sscanf(argv[i],"%u:%u%c",&t,&v,&extra)!=2 || v>UINT16_MAX || t%100 ||
       (target_update_count && t<=target_updates[target_update_count-1].time_ms))return 1;
    target_updates[target_update_count].time_ms=t;target_updates[target_update_count++].target=(uint16_t)v;
   }
   else if(!strcmp(key,"--revised-sensor-ramp")) {
    char extra;
    if(sscanf(argv[i],"%u:%u:%lf%c",&sensor_ramp_start,&sensor_ramp_rise,&sensor_ramp_offset,&extra)!=3 ||
       !sensor_ramp_rise || sensor_ramp_start%100 || !isfinite(sensor_ramp_offset))return 1;
   }
   else if(!strcmp(key,"--revised-sensor-variation")) {
    char extra;
    if(sscanf(argv[i],"%lf:%lf:%u%c",&sensor_jitter,&sensor_drift,&sensor_variation_period,&extra)!=3 ||
       !isfinite(sensor_jitter)||!isfinite(sensor_drift)||sensor_jitter<0||sensor_drift<0||sensor_variation_period<100)return 1;
   }
   else if(!strcmp(key,"--revised-evidence"))trace_path=argv[i];
   else if(!strcmp(key,"--revised-observations"))observation_path=argv[i];
   else if(!strcmp(key,"--revised-config"))config_path=argv[i];
   else if(!strcmp(key,"--revised-c2-config"))c2_path=argv[i];
   else if(!strcmp(key,"--revised-metrics"))metrics_path=argv[i];
   else if(!strcmp(key,"--revised-evaluation-start")){if(number(argv[i],&evaluation_start))return 1;}
   else if(!strcmp(key,"--revised-weighted-choice")){unsigned int n;if(number(argv[i],&n)||n>=12)return 1;weighted_choice=(int)n;ws_set=true;}
   else {fprintf(stderr,"Invalid final option: %s\n",key);return 1;}
   enabled=true;
  } else if(!strcmp(argv[i],"--detector")&&i+1<argc&&!strcmp(argv[i+1],"clo_dsf_revised")) {
   primary=enabled=true;argv[write++]=argv[i++];argv[write++]="builtin_ecu";
  } else argv[write++]=argv[i];
 }
 argc=write;argv[write]=NULL;
 if(enabled && (!config_path || final_config_read(config_path,&config))){fprintf(stderr,"A complete valid --revised-config is required.\n");return 1;}
 if(comparison && (!c2_path||historical_config_read(c2_path,&c2_config)||!ws_set)){fprintf(stderr,"Comparison requires historical C2 config and frozen Weighted Sum choice.\n");return 1;}
 if(primary)for(int i=1;i+1<argc;i++)if(!strcmp(argv[i],"--detector-action")&&strcmp(argv[i+1],"observe_only")){fprintf(stderr,"Final research detector requires observe_only.\n");return 1;}
 if(clo_prechange_step)names[1]="Pre-change CLO-DSF";
 clo_revised_init(&prechange);clo_revised_init(&detector);clo_final_init(&previous);c2_init(&candidate2);
 plain_config=c2_config.common;clo_dsf_init(&plain);
 detection_algorithm_init(&hybrid,DETECTION_ALGORITHM_HYBRID_ADAPTIVE_KALMAN,DETECTION_ACTION_OBSERVE_ONLY);
 for(int i=0;i<METHODS;i++)scores[i].first_alarm=scores[i].first_post_alarm=scores[i].first_localization=-1;
 char automatic[ECU_PATH_BUFFER_SIZE+32];
 if(primary&&!trace_path){const char *raw=ECU_DEFAULT_LOG_PATH;if(argc>1){size_t n=strlen(argv[1]);if(n>=4&&!strcmp(argv[1]+n-4,".csv"))raw=argv[1];}int n=snprintf(automatic,sizeof(automatic),"%s.revised.csv",raw);if(n<0||(size_t)n>=sizeof(automatic))return 1;trace_path=automatic;}
 if(trace_path){trace=fopen(trace_path,"w");if(!trace)return 1;log_header(trace);}
 if(observation_path){observations=fopen(observation_path,"w");if(!observations){if(trace)fclose(trace);return 1;}final_observation_header(observations);}
 int result=clo_accepted_main(argc,argv);
 if(trace){bool bad=ferror(trace);if(fclose(trace)||bad)result=1;}
 if(observations){bool bad=ferror(observations);if(fclose(observations)||bad)result=1;}
 if(!result&&metrics_write())result=1;
 return result;
}
