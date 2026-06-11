#ifndef DETECTION_ALGORITHM_H
#define DETECTION_ALGORITHM_H

#include <stdbool.h>

typedef enum {
    DETECTION_ALGORITHM_BUILTIN_ECU = 0,
    DETECTION_ALGORITHM_THRESHOLD,
    DETECTION_ALGORITHM_EWMA,
    DETECTION_ALGORITHM_CUSUM
} detection_algorithm_t;

typedef struct {
    detection_algorithm_t selected_algorithm;
    float ewma_fan_tracking_error;
    float ewma_pump_tracking_error;
    float ewma_coolant_sensor_residual_c;
    float cusum_fan_tracking_error;
    float cusum_pump_tracking_error;
    float cusum_coolant_sensor_residual_c;
    float current_score;
    bool alarm_active;
    bool detected;
    int first_detection_time_ms;
    unsigned int false_positive_count;
    bool previous_alarm_active;
    char runtime_label[64];
} detection_algorithm_state_t;

struct ecu_state;

void detection_algorithm_init(
    detection_algorithm_state_t *detector,
    detection_algorithm_t selected_algorithm
);
void detection_algorithm_step(struct ecu_state *state);
detection_algorithm_t detection_algorithm_from_string(const char *text);
const char *detection_algorithm_name(detection_algorithm_t algorithm);

#endif
