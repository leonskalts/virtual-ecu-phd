#include "hazard_model.h"
#include "ecu_types.h"
#include "cross_layer_fault.h"
#include <math.h>
#include <string.h>

void hazard_config_default(hazard_config_t *c)
{
    *c = (hazard_config_t){ .warning_threshold_c = ECU_WARN_COOLANT_TEMP_C,
        .critical_threshold_c = ECU_CRITICAL_COOLANT_TEMP_C,
        .max_critical_exposure_ms = 1000U, .fault_tolerant_time_interval_ms = 5000U,
        .recovery_hold_ms = 1000U };
}
void hazard_model_init(hazard_status_t *s)
{
    *s = (hazard_status_t){ .critical_entry_ms = -1, .hazard_entry_ms = -1,
        .hazard_exit_ms = -1, .previous_time_ms = -1, .safe_candidate_ms = -1,
        .containment_ms = -1, .containment_success = -1, .ftti_met = -1,
        .max_propagation_stage = -1 };
}

static bool effects_resolved(const runtime_observation_t *o, const experiment_ground_truth_t *t)
{
    const runtime_observation_t *r = &t->reference_observation;
    return !t->fault_active && fabsf(t->coolant_true_c-t->reference_coolant_true_c) < 0.01f &&
        fabsf(o->control_target_c-r->control_target_c) < 0.000001f &&
        fabsf(o->pump_command-r->pump_command) < 0.000001f &&
        fabsf(o->fan_command-r->fan_command) < 0.000001f &&
        fabsf(o->pump_actual-r->pump_actual) < 0.000001f &&
        fabsf(o->fan_actual-r->fan_actual) < 0.000001f &&
        fabsf(o->coolant_measured_c-r->coolant_measured_c) < 0.01f &&
        o->sample_timestamp_ms == r->sample_timestamp_ms &&
        o->control_execution_ms == r->control_execution_ms;
}

static void path_append(char *path, size_t size, const char *stage)
{
    size_t used = strlen(path);
    snprintf(path+used,size-used,"%s%s",used ? ">" : "",stage);
}

void hazard_model_step(const hazard_config_t *c, hazard_status_t *s,
    const runtime_observation_t *o, const experiment_ground_truth_t *t)
{
    if (!c->enabled) return;
    const propagation_monitor_t *p = &t->propagation;
    int now = (int)o->time_ms;
    unsigned int dt = s->previous_time_ms < 0 ? 0U : (unsigned int)(now-s->previous_time_ms);
    bool critical = t->coolant_true_c >= c->critical_threshold_c;
    if (s->previous_critical) s->critical_exposure_ms += dt;
    s->warning_active = t->coolant_true_c >= c->warning_threshold_c;
    if (critical && !s->previous_critical) s->critical_entry_ms = now;
    s->critical_entered = s->critical_entered || critical;
    s->consecutive_critical_ms = critical ? (unsigned int)(now-s->critical_entry_ms) : 0U;
    bool hazard = critical && s->consecutive_critical_ms >= c->max_critical_exposure_ms;
    if (hazard && !s->hazard_entered) s->hazard_entry_ms = now;
    if (s->hazard_active && !hazard && s->hazard_exit_ms < 0) s->hazard_exit_ms = now;
    s->hazard_entered = s->hazard_entered || hazard;
    s->hazard_active = hazard;
    s->critical_active = critical;
    s->previous_critical = critical;
    s->previous_time_ms = now;
    if (p->injection_ms < 0) {
        s->preexisting_hazard = s->hazard_entered;
        return;
    }
    /* The plant sample at the injection tick predates the new fault's physical
     * effect. A hazard already present at that boundary is pre-existing too. */
    if (s->hazard_entry_ms >= 0 && s->hazard_entry_ms <= p->injection_ms)
        s->preexisting_hazard = true;
    bool affected = p->internal_ms >= 0 || p->control_ms >= 0 ||
        p->actuator_command_ms >= 0 || p->actuator_realization_ms >= 0 || p->plant_ms >= 0;
    bool applicable = affected && !s->preexisting_hazard;
    bool stable = applicable && t->coolant_true_c < c->warning_threshold_c &&
        (o->safety_state > 0 || effects_resolved(o,t));
    if (stable) {
        if (s->safe_candidate_ms < 0) s->safe_candidate_ms = now;
        if ((unsigned int)(now-s->safe_candidate_ms) >= c->recovery_hold_ms && s->containment_ms < 0)
            s->containment_ms = now;
    } else {
        s->safe_candidate_ms = s->containment_ms = -1;
    }
    if (applicable) {
        s->containment_success = s->containment_ms >= 0 && !s->hazard_entered;
        if (s->hazard_entered) s->ftti_met = 0;
        else if (s->containment_ms >= 0)
            s->ftti_met = (unsigned int)(s->containment_ms-p->injection_ms) <= c->fault_tolerant_time_interval_ms;
        else s->ftti_met = (unsigned int)(now-p->injection_ms) >= c->fault_tolerant_time_interval_ms ? 0 : -1;
    }
    s->recovery_seen = s->recovery_seen || s->containment_success == 1;
    s->max_propagation_stage = 0;
    s->propagation_path_signature[0] = '\0';
    path_append(s->propagation_path_signature,sizeof(s->propagation_path_signature),cross_layer_layer_name(t->fault.layer));
    if (p->internal_ms >= 0) {
        s->max_propagation_stage = 1;
        path_append(s->propagation_path_signature,sizeof(s->propagation_path_signature),
            t->fault.layer == FAULT_LAYER_COMMUNICATION ? "sensing" : "internal");
    }
    if (p->control_ms >= 0) {
        s->max_propagation_stage = 2;
        path_append(s->propagation_path_signature,sizeof(s->propagation_path_signature),"control");
    }
    if (p->actuator_command_ms >= 0 || p->actuator_realization_ms >= 0) {
        s->max_propagation_stage = 3;
        path_append(s->propagation_path_signature,sizeof(s->propagation_path_signature),"actuator");
    }
    if (p->plant_ms >= 0) {
        s->max_propagation_stage = 4;
        path_append(s->propagation_path_signature,sizeof(s->propagation_path_signature),"plant");
    }
    if (s->hazard_entered && !s->preexisting_hazard) {
        s->max_propagation_stage = 5;
        path_append(s->propagation_path_signature,sizeof(s->propagation_path_signature),"hazard");
    }
    if (p->safety_response_ms >= 0 || s->recovery_seen) {
        s->max_propagation_stage = 6;
        path_append(s->propagation_path_signature,sizeof(s->propagation_path_signature),
            p->safety_response_ms >= 0 ? "safety" : "recovery");
    }
}

