#include "cross_layer_fault.h"
#include <string.h>

void cross_layer_csv_header(FILE *stream)
{
    fputs(",cross_layer_fault_enabled,cross_layer_fault_id,cross_layer_fault_layer,"
        "cross_layer_fault_model,cross_layer_fault_behavior,cross_layer_fault_target,"
        "cross_layer_fault_start_ms,cross_layer_fault_duration_ms,experiment_seed,"
        "fault_injection_active,memory_original_value,memory_corrupted_value,memory_bit_index,"
        "control_task_deadline_miss,control_task_execution_skipped,control_task_delay_ms,"
        "control_task_expected_execution_ms,control_task_actual_execution_ms,"
        "control_task_recovery,control_task_last_execution_ms", stream);
}

void cross_layer_csv_row(FILE *stream, const ecu_state_t *state)
{
    const fault_descriptor_t *f = &state->cross_layer_fault;
    const cross_layer_fault_state_t *r = &state->cross_layer_runtime;
    fprintf(stream, ",%d", f->enabled);
    if (f->enabled) {
        fprintf(stream, ",%u,%s,%s,%s,%s,%u,%u", f->fault_id,
            cross_layer_layer_name(f->layer), cross_layer_model_name(f->model),
            cross_layer_behavior_name(f->behavior), cross_layer_target_name(f->target),
            f->start_ms, f->duration_ms);
    } else {
        fputs(",,,,,,,", stream);
    }
    fprintf(stream, ",%u,%d", (unsigned int)f->seed, r->active);
    if (r->memory_values_valid) {
        fprintf(stream, ",%u,%u,%u", r->memory_original_value, r->memory_corrupted_value, f->bit_index);
    } else {
        fputs(",,,", stream);
    }
    /* A skipped task has no actual execution or delay-to-execution value. */
    fprintf(stream, ",%d,%d,", r->deadline_missed, r->execution_skipped);
    if (!r->execution_skipped) fprintf(stream, "%u", r->actual_delay_ms);
    fprintf(stream, ",%d,", r->expected_execution_ms);
    if (r->actual_execution_ms >= 0) fprintf(stream, "%d", r->actual_execution_ms);
    fprintf(stream, ",%d,%d", r->execution_recovered, state->control.last_execution_ms);
}

void cross_layer_fault_init(ecu_state_t *state)
{
    cross_layer_fault_state_t *r = &state->cross_layer_runtime;
    memset(r, 0, sizeof(*r));
    r->expected_execution_ms = r->actual_execution_ms = -1;
    r->last_activation_ms = r->last_recovery_ms = -1;
    r->nominal_release_ms = r->job_due_ms = r->deadline_ms = -1;
    r->delivered_ms = r->replay_source_ms = -1;
    r->delivered_value = state->sensors.coolant_temp_meas_c;
}

/* One temporal policy for every new injector. Intermittent duration bounds the
 * entire train; active/off windows are half-open and phase-locked to start. */
void cross_layer_fault_step(ecu_state_t *state)
{
    const fault_descriptor_t *f = &state->cross_layer_fault;
    cross_layer_fault_state_t *r = &state->cross_layer_runtime;
    unsigned int now = state->time.time_ms;
    bool was_active = r->active;
    r->active = false;
    r->phase = !f->enabled ? FAULT_PHASE_DISABLED : FAULT_PHASE_WAITING;
    if (f->enabled && now >= f->start_ms) {
        unsigned int elapsed = now - f->start_ms;
        if (f->behavior != FAULT_BEHAVIOR_PERMANENT && elapsed >= f->duration_ms) {
            r->phase = FAULT_PHASE_RECOVERED;
        } else {
            r->active = f->behavior != FAULT_BEHAVIOR_INTERMITTENT ||
                elapsed % (f->intermittent_on_ms + f->intermittent_off_ms) < f->intermittent_on_ms;
            r->phase = r->active ? FAULT_PHASE_ACTIVE : FAULT_PHASE_INACTIVE;
        }
    }
    if (r->active && !was_active) {
        r->activation_count++;
        r->last_activation_ms = (int)now;
        r->active_update_count = 0;
        if (!r->injected) {
            r->injected = true;
            state->propagation.injection_ms = (int)now;
        }
        if (f->layer == FAULT_LAYER_MEMORY) {
            r->memory_original_value = state->control.target_register_c;
            r->memory_values_valid = true;
            if (f->model == FAULT_MODEL_BIT_FLIP) {
                state->control.target_register_c ^= (uint16_t)(1U << f->bit_index);
            }
        }
    }
    if (was_active && !r->active) {
        r->last_recovery_ms = (int)now;
        if (r->memory_values_valid) state->control.target_register_c = r->memory_original_value;
    }
    if (r->active && f->layer == FAULT_LAYER_MEMORY) {
        if (f->model == FAULT_MODEL_STUCK_BIT) {
            uint16_t mask = (uint16_t)(1U << f->bit_index);
            state->control.target_register_c = f->stuck_polarity ?
                state->control.target_register_c | mask : state->control.target_register_c & (uint16_t)~mask;
        }
        r->memory_corrupted_value = state->control.target_register_c;
        if (r->memory_corrupted_value != r->memory_original_value && state->propagation.internal_ms < 0)
            state->propagation.internal_ms = (int)now;
    }
}

