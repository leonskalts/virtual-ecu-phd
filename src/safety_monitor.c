#include "safety_monitor.h"

#include "config.h"
#include "diagnostics.h"

/* Safety monitor: applies an explicit state-transition policy so experiments can
 * analyze when the ECU escalates from nominal control to protective action. */
static safe_state_t max_state(safe_state_t left, safe_state_t right)
{
    return (left > right) ? left : right;
}

static safe_state_t requested_state_from_diagnostics(const ecu_state_t *state)
{
    safe_state_t requested = SAFE_STATE_NORMAL;

    if (state->diagnostics.overtemp_warning ||
        state->diagnostics.pump_tracking_dtc.pending ||
        state->diagnostics.fan_tracking_dtc.pending) {
        requested = SAFE_STATE_PRECAUTIONARY_COOLING;
    }

    if (state->diagnostics.overtemp_critical ||
        state->diagnostics.cooling_performance_dtc.confirmed ||
        state->diagnostics.pump_tracking_dtc.confirmed ||
        state->diagnostics.fan_tracking_dtc.confirmed) {
        requested = max_state(requested, SAFE_STATE_LIMP_HOME);
    }

    if (state->diagnostics.overtemp_critical_dtc.confirmed &&
        state->plant.coolant_temp_true_c >= ECU_SHUTDOWN_COOLANT_TEMP_C &&
        diagnostics_dtc_class(&state->diagnostics.overtemp_critical_dtc) >= DIAG_CLASS_PERSISTENT) {
        requested = SAFE_STATE_CONTROLLED_SHUTDOWN;
    }

    if (state->diagnostics.coolant_sensor_dtc.pending &&
        !state->diagnostics.overtemp_warning &&
        !state->diagnostics.overtemp_critical &&
        !state->diagnostics.cooling_performance_dtc.pending &&
        !state->diagnostics.pump_tracking_dtc.pending &&
        !state->diagnostics.fan_tracking_dtc.pending) {
        requested = SAFE_STATE_NORMAL;
    }

    return requested;
}

static safe_state_t requested_state_from_detector(const ecu_state_t *state)
{
    if (!state->detection.action_requested) {
        return SAFE_STATE_NORMAL;
    }

    switch (state->detection.selected_action) {
    case DETECTION_ACTION_PRECAUTIONARY_COOLING:
        return SAFE_STATE_PRECAUTIONARY_COOLING;
    case DETECTION_ACTION_LIMP_HOME:
        return SAFE_STATE_LIMP_HOME;
    case DETECTION_ACTION_OBSERVE_ONLY:
    default:
        return SAFE_STATE_NORMAL;
    }
}

const char *safety_monitor_state_label(safe_state_t state)
{
    switch (state) {
    case SAFE_STATE_PRECAUTIONARY_COOLING:
        return "precautionary_cooling";
    case SAFE_STATE_LIMP_HOME:
        return "limp_home";
    case SAFE_STATE_CONTROLLED_SHUTDOWN:
        return "controlled_shutdown";
    case SAFE_STATE_NORMAL:
    default:
        return "normal";
    }
}

void safety_monitor_init(ecu_state_t *state)
{
    state->safety.current_state = SAFE_STATE_NORMAL;
    state->safety.requested_state = SAFE_STATE_NORMAL;
    state->safety.recovery_counter = 0U;
    state->safety.transition_count = 0U;
    state->safety.max_cooling_active = false;
    state->safety.torque_derate_active = false;
    state->safety.shutdown_requested = false;
    state->safety.load_limit_scale = 1.0f;
}

static void apply_requested_state(ecu_state_t *state, safe_state_t requested)
{
    state->safety.requested_state = requested;

    if (requested > state->safety.current_state) {
        state->safety.current_state = requested;
        state->safety.recovery_counter = 0U;
        state->safety.transition_count++;
    } else if (requested < state->safety.current_state) {
        state->safety.recovery_counter++;

        if (state->safety.recovery_counter >= ECU_SAFE_STATE_RECOVERY_COUNT) {
            state->safety.current_state = requested;
            state->safety.recovery_counter = 0U;
            state->safety.transition_count++;
        }
    } else {
        state->safety.recovery_counter = 0U;
    }

    state->safety.max_cooling_active = false;
    state->safety.torque_derate_active = false;
    state->safety.shutdown_requested = false;
    state->safety.load_limit_scale = 1.0f;

    switch (state->safety.current_state) {
    case SAFE_STATE_PRECAUTIONARY_COOLING:
        state->safety.max_cooling_active = true;
        state->safety.load_limit_scale = ECU_PRECAUTIONARY_LOAD_SCALE;
        break;
    case SAFE_STATE_LIMP_HOME:
        state->safety.max_cooling_active = true;
        state->safety.torque_derate_active = true;
        state->safety.load_limit_scale = ECU_LIMP_HOME_LOAD_SCALE;
        break;
    case SAFE_STATE_CONTROLLED_SHUTDOWN:
        state->safety.max_cooling_active = true;
        state->safety.torque_derate_active = true;
        state->safety.shutdown_requested = true;
        state->safety.load_limit_scale = ECU_CONTROLLED_SHUTDOWN_LOAD_SCALE;
        break;
    case SAFE_STATE_NORMAL:
    default:
        break;
    }

    if (state->safety.max_cooling_active) {
        state->control.pump_command = 1.0f;
        state->control.fan_command = 1.0f;
    }
}

void safety_monitor_step(ecu_state_t *state)
{
    apply_requested_state(state, requested_state_from_diagnostics(state));
}

bool safety_monitor_apply_detector_request(ecu_state_t *state)
{
    safe_state_t detector_requested;
    safe_state_t combined_requested;

    if (!state->detection.action_requested) {
        return false;
    }

    detector_requested = requested_state_from_detector(state);
    combined_requested = max_state(state->safety.requested_state, detector_requested);
    apply_requested_state(state, combined_requested);
    return true;
}
