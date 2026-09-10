#include "propagation_monitor.h"

#include "ecu_types.h"
#include <math.h>

/* Reporting tolerances only; these never enter a detector or safety decision. */
#define COMMAND_EPSILON 0.000001f
#define PLANT_MANIFESTATION_C 0.01f

static void first_seen(int *timestamp, unsigned int now, bool seen)
{
    if (*timestamp < 0 && seen) *timestamp = (int)now;
}

void propagation_monitor_init(ecu_state_t *state)
{
    bool enabled = state->propagation.enabled;
    state->propagation = (propagation_monitor_t){
        .enabled = enabled, .injection_ms = -1, .internal_ms = -1,
        .control_ms = -1, .actuator_command_ms = -1, .actuator_realization_ms = -1,
        .plant_ms = -1, .detector_ms = -1, .safety_response_ms = -1, .safe_state_ms = -1,
        .last_observation_ms = -1
    };
}

static bool commands_differ(const ecu_state_t *state, const ecu_state_t *reference)
{
    return fabsf(state->control.pump_command - reference->control.pump_command) > COMMAND_EPSILON ||
        fabsf(state->control.fan_command - reference->control.fan_command) > COMMAND_EPSILON;
}

void propagation_monitor_control(ecu_state_t *state, const ecu_state_t *reference)
{
    propagation_monitor_t *p = &state->propagation;
    unsigned int now = state->time.time_ms;
    if (!p->enabled) return;
    /* Legacy activation is evaluation metadata, never a detector input. */
    first_seen(&p->injection_ms, now, state->faults.enabled);
    if (p->injection_ms < 0) return;
    first_seen(&p->internal_ms, now,
        fabsf((state->sensors.coolant_temp_meas_c - state->plant.coolant_temp_true_c) -
            (reference->sensors.coolant_temp_meas_c - reference->plant.coolant_temp_true_c)) > COMMAND_EPSILON ||
        fabsf(state->control.active_control_target_c - reference->control.active_control_target_c) > COMMAND_EPSILON ||
        state->sensors.coolant_sensor_last_update_ms != reference->sensors.coolant_sensor_last_update_ms);
    first_seen(&p->control_ms, now,
        state->control.last_execution_ms != reference->control.last_execution_ms ||
        fabsf(state->control.active_control_target_c - reference->control.active_control_target_c) > COMMAND_EPSILON ||
        commands_differ(state, reference));
}

void propagation_monitor_step(ecu_state_t *state, const ecu_state_t *reference)
{
    propagation_monitor_t *p = &state->propagation;
    unsigned int now = state->time.time_ms;
    if (!p->enabled) return;
    p->reference_coolant_c = reference->plant.coolant_temp_true_c;
    p->coolant_deviation_c = state->plant.coolant_temp_true_c - p->reference_coolant_c;
    if (p->injection_ms < 0) return;
    /* These are FINAL applied commands and realizations, after safety overrides. */
    first_seen(&p->actuator_command_ms, now, commands_differ(state, reference));
    first_seen(&p->actuator_realization_ms, now,
        fabsf(state->actuators.pump_actual - reference->actuators.pump_actual) > COMMAND_EPSILON ||
        fabsf(state->actuators.fan_actual - reference->actuators.fan_actual) > COMMAND_EPSILON);
    /* The plant stored at t is the result of the preceding integration step. */
    first_seen(&p->plant_ms, now, fabsf(p->coolant_deviation_c) >= PLANT_MANIFESTATION_C);
    first_seen(&p->detector_ms, now, state->detection.alarm_active && !reference->detection.alarm_active);
    first_seen(&p->safety_response_ms, now,
        state->safety.requested_state > reference->safety.requested_state);
    first_seen(&p->safe_state_ms, now,
        state->safety.current_state > reference->safety.current_state &&
        state->safety.max_cooling_active);
    /* Integrate only completed intervals using the previous observed sample. */
    if (p->last_observation_ms >= 0 && p->previous_unsafe) {
        p->unsafe_exposure_time_ms += now - (unsigned int)p->last_observation_ms;
    }
    p->previous_unsafe = state->plant.coolant_temp_true_c >= ECU_CRITICAL_COOLANT_TEMP_C;
    p->unsafe_state_entered = p->unsafe_state_entered || p->previous_unsafe;
    p->last_observation_ms = (int)now;
}

