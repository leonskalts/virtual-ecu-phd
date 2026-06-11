#include "detection_algorithm.h"

#include <stdio.h>
#include <string.h>

#include "config.h"
#include "diagnostics.h"
#include "ecu_types.h"

#define THRESHOLD_FAN_TRACKING_ERROR 0.25f
#define THRESHOLD_PUMP_TRACKING_ERROR 0.20f
#define THRESHOLD_COOLANT_SENSOR_RESIDUAL_C 2.00f

#define EWMA_ALPHA 0.20f

#define CUSUM_ALLOWANCE_FAN_TRACKING_ERROR 0.05f
#define CUSUM_ALLOWANCE_PUMP_TRACKING_ERROR 0.05f
#define CUSUM_ALLOWANCE_COOLANT_SENSOR_RESIDUAL_C 0.25f
#define CUSUM_LIMIT_FAN_TRACKING_ERROR 0.80f
#define CUSUM_LIMIT_PUMP_TRACKING_ERROR 0.80f
#define CUSUM_LIMIT_COOLANT_SENSOR_RESIDUAL_C 8.00f

/* Lightweight healthy-thermal observer. It predicts one coolant-temperature
 * step using the nominal 92 C controller target and ideal healthy actuator
 * response. Positive observed-minus-expected heating is accumulated after a
 * small per-step allowance. This is a deterministic research heuristic, not a
 * production state estimator or Kalman filter. */
#define THERMAL_OBSERVER_MISMATCH_ALLOWANCE_C 0.015f
#define THERMAL_OBSERVER_DECISION_LIMIT_C 1.50f

static float abs_float(float value)
{
    return (value < 0.0f) ? -value : value;
}

static float max_zero(float value)
{
    return (value > 0.0f) ? value : 0.0f;
}

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

static float thermal_observer_expected_delta(const ecu_state_t *state)
{
    const float dt_s = (float)ECU_DT_MS / 1000.0f;
    const float coolant_temp_c = state->sensors.coolant_temp_meas_c;
    const float engine_load = state->plant.engine_load;
    const float vehicle_speed_kph = state->sensors.vehicle_speed_meas_kph;
    const float ambient_temp_c = state->sensors.ambient_temp_meas_c;
    const float temp_error_c = coolant_temp_c - ECU_TARGET_COOLANT_TEMP_C;
    const float load_term = 0.35f * engine_load;
    const float speed_term = vehicle_speed_kph / 200.0f;
    const float nominal_pump = clamp_unit(
        0.30f + (0.025f * temp_error_c) + load_term
    );
    const float nominal_fan = clamp_unit(
        0.25f + (0.065f * temp_error_c) - (0.10f * speed_term)
    );
    float heat_generation = 2.2f + (9.5f * engine_load);
    float expected_rate_c_per_s;

    if (state->plant.scenario_phase == SCENARIO_PHASE_HOT_IDLE) {
        heat_generation += 2.0f;
    }
    heat_generation += state->experiment.heat_generation_bias;

    expected_rate_c_per_s =
        heat_generation -
        (7.5f * nominal_pump) -
        (6.0f * nominal_fan) -
        ((vehicle_speed_kph / 40.0f) * state->experiment.ram_air_scale) -
        (0.08f * (coolant_temp_c - ambient_temp_c));

    return expected_rate_c_per_s * dt_s;
}

static void set_score_and_label(
    detection_algorithm_state_t *detector,
    float fan_score,
    float pump_score,
    float sensor_score
)
{
    detector->current_score = fan_score;
    snprintf(detector->runtime_label, sizeof(detector->runtime_label), "%s", "fan_tracking_error");

    if (pump_score > detector->current_score) {
        detector->current_score = pump_score;
        snprintf(detector->runtime_label, sizeof(detector->runtime_label), "%s", "pump_tracking_error");
    }

    if (sensor_score > detector->current_score) {
        detector->current_score = sensor_score;
        snprintf(
            detector->runtime_label,
            sizeof(detector->runtime_label),
            "%s",
            "coolant_sensor_residual_c"
        );
    }
}

void detection_algorithm_init(
    detection_algorithm_state_t *detector,
    detection_algorithm_t selected_algorithm,
    detection_action_t selected_action
)
{
    memset(detector, 0, sizeof(*detector));
    detector->selected_algorithm = selected_algorithm;
    detector->selected_action = selected_action;
    detector->first_detection_time_ms = -1;
    detector->action_time_ms = -1;
    snprintf(detector->runtime_label, sizeof(detector->runtime_label), "%s", "none");
    snprintf(detector->action_reason, sizeof(detector->action_reason), "%s", "none");
}

