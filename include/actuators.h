#ifndef ACTUATORS_H
#define ACTUATORS_H

#include "ecu_types.h"

void actuators_init(ecu_state_t *state);
void actuators_step(ecu_state_t *state);

#endif
