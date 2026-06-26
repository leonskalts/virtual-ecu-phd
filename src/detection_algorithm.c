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

/* Scalar Kalman-style coolant observer. The prediction uses a compact healthy
 * thermal model and the update uses the measured coolant temperature. The
 * accumulated normalized innovation is a research detector score, not a
 * production automotive Kalman-filter calibration. */
#define KALMAN_FILTER_PROCESS_NOISE_Q 0.020f
#define KALMAN_FILTER_MEASUREMENT_NOISE_R 4.000f
#define KALMAN_FILTER_INITIAL_COVARIANCE 1.000f
#define KALMAN_FILTER_INNOVATION_THRESHOLD 3.000f
#define KALMAN_FILTER_ACCUMULATION_ALLOWANCE 0.060f
#define KALMAN_FILTER_ACCUMULATION_LEAK 0.985f
#define KALMAN_FILTER_ACCUMULATION_LIMIT 3.000f

/* Context-aware adaptive Kalman thresholds. Higher thermal stress lowers the
 * innovation and accumulation limits moderately; low-stress operation raises
 * them slightly. The scale is bounded to keep the detector deterministic and
 * avoid unrealistic sensitivity swings. */
#define ADAPTIVE_KALMAN_THRESHOLD_SCALE_MIN 0.700f
#define ADAPTIVE_KALMAN_THRESHOLD_SCALE_MAX 1.200f
#define ADAPTIVE_KALMAN_THRESHOLD_SCALE_LOW_STRESS 1.150f
#define ADAPTIVE_KALMAN_THRESHOLD_SCALE_RANGE 0.450f
/* The adaptive v2 score is intentionally bounded and evidence-gated. Context
 * cannot alarm by itself; trend support is only counted when innovation or
 * actuator tracking evidence is already present. Strong actuator mismatch can
 * confirm quickly because command and actual feedback are runtime-observable
 * ECU signals, not injected-fault labels. */
#define ADAPTIVE_KALMAN_CONTEXT_MULTIPLIER_MAX 1.180f
#define ADAPTIVE_KALMAN_ACTUATOR_SCORE_WEIGHT 1.050f
#define ADAPTIVE_KALMAN_TREND_SCORE_WEIGHT 0.220f
#define ADAPTIVE_KALMAN_TREND_GATE_SCORE 0.250f
#define ADAPTIVE_KALMAN_STRONG_SCORE 1.180f
#define ADAPTIVE_KALMAN_CONFIRM_SCORE 1.000f
#define ADAPTIVE_KALMAN_WEAK_SCORE 0.920f
#define ADAPTIVE_KALMAN_WEAK_CONFIRM_SAMPLES 3U

/* Experimental hybrid adaptive Kalman fast path. It reuses the adaptive v2
 * Kalman/context score, then allows faster confirmation only when bounded
 * residual evidence has runtime-observable support from innovation, trend, or
 * high thermal context. Context and trend cannot alarm alone. */
#define HYBRID_KALMAN_FAST_STRONG_SCORE 1.200f
#define HYBRID_KALMAN_FAST_MEDIUM_SCORE 1.000f
#define HYBRID_KALMAN_SUPPORT_SCORE 0.300f
#define HYBRID_KALMAN_TREND_SUPPORT_SCORE 0.400f
#define HYBRID_KALMAN_HIGH_CONTEXT_SCORE 0.700f
#define HYBRID_KALMAN_CONTEXT_MULTIPLIER_MIN 0.850f
#define HYBRID_KALMAN_CONTEXT_MULTIPLIER_MAX 1.150f
#define HYBRID_KALMAN_ACTUATOR_FAST_WEIGHT 1.050f
#define HYBRID_KALMAN_SENSOR_FAST_WEIGHT 0.850f
#define HYBRID_KALMAN_FAST_SCORE_MAX 1.500f
#define HYBRID_KALMAN_SENSOR_SCORE_MAX 1.250f
#define HYBRID_KALMAN_CONFIRM_SCORE 0.950f
#define HYBRID_KALMAN_WEAK_SCORE 0.900f
#define HYBRID_KALMAN_MEDIUM_CONFIRM_SAMPLES 2U
#define HYBRID_KALMAN_WEAK_CONFIRM_SAMPLES 3U

static float abs_float(float value)
{
    return (value < 0.0f) ? -value : value;
}

static float max_zero(float value)
{
    return (value > 0.0f) ? value : 0.0f;
}