void detection_algorithm_step(struct ecu_state *state)
{
    detection_algorithm_state_t *detector = &state->detection;
    float fan_residual = abs_float(state->control.fan_command - state->actuators.fan_actual);
    float pump_residual = abs_float(state->control.pump_command - state->actuators.pump_actual);
    float sensor_residual = abs_float(
        state->sensors.coolant_temp_meas_c - state->plant.coolant_temp_true_c
    );
    bool before_fault = state->metrics.fault_present_in_campaign &&
        state->time.time_ms < state->metrics.first_fault_start_ms;

    switch (detector->selected_algorithm) {
    case DETECTION_ALGORITHM_THRESHOLD:
        set_score_and_label(
            detector,
            fan_residual / THRESHOLD_FAN_TRACKING_ERROR,
            pump_residual / THRESHOLD_PUMP_TRACKING_ERROR,
            sensor_residual / THRESHOLD_COOLANT_SENSOR_RESIDUAL_C
        );
        detector->alarm_active = detector->current_score >= 1.0f;
        break;

    case DETECTION_ALGORITHM_EWMA:
        detector->ewma_fan_tracking_error =
            (EWMA_ALPHA * fan_residual) +
            ((1.0f - EWMA_ALPHA) * detector->ewma_fan_tracking_error);
        detector->ewma_pump_tracking_error =
            (EWMA_ALPHA * pump_residual) +
            ((1.0f - EWMA_ALPHA) * detector->ewma_pump_tracking_error);
        detector->ewma_coolant_sensor_residual_c =
            (EWMA_ALPHA * sensor_residual) +
            ((1.0f - EWMA_ALPHA) * detector->ewma_coolant_sensor_residual_c);
        set_score_and_label(
            detector,
            detector->ewma_fan_tracking_error / THRESHOLD_FAN_TRACKING_ERROR,
            detector->ewma_pump_tracking_error / THRESHOLD_PUMP_TRACKING_ERROR,
            detector->ewma_coolant_sensor_residual_c / THRESHOLD_COOLANT_SENSOR_RESIDUAL_C
        );
        detector->alarm_active = detector->current_score >= 1.0f;
        break;

    case DETECTION_ALGORITHM_CUSUM:
        detector->cusum_fan_tracking_error = max_zero(
            detector->cusum_fan_tracking_error +
            fan_residual -
            CUSUM_ALLOWANCE_FAN_TRACKING_ERROR
        );
        detector->cusum_pump_tracking_error = max_zero(
            detector->cusum_pump_tracking_error +
            pump_residual -
            CUSUM_ALLOWANCE_PUMP_TRACKING_ERROR
        );
        detector->cusum_coolant_sensor_residual_c = max_zero(
            detector->cusum_coolant_sensor_residual_c +
            sensor_residual -
            CUSUM_ALLOWANCE_COOLANT_SENSOR_RESIDUAL_C
        );
        set_score_and_label(
            detector,
            detector->cusum_fan_tracking_error / CUSUM_LIMIT_FAN_TRACKING_ERROR,
            detector->cusum_pump_tracking_error / CUSUM_LIMIT_PUMP_TRACKING_ERROR,
            detector->cusum_coolant_sensor_residual_c / CUSUM_LIMIT_COOLANT_SENSOR_RESIDUAL_C
        );
        detector->alarm_active = detector->current_score >= 1.0f;
        break;

    case DETECTION_ALGORITHM_THERMAL_OBSERVER:
        snprintf(
            detector->runtime_label,
            sizeof(detector->runtime_label),
            "%s",
            "thermal_observer_mismatch"
        );
        if (!detector->thermal_observer_initialized) {
            detector->thermal_observer_previous_coolant_temp_c =
                state->sensors.coolant_temp_meas_c;
            detector->thermal_observer_expected_delta_c =
                thermal_observer_expected_delta(state);
            detector->thermal_observer_accumulated_mismatch_c = 0.0f;
            detector->thermal_observer_initialized = true;
            detector->current_score = 0.0f;
            detector->alarm_active = false;
            break;
        }
        detector->thermal_observer_accumulated_mismatch_c = max_zero(
            detector->thermal_observer_accumulated_mismatch_c +
            (
                state->sensors.coolant_temp_meas_c -
                detector->thermal_observer_previous_coolant_temp_c
            ) -
            detector->thermal_observer_expected_delta_c -
            THERMAL_OBSERVER_MISMATCH_ALLOWANCE_C
        );
        detector->current_score =
            detector->thermal_observer_accumulated_mismatch_c /
            THERMAL_OBSERVER_DECISION_LIMIT_C;
        detector->alarm_active = detector->current_score >= 1.0f;
        detector->thermal_observer_previous_coolant_temp_c =
            state->sensors.coolant_temp_meas_c;
        detector->thermal_observer_expected_delta_c =
            thermal_observer_expected_delta(state);
        break;

    case DETECTION_ALGORITHM_BUILTIN_ECU:
    default:
        detector->alarm_active = state->diagnostics.primary_dtc != DTC_ID_NONE;
        detector->current_score = detector->alarm_active ? 1.0f : 0.0f;
        snprintf(
            detector->runtime_label,
            sizeof(detector->runtime_label),
            "%s",
            diagnostics_dtc_label(state->diagnostics.primary_dtc)
        );
        break;
    }

    if (detector->alarm_active && !detector->previous_alarm_active &&
        (before_fault || !state->metrics.fault_present_in_campaign)) {
        detector->false_positive_count++;
    }

    if (detector->alarm_active && !detector->detected && !before_fault) {
        detector->detected = true;
        detector->first_detection_time_ms = (int)state->time.time_ms;

        if (detector->selected_action != DETECTION_ACTION_OBSERVE_ONLY) {
            detector->action_requested = true;
            detector->action_time_ms = (int)state->time.time_ms;
            snprintf(
                detector->action_reason,
                sizeof(detector->action_reason),
                "%s:%s",
                detection_algorithm_name(detector->selected_algorithm),
                detector->runtime_label
            );
        }
    }

    detector->previous_alarm_active = detector->alarm_active;
}

