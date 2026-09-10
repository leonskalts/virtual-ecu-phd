#include "cross_layer_fault.h"
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

const char *cross_layer_model_name(fault_model_t model)
{
    switch (model) {
    case FAULT_MODEL_BIT_FLIP: return "bit_flip";
    case FAULT_MODEL_STUCK_BIT: return "stuck_bit";
    case FAULT_MODEL_DEADLINE_MISS: return "deadline_miss";
    case FAULT_MODEL_TASK_DELAY: return "task_delay";
    case FAULT_MODEL_DELAYED_UPDATE: return "delayed_update";
    case FAULT_MODEL_DROPPED_UPDATE: return "dropped_update";
    case FAULT_MODEL_REPLAYED_SAMPLE: return "replayed_sample";
    default: return "legacy";
    }
}
const char *cross_layer_behavior_name(fault_behavior_t behavior)
{
    switch (behavior) {
    case FAULT_BEHAVIOR_TRANSIENT: return "transient";
    case FAULT_BEHAVIOR_PERMANENT: return "permanent";
    case FAULT_BEHAVIOR_INTERMITTENT: return "intermittent";
    default: return "none";
    }
}
const char *cross_layer_layer_name(fault_layer_t layer)
{
    static const char *names[] = {"hardware", "memory", "timing", "communication", "sensing_control", "actuator"};
    return names[layer];
}
const char *cross_layer_target_name(fault_target_t target)
{
    static const char *names[] = {"none", "control_target_register", "control_task", "coolant_sensor", "pump", "fan"};
    return names[target];
}

static int parse_uint(const char *text, unsigned int *value)
{
    char *end;
    unsigned long number;
    if (*text < '0' || *text > '9') return -1;
    errno = 0;
    number = strtoul(text, &end, 10);
    if (errno || *end || number > UINT_MAX) return -1;
    *value = (unsigned int)number;
    return 0;
}

typedef struct { const char *name; size_t offset; } uint_option_t;
#define OPTION(name, member) {name, offsetof(fault_descriptor_t, member)}
static const uint_option_t integer_options[] = {
    OPTION("--fault-start-ms", start_ms), OPTION("--fault-duration-ms", duration_ms),
    OPTION("--bit-index", bit_index), OPTION("--fault-id", fault_id),
    OPTION("--intermittent-on-ms", intermittent_on_ms), OPTION("--intermittent-off-ms", intermittent_off_ms),
    OPTION("--stuck-polarity", stuck_polarity), OPTION("--communication-delay-ms", communication_delay_ms),
    OPTION("--drop-count", drop_count), OPTION("--drop-every-n-updates", drop_every_n_updates),
    OPTION("--replay-age-ms", replay_age_ms), OPTION("--task-delay-ms", task_delay_ms)
};

