#ifndef FAULT_INJECTION_H
#define FAULT_INJECTION_H

#include "ecu_types.h"

void fault_injection_init(ecu_state_t *state);
void fault_injection_step(ecu_state_t *state);

#endif