detection_algorithm_t detection_algorithm_from_string(const char *text)
{
    if (text == NULL || strcmp(text, "builtin_ecu") == 0) {
        return DETECTION_ALGORITHM_BUILTIN_ECU;
    }
    if (strcmp(text, "threshold") == 0) {
        return DETECTION_ALGORITHM_THRESHOLD;
    }
    if (strcmp(text, "ewma") == 0) {
        return DETECTION_ALGORITHM_EWMA;
    }
    if (strcmp(text, "cusum") == 0) {
        return DETECTION_ALGORITHM_CUSUM;
    }
    if (strcmp(text, "thermal_observer") == 0) {
        return DETECTION_ALGORITHM_THERMAL_OBSERVER;
    }

    return DETECTION_ALGORITHM_BUILTIN_ECU;
}

const char *detection_algorithm_name(detection_algorithm_t algorithm)
{
    switch (algorithm) {
    case DETECTION_ALGORITHM_THRESHOLD:
        return "threshold";
    case DETECTION_ALGORITHM_EWMA:
        return "ewma";
    case DETECTION_ALGORITHM_CUSUM:
        return "cusum";
    case DETECTION_ALGORITHM_THERMAL_OBSERVER:
        return "thermal_observer";
    case DETECTION_ALGORITHM_BUILTIN_ECU:
    default:
        return "builtin_ecu";
    }
}

detection_action_t detection_action_from_string(const char *text)
{
    if (text == NULL || strcmp(text, "observe_only") == 0) {
        return DETECTION_ACTION_OBSERVE_ONLY;
    }
    if (strcmp(text, "precautionary_cooling") == 0) {
        return DETECTION_ACTION_PRECAUTIONARY_COOLING;
    }
    if (strcmp(text, "limp_home") == 0) {
        return DETECTION_ACTION_LIMP_HOME;
    }

    return DETECTION_ACTION_OBSERVE_ONLY;
}

const char *detection_action_name(detection_action_t action)
{
    switch (action) {
    case DETECTION_ACTION_PRECAUTIONARY_COOLING:
        return "precautionary_cooling";
    case DETECTION_ACTION_LIMP_HOME:
        return "limp_home";
    case DETECTION_ACTION_OBSERVE_ONLY:
    default:
        return "observe_only";
    }
}
