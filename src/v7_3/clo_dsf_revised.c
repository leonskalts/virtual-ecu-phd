#include "clo_dsf_revised.h"
#include "config.h"
#include <math.h>

/* Contract: actuators_step realizes clamp(command) synchronously before this
 * scheduler's detector call. Adjacent representable floats are conservatively
 * accepted, avoiding a fitted physical tolerance. This is a virtual-ECU
 * contract, not an assumed physical actuator model or a calibrated probability.
 * Non-finite or off-cadence observations contribute no actuator evidence. */
static bool outside_response_contract(float command, float actual)
{
    const float expected = fminf(1.0f, fmaxf(0.0f, command));
    return actual < nextafterf(expected, -INFINITY) ||
           actual > nextafterf(expected, INFINITY);
}
void clo_revised_extract(clo_evidence_t *e, const runtime_observation_t *o)
{
    c2_extract(e, o);
    /* This synchronous ECU acquires before executing control. When both events
     * occur now, consuming an older delivered sample violates that ordering,
     * even if a generic freshness timeout has not expired. No age threshold is
     * reduced: this compares observed production/consumption provenance. */
    if(o->source_valid && o->source_ms==o->time_ms &&
       o->control_execution_ms==(int)o->time_ms && e->available[1] &&
       o->sample_timestamp_ms<o->source_ms)e->strength[1]=1.0;
    e->available[2] = o->target_shadow_valid;
    e->strength[2] = e->available[2] &&
        (o->target_register_c != o->target_shadow_c ||
         (o->control_execution_ms == (int)o->time_ms &&
          (!isfinite(o->control_target_c) || o->control_target_c != (float)o->target_shadow_c))) ? 1.0 : 0.0;
    e->available[4] = e->available[4] && o->time_ms % ECU_ACTUATOR_PERIOD_MS == 0;
    e->strength[4] = e->available[4] &&
        (outside_response_contract(o->pump_command, o->pump_actual) ||
         outside_response_contract(o->fan_command, o->fan_actual)) ? 1.0 : 0.0;
}

/* Independent acquisition plausibility uses the existing physical envelope.
 * Absence of local evidence does not prove a communication origin. */
static double local_sensor_strength(const runtime_observation_t *o)
{
    if (!o->source_valid || o->source_ms != o->time_ms || !isfinite(o->source_c)) return 0;
    double strength = o->source_c < ECU_SENSOR_IMPLAUSIBLE_LOW_C ||
                      o->source_c > ECU_SENSOR_IMPLAUSIBLE_HIGH_C ? 1.0 : 0.0;
    if (o->source_previous_valid && isfinite(o->source_previous_c) &&
        o->source_previous_ms < o->source_ms) {
        double dt = (o->source_ms - o->source_previous_ms) / 1000.0;
        double residual = (fabs(o->source_c - o->source_previous_c) - 2.5 * dt) / 2.0;
        strength = fmax(strength, fmin(1.0, fmax(0.0, residual)));
    }
    return strength;
}

