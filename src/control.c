#include "control.h"

#include "config.h"

/* Control module: maps measured thermal conditions to normalized pump and fan
 * requests. The controller is intentionally lightweight so it remains easy to
 * explain, tune, and extend in research experiments, including computation/
 * memory-path abstractions such as corrupted calibration parameters. */
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
    /* Conservative initial commands avoid aggressive cooling during warm-up. */
    state->control.pump_command = 0.25f;
    state->control.fan_command = 0.0f;
}

void control_step(ecu_state_t *state)
{
    float effective_target_c = ECU_TARGET_COOLANT_TEMP_C;
    float temp_error;
    float load_term = 0.35f * state->plant.engine_load;
    float speed_term = state->plant.vehicle_speed_kph / 200.0f;

    /* Calibration-memory corruption is modeled as a corrupted coolant-control
     * target stored in memory/register space, which delays cooling demand. */
    if (state->faults.enabled && state->faults.active_mode == FAULT_CALIBRATION_MEMORY_CORRUPTION) {
        effective_target_c += state->faults.control_target_offset_c;
    }

    temp_error = state->sensors.coolant_temp_meas_c - effective_target_c;

    /* The pump tracks bulk thermal load, while the fan reacts more strongly to
     * local temperature error and is reduced slightly by ram-air cooling. */
    state->control.pump_command = clamp_unit(0.30f + (0.025f * temp_error) + load_term);
    state->control.fan_command = clamp_unit(0.25f + (0.065f * temp_error) - (0.10f * speed_term));
}
