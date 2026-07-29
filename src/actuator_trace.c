#include "actuator_trace.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "config.h"

static void reset_trace(fan_actual_trace_t *trace)
{
    free(trace->samples);
    memset(trace, 0, sizeof(*trace));
}

static int parse_trace_row(
    const char *line,
    unsigned int *time_ms,
    float *fan_actual
)
{
    char trailing;

    return sscanf(line, " %u , %f %c", time_ms, fan_actual, &trailing) == 2
        ? 0
        : -1;
}

int fan_actual_trace_load(
    ecu_state_t *state,
    const char *path,
    unsigned int required_duration_ms
)
{
    fan_actual_trace_t *trace = &state->fan_actual_trace;
    fan_actual_trace_sample_t *samples = NULL;
    unsigned int capacity = 0U;
    unsigned int count = 0U;
    FILE *stream;
    char line[256];

    reset_trace(trace);
    stream = fopen(path, "r");
    if (stream == NULL) {
        fprintf(
            stderr,
            "Failed to open fan actual trace '%s': %s\n",
            path,
            strerror(errno)
        );
        return -1;
    }

    if (fgets(line, sizeof(line), stream) == NULL) {
        fprintf(stderr, "Fan actual trace '%s' is empty.\n", path);
        fclose(stream);
        return -1;
    }
    line[strcspn(line, "\r\n")] = '\0';
    if (strcmp(line, "time_ms,fan_actual") != 0) {
        fprintf(
            stderr,
            "Fan actual trace '%s' must start with 'time_ms,fan_actual'.\n",
            path
        );
        fclose(stream);
        return -1;
    }

    while (fgets(line, sizeof(line), stream) != NULL) {
        unsigned int time_ms;
        float fan_actual;
        fan_actual_trace_sample_t *resized;

        if (parse_trace_row(line, &time_ms, &fan_actual) != 0) {
            fprintf(stderr, "Invalid row in fan actual trace '%s'.\n", path);
            free(samples);
            fclose(stream);
            return -1;
        }
        if (time_ms != count * ECU_ACTUATOR_PERIOD_MS) {
            fprintf(
                stderr,
                "Fan actual trace '%s' must contain one ordered sample every "
                "%u ms starting at 0 ms.\n",
                path,
                ECU_ACTUATOR_PERIOD_MS
            );
            free(samples);
            fclose(stream);
            return -1;
        }
        if (!isfinite(fan_actual) || fan_actual < 0.0f || fan_actual > 1.0f) {
            fprintf(
                stderr,
                "Fan actual trace '%s' contains an out-of-range value at "
                "%u ms.\n",
                path,
                time_ms
            );
            free(samples);
            fclose(stream);
            return -1;
        }

        if (count == capacity) {
            unsigned int next_capacity = capacity == 0U ? 1024U : capacity * 2U;

            resized = realloc(samples, next_capacity * sizeof(*samples));
            if (resized == NULL) {
                fprintf(stderr, "Out of memory while loading fan actual trace.\n");
                free(samples);
                fclose(stream);
                return -1;
            }
            samples = resized;
            capacity = next_capacity;
        }

        samples[count].time_ms = time_ms;
        samples[count].fan_actual = fan_actual;
        count++;
    }

    fclose(stream);
    if (count == 0U || samples[count - 1U].time_ms < required_duration_ms) {
        fprintf(
            stderr,
            "Fan actual trace '%s' does not cover the simulation through "
            "%u ms.\n",
            path,
            required_duration_ms
        );
        free(samples);
        return -1;
    }

    trace->samples = samples;
    trace->sample_count = count;
    trace->enabled = true;
    snprintf(trace->source_path, sizeof(trace->source_path), "%s", path);
    return 0;
}

int fan_actual_trace_get(
    const ecu_state_t *state,
    unsigned int time_ms,
    float *fan_actual
)
{
    const fan_actual_trace_t *trace = &state->fan_actual_trace;
    unsigned int index;

    if (!trace->enabled) {
        return 1;
    }
    if ((time_ms % ECU_ACTUATOR_PERIOD_MS) != 0U) {
        return -1;
    }

    index = time_ms / ECU_ACTUATOR_PERIOD_MS;
    if (index >= trace->sample_count ||
        trace->samples[index].time_ms != time_ms) {
        return -1;
    }

    *fan_actual = trace->samples[index].fan_actual;
    return 0;
}

void fan_actual_trace_close(ecu_state_t *state)
{
    reset_trace(&state->fan_actual_trace);
}
