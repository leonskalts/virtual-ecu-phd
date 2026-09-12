#include "safety_policy_v5.h"

void safety_policy_v5_step(runtime_safety_status_t *s, safety_policy_v5_state_t *v,
    const runtime_safety_config_t *c, safety_policy_v5_mode_t mode,
    const runtime_observation_t *o, const timing_monitor_status_t *timing)
{
    if (mode != V5_GRADED) {
        runtime_safety_policy_step(s,c,o,timing);
        return;
    }
    int now = (int)o->time_ms;
    if (o->detector_alarm && s->first_existing_alarm_ms < 0) s->first_existing_alarm_ms = now;
    s->communication_alarm = o->detector_alarm && !o->sample_freshness_ok;
    if (s->communication_alarm && s->first_communication_alarm_ms < 0) s->first_communication_alarm_ms = now;
    if (!s->communication_alarm) v->communication_streak_start_ms = -1;
    else if (v->communication_streak_start_ms < 0) v->communication_streak_start_ms = now;
    s->communication_request = c->communication_protective_action && s->communication_alarm;
    s->timing_request = c->timing_mode == TIMING_PROTECTIVE_ACTION && timing->alarm && timing->severity >= TIMING_REPEATED;
    bool prolonged_communication = s->communication_request &&
        now-v->communication_streak_start_ms >= (int)(5U*o->timing.period_ms);
    bool prolonged_absence = s->timing_request && o->timing.execution_age_ms >= 5U*o->timing.period_ms;
    s->requested_state = prolonged_communication || prolonged_absence ? 2 : s->timing_request || s->communication_request ? 1 : 0;
    s->action_applied = false;
    if (s->communication_request && s->first_communication_request_ms < 0) s->first_communication_request_ms = now;
    if (s->timing_request && s->first_timing_request_ms < 0) s->first_timing_request_ms = now;
    if (s->requested_state) {
        s->request_samples++;
        if (s->first_request_ms < 0) s->first_request_ms = now;
    }
}