static void optional_int(FILE *stream, int value)
{
    fputc(',',stream); if (value >= 0) fprintf(stream,"%d",value);
}
void hazard_csv_header(FILE *stream)
{
    fputs(",hazard_monitor_enabled,hazard_warning_threshold_c,hazard_critical_threshold_c,"
        "max_critical_exposure_ms,fault_tolerant_time_interval_ms,containment_hold_ms,"
        "hazard_warning_active,critical_threshold_entered,critical_active,hazard_active,hazard_entered,"
        "hazard_entry_ms,hazard_exit_ms,critical_exposure_time_ms,consecutive_critical_exposure_ms,"
        "detected_before_hazard,safe_state_before_hazard,containment_time_ms,containment_latency_ms,"
        "ftti_met,max_propagation_stage,propagation_path_signature,preexisting_hazard",stream);
}
void hazard_csv_row(FILE *stream, const ecu_state_t *state)
{
    const hazard_config_t *c = &state->hazard_config;
    const hazard_status_t *s = &state->hazard;
    const propagation_monitor_t *p = &state->propagation;
    fprintf(stream,",%d",c->enabled);
    if (!c->enabled) { for (unsigned int i=0;i<22;i++) fputc(',',stream); return; }
    fprintf(stream,",%.3f,%.3f,%u,%u,%u,%d,%d,%d,%d,%d",c->warning_threshold_c,
        c->critical_threshold_c,c->max_critical_exposure_ms,c->fault_tolerant_time_interval_ms,
        c->recovery_hold_ms,s->warning_active,s->critical_entered,s->critical_active,s->hazard_active,s->hazard_entered);
    optional_int(stream,s->hazard_entry_ms); optional_int(stream,s->hazard_exit_ms);
    fprintf(stream,",%u,%u",s->critical_exposure_ms,s->consecutive_critical_ms);
    optional_int(stream,p->injection_ms >= 0 && s->hazard_entry_ms >= 0 && !s->preexisting_hazard ?
        p->detector_ms >= 0 && p->detector_ms < s->hazard_entry_ms : -1);
    optional_int(stream,p->injection_ms >= 0 && s->hazard_entry_ms >= 0 && !s->preexisting_hazard ?
        p->safe_state_ms >= 0 && p->safe_state_ms < s->hazard_entry_ms : -1);
    optional_int(stream,s->containment_ms);
    optional_int(stream,s->containment_ms >= 0 && p->injection_ms >= 0 ? s->containment_ms-p->injection_ms : -1);
    optional_int(stream,s->ftti_met); optional_int(stream,s->max_propagation_stage);
    fprintf(stream,",%s,%d",s->propagation_path_signature,s->preexisting_hazard);
}
