#include "ecu_types.h"
#include "scheduler_stress.h"
#include "control.h"
#include "config.h"
#include <stdlib.h>
#include <string.h>

static unsigned int random_bound(scheduler_stress_state_t *s, unsigned int maximum)
{
    s->rng = 1664525U*s->rng + 1013904223U;
    return maximum ? s->rng % (maximum+1U) : 0U;
}

void scheduler_stress_init(ecu_state_t *state)
{
    scheduler_stress_state_t *s = &state->scheduler_stress;
    *s = (scheduler_stress_state_t){ .rng=state->scheduler_stress_config.seed,
        .last_completion=-1, .first_violation=-1, .minimum_margin=100 };
    if (state->scheduler_stress_config.enabled && state->scheduler_stress_config.events_path[0]) {
        s->events = fopen(state->scheduler_stress_config.events_path,"w");
        if (!s->events) { perror("scheduler events"); exit(EXIT_FAILURE); }
        fputs("nominal_release_ms,actual_release_ms,actual_start_ms,completion_ms,deadline_ms,release_jitter_ms,execution_duration_ms,contract_margin_ms,contract_violated,rejected\n",s->events);
    }
}

static void complete_job(ecu_state_t *state, unsigned int now)
{
    scheduler_stress_state_t *s=&state->scheduler_stress;
    scheduler_job_t *j=&s->jobs[0];
    control_step(state); /* Real computation; simulated CPU occupancy ends now. */
    s->completions++; s->last_completion=(int)now;
    s->last_nominal=j->nominal; s->last_available=j->available;
    s->last_start=j->start; s->last_duration=j->execution; s->last_jitter=j->jitter;
    int margin=(int)(j->nominal+ECU_CONTROL_PERIOD_MS)-(int)now;
    if (margin<s->minimum_margin) s->minimum_margin=margin;
    if (s->events) fprintf(s->events,"%u,%u,%u,%u,%u,%u,%u,%d,%d,0\n",
        j->nominal,j->available,j->start,now,j->nominal+ECU_CONTROL_PERIOD_MS,j->jitter,j->execution,margin,margin<0);
    s->count--;
    memmove(s->jobs,s->jobs+1,s->count*sizeof(s->jobs[0]));
}

static void service(ecu_state_t *state, unsigned int now)
{
    scheduler_stress_state_t *s=&state->scheduler_stress;
    while (s->count) {
        scheduler_job_t *j=&s->jobs[0];
        if (!j->started && now>=j->start) {
            j->started=true; j->start=now; j->completion=now+j->execution;
        }
        if (!j->started || j->completion>now) break;
        complete_job(state,now);
    }
}

void scheduler_stress_tick(ecu_state_t *state)
{
    scheduler_stress_state_t *s=&state->scheduler_stress;
    const scheduler_stress_config_t *c=&state->scheduler_stress_config;
    unsigned int now=state->time.time_ms;
    service(state,now); /* Completing at the deadline precedes deadline checking. */
    if (now%ECU_CONTROL_PERIOD_MS==0) {
        s->releases++;
        unsigned int jitter=random_bound(s,c->release_jitter_ms);
        unsigned int start_jitter=random_bound(s,c->start_jitter_ms);
        bool overload=c->overload && now>=c->stress_start_ms && now-c->stress_start_ms<c->stress_duration_ms &&
            (!c->on_ms || (now-c->stress_start_ms)%(c->on_ms+c->off_ms)<c->on_ms);
        if (s->count==STRESS_QUEUE_CAPACITY) {
            s->rejected++; s->missed_latch=true;
            if (s->first_violation<0) s->first_violation=(int)now;
            if (s->events) fprintf(s->events,"%u,,,,%u,,,,1,1\n",now,now+ECU_CONTROL_PERIOD_MS);
        } else {
            s->jobs[s->count++]=(scheduler_job_t){ .nominal=now,.available=now+jitter,
                .start=now+jitter+start_jitter,.jitter=jitter,
                .execution=overload ? c->overload_execution_ms : c->execution_ms };
            if (s->count>s->max_queue) s->max_queue=s->count;
        }
        service(state,now);
    }
    for (unsigned int i=0;i<s->count;i++) {
        scheduler_job_t *j=&s->jobs[i];
        if (now>=j->nominal+ECU_CONTROL_PERIOD_MS) {
            s->deadline_latch=true;
            if (!j->deadline_counted) { j->deadline_counted=true; s->late_jobs++; }
            if (s->first_violation<0) s->first_violation=(int)now;
        }
    }
}

void scheduler_stress_sample(ecu_state_t *state)
{
    scheduler_stress_state_t *s=&state->scheduler_stress;
    runtime_timing_observation_t *o=&state->timing_recorder.observation;
    unsigned int now=state->time.time_ms;
    o->time_ms=now; o->current_release_ms=(int)(now-now%ECU_CONTROL_PERIOD_MS);
    o->release_sequence=s->releases; o->execution_sequence=s->completions;
    o->last_successful_execution_ms=s->last_completion;
    o->execution_age_ms=s->last_completion<0 ? now : now-(unsigned int)s->last_completion;
    o->job_outstanding=s->count>0;
    o->job_release_ms=s->count ? (int)s->jobs[0].nominal : (int)s->last_nominal;
    o->actual_start_ms=s->count ? (s->jobs[0].started ? (int)s->jobs[0].start : -1) : (int)s->last_start;
    o->actual_completion_ms=s->count ? -1 : s->last_completion;
    o->cancelled_release_count=s->rejected;
    o->deadline_exceeded=s->deadline_latch; o->missed_expected_execution=s->missed_latch;
    s->deadline_latch=s->missed_latch=false;
}

void scheduler_stress_close(ecu_state_t *state)
{
    if (state->scheduler_stress.events) fclose(state->scheduler_stress.events);
    state->scheduler_stress.events=NULL;
}
