#ifndef MEMORY_DIAGNOSTIC_BACKEND_H
#define MEMORY_DIAGNOSTIC_BACKEND_H
#include <stdint.h>
/* Simulation backend implements cell writes; monitor callbacks expose data only. */
uint16_t cross_layer_memory_read(void *state);
void cross_layer_memory_write(void *state, uint16_t value);
#endif
