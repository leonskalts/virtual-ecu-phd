#include "clo_dsf_candidate2.h"
#include <math.h>
#include <string.h>
static double unit(double x) { return x<0?0:x>1?1:x; }
void c2_config_default(c2_config_t *c)
{
    clo_config_default(&c->common);
    c->common.conflict_rule=DS_DEMPSTER;
    c->r_detection=1;
}
bool c2_config_valid(const c2_config_t *c)
{
    return clo_config_valid(&c->common) && c->common.conflict_rule==DS_DEMPSTER &&
        isfinite(c->r_detection) && c->r_detection>=0 && c->r_detection<=1;
}
void c2_init(c2_state_t *s)
{
    memset(s,0,sizeof(*s));
    ds_vacuous(&s->detection_mass);ds_vacuous(&s->origin_mass);
    for(int i=0;i<CLO_CHANNELS;i++)s->evidence.onset_ms[i]=-1;
    s->output.alarm_timestamp_ms=s->output.localization_timestamp_ms=-1;
    s->output.anomaly_ignorance=s->output.origin_ignorance=1;
}
static void support(ds_mass_t *m,unsigned int subset,double strength)
{
    ds_vacuous(m);
    if(subset==DS_THETA)return; /* Indistinguishable origins remain vacuous. */
    m->mass[subset]=unit(strength);m->mass[DS_THETA]=1-unit(strength);
}
static bool combine(ds_mass_t *current,const ds_mass_t *channel,double *step,double *maximum)
{
    bool ok=ds_combine(current,channel,DS_DEMPSTER,current,step);
    if(*step>*maximum)*maximum=*step;
    return ok;
}
void c2_step(c2_state_t *s,const c2_config_t *c,unsigned int extensions,const runtime_observation_t *o)
{
    if(s->has_previous_time && o->time_ms<=s->previous_time_ms)return;
    s->has_previous_time=true;s->previous_time_ms=o->time_ms;
    c2_extract(&s->evidence,o);
    c2_propagation(&s->evidence,&c->common,o->time_ms);
    c2_output_t *v=&s->output;
    v->detection_conflict=v->localization_conflict=0;
    v->detection_fallback=v->localization_fallback=false;
    memset(v->detection_conflict_steps,0,sizeof(v->detection_conflict_steps));
    memset(v->localization_conflict_steps,0,sizeof(v->localization_conflict_steps));
    ds_mass_t detect,origin,channel;
    ds_vacuous(&detect);ds_vacuous(&origin);
    v->propagation_support=false;
    for(int i=0;i<CLO_CHANNELS;i++) {
        double strength=s->evidence.available[i]?s->evidence.strength[i]:0;
        double rd=(extensions&C2_DETECTION_RELIABILITY)?c->r_detection:1;
        double rl=(extensions&C2_ORIGIN_RELIABILITY)?((i==3||i==5)?c->common.r_indirect:c->common.r_direct):1;
        bool forward=(s->evidence.propagation_transitions & (63U<<(6*i)))!=0;
        if((extensions&C2_PROPAGATION) && c->common.propagation_bonus>0 && forward) {
            rl=unit(rl*(1+c->common.propagation_bonus));v->propagation_support=true;
        }
        s->detection_reliability[i]=s->evidence.available[i]?rd:0;
        s->origin_reliability[i]=s->evidence.available[i]?rl:0;
        /* Detection never reads origin mass, its discount, or propagation. */
        support(&channel,C2_D_ABNORMAL,strength);
        ds_discount(&channel,s->detection_reliability[i],&channel);
        if(!combine(&detect,&channel,&v->detection_conflict_steps[i],&v->detection_conflict))v->detection_fallback=true;
        support(&channel,c2_origin_support[i],strength);
        ds_discount(&channel,s->origin_reliability[i],&channel);
        if(!combine(&origin,&channel,&v->localization_conflict_steps[i],&v->localization_conflict))v->localization_fallback=true;
    }
    if(extensions&C2_TEMPORAL) {
        ds_discount(&s->detection_mass,c->common.lambda_temporal,&channel);
        if(!combine(&detect,&channel,&v->detection_conflict_steps[6],&v->detection_conflict))v->detection_fallback=true;
        ds_discount(&s->origin_mass,c->common.lambda_temporal,&channel);
        if(!combine(&origin,&channel,&v->localization_conflict_steps[6],&v->localization_conflict))v->localization_fallback=true;
    }
    s->detection_mass=detect;s->origin_mass=origin;
    v->anomaly_belief=ds_belief(&detect,C2_D_ABNORMAL);
    v->anomaly_plausibility=ds_plausibility(&detect,C2_D_ABNORMAL);
    v->anomaly_decision_score=v->anomaly_belief;v->anomaly_ignorance=detect.mass[DS_THETA];
    if(v->anomaly_decision_score>=c->common.alarm_threshold_confirmed) {
        if(s->confirmation_count<c->common.confirmation_persistence)s->confirmation_count++;
    } else s->confirmation_count=0;
    v->alarm=s->confirmation_count>=c->common.confirmation_persistence;
    v->state=v->alarm?CLO_STATE_CONFIRMED:v->anomaly_decision_score>=c->common.alarm_threshold_suspect?CLO_STATE_SUSPECT:CLO_STATE_NORMAL;
    if(v->alarm && v->alarm_timestamp_ms<0)v->alarm_timestamp_ms=(int)o->time_ms;
    c2_origin_betp(&origin,v->origin_scores);
    double best=-1,second=-1;unsigned int top=0;
    for(unsigned int i=0;i<5;i++) {
        if(v->origin_scores[i]>best) {second=best;best=v->origin_scores[i];top=i;}
        else if(v->origin_scores[i]>second)second=v->origin_scores[i];
    }
    v->leading_origin=1U<<(top+1); /* Public names use Candidate 1 origin IDs. */
    v->origin_score=best;v->origin_margin=best-second;
    v->origin_belief=ds_belief(&origin,c2_origin_blocks[top]);
    v->origin_plausibility=ds_plausibility(&origin,c2_origin_blocks[top]);
    v->origin_ignorance=origin.mass[DS_THETA];
    v->localization_valid=v->alarm && best>=c->common.localization_threshold &&
        v->origin_margin>=c->common.localization_margin_threshold && v->origin_ignorance<=c->common.ignorance_limit;
    v->estimated_origin=v->localization_valid?v->leading_origin:0;
    if(v->localization_valid && v->localization_timestamp_ms<0)v->localization_timestamp_ms=(int)o->time_ms;
}
