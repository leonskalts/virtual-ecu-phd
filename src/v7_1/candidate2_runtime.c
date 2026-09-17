/* Integration/evaluation adapter, not a detector dependency. Only the runtime
 * observation is passed to either candidate. Scoring metadata never feeds back. */
#include "clo_dsf_candidate2.h"
#include "ecu_types.h"
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
int clo_accepted_main(int argc,char **argv);
void __real_detection_algorithm_step(struct ecu_state *state);
#define C2_BANK 17
#define METHODS 44
static const char *const names[METHODS]={
    "Candidate 2","B1 Dual-frame","B2 Origin reliability","B3 Propagation","B4 Temporal",
    "Detection reliability 0.9","No origin reliability","Full propagation on","Full propagation off",
    "candidate_0","candidate_1","candidate_2","candidate_3","candidate_4","candidate_5","candidate_6","candidate_7",
    "Candidate 1","Plain DS","Simple OR","Weighted Sum","Hybrid","Timing Monitor",
    "weighted_0","weighted_1","weighted_2","weighted_3","weighted_4","weighted_5",
    "weighted_6","weighted_7","weighted_8","weighted_9","weighted_10","weighted_11",
    "Single frame positive",
    "candidate_0_no_prop","candidate_1_no_prop","candidate_2_no_prop","candidate_3_no_prop",
    "candidate_4_no_prop","candidate_5_no_prop","candidate_6_no_prop","candidate_7_no_prop"};
