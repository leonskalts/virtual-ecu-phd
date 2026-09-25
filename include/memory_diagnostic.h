#ifndef MEMORY_DIAGNOSTIC_H
#define MEMORY_DIAGNOSTIC_H
#include <stdbool.h>
#include <stdint.h>
#define MEMORY_DIAGNOSTIC_PERIOD_MS 1000U
typedef struct {
    unsigned int checked_ms, checks, operations;
    bool valid, failed;
} memory_diagnostic_t;
typedef uint16_t (*memory_read_fn)(void *);
typedef void (*memory_write_fn)(void *, uint16_t);
/* Caller guarantees exclusive access for the entire synchronous transaction.
 * Neither callback exposes a failure label or a faulty bit identity. */
void memory_diagnostic_step(memory_diagnostic_t *, unsigned int,
                            memory_read_fn, memory_write_fn, void *);
#endif
