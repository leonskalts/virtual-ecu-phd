#include "runtime_timing_observation.h"

void runtime_timing_init(runtime_timing_recorder_t *r, unsigned int period_ms)
{
    *r = (runtime_timing_recorder_t){ .cancelled_deadline_ms = -1,
        .observation = { .task_id = 1, .period_ms = period_ms,
            .relative_deadline_ms = period_ms, .current_release_ms = -1,
            .job_release_ms = -1, .actual_start_ms = -1, .actual_completion_ms = -1,
            .last_successful_execution_ms = -1 } };
}

void runtime_timing_release(runtime_timing_recorder_t *r, unsigned int now)
{
    runtime_timing_observation_t *o = &r->observation;
    if (!o->period_ms) return;
    o->time_ms = now;
    o->current_release_ms = (int)now;
    o->release_sequence++;
    o->missed_expected_execution = false;
    o->deadline_exceeded = r->cancelled_deadline_ms >= 0 && now >= (unsigned int)r->cancelled_deadline_ms;
    if (o->deadline_exceeded) r->cancelled_deadline_ms = -1;
}

void runtime_timing_admit(runtime_timing_recorder_t *r)
{
    runtime_timing_observation_t *o = &r->observation;
    if (!o->period_ms) return;
    o->job_outstanding = true;
    o->job_release_ms = o->current_release_ms;
    o->actual_start_ms = o->actual_completion_ms = -1;
}

void runtime_timing_cancel_release(runtime_timing_recorder_t *r, bool cancel_outstanding)
{
    runtime_timing_observation_t *o = &r->observation;
    if (!o->period_ms) return;
    /* One release each period and D=P: at most one newly cancelled deadline
     * awaits the next release boundary. Cancellation is a real dispatch event. */
    o->missed_expected_execution = true;
    o->cancelled_release_count++;
    r->cancelled_deadline_ms = o->current_release_ms + (int)o->relative_deadline_ms;
    if (cancel_outstanding) o->job_outstanding = false;
}

void runtime_timing_start(runtime_timing_recorder_t *r, unsigned int now)
{
    if (r->observation.period_ms) r->observation.actual_start_ms = (int)now;
}

void runtime_timing_complete(runtime_timing_recorder_t *r, unsigned int now)
{
    runtime_timing_observation_t *o = &r->observation;
    if (!o->period_ms) return;
    o->actual_completion_ms = o->last_successful_execution_ms = (int)now;
    o->execution_sequence++;
    o->job_outstanding = false;
}

void runtime_timing_observe(runtime_timing_recorder_t *r, unsigned int now)
{
    runtime_timing_observation_t *o = &r->observation;
    if (!o->period_ms) return;
    o->time_ms = now;
    o->execution_age_ms = o->last_successful_execution_ms < 0 ? now : now-(unsigned int)o->last_successful_execution_ms;
    /* Sample after completions: completing exactly at D meets the deadline. */
    if (o->job_release_ms >= 0) {
        unsigned int deadline = (unsigned int)o->job_release_ms + o->relative_deadline_ms;
        o->deadline_exceeded = o->deadline_exceeded ||
            (o->job_outstanding && now >= deadline) ||
            (o->actual_completion_ms == (int)now && now > deadline);
    }
}
