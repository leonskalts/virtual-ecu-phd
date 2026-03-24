#ifndef SAFETY_MONITOR_H
#define SAFETY_MONITOR_H

#include "ecu_types.h"

void safety_monitor_init(ecu_state_t *state);
void safety_monitor_step(ecu_state_t *state);
const char *safety_monitor_state_label(safe_state_t state);

#endif
