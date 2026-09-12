#ifndef SCHEDULER_STRESS_H
#define SCHEDULER_STRESS_H
#include <stdbool.h>
#include <stdio.h>
#include "runtime_timing_observation.h"
#define STRESS_QUEUE_CAPACITY 4
/* Workload parameters belong to the scheduler, never to the timing monitor. */
typedef struct {
    bool enabled, overload;
    unsigned int seed, release_jitter_ms, start_jitter_ms, execution_ms;
    unsigned int stress_start_ms, stress_duration_ms, overload_execution_ms;
    unsigned int on_ms, off_ms;
    char events_path[512];
} scheduler_stress_config_t;
typedef struct {
    unsigned int nominal, available, start, completion, execution, jitter;
    bool started, deadline_counted;
} scheduler_job_t;
typedef struct {
    scheduler_job_t jobs[STRESS_QUEUE_CAPACITY];
    unsigned int count, rng, releases, completions, rejected, late_jobs, max_queue;
    int last_completion, first_violation, minimum_margin;
    unsigned int last_nominal, last_available, last_start, last_duration, last_jitter;
    bool deadline_latch, missed_latch;
    FILE *events;
} scheduler_stress_state_t;
struct ecu_state;
void scheduler_stress_init(struct ecu_state *state);
void scheduler_stress_tick(struct ecu_state *state);
void scheduler_stress_sample(struct ecu_state *state);
void scheduler_stress_close(struct ecu_state *state);
#endif
