#ifndef LOGGER_H
#define LOGGER_H

#include "ecu_types.h"

int logger_open(ecu_state_t *state, const char *path);
void logger_write(ecu_state_t *state);
void logger_close(ecu_state_t *state);

#endif
