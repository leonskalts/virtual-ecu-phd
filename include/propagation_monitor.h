#ifndef PROPAGATION_MONITOR_H
#define PROPAGATION_MONITOR_H

#include <stdbool.h>
#include <stdio.h>

/* Experiment instrumentation only. A negative timestamp means not reached. */
typedef struct {
    bool enabled;
    int injection_ms;
    int internal_ms;
    int control_ms;
    int actuator_command_ms;
    int actuator_realization_ms;
    int plant_ms;
    int detector_ms;
    int safety_response_ms;
    int safe_state_ms;
    bool unsafe_state_entered;
    unsigned int unsafe_exposure_time_ms;
    bool previous_unsafe;
    int last_observation_ms;
    float reference_coolant_c;
    float coolant_deviation_c;
} propagation_monitor_t;

struct ecu_state;
void propagation_monitor_init(struct ecu_state *state);
void propagation_monitor_control(struct ecu_state *state, const struct ecu_state *reference);
void propagation_monitor_step(struct ecu_state *state, const struct ecu_state *reference);
void propagation_monitor_csv_header(FILE *stream);
void propagation_monitor_csv_row(FILE *stream, const struct ecu_state *state);

#endif
