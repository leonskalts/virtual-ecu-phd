#ifndef CONTROL_H
#define CONTROL_H

#include "ecu_types.h"

void control_init(ecu_state_t *state);
void control_step(ecu_state_t *state);

#endif
