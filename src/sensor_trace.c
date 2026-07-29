#include "sensor_trace.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "config.h"

static void reset_trace(coolant_sensor_trace_t *trace)
{
    free(trace->samples);
    memset(trace, 0, sizeof(*trace));
}

static int parse_trace_row(
    const char *line,
    unsigned int *time_ms,
    float *coolant_temp_c
)
{
    char trailing;

    return sscanf(
        line,
        " %u , %f %c",
        time_ms,
        coolant_temp_c,
        &trailing
    ) == 2 ? 0 : -1;
}

int coolant_sensor_trace_load(
    ecu_state_t *state,
    const char *path,
    unsigned int required_duration_ms
)
{
    coolant_sensor_trace_t *trace = &state->coolant_sensor_trace;
    coolant_sensor_trace_sample_t *samples = NULL;
    unsigned int capacity = 0U;
    unsigned int count = 0U;
    FILE *stream;
    char line[256];

    reset_trace(trace);
    stream = fopen(path, "r");
    if (stream == NULL) {
        fprintf(
            stderr,
            "Failed to open coolant sensor trace '%s': %s\n",
            path,
            strerror(errno)
        );
        return -1;
    }

    if (fgets(line, sizeof(line), stream) == NULL) {
        fprintf(stderr, "Coolant sensor trace '%s' is empty.\n", path);
        fclose(stream);
        return -1;
    }
    line[strcspn(line, "\r\n")] = '\0';
    if (strcmp(line, "time_ms,coolant_temp_c") != 0) {
        fprintf(
            stderr,
            "Coolant sensor trace '%s' must start with "
            "'time_ms,coolant_temp_c'.\n",
            path
        );
        fclose(stream);
        return -1;
    }

    while (fgets(line, sizeof(line), stream) != NULL) {
        unsigned int time_ms;
        float coolant_temp_c;
        coolant_sensor_trace_sample_t *resized;

        if (parse_trace_row(line, &time_ms, &coolant_temp_c) != 0) {
            fprintf(stderr, "Invalid row in coolant sensor trace '%s'.\n", path);
            free(samples);
            fclose(stream);
            return -1;
        }
        if (time_ms != count * ECU_SENSOR_PERIOD_MS) {
            fprintf(
                stderr,
                "Coolant sensor trace '%s' must contain one ordered sample "
                "every %u ms starting at 0 ms.\n",
                path,
                ECU_SENSOR_PERIOD_MS
            );
            free(samples);
            fclose(stream);
            return -1;
        }
        if (!isfinite(coolant_temp_c) ||
            coolant_temp_c < ECU_SENSOR_IMPLAUSIBLE_LOW_C ||
            coolant_temp_c > ECU_SENSOR_IMPLAUSIBLE_HIGH_C) {
            fprintf(
                stderr,
                "Coolant sensor trace '%s' contains an out-of-range value "
                "at %u ms.\n",
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
                fprintf(stderr, "Out of memory while loading coolant sensor trace.\n");
                free(samples);
                fclose(stream);
                return -1;
            }
            samples = resized;
            capacity = next_capacity;
        }

        samples[count].time_ms = time_ms;
        samples[count].coolant_temp_c = coolant_temp_c;
        count++;
    }

    fclose(stream);
    if (count == 0U || samples[count - 1U].time_ms < required_duration_ms) {
        fprintf(
            stderr,
            "Coolant sensor trace '%s' does not cover the simulation through "
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

int coolant_sensor_trace_get(
    const ecu_state_t *state,
    unsigned int time_ms,
    float *coolant_temp_c
)
{
    const coolant_sensor_trace_t *trace = &state->coolant_sensor_trace;
    unsigned int index;

    if (!trace->enabled) {
        return 1;
    }
    if ((time_ms % ECU_SENSOR_PERIOD_MS) != 0U) {
        return -1;
    }

    index = time_ms / ECU_SENSOR_PERIOD_MS;
    if (index >= trace->sample_count ||
        trace->samples[index].time_ms != time_ms) {
        return -1;
    }

    *coolant_temp_c = trace->samples[index].coolant_temp_c;
    return 0;
}

void coolant_sensor_trace_close(ecu_state_t *state)
{
    reset_trace(&state->coolant_sensor_trace);
}
