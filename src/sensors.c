#include "sensors.h"

#include "config.h"

/* Sensor module: exposes the plant through measured channels so experiments can
 * compare true and measured signals while keeping the ECU interfaces explicit.
 * Sensing-path hardware-origin abstractions are injected here as front-end,
 * ADC, or interface faults rather than plant disturbances. */
static float intermittent_sensor_error(unsigned int time_ms, float amplitude_c)
{
    unsigned int phase = (time_ms / ECU_SENSOR_PERIOD_MS) % 6U;

    if (phase == 0U || phase == 3U) {
        return amplitude_c;
    }

    if (phase == 1U || phase == 4U) {
        return -0.5f * amplitude_c;
    }

    return 0.0f;
}

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

    /* Persistent measurement offset models ADC/reference/front-end faults. */
    if (state->faults.enabled && state->faults.active_mode == FAULT_SENSOR_BIAS) {
        coolant_meas += state->faults.sensor_bias_c;
    }

    /* Bursty corruption models intermittent sensor-interface disturbances. */
    if (state->faults.enabled && state->faults.active_mode == FAULT_SENSOR_INTERFACE_INTERMITTENT) {
        coolant_meas += intermittent_sensor_error(
            state->time.time_ms,
            state->faults.sensor_intermittent_amplitude_c
        );
    }

    state->sensors.coolant_temp_meas_c = coolant_meas;
    state->sensors.radiator_temp_meas_c = state->plant.radiator_temp_true_c;
    state->sensors.ambient_temp_meas_c = state->plant.ambient_temp_c;
    state->sensors.vehicle_speed_meas_kph = state->plant.vehicle_speed_kph;
}
