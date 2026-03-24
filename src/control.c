#include "control.h"

#include "config.h"

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

void control_init(ecu_state_t *state)
{
    state->control.pump_command = 0.25f;
    state->control.fan_command = 0.0f;
}

void control_step(ecu_state_t *state)
{
    float temp_error = state->sensors.coolant_temp_meas_c - ECU_TARGET_COOLANT_TEMP_C;
    float load_term = 0.35f * state->plant.engine_load;
    float speed_term = state->plant.vehicle_speed_kph / 200.0f;

    state->control.pump_command = clamp_unit(0.30f + (0.025f * temp_error) + load_term);
    state->control.fan_command = clamp_unit(0.25f + (0.065f * temp_error) - (0.10f * speed_term));
}
