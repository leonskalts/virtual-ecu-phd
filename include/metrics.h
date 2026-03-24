#ifndef METRICS_H
#define METRICS_H

#include <stddef.h>

#include "ecu_types.h"

void metrics_init(ecu_state_t *state);
void metrics_step(ecu_state_t *state);
int metrics_write_summary(const ecu_state_t *state, const char *log_path, char *summary_path, size_t summary_path_size);

#endif
