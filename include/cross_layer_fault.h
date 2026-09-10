#ifndef CROSS_LAYER_FAULT_H
#define CROSS_LAYER_FAULT_H

#include "ecu_types.h"

int cross_layer_parse_options(int *argc, char **argv, ecu_state_t *state);
int cross_layer_validate(const ecu_state_t *state);
void cross_layer_fault_init(ecu_state_t *state);
bool cross_layer_control_execution(ecu_state_t *state);
void cross_layer_csv_header(FILE *stream);
void cross_layer_csv_row(FILE *stream, const ecu_state_t *state);

#endif