int cross_layer_parse_options(int *argc, char **argv, ecu_state_t *state)
{
    fault_descriptor_t *f = &state->cross_layer_fault;
    const char *layer = NULL, *target = NULL;
    bool configured = false, bit_supplied = false;
    int read_index, write_index = 1;
    *f = (fault_descriptor_t){ .fault_id = 1U, .model = FAULT_MODEL_LEGACY,
        .behavior = FAULT_BEHAVIOR_TRANSIENT, .start_ms = 45000U,
        .duration_ms = 100U, .bit_index = 3U, .intermittent_on_ms = 100U,
        .intermittent_off_ms = 100U, .stuck_polarity = 1U,
        .communication_delay_ms = 300U, .drop_count = 3U,
        .replay_age_ms = 500U, .task_delay_ms = 200U };
    hazard_config_default(&state->hazard_config);
    for (read_index = 1; read_index < *argc; read_index++) {
        const char *option = argv[read_index], *value;
        unsigned int number;
        const uint_option_t *integer = NULL;
        for (size_t i = 0; i < sizeof(integer_options)/sizeof(integer_options[0]); i++) {
            if (!strcmp(option, integer_options[i].name)) integer = &integer_options[i];
        }
        bool hazard = !strcmp(option, "--hazard-monitor") || !strcmp(option, "--hazard-warning-c") ||
            !strcmp(option, "--hazard-critical-c") || !strcmp(option, "--max-critical-exposure-ms") ||
            !strcmp(option, "--ftti-ms") || !strcmp(option, "--containment-hold-ms");
        bool ours = integer || hazard || !strcmp(option,"--cross-layer-fault") ||
            !strcmp(option,"--fault-layer") || !strcmp(option,"--fault-target") ||
            !strcmp(option,"--fault-behavior") || !strcmp(option,"--seed") ||
            !strcmp(option,"--cross-layer-monitor");
        if (!ours) { argv[write_index++] = argv[read_index]; continue; }
        if (++read_index >= *argc) { fprintf(stderr,"Missing value for %s.\n",option); return -1; }
        value = argv[read_index];
        if (hazard) {
            hazard_config_t *h = &state->hazard_config;
            h->enabled = state->propagation.enabled = true;
            if (!strcmp(option,"--hazard-monitor")) {
                if (strcmp(value,"on")) goto invalid;
            } else if (!strcmp(option,"--hazard-warning-c") || !strcmp(option,"--hazard-critical-c")) {
                char *end; errno = 0; float parsed = strtof(value,&end);
                if (errno || end == value || *end || !isfinite(parsed)) goto invalid;
                if (!strcmp(option,"--hazard-warning-c")) h->warning_threshold_c = parsed;
                else h->critical_threshold_c = parsed;
            } else {
                if (parse_uint(value,&number)) goto invalid;
                if (!strcmp(option,"--max-critical-exposure-ms")) h->max_critical_exposure_ms = number;
                if (!strcmp(option,"--ftti-ms")) h->fault_tolerant_time_interval_ms = number;
                if (!strcmp(option,"--containment-hold-ms")) h->recovery_hold_ms = number;
            }
            continue;
        }
        if (!strcmp(option,"--cross-layer-monitor")) {
            if (strcmp(value,"on")) goto invalid;
            state->propagation.enabled = true; continue;
        }
        if (!strcmp(option,"--seed")) {
            if (parse_uint(value,&number)) goto invalid;
            f->seed = number; continue;
        }
        configured = true;
        if (integer) {
            if (parse_uint(value,&number)) goto invalid;
            *(unsigned int *)((char *)f + integer->offset) = number;
            if (!strcmp(option,"--bit-index")) bit_supplied = true;
        } else if (!strcmp(option,"--cross-layer-fault")) {
            f->enabled = false;
            for (int model = FAULT_MODEL_BIT_FLIP; model <= FAULT_MODEL_REPLAYED_SAMPLE; model++) {
                if (strcmp(cross_layer_model_name((fault_model_t)model),"legacy") &&
                    !strcmp(value,cross_layer_model_name((fault_model_t)model))) {
                    f->model = (fault_model_t)model; f->enabled = true; break;
                }
            }
            if (!f->enabled) goto invalid;
        } else if (!strcmp(option,"--fault-layer")) layer = value;
        else if (!strcmp(option,"--fault-target")) target = value;
        else if (!strcmp(option,"--fault-behavior")) {
            if (!strcmp(value,"transient")) f->behavior = FAULT_BEHAVIOR_TRANSIENT;
            else if (!strcmp(value,"permanent")) f->behavior = FAULT_BEHAVIOR_PERMANENT;
            else if (!strcmp(value,"intermittent")) f->behavior = FAULT_BEHAVIOR_INTERMITTENT;
            else goto invalid;
        }
        continue;
invalid:
        fprintf(stderr,"Invalid value for %s: %s.\n",option,value); return -1;
    }
    *argc = write_index; argv[write_index] = NULL;
    if (configured && !f->enabled) {
        fprintf(stderr,"Cross-layer parameters require --cross-layer-fault.\n"); return -1;
    }
    if (!f->enabled) return 0;
    bool memory = f->model == FAULT_MODEL_BIT_FLIP || f->model == FAULT_MODEL_STUCK_BIT;
    bool timing = f->model == FAULT_MODEL_DEADLINE_MISS || f->model == FAULT_MODEL_TASK_DELAY;
    f->layer = memory ? FAULT_LAYER_MEMORY : timing ? FAULT_LAYER_TIMING : FAULT_LAYER_COMMUNICATION;
    f->target = memory ? FAULT_TARGET_CONTROL_TARGET_REGISTER : timing ? FAULT_TARGET_CONTROL_TASK : FAULT_TARGET_COOLANT_SENSOR;
    if ((layer && strcmp(layer,cross_layer_layer_name(f->layer))) ||
        (target && strcmp(target,cross_layer_target_name(f->target))) || (!memory && bit_supplied)) {
        fprintf(stderr,"Incompatible fault layer, target or bit index.\n"); return -1;
    }
    state->propagation.enabled = true;
    return 0;
}

