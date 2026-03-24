#include "thermal_plant.h"

#include "config.h"

static float clamp_nonnegative(float value)
{
    if (value < 0.0f) {
        return 0.0f;
    }
    return value;
}

void thermal_plant_init(ecu_state_t *state)
{
    state->plant.ambient_temp_c = 25.0f;
    state->plant.engine_load = 0.35f;
    state->plant.engine_speed_rpm = 1500.0f;
    state->plant.vehicle_speed_kph = 35.0f;
    state->plant.coolant_temp_true_c = 88.0f;
    state->plant.radiator_temp_true_c = 78.0f;
}

void thermal_plant_step(ecu_state_t *state)
{
    float time_s = (float)state->time.time_ms / 1000.0f;
    float dt_s = (float)ECU_DT_MS / 1000.0f;
    float heat_generation;
    float pump_cooling;
    float fan_cooling;
    float ram_air_cooling;
    float ambient_coupling;
    float temp_delta;

    if (time_s < 20.0f) {
        state->plant.engine_load = 0.35f;
        state->plant.vehicle_speed_kph = 35.0f;
        state->plant.engine_speed_rpm = 1500.0f;
        state->plant.ambient_temp_c = 25.0f;
    } else if (time_s < 60.0f) {
        state->plant.engine_load = 0.72f;
        state->plant.vehicle_speed_kph = 85.0f;
        state->plant.engine_speed_rpm = 2800.0f;
        state->plant.ambient_temp_c = 28.0f;
    } else if (time_s < 90.0f) {
        state->plant.engine_load = 0.82f;
        state->plant.vehicle_speed_kph = 15.0f;
        state->plant.engine_speed_rpm = 2200.0f;
        state->plant.ambient_temp_c = 31.0f;
    } else {
        state->plant.engine_load = 0.98f;
        state->plant.vehicle_speed_kph = 0.0f;
        state->plant.engine_speed_rpm = 2100.0f;
        state->plant.ambient_temp_c = 35.0f;
    }

    if (state->safety.limp_home_active) {
        state->plant.engine_load *= 0.65f;
    }

    heat_generation = 1.8f + (8.5f * state->plant.engine_load);
    pump_cooling = 7.5f * state->actuators.pump_actual;
    fan_cooling = 6.0f * state->actuators.fan_actual;
    ram_air_cooling = state->plant.vehicle_speed_kph / 35.0f;
    ambient_coupling = 0.08f * (state->plant.coolant_temp_true_c - state->plant.ambient_temp_c);

    temp_delta = heat_generation - pump_cooling - fan_cooling - ram_air_cooling - ambient_coupling;
    state->plant.coolant_temp_true_c += temp_delta * dt_s;
    state->plant.coolant_temp_true_c = clamp_nonnegative(state->plant.coolant_temp_true_c);

    state->plant.radiator_temp_true_c =
        state->plant.ambient_temp_c +
        (state->plant.coolant_temp_true_c - state->plant.ambient_temp_c) *
        (0.55f - (0.15f * state->actuators.fan_actual));
}
