/* V7 integration adapter ONLY. The evidence algorithm has no dependency on
 * ecu_state, experiment configuration, injection or reference instrumentation.
 * GNU ld wrap calls the original scheduler and original detectors unchanged. */
#include "clo_dsf.h"
#include "ecu_types.h"
#include "runtime_observation.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <errno.h>
#include <limits.h>

int clo_accepted_main(int argc, char **argv);
void __real_detection_algorithm_step(struct ecu_state *state);
#define BANK_SIZE 14
#define LEGACY_SIZE 7
static const char *const names[BANK_SIZE]={"CLO-DSF","Simple OR","Weighted Sum","Plain DS","A1 Observability","A2 Propagation",
    "candidate_0","candidate_1","candidate_2","candidate_3","candidate_4","candidate_5","candidate_6","candidate_7"};
static const char *const legacy_names[LEGACY_SIZE]={"Threshold","EWMA","CUSUM","Thermal Observer","Kalman","Hybrid","Timing Monitor"};
static clo_dsf_t bank[BANK_SIZE];
static clo_config_t configs[BANK_SIZE];
static detection_algorithm_state_t legacy[LEGACY_SIZE-1];
static const detection_algorithm_t legacy_ids[LEGACY_SIZE-1]={DETECTION_ALGORITHM_THRESHOLD,DETECTION_ALGORITHM_EWMA,DETECTION_ALGORITHM_CUSUM,DETECTION_ALGORITHM_THERMAL_OBSERVER,DETECTION_ALGORITHM_KALMAN_FILTER,DETECTION_ALGORITHM_HYBRID_ADAPTIVE_KALMAN};
static const clo_variant_t variants[6]={CLO_FULL,CLO_OR,CLO_WEIGHTED,CLO_PLAIN,CLO_OBSERVABILITY,CLO_PROPAGATION};
/* Evaluation-only accumulators. They never feed a detector. */
typedef struct {
    int first_alarm, first_post_alarm, first_localization, origin_at_alarm, first_origin;
    bool previous_alarm;
    unsigned int samples, alarm_samples, pre_alarm_samples, propagation_samples, high_conflict_samples;
    double ignorance_sum, conflict_sum, max_conflict;
} score_t;
static score_t scores[BANK_SIZE+LEGACY_SIZE];
static FILE *evidence_file;
static bool enabled, primary, comparison, search;
static unsigned int evaluation_start;
static const char *metrics_path;
static int io_error;

