#include "timing_safety_monitor.h"

void timing_safety_monitor_init(timing_monitor_status_t *s)
{
    *s = (timing_monitor_status_t){ .first_alarm_ms = -1, .first_violation_ms = -1 };
}

void timing_safety_monitor_step(timing_monitor_status_t *s,
    const runtime_timing_observation_t *o, timing_monitor_mode_t mode, timing_evidence_t evidence)
{
    if (!o->period_ms) return;
    s->deadline_evidence = o->deadline_exceeded;
    s->age_evidence = o->execution_age_ms > o->period_ms + o->relative_deadline_ms;
    s->missed_execution_evidence = o->missed_expected_execution;
    s->contract_violation = s->deadline_evidence || s->age_evidence || s->missed_execution_evidence;
    if (s->contract_violation) {
        if (s->first_violation_ms < 0) s->first_violation_ms = (int)o->time_ms;
        s->violation_samples++;
    }
    bool selected = (evidence != TIMING_EXECUTION_AGE_ONLY && s->deadline_evidence) ||
        (evidence != TIMING_DEADLINE_ONLY && (s->age_evidence || s->missed_execution_evidence));
    unsigned int kept = 0;
    for (unsigned int i = 0; i < s->violation_count; i++) {
        if (o->time_ms-s->violation_times[i] < 10U*o->period_ms)
            s->violation_times[kept++] = s->violation_times[i];
    }
    /* One observation per control period, no fabricated independent events. */
    if (selected && kept < 10U) s->violation_times[kept++] = o->time_ms;
    s->window_count = s->violation_count = kept;
    bool critical = evidence != TIMING_DEADLINE_ONLY && o->execution_age_ms >= 3U*o->period_ms;
    s->alarm = mode != TIMING_DISABLED && (selected || kept >= 3U || critical);
    s->severity = !s->alarm ? TIMING_NORMAL : critical ? TIMING_CRITICAL_ABSENCE :
        kept >= 3U ? TIMING_REPEATED : TIMING_TRANSIENT;
    if (s->alarm) {
        s->detected = true;
        s->alarm_samples++;
        if (s->first_alarm_ms < 0) s->first_alarm_ms = (int)o->time_ms;
    }
}
