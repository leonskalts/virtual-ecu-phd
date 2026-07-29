#ifndef ACTUATOR_TRACE_H
#define ACTUATOR_TRACE_H

#include "ecu_types.h"

int fan_actual_trace_load(
    ecu_state_t *state,
    const char *path,
    unsigned int required_duration_ms
);
int fan_actual_trace_get(
    const ecu_state_t *state,
    unsigned int time_ms,
    float *fan_actual
);
void fan_actual_trace_close(ecu_state_t *state);

#endif
