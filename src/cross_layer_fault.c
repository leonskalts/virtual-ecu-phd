#include "cross_layer_fault.h"

#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

static int parse_uint(const char *text, unsigned int *value)
{
    char *end;
    unsigned long number;
    if (*text < '0' || *text > '9') {
        return -1;
    }
    errno = 0;
    number = strtoul(text, &end, 10);
    if (errno || *end || number > UINT_MAX) {
        return -1;
    }
    *value = (unsigned int)number;
    return 0;
}

/* Remove only our options, preserving the legacy positional/suffix parser. */
int cross_layer_parse_options(int *argc, char **argv, ecu_state_t *state)
{
    fault_descriptor_t *f = &state->cross_layer_fault;
    const char *layer = NULL, *target = NULL;
    bool configured = false, bit_supplied = false;
    int read_index, write_index = 1;
    *f = (fault_descriptor_t){
        .fault_id = 1U, .model = FAULT_MODEL_LEGACY,
        .behavior = FAULT_BEHAVIOR_TRANSIENT, .start_ms = 45000U,
        .duration_ms = ECU_CONTROL_PERIOD_MS, .bit_index = 3U
    };
    for (read_index = 1; read_index < *argc; read_index++) {
        const char *option = argv[read_index];
        const char *value;
        unsigned int number;
        bool ours = strcmp(option, "--cross-layer-fault") == 0 ||
            strcmp(option, "--fault-layer") == 0 || strcmp(option, "--fault-target") == 0 ||
            strcmp(option, "--fault-behavior") == 0 || strcmp(option, "--fault-start-ms") == 0 ||
            strcmp(option, "--fault-duration-ms") == 0 || strcmp(option, "--bit-index") == 0 ||
            strcmp(option, "--seed") == 0 || strcmp(option, "--fault-id") == 0 ||
            strcmp(option, "--cross-layer-monitor") == 0;
        if (!ours) {
            argv[write_index++] = argv[read_index];
            continue;
        }
        if (++read_index >= *argc) {
            fprintf(stderr, "Missing value for %s.\n", option);
            return -1;
        }
        value = argv[read_index];
        if (strcmp(option, "--cross-layer-monitor") == 0) {
            if (strcmp(value, "on") != 0) {
                fprintf(stderr, "--cross-layer-monitor expects on.\n");
                return -1;
            }
            state->propagation.enabled = true;
            continue;
        }
        if (strcmp(option, "--seed") == 0) {
            if (parse_uint(value, &number) != 0) {
                fprintf(stderr, "Seed must be an unsigned 32-bit integer.\n");
                return -1;
            }
            f->seed = (uint32_t)number;
            continue;
        }
        configured = true;
        if (strcmp(option, "--cross-layer-fault") == 0) {
            if (strcmp(value, "bit_flip") == 0) {
                f->model = FAULT_MODEL_BIT_FLIP;
            } else if (strcmp(value, "deadline_miss") == 0) {
                f->model = FAULT_MODEL_DEADLINE_MISS;
            } else {
                fprintf(stderr, "Supported cross-layer faults: bit_flip, deadline_miss.\n");
                return -1;
            }
            f->enabled = true;
        } else if (strcmp(option, "--fault-layer") == 0) {
            layer = value;
        } else if (strcmp(option, "--fault-target") == 0) {
            target = value;
        } else if (strcmp(option, "--fault-behavior") == 0) {
            if (strcmp(value, "transient") != 0) {
                fprintf(stderr, "Only transient cross-layer behavior is implemented in v1.\n");
                return -1;
            }
        } else {
            if (parse_uint(value, &number) != 0) {
                fprintf(stderr, "Invalid unsigned integer for %s: %s.\n", option, value);
                return -1;
            }
            if (strcmp(option, "--fault-start-ms") == 0) f->start_ms = number;
            if (strcmp(option, "--fault-duration-ms") == 0) f->duration_ms = number;
            if (strcmp(option, "--fault-id") == 0) f->fault_id = number;
            if (strcmp(option, "--bit-index") == 0) {
                f->bit_index = number;
                bit_supplied = true;
            }
        }
    }
    *argc = write_index;
    argv[write_index] = NULL;
    if (configured && !f->enabled) {
        fprintf(stderr, "Cross-layer fault parameters require --cross-layer-fault.\n");
        return -1;
    }
    if (!f->enabled) return 0;
    f->layer = f->model == FAULT_MODEL_BIT_FLIP ? FAULT_LAYER_MEMORY : FAULT_LAYER_TIMING;
    f->target = f->model == FAULT_MODEL_BIT_FLIP ?
        FAULT_TARGET_CONTROL_TARGET_REGISTER : FAULT_TARGET_CONTROL_TASK;
    if ((layer && strcmp(layer, f->layer == FAULT_LAYER_MEMORY ? "memory" : "timing") != 0) ||
        (target && strcmp(target, f->target == FAULT_TARGET_CONTROL_TASK ?
            "control_task" : "control_target_register") != 0) ||
        (f->model == FAULT_MODEL_DEADLINE_MISS && bit_supplied)) {
        fprintf(stderr, "Incompatible layer, target, or bit index for the selected fault.\n");
        return -1;
    }
    state->propagation.enabled = true;
    return 0;
}

