#include "memory_diagnostic.h"

void memory_diagnostic_step(memory_diagnostic_t *s, unsigned int now,
                            memory_read_fn read, memory_write_fn write, void *ctx)
{
    if (!read || !write) return;
    if (s->valid && (now < s->checked_ms ||
                    now - s->checked_ms < MEMORY_DIAGNOSTIC_PERIOD_MS)) return;
    uint16_t saved = read(ctx);
    write(ctx, 0);
    bool failed = read(ctx) != 0;
    write(ctx, UINT16_MAX);
    failed = (read(ctx) != UINT16_MAX) || failed;
    write(ctx, saved);
    failed = (read(ctx) != saved) || failed;
    s->checked_ms = now;
    s->checks++;
    s->operations += 7; /* Four reads, three writes; includes restore verification. */
    s->valid = true;
    s->failed = failed;
}
