/* Exact additive copy of Candidate 1's private runtime evidence extraction and
 * episode graph. Candidate 1 remains byte-identical; equivalence is tested.
 * No new measurements or thresholds are introduced for Candidate 2. */
#include "clo_dsf_candidate2.h"
#include "config.h"
#include <math.h>
#include <string.h>
static double unit(double x) { return x<0?0:x>1?1:x; }
static double maximum(double a,double b) { return a>b?a:b; }
void c2_extract(clo_evidence_t *e, const runtime_observation_t *o)
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
void c2_propagation(clo_evidence_t *e, const clo_config_t *c, unsigned int now)
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
