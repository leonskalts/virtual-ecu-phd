#ifndef SENSOR_TRACE_H
#define SENSOR_TRACE_H

#include "ecu_types.h"

int coolant_sensor_trace_load(
    ecu_state_t *state,
    const char *path,
    unsigned int required_duration_ms
);
int coolant_sensor_trace_get(
    const ecu_state_t *state,
    unsigned int time_ms,
    float *coolant_temp_c
);
void coolant_sensor_trace_close(ecu_state_t *state);

#endif