static void score_step(score_t *s, unsigned int now, bool alarm, unsigned int origin, double ignorance, double conflict, bool prop)
{
    s->samples++; s->alarm_samples+=alarm;
    if (alarm && now<evaluation_start) s->pre_alarm_samples++;
    if (alarm && !s->previous_alarm) {
        if(s->first_alarm<0) s->first_alarm=(int)now;
        if(now>=evaluation_start && s->first_post_alarm<0) { s->first_post_alarm=(int)now; s->origin_at_alarm=(int)origin; }
    }
    if(alarm && origin && now>=evaluation_start && s->first_post_alarm>=0 && s->first_localization<0) {
        s->first_localization=(int)now; s->first_origin=(int)origin;
    }
    s->previous_alarm=alarm;
    s->ignorance_sum+=ignorance; s->conflict_sum+=conflict;
    if(conflict>s->max_conflict) s->max_conflict=conflict;
    s->high_conflict_samples+=conflict>=.5;
    s->propagation_samples+=prop;
}
static void evidence_header(FILE *f)
{
    fprintf(f,"time_ms,detector_state,fault_belief,estimated_origin,origin_score,origin_margin,origin_belief,origin_plausibility,ignorance_mass,conflict_mass,propagation_support,propagation_transitions,alarm,localization_valid,alarm_timestamp_ms,localization_timestamp_ms,combination_fallback");
    for(int i=0;i<CLO_CHANNELS;i++) fprintf(f,",%s_evidence,%s_reliability,%s_available",clo_channel_names[i],clo_channel_names[i],clo_channel_names[i]);
    for(int i=0;i<CLO_CHANNELS+2;i++) fprintf(f,",conflict_step_%d",i);
    fputc('\n',f);
}
static void evidence_row(FILE *f, unsigned int now, const clo_dsf_t *s)
{
    const clo_output_t *o=&s->output;
    fprintf(f,"%u,%s,%.9g,%s,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%d,%u,%d,%d,%d,%d,%d",now,
        clo_state_name(o->state),o->fault_belief,clo_origin_name(o->estimated_origin),o->origin_score,o->origin_margin,
        o->origin_belief,o->origin_plausibility,o->ignorance_mass,o->conflict_mass,o->propagation_support,
        s->evidence.propagation_transitions,o->alarm,o->localization_valid,o->alarm_timestamp_ms,o->localization_timestamp_ms,o->combination_fallback);
    for(int i=0;i<CLO_CHANNELS;i++) fprintf(f,",%.9g,%.9g,%d",s->evidence.strength[i],s->evidence.reliability[i],s->evidence.available[i]);
    for(int i=0;i<CLO_CHANNELS+2;i++) fprintf(f,",%.9g",o->conflict_steps[i]);
    fputc('\n',f);
}
void __wrap_detection_algorithm_step(struct ecu_state *state)
{
    /* Reference state has no log; it never enters the v7 observer bank. */
    if(!enabled || !state->log_file) { __real_detection_algorithm_step(state); return; }
    runtime_observation_t o;
    runtime_observation_capture(state,&o);
    for(int i=0;i<(comparison?(search?BANK_SIZE:6):1);i++) {
        clo_dsf_step(&bank[i],&configs[i],i<6?variants[i]:CLO_FULL,&o);
        clo_output_t *v=&bank[i].output;
        score_step(&scores[i],o.time_ms,v->alarm,v->estimated_origin,v->ignorance_mass,v->conflict_mass,v->propagation_support);
    }
    if(comparison) {
        for(int i=0;i<LEGACY_SIZE-1;i++) {
            ecu_state_t shadow=*state;
            shadow.detection=legacy[i];
            __real_detection_algorithm_step(&shadow);
            legacy[i]=shadow.detection;
            score_step(&scores[BANK_SIZE+i],o.time_ms,legacy[i].alarm_active,0,0,0,false);
        }
        score_step(&scores[BANK_SIZE+LEGACY_SIZE-1],o.time_ms,state->timing_monitor.alarm,0,0,0,false);
    }
    if(evidence_file) evidence_row(evidence_file,o.time_ms,&bank[0]);
    if(primary) {
        /* Observe-only; existing safety requests/policies remain untouched.
         * Legacy CSV algorithm enum remains builtin_ecu, so consumers must use
         * the explicitly named v7 sidecar for experimental detector results. */
        state->detection.current_score=(float)bank[0].output.fault_belief;
        state->detection.alarm_active=bank[0].output.alarm;
        state->detection.detected=bank[0].output.alarm_timestamp_ms>=0;
        state->detection.first_detection_time_ms=bank[0].output.alarm_timestamp_ms;
        snprintf(state->detection.runtime_label,sizeof(state->detection.runtime_label),"clo_dsf_experimental");
    } else __real_detection_algorithm_step(state);
}
static int unsigned_value(const char *value, unsigned int *out)
{
    char *end; errno=0;
    unsigned long number=strtoul(value,&end,10);
    if(*value<'0'||*value>'9'||*end||errno||number>UINT_MAX) return -1;
    *out=(unsigned int)number; return 0;
}
static int read_config(const char *path, clo_config_t *c)
{
    FILE *f=fopen(path,"r"); if(!f) return -1;
    char line[256],key[100],value[100]; unsigned int seen=0;
    while(fgets(line,sizeof(line),f)) {
        if(line[0]=='#'||line[0]=='\n') continue;
        char extra;
        if(sscanf(line,"%99[^=]=%99s %c",key,value,&extra)!=2) { fclose(f); return -1; }
        double *target=NULL;
        const char *keys[]={"r_direct","r_indirect","lambda_temporal","propagation_bonus","alarm_threshold_suspect","alarm_threshold_confirmed","localization_threshold","localization_margin_threshold","ignorance_limit"};
        double *values[]={&c->r_direct,&c->r_indirect,&c->lambda_temporal,&c->propagation_bonus,&c->alarm_threshold_suspect,&c->alarm_threshold_confirmed,&c->localization_threshold,&c->localization_margin_threshold,&c->ignorance_limit};
        int index=-1;
        for(int i=0;i<9;i++) if(!strcmp(key,keys[i])) { target=values[i]; index=i; }
        if(target) { char *end; errno=0; *target=strtod(value,&end); if(*end||errno) { fclose(f); return -1; } }
        else if(!strcmp(key,"propagation_window_ms")) { index=9; if(unsigned_value(value,&c->propagation_window_ms)) { fclose(f);return -1;} }
        else if(!strcmp(key,"confirmation_persistence")) { index=10; if(unsigned_value(value,&c->confirmation_persistence)) { fclose(f);return -1;} }
        else if(!strcmp(key,"conflict_rule")) {
            index=11;
            if(!strcmp(value,"yager")) c->conflict_rule=DS_YAGER;
            else if(!strcmp(value,"dempster")) c->conflict_rule=DS_DEMPSTER;
            else { fclose(f);return -1; }
        } else { fclose(f);return -1; }
        if(seen&(1U<<index)) { fclose(f);return -1; }
        seen|=1U<<index;
    }
    bool ok=!ferror(f); fclose(f);
    return ok && seen==4095U && clo_config_valid(c)?0:-1;
}
static void metrics_write(void)
{
    if(!metrics_path) return;
    FILE *f=fopen(metrics_path,"w");
    if(!f) { perror(metrics_path);io_error=1;return; }
    fprintf(f,"method,first_alarm_ms,first_post_alarm_ms,origin_at_alarm,first_localization_ms,first_origin,samples,alarm_samples,pre_alarm_samples,mean_ignorance,mean_conflict,max_conflict,high_conflict_samples,propagation_samples\n");
    for(int i=0;i<(comparison?BANK_SIZE+LEGACY_SIZE:1);i++) {
        if (comparison && !search && i>=6 && i<BANK_SIZE) continue;
        score_t *s=&scores[i];
        fprintf(f,"%s,%d,%d,%s,%d,%s,%u,%u,%u,%.12g,%.12g,%.12g,%u,%u\n",i<BANK_SIZE?names[i]:legacy_names[i-BANK_SIZE],
            s->first_alarm,s->first_post_alarm,clo_origin_name((unsigned int)s->origin_at_alarm),s->first_localization,clo_origin_name((unsigned int)s->first_origin),s->samples,s->alarm_samples,s->pre_alarm_samples,
            s->samples?s->ignorance_sum/s->samples:0,s->samples?s->conflict_sum/s->samples:0,s->max_conflict,s->high_conflict_samples,s->propagation_samples);
    }
    bool bad=ferror(f); if(fclose(f)||bad) io_error=1;
}
int main(int argc, char **argv)
{
    const char *evidence_path=NULL,*config_path=NULL;
    int write=1;
    for(int i=1;i<argc;i++) {
        if(!strncmp(argv[i],"--clo-",6)) {
            const char *key=argv[i];
            if(++i>=argc) { fprintf(stderr,"Missing value for %s\n",key); return 1; }
            if(!strcmp(key,"--clo-evidence")) evidence_path=argv[i];
            else if(!strcmp(key,"--clo-metrics")) metrics_path=argv[i];
            else if(!strcmp(key,"--clo-config")) config_path=argv[i];
            else if(!strcmp(key,"--clo-comparison") && (!strcmp(argv[i],"train") || !strcmp(argv[i],"validation"))) { comparison=true;search=!strcmp(argv[i],"train"); }
            else if(!strcmp(key,"--clo-evaluation-start")) { if(unsigned_value(argv[i],&evaluation_start)) return 1; }
            else { fprintf(stderr,"Invalid CLO option: %s\n",key);return 1; }
            enabled=true;
        } else if(!strcmp(argv[i],"--detector") && i+1<argc && !strcmp(argv[i+1],"clo_dsf")) {
            enabled=primary=true; argv[write++]=argv[i++];argv[write++]="builtin_ecu";
        } else argv[write++]=argv[i];
    }
    argc=write;argv[write]=NULL;
    if(primary) for(int i=1;i+1<argc;i++) if(!strcmp(argv[i],"--detector-action")&&strcmp(argv[i+1],"observe_only")) {
        fprintf(stderr,"CLO-DSF development supports observe_only.\n");return 1;
    }
    clo_config_t c;clo_config_default(&c);
    if(config_path && read_config(config_path,&c)) { fprintf(stderr,"Invalid complete CLO config: %s\n",config_path);return 1; }
    for(int i=0;i<BANK_SIZE;i++) { clo_dsf_init(&bank[i]); configs[i]=c; }
    /* Pre-registered coarse 2x2x2 search. No validation-adaptive configuration. */
    for(int i=0;i<8;i++) {
        clo_config_default(&configs[i+6]);
        configs[i+6].conflict_rule=(i&1)?DS_DEMPSTER:DS_YAGER;
        configs[i+6].lambda_temporal=(i&2)?.9:.8;
        configs[i+6].alarm_threshold_confirmed=(i&4)?.75:.65;
    }
    for(int i=0;i<LEGACY_SIZE-1;i++) detection_algorithm_init(&legacy[i],legacy_ids[i],DETECTION_ACTION_OBSERVE_ONLY);
    for(int i=0;i<BANK_SIZE+LEGACY_SIZE;i++) scores[i].first_alarm=scores[i].first_post_alarm=scores[i].first_localization=-1;
    char automatic[ECU_PATH_BUFFER_SIZE+32];
    if(primary && !evidence_path) {
        const char *raw_path=ECU_DEFAULT_LOG_PATH;
        if(argc>1) {
            size_t length=strlen(argv[1]);
            if(length>=4 && !strcmp(argv[1]+length-4,".csv")) raw_path=argv[1];
        }
        int written=snprintf(automatic,sizeof(automatic),"%s.clo_dsf.csv",raw_path);
        if(written<0 || (size_t)written>=sizeof(automatic)) {
            fprintf(stderr,"CLO evidence path too long.\n");return 1;
        }
        evidence_path=automatic;
    }
    if(evidence_path) {
        evidence_file=fopen(evidence_path,"w");
        if(!evidence_file) { perror(evidence_path);return 1; }
        evidence_header(evidence_file);
    }
    int result=clo_accepted_main(argc,argv);
    if(evidence_file) { bool bad=ferror(evidence_file); if(fclose(evidence_file)||bad) io_error=1; }
    if(!result) metrics_write();
    if(enabled) printf("Experimental runtime detector: CLO-DSF; primary=%d; state=%s; estimated origin=%s\n",primary,clo_state_name(bank[0].output.state),clo_origin_name(bank[0].output.estimated_origin));
    return result?result:io_error;
}
