#ifndef RUNTIME_OBSERVATION_H
#define RUNTIME_OBSERVATION_H

#include <stdbool.h>

/* Allowlist for future runtime monitors: deliberately no plant truth or labels. */
typedef struct {
    unsigned int time_ms;
    float coolant_measured_c;
    unsigned int sample_timestamp_ms;
    unsigned int sample_age_ms;
    float control_target_c;
    float pump_command, fan_command, pump_actual, fan_actual;
    int control_execution_ms;
    int diagnostic_id;
    int safety_state;
    bool detector_alarm;
    float engine_load, ambient_c, vehicle_speed_kph;
} runtime_observation_t;

struct ecu_state;
void runtime_observation_capture(const struct ecu_state *state, runtime_observation_t *observation);
#endif
