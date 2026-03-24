#include "fault_injection.h"

/* Fault-injection module: schedules deterministic fault scenarios with an
 * explicit distinction between transient disturbances and permanent failures. */
void fault_injection_init(ecu_state_t *state)
{
    state->faults.active_mode = FAULT_NONE;
    state->faults.active_behavior = FAULT_BEHAVIOR_NONE;
    state->faults.enabled = false;
    state->faults.sensor_bias_c = 0.0f;
    state->faults.pump_scale = 1.0f;
}

const char *fault_injection_mode_label(fault_mode_t mode)
{
    switch (mode) {
    case FAULT_SENSOR_BIAS:
        return "sensor_bias";
    case FAULT_PUMP_DEGRADED:
        return "pump_degraded";
    case FAULT_FAN_STUCK_OFF:
        return "fan_stuck_off";
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

void fault_injection_step(ecu_state_t *state)
{
    state->faults.enabled = false;
    state->faults.active_mode = FAULT_NONE;
    state->faults.active_behavior = FAULT_BEHAVIOR_NONE;
    state->faults.sensor_bias_c = 0.0f;
    state->faults.pump_scale = 1.0f;

    /* 30-45 s: transient sensor bias used to test residual-based diagnosis. */
    if (state->time.time_ms >= 30000U && state->time.time_ms < 45000U) {
        state->faults.enabled = true;
        state->faults.active_mode = FAULT_SENSOR_BIAS;
        state->faults.active_behavior = FAULT_BEHAVIOR_TRANSIENT;
        state->faults.sensor_bias_c = 6.0f;
        return;
    }

    /* 60-85 s: transient pump degradation creates an actuator tracking fault. */
    if (state->time.time_ms >= 60000U && state->time.time_ms < 85000U) {
        state->faults.enabled = true;
        state->faults.active_mode = FAULT_PUMP_DEGRADED;
        state->faults.active_behavior = FAULT_BEHAVIOR_TRANSIENT;
        state->faults.pump_scale = 0.45f;
        return;
    }

    /* 90 s onward: permanent fan failure is left active for the rest of the run. */
    if (state->time.time_ms >= 90000U) {
        state->faults.enabled = true;
        state->faults.active_mode = FAULT_FAN_STUCK_OFF;
        state->faults.active_behavior = FAULT_BEHAVIOR_PERMANENT;
    }
}