static const double ws_thresholds[6]={.04,.06,.08,.10,.14,.18};
static const double ws_weights[2][6]={{1./6,1./6,1./6,1./6,1./6,1./6},{.2,.2,.2,.1,.2,.1}};
static c2_state_t bank[C2_BANK], no_prop[8];
static c2_config_t configs[C2_BANK];
static clo_dsf_t c1,plain;
static clo_config_t c1_config,plain_config;
static detection_algorithm_state_t hybrid;
static FILE *trace;
static bool enabled,comparison,search;
static int primary,weighted_choice;
static unsigned int evaluation_start;
static const char *metrics_path;
typedef struct {
    int first_alarm,first_post_alarm,first_localization;
    unsigned int origin_at_alarm,leading_at_alarm,first_origin;
    double score_at_alarm,margin_at_alarm,ignorance_at_alarm;
    unsigned int samples,alarm_samples,pre_alarm_samples,propagation_samples,high_detection,high_localization;
    double anomaly_ignorance_sum,origin_ignorance_sum,detection_conflict_sum,localization_conflict_sum;
    bool previous_alarm;
} score_t;
static score_t scores[METHODS];
static unsigned int simple_streak;
static bool applicable(int i)
{
    if(!comparison)return i==0 || (primary==1 && i==17);
    return search || !((i>=9&&i<17)||(i>=23&&i<35)||i>=36);
}
static void score_step(int index,unsigned int now,bool alarm,unsigned int origin,unsigned int leading,
    double confidence,double margin,double origin_ignorance,double anomaly_ignorance,
    double detection_conflict,double localization_conflict,bool prop)
{
    score_t *s=&scores[index];s->samples++;s->alarm_samples+=alarm;
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
    fprintf(f,"time_ms,detector_state,anomaly_belief,anomaly_plausibility,anomaly_decision_score,anomaly_ignorance,detection_conflict,estimated_origin,origin_score,origin_belief,origin_plausibility,origin_margin,origin_ignorance,localization_conflict,propagation_support,propagation_transitions,alarm,localization_valid,alarm_timestamp_ms,localization_timestamp_ms,detection_fallback,localization_fallback");
    for(int i=0;i<6;i++)fprintf(f,",%s_evidence,%s_detection_reliability,%s_origin_reliability",clo_channel_names[i],clo_channel_names[i],clo_channel_names[i]);
    for(int i=0;i<7;i++)fprintf(f,",detection_K_%d,localization_K_%d",i,i);
    for(unsigned int i=1;i<32;i++)fprintf(f,",origin_mass_%u",i);
    fprintf(f,",detection_mass_normal,detection_mass_abnormal,detection_mass_ignorance\n");
}
static void log_row(FILE *f,unsigned int now,const c2_state_t *s)
{
    const c2_output_t *v=&s->output;
    fprintf(f,"%u,%s,%.9g,%.9g,%.9g,%.9g,%.9g,%s,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%d,%u,%d,%d,%d,%d,%d,%d",now,
        clo_state_name(v->state),v->anomaly_belief,v->anomaly_plausibility,v->anomaly_decision_score,v->anomaly_ignorance,v->detection_conflict,
        clo_origin_name(v->estimated_origin),v->origin_score,v->origin_belief,v->origin_plausibility,v->origin_margin,v->origin_ignorance,v->localization_conflict,
        v->propagation_support,s->evidence.propagation_transitions,v->alarm,v->localization_valid,v->alarm_timestamp_ms,v->localization_timestamp_ms,v->detection_fallback,v->localization_fallback);
    for(int i=0;i<6;i++)fprintf(f,",%.9g,%.9g,%.9g",s->evidence.strength[i],s->detection_reliability[i],s->origin_reliability[i]);
    for(int i=0;i<7;i++)fprintf(f,",%.9g,%.9g",v->detection_conflict_steps[i],v->localization_conflict_steps[i]);
    for(unsigned int i=1;i<32;i++)fprintf(f,",%.9g",s->origin_mass.mass[c2_encode_origin_subset(i)]);
    fprintf(f,",%.9g,%.9g,%.9g\n",s->detection_mass.mass[C2_D_NORMAL],s->detection_mass.mass[C2_D_ABNORMAL],s->detection_mass.mass[DS_THETA]);
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
static void single_positive(unsigned int now,const clo_evidence_t *e)
{
    ds_mass_t mass,channel;ds_vacuous(&mass);double maximum=0;
    for(unsigned int i=0;i<6;i++) {
        clo_evidence_mass(i,e->strength[i],e->available[i],&channel);
        double k=0;ds_combine(&mass,&channel,DS_DEMPSTER,&mass,&k);if(k>maximum)maximum=k;
    }
    double belief=ds_belief(&mass,CLO_ABNORMAL);
    if(belief>=configs[0].common.alarm_threshold_confirmed) {if(simple_streak<configs[0].common.confirmation_persistence)simple_streak++;}
    else simple_streak=0;
    double p[6];ds_pignistic(&mass,p);double best=-1,second=-1;unsigned int origin=0;
    for(unsigned int i=1;i<6;i++)if(p[i]>best){second=best;best=p[i];origin=1U<<i;}else if(p[i]>second)second=p[i];
    bool alarm=simple_streak>=configs[0].common.confirmation_persistence;
    bool local=alarm && best>=configs[0].common.localization_threshold && best-second>=configs[0].common.localization_margin_threshold && mass.mass[DS_THETA]<=configs[0].common.ignorance_limit;
    score_step(35,now,alarm,local?origin:0,origin,best,best-second,mass.mass[DS_THETA],mass.mass[DS_THETA],maximum,maximum,false);
}
void __wrap_detection_algorithm_step(struct ecu_state *state)
{
    if(!enabled || !state->log_file){__real_detection_algorithm_step(state);return;}
    runtime_observation_t o;runtime_observation_capture(state,&o);
    for(int i=0;i<C2_BANK;i++)if(applicable(i)) {
        unsigned int flags=C2_FULL;
        if(i==1)flags=0;
        if(i==2)flags=C2_ORIGIN_RELIABILITY;
        if(i==3)flags=C2_ORIGIN_RELIABILITY|C2_PROPAGATION;
        if(i==6)flags=C2_FULL^C2_ORIGIN_RELIABILITY;
        c2_step(&bank[i],&configs[i],flags,&o);
        c2_output_t *v=&bank[i].output;
        score_step(i,o.time_ms,v->alarm,v->estimated_origin,v->leading_origin,v->origin_score,v->origin_margin,
            v->origin_ignorance,v->anomaly_ignorance,v->detection_conflict,v->localization_conflict,v->propagation_support);
    }
    if(search)for(int i=0;i<8;i++) {
        c2_config_t cfg=configs[i+9];cfg.common.propagation_bonus=0;
        c2_step(&no_prop[i],&cfg,C2_FULL,&o);
        c2_output_t *v=&no_prop[i].output;
        score_step(36+i,o.time_ms,v->alarm,v->estimated_origin,v->leading_origin,v->origin_score,v->origin_margin,
            v->origin_ignorance,v->anomaly_ignorance,v->detection_conflict,v->localization_conflict,v->propagation_support);
    }
    if(trace)log_row(trace,o.time_ms,&bank[0]);
    if(applicable(17)){clo_dsf_step(&c1,&c1_config,CLO_FULL,&o);old_score(17,o.time_ms,&c1);}
    if(comparison) {
        clo_dsf_step(&plain,&plain_config,CLO_PLAIN,&o);old_score(18,o.time_ms,&plain);
        double peak=0;for(int i=0;i<6;i++)if(bank[0].evidence.strength[i]>peak)peak=bank[0].evidence.strength[i];
        simple_score(19,o.time_ms,peak>=.5);
        for(int k=0;k<12;k++)if(search || k==weighted_choice) {
            double score=0;for(int j=0;j<6;j++)score+=ws_weights[k/6][j]*bank[0].evidence.strength[j];
            bool alarm=score>=ws_thresholds[k%6];
            if(search)simple_score(23+k,o.time_ms,alarm);
            if(k==weighted_choice)simple_score(20,o.time_ms,alarm);
        }
        ecu_state_t shadow=*state;shadow.detection=hybrid;
        __real_detection_algorithm_step(&shadow);hybrid=shadow.detection;
        simple_score(21,o.time_ms,hybrid.alarm_active);
        simple_score(22,o.time_ms,state->timing_monitor.alarm);
        single_positive(o.time_ms,&bank[0].evidence);
    }
    if(primary) {
        bool alarm=primary==1?c1.output.alarm:bank[0].output.alarm;
        int first=primary==1?c1.output.alarm_timestamp_ms:bank[0].output.alarm_timestamp_ms;
        state->detection.current_score=(float)(primary==1?c1.output.fault_belief:bank[0].output.anomaly_decision_score);
        state->detection.alarm_active=alarm;state->detection.detected=first>=0;state->detection.first_detection_time_ms=first;
        snprintf(state->detection.runtime_label,sizeof(state->detection.runtime_label),"clo_dsf_candidate%d_experimental",primary);
    } else __real_detection_algorithm_step(state);
}
static int number(const char *value,unsigned int *out)
{
    errno=0;char *end;unsigned long n=strtoul(value,&end,10);
    if(*value<'0'||*value>'9'||*end||errno||n>UINT_MAX)return -1;
    *out=(unsigned int)n;return 0;
}
static int config_read(const char *path,c2_config_t *c)
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
static int metrics_write(void)
{
    if(!metrics_path)return 0;
    FILE *f=fopen(metrics_path,"w");if(!f)return -1;
    fprintf(f,"method,first_alarm_ms,first_post_alarm_ms,origin_at_alarm,leading_at_alarm,origin_score_at_alarm,origin_margin_at_alarm,origin_ignorance_at_alarm,first_localization_ms,first_origin,samples,alarm_samples,pre_alarm_samples,mean_anomaly_ignorance,mean_origin_ignorance,mean_detection_conflict,mean_localization_conflict,high_detection_conflict_samples,high_localization_conflict_samples,propagation_samples\n");
    for(int i=0;i<METHODS;i++)if(applicable(i)) {
        score_t *s=&scores[i];double n=s->samples?s->samples:1;
        fprintf(f,"%s,%d,%d,%s,%s,%.12g,%.12g,%.12g,%d,%s,%u,%u,%u,%.12g,%.12g,%.12g,%.12g,%u,%u,%u\n",names[i],s->first_alarm,s->first_post_alarm,
            clo_origin_name(s->origin_at_alarm),clo_origin_name(s->leading_at_alarm),s->score_at_alarm,s->margin_at_alarm,s->ignorance_at_alarm,
            s->first_localization,clo_origin_name(s->first_origin),s->samples,s->alarm_samples,s->pre_alarm_samples,
            s->anomaly_ignorance_sum/n,s->origin_ignorance_sum/n,s->detection_conflict_sum/n,s->localization_conflict_sum/n,
            s->high_detection,s->high_localization,s->propagation_samples);
    }
    bool bad=ferror(f);return fclose(f)||bad?-1:0;
}
int main(int argc,char **argv)
{
    int write=1;const char *trace_path=NULL,*config_path=NULL;
    for(int i=1;i<argc;i++) {
        if(!strncmp(argv[i],"--c2-",5)) {
            const char *key=argv[i];if(++i>=argc){fprintf(stderr,"Missing %s value\n",key);return 1;}
            if(!strcmp(key,"--c2-evidence"))trace_path=argv[i];
            else if(!strcmp(key,"--c2-config"))config_path=argv[i];
            else if(!strcmp(key,"--c2-metrics"))metrics_path=argv[i];
            else if(!strcmp(key,"--c2-evaluation-start")){if(number(argv[i],&evaluation_start))return 1;}
            else if(!strcmp(key,"--c2-weighted-choice")){unsigned int n;if(number(argv[i],&n)||n>=12)return 1;weighted_choice=(int)n;}
            else if(!strcmp(key,"--c2-comparison")&&(!strcmp(argv[i],"train")||!strcmp(argv[i],"validation"))){comparison=true;search=!strcmp(argv[i],"train");}
            else {fprintf(stderr,"Invalid Candidate 2 option: %s\n",key);return 1;}
            enabled=true;
        } else if(!strcmp(argv[i],"--detector") && i+1<argc && (!strcmp(argv[i+1],"clo_dsf_candidate1")||!strcmp(argv[i+1],"clo_dsf_candidate2"))) {
            primary=!strcmp(argv[i+1],"clo_dsf_candidate1")?1:2;enabled=true;argv[write++]=argv[i++];argv[write++]="builtin_ecu";
        } else argv[write++]=argv[i];
    }
    argc=write;argv[write]=NULL;
    if(primary)for(int i=1;i+1<argc;i++)if(!strcmp(argv[i],"--detector-action")&&strcmp(argv[i+1],"observe_only")){fprintf(stderr,"Experimental candidates require observe_only.\n");return 1;}
    c2_config_t c;c2_config_default(&c);
    if(config_path && config_read(config_path,&c)){fprintf(stderr,"Invalid complete Candidate 2 config: %s\n",config_path);return 1;}
    for(int i=0;i<C2_BANK;i++){c2_init(&bank[i]);configs[i]=c;}
    configs[3].common.propagation_bonus=configs[4].common.propagation_bonus=configs[7].common.propagation_bonus=.1;
    configs[4].r_detection=1;configs[5].r_detection=.9;
    configs[8].common.propagation_bonus=0;
    for(int i=0;i<8;i++) {
        c2_config_default(&configs[i+9]);
        configs[i+9].common.alarm_threshold_confirmed=(i&1)?.65:.5;
        configs[i+9].common.confirmation_persistence=(i&2)?2:1;
        configs[i+9].common.lambda_temporal=(i&4)?.8:.6;
    }
    for(int i=0;i<8;i++)c2_init(&no_prop[i]);
    clo_config_default(&c1_config);c1_config.conflict_rule=DS_DEMPSTER;
    plain_config=c.common;clo_dsf_init(&c1);clo_dsf_init(&plain);
    detection_algorithm_init(&hybrid,DETECTION_ALGORITHM_HYBRID_ADAPTIVE_KALMAN,DETECTION_ACTION_OBSERVE_ONLY);
    for(int i=0;i<METHODS;i++)scores[i].first_alarm=scores[i].first_post_alarm=scores[i].first_localization=-1;
    char automatic[ECU_PATH_BUFFER_SIZE+32];
    if(primary==2 && !trace_path) {
        const char *raw=ECU_DEFAULT_LOG_PATH;
        if(argc>1){size_t n=strlen(argv[1]);if(n>=4&&!strcmp(argv[1]+n-4,".csv"))raw=argv[1];}
        int n=snprintf(automatic,sizeof(automatic),"%s.candidate2.csv",raw);
        if(n<0||(size_t)n>=sizeof(automatic))return 1;
        trace_path=automatic;
    }
    if(trace_path){trace=fopen(trace_path,"w");if(!trace){perror(trace_path);return 1;}log_header(trace);}
    int result=clo_accepted_main(argc,argv);
    if(trace){bool bad=ferror(trace);if(fclose(trace)||bad)result=1;}
    if(!result && metrics_write())result=1;
    if(enabled)printf("Experimental CLO-DSF mode: %s; Candidate 2 state=%s origin=%s\n",primary==1?"Candidate 1":primary==2?"Candidate 2":"Comparison",clo_state_name(bank[0].output.state),clo_origin_name(bank[0].output.estimated_origin));
    return result;
}
