#include "fault_injection.h"

void fault_injection_init(ecu_state_t *state)
{
    state->faults.active_mode = FAULT_NONE;
    state->faults.enabled = false;
    state->faults.sensor_bias_c = 0.0f;
    state->faults.pump_scale = 1.0f;
}

void fault_injection_step(ecu_state_t *state)
{
    state->faults.enabled = false;
    state->faults.active_mode = FAULT_NONE;
    state->faults.sensor_bias_c = 0.0f;
    state->faults.pump_scale = 1.0f;

    if (state->time.time_ms >= 30000U && state->time.time_ms < 60000U) {
        state->faults.enabled = true;
        state->faults.active_mode = FAULT_SENSOR_BIAS;
        state->faults.sensor_bias_c = 6.0f;
        return;
    }

    if (state->time.time_ms >= 60000U && state->time.time_ms < 90000U) {
        state->faults.enabled = true;
        state->faults.active_mode = FAULT_PUMP_DEGRADED;
        state->faults.pump_scale = 0.45f;
        return;
    }

    if (state->time.time_ms >= 90000U) {
        state->faults.enabled = true;
        state->faults.active_mode = FAULT_FAN_STUCK_OFF;
    }
}
