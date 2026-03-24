#ifndef FAULT_INJECTION_H
#define FAULT_INJECTION_H

#include "ecu_types.h"

void fault_injection_init(ecu_state_t *state);
void fault_injection_step(ecu_state_t *state);
const char *fault_injection_mode_label(fault_mode_t mode);
const char *fault_injection_behavior_label(fault_behavior_t behavior);

#endif