int cross_layer_validate(const ecu_state_t *state)
{
    const fault_descriptor_t *f = &state->cross_layer_fault;
    unsigned int duration = state->simulation.duration_ms;
    if (state->propagation.enabled && (state->coolant_sensor_trace.enabled ||
        state->fan_actual_trace.enabled || state->calibration_trace.enabled)) {
        fprintf(stderr, "Cross-layer reference monitoring does not support external replay traces in v1.\n");
        return -1;
    }
    if (!f->enabled) return 0;
    if (state->experiment.event_count != 0U) {
        fprintf(stderr, "Use baseline with new cross-layer faults; combined injections are reserved for a later version.\n");
        return -1;
    }
    if (f->start_ms % ECU_CONTROL_PERIOD_MS || f->duration_ms == 0U ||
        f->duration_ms % ECU_CONTROL_PERIOD_MS || f->start_ms >= duration ||
        f->duration_ms > duration - f->start_ms ||
        (f->model == FAULT_MODEL_BIT_FLIP && f->bit_index > 5U) ||
        (f->model == FAULT_MODEL_DEADLINE_MISS && f->duration_ms != ECU_CONTROL_PERIOD_MS)) {
        fprintf(stderr, "Cross-layer start/duration must align to 100 ms and end within the run; "
            "duration must be positive. Bit index: 0..5. Deadline miss duration: exactly 100 ms.\n");
        return -1;
    }
    return 0;
}

void cross_layer_fault_init(ecu_state_t *state)
{
    memset(&state->cross_layer_runtime, 0, sizeof(state->cross_layer_runtime));
    state->cross_layer_runtime.expected_execution_ms = -1;
    state->cross_layer_runtime.actual_execution_ms = -1;
}

/* Called only when the real control task is due, before its inputs are read. */
bool cross_layer_control_execution(ecu_state_t *state)
{
    const fault_descriptor_t *f = &state->cross_layer_fault;
    cross_layer_fault_state_t *r = &state->cross_layer_runtime;
    unsigned int now = state->time.time_ms;
    bool was_active = r->active;
    r->execution_skipped = false;
    r->execution_recovered = false;
    r->expected_execution_ms = (int)now;
    r->actual_execution_ms = (int)now;
    r->active = f->enabled && now >= f->start_ms && now - f->start_ms < f->duration_ms;
    if (r->active && !r->injected) {
        r->injected = true;
        state->propagation.injection_ms = (int)now;
        state->propagation.internal_ms = (int)now;
        if (f->model == FAULT_MODEL_BIT_FLIP) {
            r->memory_original_value = state->control.target_register_c;
            r->memory_corrupted_value = (uint16_t)(r->memory_original_value ^ (1U << f->bit_index));
            r->memory_values_valid = true;
            state->control.target_register_c = r->memory_corrupted_value;
        }
    }
    if (was_active && !r->active && r->memory_values_valid) {
        state->control.target_register_c = r->memory_original_value;
    }
    if (r->active && f->model == FAULT_MODEL_DEADLINE_MISS) {
        r->execution_skipped = true;
        r->actual_execution_ms = -1;
    }
    r->execution_recovered = r->previous_execution_skipped && !r->execution_skipped;
    r->previous_execution_skipped = r->execution_skipped;
    return !r->execution_skipped;
}

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
        fprintf(stream, ",%u,%s,%s,transient,%s,%u,%u", f->fault_id,
            f->layer == FAULT_LAYER_MEMORY ? "memory" : "timing",
            f->model == FAULT_MODEL_BIT_FLIP ? "bit_flip" : "deadline_miss",
            f->target == FAULT_TARGET_CONTROL_TASK ? "control_task" : "control_target_register",
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
    fprintf(stream, ",%d,%d,", r->execution_skipped, r->execution_skipped);
    if (!r->execution_skipped) fputc('0', stream);
    fprintf(stream, ",%d,", r->expected_execution_ms);
    if (r->actual_execution_ms >= 0) fprintf(stream, "%d", r->actual_execution_ms);
    fprintf(stream, ",%d,%d", r->execution_recovered, state->control.last_execution_ms);
}
