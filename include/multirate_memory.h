#ifndef MULTIRATE_MEMORY_H
#define MULTIRATE_MEMORY_H
#include "memory_diagnostic.h"
/* Nominal500ms alternates600/400; nominal250ms alternates300/200.
 * Scheduling runs on the unchanged100ms ECU grid, not a fabricated sub-tick. */
void mr_memory_step(memory_diagnostic_t *,unsigned,unsigned,memory_read_fn,memory_write_fn,void *);
#endif
