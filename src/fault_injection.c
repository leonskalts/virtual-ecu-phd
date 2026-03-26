#include "fault_injection.h"

#include "config.h"

/* Fault-injection module: schedules deterministic hardware-origin fault
 * abstractions across sensing, timing/communication, actuation, and
 * computation/memory paths. These are cross-layer ECU manifestations of
 * electronics faults, not transistor-accurate simulations. */
void fault_injection_init(ecu_state_t *state)
{
    state->faults.active_mode = FAULT_NONE;
    state->faults.active_behavior = FAULT_BEHAVIOR_NONE;
    state->faults.active_event_index = -1;
    state->faults.enabled = false;
    state->faults.active_start_ms = 0U;
    state->faults.active_duration_ms = 0U;
    state->faults.active_parameter = 0.0f;
    state->faults.sensor_bias_c = 0.0f;
    state->faults.sensor_intermittent_amplitude_c = 0.0f;
    state->faults.sensor_update_hold_ms = ECU_SENSOR_PERIOD_MS;
    state->faults.stale_sample_timestamp_ms = 0U;
    state->faults.stale_coolant_temp_c = 0.0f;
    state->faults.stale_sample_valid = false;
    state->faults.pump_scale = 1.0f;
    state->faults.control_target_offset_c = 0.0f;
}

const char *fault_injection_mode_label(fault_mode_t mode)
{
    switch (mode) {
    case FAULT_SENSOR_BIAS:
        return "sensor_bias";
    case FAULT_SENSOR_INTERFACE_INTERMITTENT:
        return "sensor_interface_intermittent";
    case FAULT_STALE_SENSOR_DATA:
        return "stale_sensor_data";
    case FAULT_PUMP_DEGRADED:
        return "pump_degraded";
    case FAULT_FAN_STUCK_OFF:
        return "fan_stuck_off";
    case FAULT_CALIBRATION_MEMORY_CORRUPTION:
        return "calibration_memory_corruption";
    case FAULT_NONE:
    default:
        return "none";
    }
}

const char *fault_injection_behavior_label(fault_behavior_t behavior)
{
    switch (behavior) {
    case FAULT_BEHAVIOR_TRANSIENT:
        return "transient";
    case FAULT_BEHAVIOR_PERMANENT:
        return "permanent";
    case FAULT_BEHAVIOR_NONE:
    default:
        return "none";
    }
}

float fault_injection_default_parameter(fault_mode_t mode)
{
    switch (mode) {
    case FAULT_SENSOR_BIAS:
        return 6.0f;
    case FAULT_SENSOR_INTERFACE_INTERMITTENT:
        return 8.0f;
    case FAULT_STALE_SENSOR_DATA:
        return 2500.0f;
    case FAULT_PUMP_DEGRADED:
        return 0.45f;
    case FAULT_FAN_STUCK_OFF:
        return 0.0f;
    case FAULT_CALIBRATION_MEMORY_CORRUPTION:
        return 16.0f;
    case FAULT_NONE:
    default:
        return 0.0f;
    }
}

static bool fault_event_active(const fault_event_t *event, unsigned int time_ms)
{
    unsigned int end_ms;

    if (event->mode == FAULT_NONE) {
        return false;
    }

    if (time_ms < event->start_ms) {
        return false;
    }

    if (event->duration_ms == 0U) {
        return true;
    }

    end_ms = event->start_ms + event->duration_ms;
    return time_ms < end_ms;
}

static void apply_fault_event(ecu_state_t *state, const fault_event_t *event, int event_index)
{
    state->faults.enabled = true;
    state->faults.active_mode = event->mode;
    state->faults.active_behavior = event->behavior;
    state->faults.active_event_index = event_index;
    state->faults.active_start_ms = event->start_ms;
    state->faults.active_duration_ms = event->duration_ms;
    state->faults.active_parameter = event->parameter;

    switch (event->mode) {
    case FAULT_SENSOR_BIAS:
        state->faults.sensor_bias_c = event->parameter;
        break;
    case FAULT_SENSOR_INTERFACE_INTERMITTENT:
        state->faults.sensor_intermittent_amplitude_c = event->parameter;
        break;
    case FAULT_STALE_SENSOR_DATA:
        state->faults.sensor_update_hold_ms = (event->parameter > (float)ECU_SENSOR_PERIOD_MS)
            ? (unsigned int)event->parameter
            : ECU_SENSOR_PERIOD_MS;
        break;
    case FAULT_PUMP_DEGRADED:
        state->faults.pump_scale = event->parameter;
        break;
    case FAULT_CALIBRATION_MEMORY_CORRUPTION:
        state->faults.control_target_offset_c = event->parameter;
        break;
    case FAULT_FAN_STUCK_OFF:
    case FAULT_NONE:
    default:
        break;
    }
}

void fault_injection_step(ecu_state_t *state)
{
    unsigned int i;
    bool stale_fault_active = false;

    state->faults.enabled = false;
    state->faults.active_mode = FAULT_NONE;
    state->faults.active_behavior = FAULT_BEHAVIOR_NONE;
    state->faults.active_event_index = -1;
    state->faults.active_start_ms = 0U;
    state->faults.active_duration_ms = 0U;
    state->faults.active_parameter = 0.0f;
    state->faults.sensor_bias_c = 0.0f;
    state->faults.sensor_intermittent_amplitude_c = 0.0f;
    state->faults.sensor_update_hold_ms = ECU_SENSOR_PERIOD_MS;
    state->faults.pump_scale = 1.0f;
    state->faults.control_target_offset_c = 0.0f;

    for (i = 0U; i < state->experiment.event_count; i++) {
        if (fault_event_active(&state->experiment.events[i], state->time.time_ms)) {
            stale_fault_active = state->experiment.events[i].mode == FAULT_STALE_SENSOR_DATA;
            apply_fault_event(state, &state->experiment.events[i], (int)i);
            break;
        }
    }

    if (!stale_fault_active) {
        state->faults.stale_sample_valid = false;
        state->faults.stale_sample_timestamp_ms = 0U;
    }
}