bool cross_layer_control_execution(ecu_state_t *state)
{
    const fault_descriptor_t *f = &state->cross_layer_fault;
    cross_layer_fault_state_t *r = &state->cross_layer_runtime;
    int now = (int)state->time.time_ms;
    bool execute = true;
    r->execution_skipped = r->execution_recovered = r->deadline_missed = r->release_discarded = false;
    r->expected_execution_ms = now;
    r->actual_execution_ms = now;
    r->actual_delay_ms = 0;
    if (f->enabled && f->model == FAULT_MODEL_TASK_DELAY) {
        if (r->pending_job) {
            /* Single outstanding job: discard releases while pending, including
             * the release coincident with delayed completion. No catch-up burst. */
            r->release_discarded = true;
            execute = now >= r->job_due_ms;
            if (execute) {
                r->pending_job = false;
                r->actual_delay_ms = (unsigned int)(now - r->nominal_release_ms);
                r->deadline_missed = now > r->deadline_ms;
            } else r->deadline_missed = now >= r->deadline_ms;
        } else {
            r->nominal_release_ms = now;
            r->deadline_ms = now + (int)ECU_CONTROL_PERIOD_MS;
            if (r->active) {
                r->pending_job = true;
                r->job_due_ms = now + (int)f->task_delay_ms;
                execute = false;
            }
        }
    } else {
        r->nominal_release_ms = now;
        r->deadline_ms = now + (int)ECU_CONTROL_PERIOD_MS;
        if (r->active && f->model == FAULT_MODEL_DEADLINE_MISS) {
            execute = false;
            r->deadline_missed = true;
        }
    }
    r->execution_skipped = !execute;
    if (!execute) {
        r->actual_execution_ms = -1;
        if (state->propagation.internal_ms < 0) state->propagation.internal_ms = now;
    }
    r->execution_recovered = r->previous_execution_skipped && execute;
    r->previous_execution_skipped = !execute;
    return execute;
}

void cross_layer_v2_csv_header(FILE *stream)
{
    fputs(",fault_active,fault_activation_count,current_fault_phase,last_activation_ms,last_recovery_ms,"
        "intermittent_on_ms,intermittent_off_ms,stuck_polarity,"
        "nominal_release_ms,actual_execution_ms,task_delay_ms,deadline_ms,deadline_missed,execution_skipped,"
        "control_release_discarded,configured_task_delay_ms,"
        "sample_generated_ms,sample_delivered_ms,sample_age_ms,update_delayed,configured_delay_ms,"
        "update_generated,update_delivered,update_dropped,consecutive_drops,"
        "current_generated_value,delivered_value,replay_source_timestamp_ms,replay_active,"
        "communication_drop_count,drop_every_n_updates,replay_age_ms,total_drops", stream);
}
static void optional_ms(FILE *stream, int time)
{
    fputc(',',stream); if (time >= 0) fprintf(stream,"%d",time);
}
void cross_layer_v2_csv_row(FILE *stream, const ecu_state_t *state)
{
    const fault_descriptor_t *f = &state->cross_layer_fault;
    const cross_layer_fault_state_t *r = &state->cross_layer_runtime;
    static const char *phases[] = {"disabled","waiting","active","inactive","recovered"};
    fprintf(stream,",%d,%u,%s",r->active,r->activation_count,phases[r->phase]);
    optional_ms(stream,r->last_activation_ms); optional_ms(stream,r->last_recovery_ms);
    if (f->enabled && f->behavior == FAULT_BEHAVIOR_INTERMITTENT)
        fprintf(stream,",%u,%u",f->intermittent_on_ms,f->intermittent_off_ms);
    else fputs(",,",stream);
    fputc(',',stream);
    if (f->enabled && f->model == FAULT_MODEL_STUCK_BIT) fprintf(stream,"%u",f->stuck_polarity);
    optional_ms(stream,r->nominal_release_ms); optional_ms(stream,r->actual_execution_ms);
    fputc(',',stream); if (r->actual_execution_ms >= 0) fprintf(stream,"%u",r->actual_delay_ms);
    fprintf(stream,",%d,%d,%d,%d,",r->deadline_ms,r->deadline_missed,r->execution_skipped,r->release_discarded);
    if (f->enabled && f->model == FAULT_MODEL_TASK_DELAY) fprintf(stream,"%u",f->task_delay_ms);
    if (f->enabled && f->layer == FAULT_LAYER_COMMUNICATION) {
        fprintf(stream,",%u",r->generated_ms); optional_ms(stream,r->delivered_ms);
        fprintf(stream,",%u,%d,",state->time.time_ms-r->delivered_source_ms,r->update_delayed);
        if (f->model == FAULT_MODEL_DELAYED_UPDATE) fprintf(stream,"%u",f->communication_delay_ms);
        fprintf(stream,",%d,%d,%d,%u,%.9f,%.9f",r->update_generated,r->update_delivered,
            r->update_dropped,r->consecutive_drops,r->generated_value,r->delivered_value);
        optional_ms(stream,r->replay_source_ms);
        fprintf(stream,",%d,",r->replay_active);
        if (f->model == FAULT_MODEL_DROPPED_UPDATE) fprintf(stream,"%u",f->drop_count);
        fputc(',',stream);
        if (f->model == FAULT_MODEL_DROPPED_UPDATE) fprintf(stream,"%u",f->drop_every_n_updates);
        fputc(',',stream);
        if (f->model == FAULT_MODEL_REPLAYED_SAMPLE) fprintf(stream,"%u",f->replay_age_ms);
        fprintf(stream,",%u",r->total_drops);
    } else {
        for (unsigned int i=0;i<17;i++) fputc(',',stream);
    }
}
