#ifndef SENSORS_H
#define SENSORS_H

#include "ecu_types.h"

void sensors_init(ecu_state_t *state);
void sensors_step(ecu_state_t *state);

#endif
