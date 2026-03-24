#include "diagnostics.h"

#include "config.h"

void diagnostics_init(ecu_state_t *state)
{
    state->diagnostics.overtemp_warning = false;
    state->diagnostics.overtemp_critical = false;
    state->diagnostics.sensor_implausible = false;
    state->diagnostics.cooling_performance_low = false;
    state->diagnostics.actuator_fault = false;
}

void diagnostics_step(ecu_state_t *state)
{
    float measured = state->sensors.coolant_temp_meas_c;
    float cooling_gap = state->control.pump_command - state->actuators.pump_actual;
    float fan_gap = state->control.fan_command - state->actuators.fan_actual;

    state->diagnostics.overtemp_warning = measured >= ECU_WARN_COOLANT_TEMP_C;
    state->diagnostics.overtemp_critical = measured >= ECU_CRITICAL_COOLANT_TEMP_C;
    state->diagnostics.sensor_implausible =
        (measured < ECU_SENSOR_IMPLAUSIBLE_LOW_C) ||
        (measured > ECU_SENSOR_IMPLAUSIBLE_HIGH_C);

    state->diagnostics.cooling_performance_low =
        (measured > ECU_TARGET_COOLANT_TEMP_C + 10.0f) &&
        (state->actuators.pump_actual > 0.80f) &&
        (state->actuators.fan_actual > 0.80f);

    state->diagnostics.actuator_fault =
        (cooling_gap > 0.25f) || (fan_gap > 0.25f);
}
