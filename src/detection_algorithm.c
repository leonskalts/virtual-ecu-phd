#include "detection_algorithm.h"

#include <stdio.h>
#include <string.h>

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

static float abs_float(float value)
{
    return (value < 0.0f) ? -value : value;
}

static float max_zero(float value)
{
    return (value > 0.0f) ? value : 0.0f;
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
    detection_algorithm_t selected_algorithm
)
{
    memset(detector, 0, sizeof(*detector));
    detector->selected_algorithm = selected_algorithm;
    detector->first_detection_time_ms = -1;
    snprintf(detector->runtime_label, sizeof(detector->runtime_label), "%s", "none");
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
    case DETECTION_ALGORITHM_BUILTIN_ECU:
    default:
        return "builtin_ecu";
    }
}
