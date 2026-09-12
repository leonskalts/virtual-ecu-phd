#ifndef TIMING_SAFETY_MONITOR_H
#define TIMING_SAFETY_MONITOR_H
#include "runtime_timing_observation.h"

typedef enum { TIMING_DISABLED, TIMING_OBSERVE_ONLY, TIMING_PROTECTIVE_ACTION } timing_monitor_mode_t;
typedef enum { TIMING_DEADLINE_ONLY, TIMING_EXECUTION_AGE_ONLY, TIMING_COMBINED } timing_evidence_t;
typedef enum { TIMING_NORMAL, TIMING_TRANSIENT, TIMING_REPEATED, TIMING_CRITICAL_ABSENCE } timing_severity_t;
typedef struct {
    bool alarm, detected, contract_violation, deadline_evidence, age_evidence, missed_execution_evidence;
    timing_severity_t severity;
    unsigned int window_count, alarm_samples, violation_samples;
    int first_alarm_ms, first_violation_ms;
    unsigned int violation_times[10], violation_count;
} timing_monitor_status_t;

void timing_safety_monitor_init(timing_monitor_status_t *s);
void timing_safety_monitor_step(timing_monitor_status_t *s,
    const runtime_timing_observation_t *o, timing_monitor_mode_t mode, timing_evidence_t evidence);
#endif