#include <string.h>
static double unit(double x) { return x<0?0:x>1?1:x; }
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
void clo_revised_init(clo_revised_t *s)
{
    memset(s,0,sizeof(*s));
    clo_final_init(&s->fusion);
}
void clo_revised_step(clo_revised_t *state,const clo_final_config_t *c,const runtime_observation_t *o)
{
    clo_final_t *s=&state->fusion;
    if(s->has_previous_time && o->time_ms<=s->previous_time_ms)return;
    s->has_previous_time=true;s->previous_time_ms=o->time_ms;
    clo_revised_extract(&s->evidence,o);
    double local = local_sensor_strength(o);
    /* A minimal two-edge total-variation residual catches weak alternating
     * pulses that a discounted one-step residual forgets between excursions.
     * Reuse the same physical slew envelope and 2 C normalization. Only adjacent
     * opposing excesses are added, never same-direction thermal excursions or
     * missing/gapped samples. This replaces one feature; it is not a second DS
     * source and is not recursively accumulated. */
    bool valid=o->source_valid && o->source_previous_valid &&
        o->source_ms==o->time_ms && o->source_previous_ms<o->source_ms &&
        isfinite(o->source_c) && isfinite(o->source_previous_c);
    double excess=0;int direction=0;
    if(valid) {
        double delta=(double)o->source_c-o->source_previous_c;
        double dt=(o->source_ms-o->source_previous_ms)/1000.0;
        excess=fmax(0.0,(fabs(delta)-2.5*dt)/2.0);
        direction=delta>0?1:delta<0?-1:0;
        if(excess>0 && state->previous_local_excess>0 && state->previous_local_valid &&
           state->previous_local_ms==o->source_previous_ms &&
           direction==-state->previous_local_direction)
            local=fmax(local,fmin(1.0,excess+state->previous_local_excess));
    }
    state->previous_local_valid=valid;
    state->previous_local_excess=excess;
    state->previous_local_direction=direction;
    state->previous_local_ms=o->source_ms;
    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);
    s->evidence.available[3] = s->evidence.available[3] || local > 0;
    /* Establish precedence only from a directly observed contract violation,
     * never from the leading BetP guess. Same-tick competing observations do
     * not establish a causal order. Weak local residuals cannot reserve origin. */
    /* Zero command/response is not a recovery witness for a stuck actuator.
     * Retain provenance until that same component successfully responds to a
     * positive command. This records a contract, not an indefinitely fixed label. */
    bool actuator_recovered=true;
    if(s->evidence.available[4]) {
        const float command[2]={o->pump_command,o->fan_command};
        const float actual[2]={o->pump_actual,o->fan_actual};
        for(unsigned int i=0;i<2;i++) {
            if(outside_response_contract(command[i],actual[i]))state->actuator_unresolved|=1U<<i;
            if((state->actuator_unresolved&(1U<<i)) &&
               (command[i]<=0 || outside_response_contract(command[i],actual[i])))actuator_recovered=false;
        }
    }
    else if(state->actuator_unresolved)actuator_recovered=false;
    /* A quiet, clipped/sub-ambient cooling excursion is not thermal recovery.
     * This passive coolant circuit has no refrigeration. Cold starts can be
     * below current ambient, so this only delays re-arming an existing actuator
     * episode; it never creates an alarm or assigns an origin. Missing trusted
     * acquisition/ambient evidence likewise cannot certify recovery. */
    if(state->actuator_unresolved &&
       (!o->source_valid || o->source_ms!=o->time_ms || !isfinite(o->source_c) ||
        !isfinite(o->ambient_c) || o->source_c<o->ambient_c))actuator_recovered=false;
    unsigned int direct=0, direct_count=0;
    for(int i=0;i<CLO_CHANNELS;i++)
        if(i!=3 && i!=5 && s->evidence.available[i] &&
           s->evidence.strength[i]>=c->confirmed_threshold)
            { direct |= c2_origin_support[i]; direct_count++; }
    if(direct && !state->direct_origins) {
        state->direct_origins=direct;
        state->direct_onset_ms=o->time_ms;
        if(direct_count>1 || (local>=c->confirmed_threshold && !state->sensor_established_first))
            state->ambiguous_onset=true;
    }
    const bool downstream_sensor=state->direct_origins &&
        !state->sensor_established_first && o->time_ms>state->direct_onset_ms;
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
        double rd=s->evidence.available[i]?c->r_detection:0;
        /* Detection never reads origin mass, its discount, or propagation. */
        support(&channel,C2_D_ABNORMAL,strength);
        ds_discount(&channel,rd,&channel);
        if(!combine(&detect,&channel,&v->detection_conflict_steps[i],&v->detection_conflict))v->detection_fallback=true;
        /* One source mass per channel: do not count delivered and local
         * observations twice. Singleton support never exceeds local evidence. */
        unsigned int subset = c2_origin_support[i];
        double origin_strength = strength;
        if (i == 3 && local > 0) { subset = c2_origin_blocks[3]; origin_strength = local; }
        /* Suppress contamination only in localization. Detection above still
         * receives the entire measured anomaly. No propagation bonus/locking. */
        if(i==3 && downstream_sensor)origin_strength=0;
        support(&channel,subset,origin_strength);
        if(!combine(&origin,&channel,&v->localization_conflict_steps[i],&v->localization_conflict))v->localization_fallback=true;
    }
    { /* Temporal fusion is always part of the final algorithm. */
        ds_discount(&s->detection_mass,c->lambda_temporal,&channel);
        if(!combine(&detect,&channel,&v->detection_conflict_steps[6],&v->detection_conflict))v->detection_fallback=true;
        ds_discount(&s->origin_mass,c->lambda_temporal,&channel);
        if(!combine(&origin,&channel,&v->localization_conflict_steps[6],&v->localization_conflict))v->localization_fallback=true;
    }
    s->detection_mass=detect;s->origin_mass=origin;
    v->anomaly_belief=ds_belief(&detect,C2_D_ABNORMAL);
    v->anomaly_plausibility=ds_plausibility(&detect,C2_D_ABNORMAL);
    v->anomaly_decision_score=v->anomaly_belief;v->anomaly_ignorance=detect.mass[DS_THETA];
    if(v->anomaly_decision_score>=c->confirmed_threshold) {
        if(s->confirmation_count<c->confirmation_persistence)s->confirmation_count++;
    } else s->confirmation_count=0;
    v->alarm=s->confirmation_count>=c->confirmation_persistence;
    v->state=v->alarm?CLO_STATE_CONFIRMED:v->anomaly_decision_score>=c->suspect_threshold?CLO_STATE_SUSPECT:CLO_STATE_NORMAL;
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
    v->localization_valid=v->alarm && best>=c->localization_threshold &&
        v->origin_margin>=c->localization_margin_threshold && v->origin_ignorance<=c->ignorance_limit;
    if(state->ambiguous_onset)v->localization_valid=false;
    v->estimated_origin=v->localization_valid?v->leading_origin:0;
    if(!state->direct_origins && local>0 && v->localization_valid &&
       v->estimated_origin==CLO_SENSOR_CONTROL)state->sensor_established_first=true;
    /* Quiet recovery closes the episode. A subsequent unrelated sensor event
     * can establish its own origin. Earlier mass still decays normally to UNKNOWN. */
    bool evidence_quiet=true;
    for(int i=0;i<CLO_CHANNELS;i++)
        if(s->evidence.available[i] && s->evidence.strength[i]>0)evidence_quiet=false;
    if(v->state==CLO_STATE_NORMAL && evidence_quiet && actuator_recovered) {
        state->actuator_unresolved=0;
        state->direct_origins=0;
        state->direct_onset_ms=0;
        state->sensor_established_first=false;
        state->ambiguous_onset=false;
    }
    if(v->localization_valid && v->localization_timestamp_ms<0)v->localization_timestamp_ms=(int)o->time_ms;
}
