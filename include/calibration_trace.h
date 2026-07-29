#ifndef CALIBRATION_TRACE_H
#define CALIBRATION_TRACE_H

#include "ecu_types.h"

int calibration_trace_load(
    ecu_state_t *state,
    const char *path,
    unsigned int required_duration_ms
);
int calibration_trace_get(
    const ecu_state_t *state,
    unsigned int time_ms,
    float *control_target_c
);
void calibration_trace_close(ecu_state_t *state);

#endif
