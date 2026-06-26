#ifndef DETECTION_ALGORITHM_H
#define DETECTION_ALGORITHM_H

#include <stdbool.h>

typedef enum {
    DETECTION_ALGORITHM_BUILTIN_ECU = 0,
    DETECTION_ALGORITHM_THRESHOLD,
    DETECTION_ALGORITHM_EWMA,
    DETECTION_ALGORITHM_CUSUM,
    DETECTION_ALGORITHM_THERMAL_OBSERVER,
    DETECTION_ALGORITHM_KALMAN_FILTER,
    DETECTION_ALGORITHM_ADAPTIVE_KALMAN_FILTER,
    DETECTION_ALGORITHM_HYBRID_ADAPTIVE_KALMAN
} detection_algorithm_t;

typedef enum {
    DETECTION_ACTION_OBSERVE_ONLY = 0,
    DETECTION_ACTION_PRECAUTIONARY_COOLING,
    DETECTION_ACTION_LIMP_HOME
} detection_action_t;

typedef struct {
    detection_algorithm_t selected_algorithm;
    detection_action_t selected_action;
    float ewma_fan_tracking_error;
    float ewma_pump_tracking_error;
    float ewma_coolant_sensor_residual_c;
    float cusum_fan_tracking_error;
    float cusum_pump_tracking_error;
    float cusum_coolant_sensor_residual_c;
    float thermal_observer_previous_coolant_temp_c;
    float thermal_observer_expected_delta_c;
    float thermal_observer_accumulated_mismatch_c;
    bool thermal_observer_initialized;
    bool kalman_filter_initialized;
    float kalman_filter_estimated_coolant_temp_c;
    float kalman_filter_estimate_covariance;
    float kalman_filter_process_noise_q;
    float kalman_filter_measurement_noise_r;
    float kalman_filter_expected_delta_c;
    float kalman_filter_innovation_c;
    float kalman_filter_accumulated_innovation;
    float kalman_filter_previous_coolant_temp_c;
    unsigned int adaptive_kalman_filter_confirmation_count;
    float current_score;
    bool alarm_active;
    bool detected;
    int first_detection_time_ms;
    unsigned int false_positive_count;
    bool previous_alarm_active;
    bool action_requested;
    int action_time_ms;
    char runtime_label[64];
    char action_reason[96];
} detection_algorithm_state_t;

struct ecu_state;

void detection_algorithm_init(
    detection_algorithm_state_t *detector,
    detection_algorithm_t selected_algorithm,
    detection_action_t selected_action
);
void detection_algorithm_step(struct ecu_state *state);
detection_algorithm_t detection_algorithm_from_string(const char *text);
const char *detection_algorithm_name(detection_algorithm_t algorithm);
detection_action_t detection_action_from_string(const char *text);
const char *detection_action_name(detection_action_t action);

#endif
