#ifndef DIAGNOSTICS_H
#define DIAGNOSTICS_H

#include "ecu_types.h"

void diagnostics_init(ecu_state_t *state);
void diagnostics_step(ecu_state_t *state);

#endif
