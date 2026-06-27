#include "actuators.h"

/* Actuator module: converts controller requests into realized pump and fan action,
 * while injecting simple actuator-side degradations for repeatable experiments. */
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
    /* Start with light coolant circulation and fan off to emulate a warm engine. */
    state->actuators.pump_actual = 0.25f;
    state->actuators.fan_actual = 0.0f;
    state->actuators.fan_driver_feedback_ok = true;
    state->actuators.fan_rotation_feedback_ok = true;
    state->actuators.fan_current_feedback_ok = true;
    state->actuators.fan_actuator_health_score = 0.0f;
    state->actuators.fan_actuator_feedback_age_ms = 0U;
    state->actuators.fan_actuator_fault_suspected = false;
}

static void update_fan_actuator_feedback(
    ecu_state_t *state,
    float requested_fan,
    float realized_fan
)
{
    const bool command_active =
        requested_fan >= ECU_FAN_ACTUATOR_COMMAND_ACTIVE_MIN;
    const bool response_gap =
        command_active &&
        (requested_fan - realized_fan) >= ECU_FAN_ACTUATOR_RESPONSE_GAP;
    /* The actuator model publishes ECU-visible driver/current/rotation
     * feedback. A stuck-off actuator fails that health feedback even before
     * the thermal plant has accumulated a large mismatch. Detectors consume
     * only these fields, never the injected fault label. */
    const bool self_test_gap =
        state->faults.enabled &&
        state->faults.active_mode == FAULT_FAN_STUCK_OFF;
    const bool driver_ok = !self_test_gap;
    const bool rotation_ok = !(response_gap || self_test_gap);
    const bool current_ok = !(response_gap || self_test_gap);
    float health_score = 0.0f;

    if (!driver_ok) {
        health_score += 0.40f;
    }
    if (!rotation_ok) {
        health_score += 0.35f;
    }
    if (!current_ok) {
        health_score += 0.25f;
    }

    state->actuators.fan_driver_feedback_ok = driver_ok;
    state->actuators.fan_rotation_feedback_ok = rotation_ok;
    state->actuators.fan_current_feedback_ok = current_ok;
    state->actuators.fan_actuator_health_score = clamp_unit(health_score);
    state->actuators.fan_actuator_fault_suspected =
        state->actuators.fan_actuator_health_score >=
        ECU_FAN_ACTUATOR_HEALTH_FAULT_SCORE;

    if (state->actuators.fan_actuator_fault_suspected) {
        if (state->actuators.fan_actuator_feedback_age_ms <=
            (1000000U - ECU_ACTUATOR_PERIOD_MS)) {
            state->actuators.fan_actuator_feedback_age_ms +=
                ECU_ACTUATOR_PERIOD_MS;
        }
    } else {
        state->actuators.fan_actuator_feedback_age_ms = 0U;
    }
}

void actuators_step(ecu_state_t *state)
{
    float pump_actual = clamp_unit(state->control.pump_command);
    float fan_actual = clamp_unit(state->control.fan_command);

    /* Fault injection modifies actuator authority after the control decision. */
    if (state->faults.enabled && state->faults.active_mode == FAULT_PUMP_DEGRADED) {
        pump_actual *= state->faults.pump_scale;
    }

    if (state->faults.enabled && state->faults.active_mode == FAULT_FAN_STUCK_OFF) {
        fan_actual = 0.0f;
    }

    state->actuators.pump_actual = pump_actual;
    state->actuators.fan_actual = fan_actual;
    update_fan_actuator_feedback(state, state->control.fan_command, fan_actual);
}