int cross_layer_validate(const ecu_state_t *state)
{
    const fault_descriptor_t *f = &state->cross_layer_fault;
    const hazard_config_t *h = &state->hazard_config;
    unsigned int duration = state->simulation.duration_ms;
    if (state->propagation.enabled && (state->coolant_sensor_trace.enabled ||
        state->fan_actual_trace.enabled || state->calibration_trace.enabled)) {
        fprintf(stderr,"Reference monitoring does not support external replay traces.\n"); return -1;
    }
    if (h->enabled && (h->warning_threshold_c <= 0 || h->critical_threshold_c <= h->warning_threshold_c ||
        h->critical_threshold_c > 150 || h->max_critical_exposure_ms > ECU_MAX_SIM_DURATION_MS ||
        h->fault_tolerant_time_interval_ms > ECU_MAX_SIM_DURATION_MS || h->recovery_hold_ms == 0 ||
        h->recovery_hold_ms > ECU_MAX_SIM_DURATION_MS)) {
        fprintf(stderr,"Invalid experimental hazard/FTTI configuration.\n"); return -1;
    }
    if (!f->enabled) return 0;
    if (state->experiment.event_count) {
        fprintf(stderr,"Use baseline with new faults; mixed legacy/new injections are unsupported.\n"); return -1;
    }
    if (f->start_ms % ECU_DT_MS || f->start_ms >= duration ||
        (f->behavior != FAULT_BEHAVIOR_PERMANENT &&
            (f->duration_ms == 0 || f->duration_ms % ECU_DT_MS || f->duration_ms > duration-f->start_ms)) ||
        (f->behavior == FAULT_BEHAVIOR_INTERMITTENT &&
            (!f->intermittent_on_ms || !f->intermittent_off_ms ||
             f->intermittent_on_ms % ECU_DT_MS || f->intermittent_off_ms % ECU_DT_MS ||
             f->intermittent_on_ms > ECU_MAX_SIM_DURATION_MS || f->intermittent_off_ms > ECU_MAX_SIM_DURATION_MS)) ||
        ((f->model == FAULT_MODEL_BIT_FLIP || f->model == FAULT_MODEL_STUCK_BIT) && f->bit_index > 5U) ||
        (f->model == FAULT_MODEL_STUCK_BIT && f->stuck_polarity > 1U) ||
        (f->model == FAULT_MODEL_DEADLINE_MISS && f->behavior == FAULT_BEHAVIOR_TRANSIENT && f->duration_ms != ECU_DT_MS) ||
        (f->model == FAULT_MODEL_TASK_DELAY && (!f->task_delay_ms || f->task_delay_ms % ECU_DT_MS || f->task_delay_ms > duration-f->start_ms)) ||
        (f->model == FAULT_MODEL_DELAYED_UPDATE && (!f->communication_delay_ms || f->communication_delay_ms % ECU_DT_MS || f->communication_delay_ms >= CROSS_LAYER_HISTORY_SAMPLES*ECU_DT_MS)) ||
        (f->model == FAULT_MODEL_REPLAYED_SAMPLE && (!f->replay_age_ms || f->replay_age_ms % ECU_DT_MS || f->replay_age_ms > f->start_ms || f->replay_age_ms >= CROSS_LAYER_HISTORY_SAMPLES*ECU_DT_MS)) ||
        (f->model == FAULT_MODEL_DROPPED_UPDATE && (!f->drop_count ||
            (f->drop_every_n_updates && f->drop_count > f->drop_every_n_updates)))) {
        fprintf(stderr,"Invalid fault timing or parameter: use aligned 100 ms ticks, bounded memory bits 0..5, valid polarity and positive model parameters.\n"); return -1;
    }
    return 0;
}
