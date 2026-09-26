#include "memory_diagnostic.h"

void memory_diagnostic_step(memory_diagnostic_t *s, unsigned int now,
                            memory_read_fn read, memory_write_fn write, void *ctx)
{
    if (!read || !write) return;
    /* Sweep all ten scheduler phases while preserving ten probes per10s.
     * Probe epochs:0,1100,2200,...,9900,10000,... . Nine1100ms gaps and
     * one100ms gap: mean1000ms, maximum1100ms. No fault metadata is read.
     * Each operation remains one atomic write/read/restore transaction. */
    unsigned int interval=s->checks%10U ? MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS :
        MEMORY_DIAGNOSTIC_PHASE_STEP_MS;
    if (s->valid && (now < s->checked_ms || now-s->checked_ms < interval)) return;
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
