#include "calibration_trace.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "config.h"

static void reset_trace(calibration_trace_t *trace)
{
    free(trace->samples);
    memset(trace, 0, sizeof(*trace));
}

static int parse_trace_row(
    const char *line,
    unsigned int *time_ms,
    float *control_target_c
)
{
    char trailing;

    return sscanf(
        line,
        " %u , %f %c",
        time_ms,
        control_target_c,
        &trailing
    ) == 2 ? 0 : -1;
}

int calibration_trace_load(
    ecu_state_t *state,
    const char *path,
    unsigned int required_duration_ms
)
{
    calibration_trace_t *trace = &state->calibration_trace;
    calibration_trace_sample_t *samples = NULL;
    unsigned int capacity = 0U;
    unsigned int count = 0U;
    FILE *stream;
    char line[256];

    reset_trace(trace);
    stream = fopen(path, "r");
    if (stream == NULL) {
        fprintf(
            stderr,
            "Failed to open calibration trace '%s': %s\n",
            path,
            strerror(errno)
        );
        return -1;
    }

    if (fgets(line, sizeof(line), stream) == NULL) {
        fprintf(stderr, "Calibration trace '%s' is empty.\n", path);
        fclose(stream);
        return -1;
    }
    line[strcspn(line, "\r\n")] = '\0';
    if (strcmp(line, "time_ms,control_target_c") != 0) {
        fprintf(
            stderr,
            "Calibration trace '%s' must start with "
            "'time_ms,control_target_c'.\n",
            path
        );
        fclose(stream);
        return -1;
    }

    while (fgets(line, sizeof(line), stream) != NULL) {
        unsigned int time_ms;
        float control_target_c;
        calibration_trace_sample_t *resized;

        if (parse_trace_row(line, &time_ms, &control_target_c) != 0) {
            fprintf(stderr, "Invalid row in calibration trace '%s'.\n", path);
            free(samples);
            fclose(stream);
            return -1;
        }
        if (time_ms != count * ECU_CONTROL_PERIOD_MS) {
            fprintf(
                stderr,
                "Calibration trace '%s' must contain one ordered sample "
                "every %u ms starting at 0 ms.\n",
                path,
                ECU_CONTROL_PERIOD_MS
            );
            free(samples);
            fclose(stream);
            return -1;
        }
        if (!isfinite(control_target_c) ||
            control_target_c < ECU_CONTROL_TARGET_MIN_C ||
            control_target_c > ECU_CONTROL_TARGET_MAX_C) {
            fprintf(
                stderr,
                "Calibration trace '%s' contains an out-of-range value at "
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
                fprintf(stderr, "Out of memory while loading calibration trace.\n");
                free(samples);
                fclose(stream);
                return -1;
            }
            samples = resized;
            capacity = next_capacity;
        }

        samples[count].time_ms = time_ms;
        samples[count].control_target_c = control_target_c;
        count++;
    }

    fclose(stream);
    if (count == 0U || samples[count - 1U].time_ms < required_duration_ms) {
        fprintf(
            stderr,
            "Calibration trace '%s' does not cover the simulation through "
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

int calibration_trace_get(
    const ecu_state_t *state,
    unsigned int time_ms,
    float *control_target_c
)
{
    const calibration_trace_t *trace = &state->calibration_trace;
    unsigned int index;

    if (!trace->enabled) {
        return 1;
    }
    if ((time_ms % ECU_CONTROL_PERIOD_MS) != 0U) {
        return -1;
    }

    index = time_ms / ECU_CONTROL_PERIOD_MS;
    if (index >= trace->sample_count ||
        trace->samples[index].time_ms != time_ms) {
        return -1;
    }

    *control_target_c = trace->samples[index].control_target_c;
    return 0;
}

void calibration_trace_close(ecu_state_t *state)
{
    reset_trace(&state->calibration_trace);
}
