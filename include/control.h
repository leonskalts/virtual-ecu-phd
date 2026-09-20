#ifndef CONTROL_H
#define CONTROL_H

#include "ecu_types.h"

void control_init(ecu_state_t *state);
/* Authorized transaction: commit value and protected shadow together. */
void control_commit_target(ecu_state_t *state, uint16_t target_c);
void control_step(ecu_state_t *state);

#endif
