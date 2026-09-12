#include "runtime_safety_policy.h"

void runtime_safety_policy_init(runtime_safety_status_t *s)
{
    *s = (runtime_safety_status_t){ .first_communication_alarm_ms = -1,
        .first_existing_alarm_ms = -1, .first_timing_request_ms = -1,
        .first_communication_request_ms = -1, .first_request_ms = -1, .first_action_ms = -1 };
}

void runtime_safety_policy_step(runtime_safety_status_t *s, const runtime_safety_config_t *c,
    const runtime_observation_t *o, const timing_monitor_status_t *timing)
{
    if (!c->enabled) return;
    int now = (int)o->time_ms;
    if (o->detector_alarm && s->first_existing_alarm_ms < 0) s->first_existing_alarm_ms = now;
    /* Reuse two existing runtime outputs; no new freshness threshold/detector. */
    s->communication_alarm = o->detector_alarm && !o->sample_freshness_ok;
    if (s->communication_alarm && s->first_communication_alarm_ms < 0) s->first_communication_alarm_ms = now;
    s->timing_request = c->timing_mode == TIMING_PROTECTIVE_ACTION && timing->alarm && timing->severity >= TIMING_REPEATED;
    s->communication_request = c->communication_protective_action && s->communication_alarm;
    /* Existing safety state codes: precautionary cooling=1, limp-home=2.
     * Isolated single timing anomalies are observed, without intervention. */
    s->requested_state = s->communication_request || (s->timing_request && timing->severity == TIMING_CRITICAL_ABSENCE) ? 2 : s->timing_request ? 1 : 0;
    s->action_applied = false;
    if (s->timing_request && s->first_timing_request_ms < 0) s->first_timing_request_ms = now;
    if (s->communication_request && s->first_communication_request_ms < 0) s->first_communication_request_ms = now;
    if (s->requested_state) {
        s->request_samples++;
        if (s->first_request_ms < 0) s->first_request_ms = now;
    }
}
