#include "actuators.h"

static float clamp_unit(float value)
{
    if (value < 0.0f) {
        return 0.0f;
    }
    if (value > 1.0f) {
        return 1.0f;
    }
    return value;
}

void actuators_init(ecu_state_t *state)
{
    state->actuators.pump_actual = 0.25f;
    state->actuators.fan_actual = 0.0f;
}

void actuators_step(ecu_state_t *state)
{
    float pump_actual = clamp_unit(state->control.pump_command);
    float fan_actual = clamp_unit(state->control.fan_command);

    if (state->faults.enabled && state->faults.active_mode == FAULT_PUMP_DEGRADED) {
        pump_actual *= state->faults.pump_scale;
    }

    if (state->faults.enabled && state->faults.active_mode == FAULT_FAN_STUCK_OFF) {
        fan_actual = 0.0f;
    }

    state->actuators.pump_actual = pump_actual;
    state->actuators.fan_actual = fan_actual;
}
