#ifndef CROSS_LAYER_FAULT_H
#define CROSS_LAYER_FAULT_H

#include "ecu_types.h"

int cross_layer_parse_options(int *argc, char **argv, ecu_state_t *state);
int cross_layer_validate(const ecu_state_t *state);
void cross_layer_fault_init(ecu_state_t *state);
void cross_layer_fault_step(ecu_state_t *state);
void cross_layer_sensor_delivery(ecu_state_t *state, float generated, float *delivered,
    bool *refreshed, unsigned int *source_ms);
const char *cross_layer_model_name(fault_model_t model);
const char *cross_layer_behavior_name(fault_behavior_t behavior);
const char *cross_layer_layer_name(fault_layer_t layer);
const char *cross_layer_target_name(fault_target_t target);
void cross_layer_v2_csv_header(FILE *stream);
void cross_layer_v2_csv_row(FILE *stream, const ecu_state_t *state);
bool cross_layer_control_execution(ecu_state_t *state);
void cross_layer_csv_header(FILE *stream);
void cross_layer_csv_row(FILE *stream, const ecu_state_t *state);

#endif