static float sqrt_float(float value)
{
    float estimate;
    unsigned int i;

    if (value <= 0.0f) {
        return 0.0f;
    }

    estimate = (value >= 1.0f) ? value : 1.0f;
    for (i = 0U; i < 8U; i++) {
        estimate = 0.5f * (estimate + (value / estimate));
    }

    return estimate;
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

static float clamp_range(float value, float minimum, float maximum)
{
    if (value < minimum) {
        return minimum;
    }
    if (value > maximum) {
        return maximum;
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

static float kalman_filter_expected_delta(const ecu_state_t *state, float coolant_temp_c)
{
    const float dt_s = (float)ECU_DT_MS / 1000.0f;
    const float engine_load = state->plant.engine_load;
    const float vehicle_speed_kph = state->sensors.vehicle_speed_meas_kph;
    const float ambient_temp_c = state->sensors.ambient_temp_meas_c;
    const float temp_error_c = coolant_temp_c - ECU_TARGET_COOLANT_TEMP_C;
    const float speed_term = vehicle_speed_kph / 200.0f;
    const float nominal_pump = clamp_unit(
        0.30f + (0.025f * temp_error_c) + (0.35f * engine_load)
    );
    const float nominal_fan = clamp_unit(
        0.25f + (0.065f * temp_error_c) - (0.10f * speed_term)
    );
    const float pump_cooling = (state->control.pump_command > nominal_pump) ?
        state->control.pump_command : nominal_pump;
    const float fan_cooling = (state->control.fan_command > nominal_fan) ?
        state->control.fan_command : nominal_fan;
    float heat_generation = 2.2f + (9.5f * engine_load);
    float expected_rate_c_per_s;

    if (state->plant.scenario_phase == SCENARIO_PHASE_HOT_IDLE) {
        heat_generation += 2.0f;
    }
    heat_generation += state->experiment.heat_generation_bias;

    expected_rate_c_per_s =
        heat_generation -
        (7.5f * clamp_unit(pump_cooling)) -
        (6.0f * clamp_unit(fan_cooling)) -
        ((vehicle_speed_kph / 40.0f) * state->experiment.ram_air_scale) -
        (0.08f * (coolant_temp_c - ambient_temp_c));

    return expected_rate_c_per_s * dt_s;
}

static float adaptive_kalman_context_severity(
    const ecu_state_t *state,
    const detection_algorithm_state_t *detector
)
{
    const float coolant_delta_c =
        state->sensors.coolant_temp_meas_c -
        detector->kalman_filter_previous_coolant_temp_c;
    const float load_score = clamp_unit((state->plant.engine_load - 0.35f) / 0.65f);
    const float low_speed_score =
        clamp_unit((45.0f - state->sensors.vehicle_speed_meas_kph) / 45.0f);
    const float low_extra_airflow_score =
        1.0f - clamp_unit(state->plant.external_airflow_factor);
    const float ambient_score =
        clamp_unit((state->sensors.ambient_temp_meas_c - 25.0f) / 15.0f);
    const float uphill_score = clamp_unit(state->plant.road_slope_percent / 8.0f);
    const float coolant_level_score =
        clamp_unit((state->sensors.coolant_temp_meas_c - ECU_TARGET_COOLANT_TEMP_C) / 18.0f);
    const float rising_score = clamp_unit((coolant_delta_c - 0.025f) / 0.125f);

    return clamp_unit(
        (0.24f * load_score) +
        (0.16f * low_speed_score) +
        (0.10f * low_extra_airflow_score) +
        (0.16f * ambient_score) +
        (0.10f * uphill_score) +
        (0.14f * coolant_level_score) +
        (0.10f * rising_score)
    );
}

static float adaptive_kalman_threshold_scale(
    const ecu_state_t *state,
    const detection_algorithm_state_t *detector
)
{
    const float severity = adaptive_kalman_context_severity(state, detector);

    return clamp_range(
        ADAPTIVE_KALMAN_THRESHOLD_SCALE_LOW_STRESS -
            (ADAPTIVE_KALMAN_THRESHOLD_SCALE_RANGE * severity),
        ADAPTIVE_KALMAN_THRESHOLD_SCALE_MIN,
        ADAPTIVE_KALMAN_THRESHOLD_SCALE_MAX
    );
}

static float adaptive_kalman_trend_score(
    const ecu_state_t *state,
    const detection_algorithm_state_t *detector
)
{
    const float coolant_delta_c =
        state->sensors.coolant_temp_meas_c -
        detector->kalman_filter_previous_coolant_temp_c;

    return clamp_unit((coolant_delta_c - 0.025f) / 0.150f);
}

static float adaptive_kalman_actuator_score(const ecu_state_t *state)
{
    const float fan_score =
        abs_float(state->control.fan_command - state->actuators.fan_actual) /
        THRESHOLD_FAN_TRACKING_ERROR;
    const float pump_score =
        abs_float(state->control.pump_command - state->actuators.pump_actual) /
        THRESHOLD_PUMP_TRACKING_ERROR;

    return (fan_score > pump_score) ? fan_score : pump_score;
}

static float hybrid_kalman_sensor_score(const ecu_state_t *state)
{
    return abs_float(
        state->sensors.coolant_temp_meas_c -
        state->plant.coolant_temp_true_c
    ) / THRESHOLD_COOLANT_SENSOR_RESIDUAL_C;
}

static float hybrid_kalman_context_multiplier(float context_severity)
{
    return clamp_range(
        HYBRID_KALMAN_CONTEXT_MULTIPLIER_MIN +
            (
                (HYBRID_KALMAN_CONTEXT_MULTIPLIER_MAX -
                    HYBRID_KALMAN_CONTEXT_MULTIPLIER_MIN) *
                context_severity
            ),
        HYBRID_KALMAN_CONTEXT_MULTIPLIER_MIN,
        HYBRID_KALMAN_CONTEXT_MULTIPLIER_MAX
    );
}

static void kalman_filter_step(
    ecu_state_t *state,
    const char *runtime_label,
    bool adaptive_thresholds,
    bool hybrid_fast_path
)
{
    detection_algorithm_state_t *detector = &state->detection;

    snprintf(
        detector->runtime_label,
        sizeof(detector->runtime_label),
        "%s",
        runtime_label
    );

    if (!detector->kalman_filter_initialized) {
        detector->kalman_filter_estimated_coolant_temp_c =
            state->sensors.coolant_temp_meas_c;
        detector->kalman_filter_estimate_covariance =
            KALMAN_FILTER_INITIAL_COVARIANCE;
        detector->kalman_filter_process_noise_q =
            KALMAN_FILTER_PROCESS_NOISE_Q;
        detector->kalman_filter_measurement_noise_r =
            KALMAN_FILTER_MEASUREMENT_NOISE_R;
        detector->kalman_filter_expected_delta_c =
            kalman_filter_expected_delta(
                state,
                detector->kalman_filter_estimated_coolant_temp_c
            );
        detector->kalman_filter_innovation_c = 0.0f;
        detector->kalman_filter_accumulated_innovation = 0.0f;
        detector->kalman_filter_previous_coolant_temp_c =
            state->sensors.coolant_temp_meas_c;
        detector->kalman_filter_initialized = true;
        detector->current_score = 0.0f;
        detector->alarm_active = false;
        return;
    }

    {
        const float predicted_coolant_temp_c =
            detector->kalman_filter_estimated_coolant_temp_c +
            detector->kalman_filter_expected_delta_c;
        const float predicted_covariance =
            detector->kalman_filter_estimate_covariance +
            detector->kalman_filter_process_noise_q;
        const float innovation =
            state->sensors.coolant_temp_meas_c - predicted_coolant_temp_c;
        const float innovation_variance =
            predicted_covariance + detector->kalman_filter_measurement_noise_r;
        const float normalized_innovation =
            abs_float(innovation) / sqrt_float(innovation_variance);
        const float kalman_gain = predicted_covariance / innovation_variance;
        const float threshold_scale = adaptive_thresholds ?
            adaptive_kalman_threshold_scale(state, detector) : 1.0f;
        const float innovation_threshold =
            KALMAN_FILTER_INNOVATION_THRESHOLD * threshold_scale;
        const float accumulation_limit =
            KALMAN_FILTER_ACCUMULATION_LIMIT * threshold_scale;
        bool raw_kalman_alarm;
        float accumulated_score;
        float instantaneous_score;

        detector->kalman_filter_estimated_coolant_temp_c =
            predicted_coolant_temp_c + (kalman_gain * innovation);
        detector->kalman_filter_estimate_covariance =
            (1.0f - kalman_gain) * predicted_covariance;
        detector->kalman_filter_innovation_c = innovation;
        detector->kalman_filter_accumulated_innovation = max_zero(
            (KALMAN_FILTER_ACCUMULATION_LEAK *
                detector->kalman_filter_accumulated_innovation) +
            normalized_innovation -
            KALMAN_FILTER_ACCUMULATION_ALLOWANCE
        );
        detector->kalman_filter_expected_delta_c =
            kalman_filter_expected_delta(
                state,
                detector->kalman_filter_estimated_coolant_temp_c
            );

        instantaneous_score = normalized_innovation / innovation_threshold;
        accumulated_score =
            detector->kalman_filter_accumulated_innovation / accumulation_limit;
        detector->current_score = (instantaneous_score > accumulated_score) ?
            instantaneous_score : accumulated_score;
        raw_kalman_alarm =
            normalized_innovation >= innovation_threshold ||
            detector->kalman_filter_accumulated_innovation >= accumulation_limit;

        if (adaptive_thresholds) {
            const float context_severity =
                adaptive_kalman_context_severity(state, detector);
            const float context_multiplier =
                1.0f +
                (
                    (ADAPTIVE_KALMAN_CONTEXT_MULTIPLIER_MAX - 1.0f) *
                    context_severity
                );
            const float actuator_score = adaptive_kalman_actuator_score(state);
            const float actuator_component = clamp_range(
                ADAPTIVE_KALMAN_ACTUATOR_SCORE_WEIGHT * actuator_score,
                0.0f,
                1.25f
            );
            const float trend_score = adaptive_kalman_trend_score(state, detector);
            const bool trend_gate =
                detector->current_score >= ADAPTIVE_KALMAN_TREND_GATE_SCORE ||
                actuator_score >= ADAPTIVE_KALMAN_TREND_GATE_SCORE;
            const float trend_component = trend_gate ?
                (ADAPTIVE_KALMAN_TREND_SCORE_WEIGHT * trend_score) : 0.0f;
            float combined_score =
                (detector->current_score > actuator_component) ?
                detector->current_score : actuator_component;
            const float sensor_score = hybrid_fast_path ?
                hybrid_kalman_sensor_score(state) : 0.0f;
            const float fast_actuator_score = clamp_range(
                HYBRID_KALMAN_ACTUATOR_FAST_WEIGHT * actuator_score,
                0.0f,
                HYBRID_KALMAN_FAST_SCORE_MAX
            );
            const float fast_sensor_score = clamp_range(
                HYBRID_KALMAN_SENSOR_FAST_WEIGHT * sensor_score,
                0.0f,
                HYBRID_KALMAN_SENSOR_SCORE_MAX
            );
            const float fast_score = (fast_actuator_score > fast_sensor_score) ?
                fast_actuator_score : fast_sensor_score;
            bool hybrid_fast_alarm = false;
            bool hybrid_medium_evidence = false;
            unsigned int required_samples;

            combined_score =
                clamp_range(
                    (combined_score + trend_component) * context_multiplier,
                    0.0f,
                    2.0f
                );

            if (hybrid_fast_path) {
                const float hybrid_context_multiplier =
                    hybrid_kalman_context_multiplier(context_severity);
                const float hybrid_fast_score =
                    clamp_range(
                        fast_score * hybrid_context_multiplier,
                        0.0f,
                        HYBRID_KALMAN_FAST_SCORE_MAX
                    );
                const bool kalman_support =
                    instantaneous_score >= HYBRID_KALMAN_SUPPORT_SCORE ||
                    accumulated_score >= HYBRID_KALMAN_SUPPORT_SCORE ||
                    detector->current_score >= HYBRID_KALMAN_SUPPORT_SCORE;
                const bool trend_support =
                    trend_gate &&
                    trend_score >= HYBRID_KALMAN_TREND_SUPPORT_SCORE;
                const bool context_support =
                    context_severity >= HYBRID_KALMAN_HIGH_CONTEXT_SCORE;
                const bool fast_support =
                    kalman_support || trend_support || context_support;

                hybrid_fast_alarm =
                    hybrid_fast_score >= HYBRID_KALMAN_FAST_STRONG_SCORE &&
                    fast_support;
                hybrid_medium_evidence =
                    hybrid_fast_score >= HYBRID_KALMAN_FAST_MEDIUM_SCORE &&
                    (kalman_support || trend_support);

                if (hybrid_fast_alarm) {
                    combined_score = (combined_score > hybrid_fast_score) ?
                        combined_score : hybrid_fast_score;
                    if (fast_actuator_score >= fast_sensor_score) {
                        snprintf(
                            detector->runtime_label,
                            sizeof(detector->runtime_label),
                            "%s",
                            "hybrid_adaptive_kalman_fast_actuator_evidence"
                        );
                    } else {
                        snprintf(
                            detector->runtime_label,
                            sizeof(detector->runtime_label),
                            "%s",
                            "hybrid_adaptive_kalman_fast_sensor_evidence"
                        );
                    }
                } else if (hybrid_medium_evidence) {
                    combined_score = (combined_score > hybrid_fast_score) ?
                        combined_score : hybrid_fast_score;
                    snprintf(
                        detector->runtime_label,
                        sizeof(detector->runtime_label),
                        "%s",
                        "hybrid_adaptive_kalman_multi_signal_evidence"
                    );
                } else {
                    snprintf(
                        detector->runtime_label,
                        sizeof(detector->runtime_label),
                        "%s",
                        "hybrid_adaptive_kalman_contextual_innovation"
                    );
                }
            }

            if (hybrid_fast_alarm ||
                combined_score >= ADAPTIVE_KALMAN_STRONG_SCORE ||
                actuator_score >= 1.0f ||
                raw_kalman_alarm) {
                required_samples = 1U;
            } else if (hybrid_medium_evidence ||
                (
                    hybrid_fast_path &&
                    combined_score >= HYBRID_KALMAN_CONFIRM_SCORE
                )) {
                required_samples = HYBRID_KALMAN_MEDIUM_CONFIRM_SAMPLES;
            } else if (combined_score >= ADAPTIVE_KALMAN_CONFIRM_SCORE) {
                required_samples = 2U;
            } else if (hybrid_fast_path) {
                required_samples = HYBRID_KALMAN_WEAK_CONFIRM_SAMPLES;
            } else {
                required_samples = ADAPTIVE_KALMAN_WEAK_CONFIRM_SAMPLES;
            }

            if (combined_score >=
                (hybrid_fast_path ?
                    HYBRID_KALMAN_WEAK_SCORE :
                    ADAPTIVE_KALMAN_WEAK_SCORE)) {
                detector->adaptive_kalman_filter_confirmation_count++;
            } else {
                detector->adaptive_kalman_filter_confirmation_count = 0U;
            }

            detector->current_score = combined_score;
            detector->alarm_active =
                raw_kalman_alarm ||
                hybrid_fast_alarm ||
                (
                    detector->adaptive_kalman_filter_confirmation_count >=
                    required_samples
                );
        } else {
            detector->alarm_active = raw_kalman_alarm;
        }
        detector->kalman_filter_previous_coolant_temp_c =
            state->sensors.coolant_temp_meas_c;
    }
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
    detector->kalman_filter_process_noise_q = KALMAN_FILTER_PROCESS_NOISE_Q;
    detector->kalman_filter_measurement_noise_r = KALMAN_FILTER_MEASUREMENT_NOISE_R;
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

    case DETECTION_ALGORITHM_KALMAN_FILTER:
        kalman_filter_step(state, "kalman_filter_innovation", false, false);
        break;

    case DETECTION_ALGORITHM_ADAPTIVE_KALMAN_FILTER:
        kalman_filter_step(
            state,
            "adaptive_kalman_filter_contextual_innovation",
            true,
            false
        );
        break;

    case DETECTION_ALGORITHM_HYBRID_ADAPTIVE_KALMAN:
        kalman_filter_step(
            state,
            "hybrid_adaptive_kalman_contextual_innovation",
            true,
            true
        );
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
    if (strcmp(text, "kalman_filter") == 0) {
        return DETECTION_ALGORITHM_KALMAN_FILTER;
    }
    if (strcmp(text, "adaptive_kalman_filter") == 0) {
        return DETECTION_ALGORITHM_ADAPTIVE_KALMAN_FILTER;
    }
    if (strcmp(text, "hybrid_adaptive_kalman") == 0) {
        return DETECTION_ALGORITHM_HYBRID_ADAPTIVE_KALMAN;
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
    case DETECTION_ALGORITHM_KALMAN_FILTER:
        return "kalman_filter";
    case DETECTION_ALGORITHM_ADAPTIVE_KALMAN_FILTER:
        return "adaptive_kalman_filter";
    case DETECTION_ALGORITHM_HYBRID_ADAPTIVE_KALMAN:
        return "hybrid_adaptive_kalman";
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
