#ifndef RUNTIME_TIMING_OBSERVATION_H
#define RUNTIME_TIMING_OBSERVATION_H
#include <stdbool.h>

/* Scheduler-owned event ledger. No injection or evaluation metadata. */
typedef struct {
    unsigned int task_id, time_ms, period_ms, relative_deadline_ms;
    unsigned int release_sequence, execution_sequence;
    int current_release_ms, job_release_ms, actual_start_ms, actual_completion_ms;
    int last_successful_execution_ms;
    unsigned int execution_age_ms;
    bool job_outstanding, missed_expected_execution, deadline_exceeded;
    unsigned int cancelled_release_count;
} runtime_timing_observation_t;

typedef struct {
    runtime_timing_observation_t observation;
    int cancelled_deadline_ms;
} runtime_timing_recorder_t;

void runtime_timing_init(runtime_timing_recorder_t *r, unsigned int period_ms);
void runtime_timing_release(runtime_timing_recorder_t *r, unsigned int now);
void runtime_timing_admit(runtime_timing_recorder_t *r);
void runtime_timing_cancel_release(runtime_timing_recorder_t *r, bool cancel_outstanding);
void runtime_timing_start(runtime_timing_recorder_t *r, unsigned int now);
void runtime_timing_complete(runtime_timing_recorder_t *r, unsigned int now);
void runtime_timing_observe(runtime_timing_recorder_t *r, unsigned int now);
#endif
