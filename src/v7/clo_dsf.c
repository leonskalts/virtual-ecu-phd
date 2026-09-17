#include "clo_dsf.h"
#include "config.h"
#include <math.h>
#include <string.h>
static double unit(double x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
static double maximum(double a, double b) { return a > b ? a : b; }
void clo_config_default(clo_config_t *c)
{
    *c = (clo_config_t){ .r_direct=.9, .r_indirect=.6, .lambda_temporal=.8,
        .propagation_bonus=.1, .propagation_window_ms=3000,
        .alarm_threshold_suspect=.35, .alarm_threshold_confirmed=.65,
        .confirmation_persistence=2, .localization_threshold=.55,
        .localization_margin_threshold=.15, .ignorance_limit=.5, .conflict_rule=DS_YAGER };
}
bool clo_config_valid(const clo_config_t *c)
{
    const double values[] = {c->r_direct,c->r_indirect,c->lambda_temporal,c->propagation_bonus,
        c->alarm_threshold_suspect,c->alarm_threshold_confirmed,c->localization_threshold,
        c->localization_margin_threshold,c->ignorance_limit};
    for (unsigned int i=0; i<sizeof(values)/sizeof(values[0]); i++)
        if (!isfinite(values[i]) || values[i]<0 || values[i]>1) return false;
    return c->lambda_temporal < 1 && c->confirmation_persistence > 0 &&
        c->confirmation_persistence <= 1000 && c->propagation_window_ms <= 60000 &&
        c->alarm_threshold_suspect < c->alarm_threshold_confirmed &&
        (c->conflict_rule == DS_YAGER || c->conflict_rule == DS_DEMPSTER);
}
void clo_dsf_init(clo_dsf_t *s)
{
    memset(s,0,sizeof(*s)); ds_vacuous(&s->fused);
    for (int i=0;i<CLO_CHANNELS;i++) s->evidence.onset_ms[i]=-1;
    s->output.alarm_timestamp_ms=s->output.localization_timestamp_ms=-1;
    s->output.ignorance_mass=1;
}
void clo_evidence_mass(unsigned int channel, double strength, bool available, ds_mass_t *m)
{
    ds_vacuous(m);
    if (channel>=CLO_CHANNELS || !available || !isfinite(strength)) return;
    double e=unit(strength);
    m->mass[clo_supported_subsets[channel]]=e;
    m->mass[DS_THETA]=1-e;
}
static void extract(clo_evidence_t *e, const runtime_observation_t *o)
{
    memset(e->strength,0,sizeof(e->strength));
    memset(e->available,0,sizeof(e->available));
    e->available[0]=o->timing.period_ms>0;
    if (e->available[0]) {
        double limit=(double)o->timing.period_ms+o->timing.relative_deadline_ms;
        double age=unit(((double)o->timing.execution_age_ms-limit)/o->timing.period_ms);
        bool late=o->timing.actual_completion_ms>=0 && o->timing.job_release_ms>=0 &&
            (double)o->timing.actual_completion_ms-o->timing.job_release_ms>o->timing.relative_deadline_ms;
        e->strength[0]=maximum(age,(o->timing.deadline_exceeded || o->timing.missed_expected_execution || late)?1:0);
    }
    e->available[1]=o->sample_expected_period_ms>0 && o->sample_timestamp_ms<=o->time_ms;
    if (e->available[1]) {
        e->strength[1]=unit(((double)o->sample_age_ms-ECU_COOLANT_SENSOR_FRESHNESS_STALE_MS)/ECU_COOLANT_SENSOR_FRESHNESS_STALE_MS);
        if (!o->sample_freshness_ok || (e->initialized && o->sample_timestamp_ms<e->previous_sample_timestamp_ms)) e->strength[1]=1;
    }
    e->available[2]=isfinite(o->control_target_c);
    if (e->available[2]) e->strength[2]=unit(fabs(o->control_target_c-ECU_TARGET_COOLANT_TEMP_C)/4.0);
    e->available[3]=isfinite(o->coolant_measured_c);
    if (e->available[3]) {
        if (o->coolant_measured_c<ECU_SENSOR_IMPLAUSIBLE_LOW_C || o->coolant_measured_c>ECU_SENSOR_IMPLAUSIBLE_HIGH_C) e->strength[3]=1;
        /* A measured slew residual, not simulator true-temperature residual.
         * 2.5 C/s is a deliberately broad physical envelope, not plant truth. */
        if (e->initialized && o->time_ms>e->previous_timestamp_ms) {
            double dt=(o->time_ms-e->previous_timestamp_ms)/1000.0;
            double residual=fabs(o->coolant_measured_c-e->previous_temperature)-2.5*dt;
            e->strength[3]=maximum(e->strength[3],unit(residual/2.0));
        }
    }
    e->available[4]=isfinite(o->fan_command)&&isfinite(o->fan_actual)&&isfinite(o->pump_command)&&isfinite(o->pump_actual);
    if (e->available[4]) e->strength[4]=unit(maximum(fabs(o->fan_command-o->fan_actual)/.25,fabs(o->pump_command-o->pump_actual)/.20));
    e->available[5]=isfinite(o->coolant_measured_c);
    if (e->available[5]) e->strength[5]=unit((o->coolant_measured_c-ECU_WARN_COOLANT_TEMP_C)/(ECU_CRITICAL_COOLANT_TEMP_C-ECU_WARN_COOLANT_TEMP_C));
    if (e->available[3]) { e->previous_temperature=o->coolant_measured_c; e->initialized=true; }
    else e->initialized=false;
    e->previous_timestamp_ms=o->time_ms;
    e->previous_sample_timestamp_ms=o->sample_timestamp_ms;
}
static void propagation(clo_evidence_t *e, const clo_config_t *c, unsigned int now)
{
    e->propagation_transitions=0;
    for (int i=0;i<CLO_CHANNELS;i++) {
        bool active=e->available[i] && e->strength[i]>=.5;
        if (active && !e->active[i]) e->onset_ms[i]=(int)now;
        if (!active) e->onset_ms[i]=-1;
        e->active[i]=active;
    }
    for (int i=0;i<CLO_CHANNELS;i++) for (int j=0;j<CLO_CHANNELS;j++)
        if ((clo_propagation_edges[i]&(1U<<j)) && e->active[i] && e->active[j] &&
            e->onset_ms[i]<e->onset_ms[j] && e->onset_ms[j]<=(int)now &&
            now-(unsigned int)e->onset_ms[i]<=c->propagation_window_ms)
            e->propagation_transitions |= 1U<<(i*CLO_CHANNELS+j);
}
static void combine(clo_output_t *o, ds_mass_t *a, const ds_mass_t *b, ds_rule_t rule, int step)
{
    if (!ds_combine(a,b,rule,a,&o->conflict_steps[step])) o->combination_fallback=true;
    o->conflict_mass=maximum(o->conflict_mass,o->conflict_steps[step]);
}
void clo_dsf_step(clo_dsf_t *s, const clo_config_t *c, clo_variant_t variant, const runtime_observation_t *o)
{
    clo_output_t *out=&s->output;
    /* Non-increasing timestamps are ignored: no duplicated evidence accumulation. */
    if (s->evidence.initialized && o->time_ms<=s->evidence.previous_timestamp_ms) return;
    extract(&s->evidence,o);
    propagation(&s->evidence,c,o->time_ms);
    out->conflict_mass=0; out->combination_fallback=false;
    memset(out->conflict_steps,0,sizeof(out->conflict_steps));
    bool obs=variant!=CLO_PLAIN, prop=variant==CLO_FULL || variant==CLO_PROPAGATION;
    out->propagation_support=prop && s->evidence.propagation_transitions!=0;
    ds_mass_t current, channel;
    ds_vacuous(&current);
    double peak=0, sum=0;
    bool all_available=true;
    ds_rule_t rule=variant==CLO_PLAIN ? DS_DEMPSTER : c->conflict_rule;
    for (int i=0;i<CLO_CHANNELS;i++) {
        double strength=s->evidence.strength[i], r=1;
        peak=maximum(peak,strength); sum+=strength;
        all_available=all_available && s->evidence.available[i];
        clo_evidence_mass((unsigned int)i,strength,s->evidence.available[i],&channel);
        if (obs) {
            r=1;
            for (unsigned int b=1;b<DS_ATOMS;b++) if (clo_supported_subsets[i]&(1U<<b)) {
                double v=clo_reliability(clo_observability[i][b],c);
                if (v<r) r=v;
            }
        }
        /* Only upstream channel reliability gains from compatible downstream
         * onset. Never assign a downstream residual to an upstream singleton. */
        if (prop && (s->evidence.propagation_transitions & (63U<<(i*CLO_CHANNELS)))) r=unit(r*(1+c->propagation_bonus));
        s->evidence.reliability[i]=s->evidence.available[i]?r:0;
        ds_discount(&channel,s->evidence.reliability[i],&channel);
        combine(out,&current,&channel,rule,i);
    }
    /* Joint absence supports NORMAL only if every channel is available.
     * It is a single, dependent absence summary, not six independent normals. */
    ds_vacuous(&channel);
    channel.mass[CLO_NORMAL]=all_available ? .5*(1-peak) : 0;
    channel.mass[DS_THETA]=1-channel.mass[CLO_NORMAL];
    combine(out,&current,&channel,rule,CLO_CHANNELS);
    if (variant==CLO_FULL) {
        ds_discount(&s->fused,c->lambda_temporal,&channel);
        combine(out,&current,&channel,rule,CLO_CHANNELS+1);
    }
    s->fused=current;
    out->fault_belief=ds_belief(&current,CLO_ABNORMAL);
    out->ignorance_mass=current.mass[DS_THETA];
    if (variant==CLO_OR) out->fault_belief=peak;
    if (variant==CLO_WEIGHTED) out->fault_belief=sum/CLO_CHANNELS;
    double confirm=(variant==CLO_OR || variant==CLO_WEIGHTED)?.5:c->alarm_threshold_confirmed;
    unsigned int persistence=(variant==CLO_OR || variant==CLO_WEIGHTED)?1:c->confirmation_persistence;
    if (out->fault_belief>=confirm) {
        if (s->confirmation_count<persistence) s->confirmation_count++;
    } else s->confirmation_count=0;
    out->alarm=s->confirmation_count>=persistence;
    out->state=out->alarm?CLO_STATE_CONFIRMED:out->fault_belief>=c->alarm_threshold_suspect?CLO_STATE_SUSPECT:CLO_STATE_NORMAL;
    if (out->alarm && out->alarm_timestamp_ms<0) out->alarm_timestamp_ms=(int)o->time_ms;
    double scores[DS_ATOMS], best=-1, second=-1;
    unsigned int origin=0;
    ds_pignistic(&current,scores);
    for (unsigned int b=1;b<DS_ATOMS;b++) {
        if (scores[b]>best) { second=best; best=scores[b]; origin=1U<<b; }
        else if (scores[b]>second) second=scores[b];
    }
    out->origin_score=best; out->origin_margin=best-second;
    out->origin_belief=ds_belief(&current,origin); out->origin_plausibility=ds_plausibility(&current,origin);
    out->localization_valid=out->alarm && best>=c->localization_threshold &&
        best-second>=c->localization_margin_threshold && out->ignorance_mass<=c->ignorance_limit &&
        variant!=CLO_OR && variant!=CLO_WEIGHTED;
    out->estimated_origin=out->localization_valid?origin:0;
    if (out->localization_valid && out->localization_timestamp_ms<0) out->localization_timestamp_ms=(int)o->time_ms;
}
const char *clo_origin_name(unsigned int o)
{
    switch(o) { case CLO_NORMAL:return "NORMAL"; case CLO_MEMORY:return "MEMORY";
    case CLO_TIMING:return "TIMING"; case CLO_COMMUNICATION:return "COMMUNICATION";
    case CLO_SENSOR_CONTROL:return "SENSOR_CONTROL"; case CLO_ACTUATOR:return "ACTUATOR"; default:return "UNKNOWN"; }
}
const char *clo_state_name(clo_state_t s)
{
    return s==CLO_STATE_CONFIRMED?"CONFIRMED":s==CLO_STATE_SUSPECT?"SUSPECT":"NORMAL";
}
