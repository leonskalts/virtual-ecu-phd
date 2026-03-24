#ifndef SCHEDULER_H
#define SCHEDULER_H

#include "ecu_types.h"

bool scheduler_task_due(unsigned int time_ms, unsigned int period_ms);
void scheduler_init(ecu_state_t *state);
void scheduler_run(ecu_state_t *state);

#endif
