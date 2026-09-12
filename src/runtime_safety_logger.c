#include "ecu_types.h"
#include "runtime_safety_policy.h"

void runtime_safety_csv_header(ecu_state_t *state)
{
    if (!state->runtime_safety_config.enabled) return;
    fputs(",runtime_safety_enabled,timing_monitor_mode,timing_evidence_mode,communication_safety_response,"
        "trusted_task_id,trusted_period_ms,trusted_relative_deadline_ms,trusted_release_sequence,"
        "trusted_current_release_ms,trusted_job_release_ms,trusted_actual_start_ms,trusted_actual_completion_ms,"
        "trusted_last_successful_execution_ms,trusted_execution_sequence,trusted_execution_age_ms,"
        "trusted_job_outstanding,trusted_missed_expected_execution,trusted_deadline_exceeded,trusted_cancelled_releases,"
        "timing_contract_violation,timing_first_violation_ms,timing_violation_samples,"
        "timing_monitor_alarm,timing_monitor_detected,timing_monitor_first_alarm_ms,timing_monitor_severity,"
        "timing_window_violations,timing_deadline_evidence,timing_age_evidence,timing_missed_execution_evidence,"
        "existing_detector_first_alarm_ms,communication_runtime_alarm,communication_first_alarm_ms,"
        "timing_action_requested,communication_action_requested,runtime_safety_requested_state,"
        "timing_first_request_ms,communication_first_request_ms,runtime_safety_first_request_ms,"
        "runtime_safety_action_applied,runtime_safety_first_action_ms,runtime_safety_request_samples,runtime_safety_action_samples",state->log_file);
}

static void optional_time(FILE *stream, int time)
{
    fputc(',',stream);
    if (time >= 0) fprintf(stream,"%d",time);
}

void runtime_safety_csv_row(const ecu_state_t *state)
{
    const runtime_safety_config_t *c = &state->runtime_safety_config;
    if (!c->enabled) return;
    const runtime_timing_observation_t *o = &state->timing_recorder.observation;
    const timing_monitor_status_t *t = &state->timing_monitor;
    const runtime_safety_status_t *s = &state->runtime_safety;
    FILE *f = state->log_file;
    static const char *modes[] = {"disabled","observe_only","protective_action"};
    static const char *evidence[] = {"deadline_only","execution_age_only","combined"};
    static const char *severity[] = {"normal","single_transient","repeated","critical_execution_absence"};
    fprintf(f,",1,%s,%s,%s,%u,%u,%u,%u",modes[c->timing_mode],evidence[c->timing_evidence],
        c->communication_protective_action ? "protective_action" : "observe_only",
        o->task_id,o->period_ms,o->relative_deadline_ms,o->release_sequence);
    optional_time(f,o->current_release_ms); optional_time(f,o->job_release_ms);
    optional_time(f,o->actual_start_ms); optional_time(f,o->actual_completion_ms);
    optional_time(f,o->last_successful_execution_ms);
    fprintf(f,",%u,%u,%d,%d,%d,%u,%d",o->execution_sequence,o->execution_age_ms,
        o->job_outstanding,o->missed_expected_execution,o->deadline_exceeded,o->cancelled_release_count,t->contract_violation);
    optional_time(f,t->first_violation_ms);
    fprintf(f,",%u,%d,%d",t->violation_samples,t->alarm,t->detected);
    optional_time(f,t->first_alarm_ms);
    fprintf(f,",%s,%u,%d,%d,%d",severity[t->severity],t->window_count,t->deadline_evidence,t->age_evidence,t->missed_execution_evidence);
    optional_time(f,s->first_existing_alarm_ms);
    fprintf(f,",%d",s->communication_alarm); optional_time(f,s->first_communication_alarm_ms);
    fprintf(f,",%d,%d,%d",s->timing_request,s->communication_request,s->requested_state);
    optional_time(f,s->first_timing_request_ms); optional_time(f,s->first_communication_request_ms);
    optional_time(f,s->first_request_ms); fprintf(f,",%d",s->action_applied); optional_time(f,s->first_action_ms);
    fprintf(f,",%u,%u",s->request_samples,s->action_samples);
}