static void optional_int(FILE *stream, bool available, int value)
{
    fputc(',', stream);
    if (available) fprintf(stream, "%d", value);
}

static void timestamp(FILE *stream, bool enabled, int value)
{
    optional_int(stream, enabled && value >= 0, value);
}

static void latency(FILE *stream, bool enabled, int start, int end)
{
    optional_int(stream, enabled && start >= 0 && end >= start, end - start);
}

void propagation_monitor_csv_header(FILE *stream)
{
    fputs(",cross_layer_monitor_enabled,fault_injection_ms,propagation_internal_ms,"
        "propagation_control_ms,propagation_actuator_command_ms,propagation_actuator_realization_ms,"
        "propagation_plant_ms,propagation_detector_ms,propagation_safety_response_ms,"
        "propagation_safe_state_ms,propagation_internal_seen,propagation_control_seen,"
        "propagation_actuator_seen,propagation_actuator_realization_seen,propagation_plant_seen,"
        "injection_to_internal_latency_ms,injection_to_control_latency_ms,"
        "injection_to_actuator_latency_ms,injection_to_plant_latency_ms,"
        "cross_layer_detection_latency_ms,detection_to_safety_response_latency_ms,"
        "propagation_depth,detected_before_plant_manifestation,safe_state_reached,"
        "unsafe_state_entered,unsafe_exposure_time_ms,containment_success,silent_corruption,"
        "reference_coolant_temp_c,plant_coolant_deviation_c", stream);
}

void propagation_monitor_csv_row(FILE *stream, const ecu_state_t *state)
{
    const propagation_monitor_t *p = &state->propagation;
    bool evaluated = p->enabled && p->injection_ms >= 0;
    /* Furthest reached stage, not a claim that every preceding layer changed. */
    int depth = p->plant_ms >= 0 ? 5 : p->actuator_realization_ms >= 0 ? 4 :
        p->actuator_command_ms >= 0 ? 3 : p->control_ms >= 0 ? 2 : p->internal_ms >= 0 ? 1 : 0;
    fprintf(stream, ",%d", p->enabled);
    timestamp(stream, p->enabled, p->injection_ms);
    timestamp(stream, p->enabled, p->internal_ms);
    timestamp(stream, p->enabled, p->control_ms);
    timestamp(stream, p->enabled, p->actuator_command_ms);
    timestamp(stream, p->enabled, p->actuator_realization_ms);
    timestamp(stream, p->enabled, p->plant_ms);
    timestamp(stream, p->enabled, p->detector_ms);
    timestamp(stream, p->enabled, p->safety_response_ms);
    timestamp(stream, p->enabled, p->safe_state_ms);
    optional_int(stream, p->enabled, p->internal_ms >= 0);
    optional_int(stream, p->enabled, p->control_ms >= 0);
    optional_int(stream, p->enabled, p->actuator_command_ms >= 0);
    optional_int(stream, p->enabled, p->actuator_realization_ms >= 0);
    optional_int(stream, p->enabled, p->plant_ms >= 0);
    latency(stream, evaluated, p->injection_ms, p->internal_ms);
    latency(stream, evaluated, p->injection_ms, p->control_ms);
    latency(stream, evaluated, p->injection_ms, p->actuator_command_ms);
    latency(stream, evaluated, p->injection_ms, p->plant_ms);
    latency(stream, evaluated, p->injection_ms, p->detector_ms);
    latency(stream, evaluated, p->detector_ms, p->safety_response_ms);
    optional_int(stream, p->enabled, depth);
    optional_int(stream, evaluated && p->detector_ms >= 0 && p->plant_ms >= 0,
        p->detector_ms < p->plant_ms);
    optional_int(stream, evaluated, p->safe_state_ms >= 0);
    optional_int(stream, evaluated, p->unsafe_state_entered);
    optional_int(stream, evaluated, (int)p->unsafe_exposure_time_ms);
    fputc(',', stream); /* Containment needs a hazard/FTTI contract; unavailable in v1. */
    optional_int(stream, evaluated, p->internal_ms >= 0 && p->detector_ms < 0);
    fputc(',', stream);
    if (p->enabled) fprintf(stream, "%.9f", p->reference_coolant_c);
    fputc(',', stream);
    if (p->enabled) fprintf(stream, "%.9f", p->coolant_deviation_c);
}
