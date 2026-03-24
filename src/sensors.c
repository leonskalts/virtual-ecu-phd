#include "sensors.h"

/* Sensor module: exposes the plant through measured channels so experiments can
 * compare true and measured signals while keeping the ECU interfaces explicit. */
void sensors_init(ecu_state_t *state)
{
    state->sensors.coolant_temp_meas_c = state->plant.coolant_temp_true_c;
    state->sensors.radiator_temp_meas_c = state->plant.radiator_temp_true_c;
    state->sensors.ambient_temp_meas_c = state->plant.ambient_temp_c;
    state->sensors.vehicle_speed_meas_kph = state->plant.vehicle_speed_kph;
}

void sensors_step(ecu_state_t *state)
{
    float coolant_meas = state->plant.coolant_temp_true_c;

    /* Sensor bias is applied only in the sensing path, not the underlying plant. */
    if (state->faults.enabled && state->faults.active_mode == FAULT_SENSOR_BIAS) {
        coolant_meas += state->faults.sensor_bias_c;
    }

    state->sensors.coolant_temp_meas_c = coolant_meas;
    state->sensors.radiator_temp_meas_c = state->plant.radiator_temp_true_c;
    state->sensors.ambient_temp_meas_c = state->plant.ambient_temp_c;
    state->sensors.vehicle_speed_meas_kph = state->plant.vehicle_speed_kph;
}
