#include "metrics.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include "diagnostics.h"
#include "detection_algorithm.h"
#include "safety_monitor.h"

/* Metrics module: accumulates paper-oriented run metrics so campaign
 * comparisons can be made from a compact summary CSV rather than raw traces. */
static float abs_float(float value)
{
    return (value < 0.0f) ? -value : value;
}

static void derive_summary_path(const char *log_path, char *summary_path, size_t summary_path_size)
{
    size_t len = strlen(log_path);

    if (len >= 4U && strcmp(log_path + len - 4U, ".csv") == 0) {
        snprintf(summary_path, summary_path_size, "%.*s_summary.csv", (int)(len - 4U), log_path);
        return;
    }

    snprintf(summary_path, summary_path_size, "%s_summary.csv", log_path);
}

static const char *safe_state_label(safe_state_t state)
{
    return safety_monitor_state_label(state);
}

static void csv_write_text(FILE *stream, const char *text)
{
    const char *cursor = (text != NULL) ? text : "";

    fputc('"', stream);
    while (*cursor != '\0') {
        if (*cursor == '"') {
            fputc('"', stream);
        }
        fputc(*cursor, stream);
        cursor++;
    }
    fputc('"', stream);
}

typedef struct {
    bool available;
    float max_coolant_temp_c;
    unsigned int safe_mode_duration_ms;
    double pump_tracking_error_abs_sum;
    double fan_tracking_error_abs_sum;
    float pump_tracking_error_max_abs;
    float fan_tracking_error_max_abs;
    unsigned int tracking_sample_count;
} trace_metrics_t;

static char *next_csv_field(char **cursor)
{
    char *scan = *cursor;
    char *field_start = *cursor;
    char *write = *cursor;

    if (*scan == '"') {
        scan++;
        field_start = write;

        while (*scan != '\0') {
            if (*scan == '"' && scan[1] == '"') {
                *write++ = '"';
                scan += 2;
            } else if (*scan == '"') {
                scan++;
                break;
            } else {
                *write++ = *scan++;
            }
        }

        *write = '\0';
        while (*scan == '\r' || *scan == '\n') {
            scan++;
        }
        if (*scan == ',') {
            scan++;
        }
        *cursor = scan;
        return field_start;
    }

    while (*scan != '\0' && *scan != ',' && *scan != '\n' && *scan != '\r') {
        scan++;
    }

    if (*scan == ',') {
        *scan = '\0';
        *cursor = scan + 1;
    } else {
        *scan = '\0';
        *cursor = scan;
    }

    return field_start;
}

static int find_csv_column(const char *header_line, const char *column_name)
{
    char header_copy[4096];
    char *cursor = header_copy;
    int index = 0;

    snprintf(header_copy, sizeof(header_copy), "%s", header_line);

    while (*cursor != '\0') {
        char *field = next_csv_field(&cursor);

        if (strcmp(field, column_name) == 0) {
            return index;
        }

        if (*cursor == '\0') {
            break;
        }

        index++;
    }

    return -1;
}

static int extract_trace_metrics(const char *log_path, trace_metrics_t *trace)
{
    FILE *log_file;
    char line[4096];
    int coolant_index;
    int safe_state_index;
    int pump_error_index;
    int fan_error_index;

    memset(trace, 0, sizeof(*trace));

    log_file = fopen(log_path, "r");
    if (log_file == NULL) {
        return -1;
    }

    if (fgets(line, sizeof(line), log_file) == NULL) {
        fclose(log_file);
        return -1;
    }

    coolant_index = find_csv_column(line, "coolant_temp_true_c");
    safe_state_index = find_csv_column(line, "safe_state_id");
    pump_error_index = find_csv_column(line, "pump_tracking_error");
    fan_error_index = find_csv_column(line, "fan_tracking_error");

    if (coolant_index < 0 || safe_state_index < 0 || pump_error_index < 0 || fan_error_index < 0) {
        fclose(log_file);
        return -1;
    }

    while (fgets(line, sizeof(line), log_file) != NULL) {
        char row_copy[4096];
        char *cursor = row_copy;
        float coolant_temp_c = 0.0f;
        float pump_tracking_error = 0.0f;
        float fan_tracking_error = 0.0f;
        int safe_state_id = 0;
        int column = 0;

        snprintf(row_copy, sizeof(row_copy), "%s", line);

        while (*cursor != '\0') {
            char *field = next_csv_field(&cursor);

            if (column == coolant_index) {
                coolant_temp_c = strtof(field, NULL);
            } else if (column == safe_state_index) {
                safe_state_id = (int)strtol(field, NULL, 10);
            } else if (column == pump_error_index) {
                pump_tracking_error = abs_float(strtof(field, NULL));
            } else if (column == fan_error_index) {
                fan_tracking_error = abs_float(strtof(field, NULL));
            }

            if (*cursor == '\0') {
                break;
            }

            column++;
        }

        if (!trace->available || coolant_temp_c > trace->max_coolant_temp_c) {
            trace->max_coolant_temp_c = coolant_temp_c;
        }

        if (safe_state_id != (int)SAFE_STATE_NORMAL) {
            trace->safe_mode_duration_ms += ECU_LOG_PERIOD_MS;
        }

        trace->pump_tracking_error_abs_sum += pump_tracking_error;
        trace->fan_tracking_error_abs_sum += fan_tracking_error;
        trace->tracking_sample_count++;

        if (pump_tracking_error > trace->pump_tracking_error_max_abs) {
            trace->pump_tracking_error_max_abs = pump_tracking_error;
        }

        if (fan_tracking_error > trace->fan_tracking_error_max_abs) {
            trace->fan_tracking_error_max_abs = fan_tracking_error;
        }

        trace->available = true;
    }

    fclose(log_file);
    return trace->available ? 0 : -1;
}

static void init_first_fault_metadata(ecu_state_t *state)
{
    unsigned int i;
    bool found = false;

    state->metrics.fault_present_in_campaign = false;
    state->metrics.first_fault_start_ms = 0U;

    for (i = 0U; i < state->experiment.event_count; i++) {
        if (state->experiment.events[i].mode == FAULT_NONE) {
            continue;
        }

        if (!found || state->experiment.events[i].start_ms < state->metrics.first_fault_start_ms) {
            state->metrics.first_fault_start_ms = state->experiment.events[i].start_ms;
            found = true;
        }
    }

    state->metrics.fault_present_in_campaign = found;
}

void metrics_init(ecu_state_t *state)
{
    memset(&state->metrics, 0, sizeof(state->metrics));
    init_first_fault_metadata(state);
    state->metrics.detection_dtc_id = DTC_ID_NONE;
    state->metrics.first_safe_state = SAFE_STATE_NORMAL;
    state->metrics.detection_latency_ms = -1;
    state->metrics.safe_state_latency_ms = -1;
    state->metrics.max_coolant_temp_c = state->plant.coolant_temp_true_c;
}

void metrics_step(ecu_state_t *state)
{
    float pump_abs_error = abs_float(state->control.pump_command - state->actuators.pump_actual);
    float fan_abs_error = abs_float(state->control.fan_command - state->actuators.fan_actual);

    if (state->plant.coolant_temp_true_c > state->metrics.max_coolant_temp_c) {
        state->metrics.max_coolant_temp_c = state->plant.coolant_temp_true_c;
    }

    if (state->safety.current_state != SAFE_STATE_NORMAL) {
        state->metrics.safe_mode_duration_ms += ECU_DT_MS;
    }

    state->metrics.pump_tracking_error_abs_sum += pump_abs_error;
    state->metrics.fan_tracking_error_abs_sum += fan_abs_error;
    state->metrics.tracking_sample_count++;

    if (pump_abs_error > state->metrics.pump_tracking_error_max_abs) {
        state->metrics.pump_tracking_error_max_abs = pump_abs_error;
    }

    if (fan_abs_error > state->metrics.fan_tracking_error_max_abs) {
        state->metrics.fan_tracking_error_max_abs = fan_abs_error;
    }

    if (state->metrics.fault_present_in_campaign &&
        state->time.time_ms >= state->metrics.first_fault_start_ms &&
        state->metrics.detection_latency_ms < 0 &&
        state->diagnostics.primary_dtc != DTC_ID_NONE) {
        state->metrics.detection_latency_ms =
            (int)(state->time.time_ms - state->metrics.first_fault_start_ms);
        state->metrics.detection_dtc_id = state->diagnostics.primary_dtc;
    }

    if (state->metrics.fault_present_in_campaign &&
        state->time.time_ms >= state->metrics.first_fault_start_ms &&
        state->metrics.safe_state_latency_ms < 0 &&
        state->safety.current_state != SAFE_STATE_NORMAL) {
        state->metrics.safe_state_latency_ms =
            (int)(state->time.time_ms - state->metrics.first_fault_start_ms);
        state->metrics.first_safe_state = state->safety.current_state;
    }
}

int metrics_write_summary(const ecu_state_t *state, const char *log_path, char *summary_path, size_t summary_path_size)
{
    FILE *summary_file;
    trace_metrics_t trace_metrics;
    float max_coolant_temp_c = state->metrics.max_coolant_temp_c;
    unsigned int safe_mode_duration_ms = state->metrics.safe_mode_duration_ms;
    double pump_mean_abs = 0.0;
    double fan_mean_abs = 0.0;

    derive_summary_path(log_path, summary_path, summary_path_size);

    if (extract_trace_metrics(log_path, &trace_metrics) == 0 && trace_metrics.tracking_sample_count > 0U) {
        max_coolant_temp_c = trace_metrics.max_coolant_temp_c;
        safe_mode_duration_ms = trace_metrics.safe_mode_duration_ms;
        pump_mean_abs = trace_metrics.pump_tracking_error_abs_sum / (double)trace_metrics.tracking_sample_count;
        fan_mean_abs = trace_metrics.fan_tracking_error_abs_sum / (double)trace_metrics.tracking_sample_count;
    } else if (state->metrics.tracking_sample_count > 0U) {
        pump_mean_abs = state->metrics.pump_tracking_error_abs_sum / (double)state->metrics.tracking_sample_count;
        fan_mean_abs = state->metrics.fan_tracking_error_abs_sum / (double)state->metrics.tracking_sample_count;
    }

    summary_file = fopen(summary_path, "w");
    if (summary_file == NULL) {
        fprintf(stderr, "Failed to open summary file '%s': %s\n", summary_path, strerror(errno));
        return -1;
    }

    fprintf(
        summary_file,
        "experiment_id,campaign_id,campaign_label,campaign_category,campaign_event_count,"
        "campaign_ambient_offset_c,campaign_engine_load_scale,campaign_heat_generation_bias,campaign_ram_air_scale,"
        "fault_present_in_campaign,first_fault_start_ms,"
        "detection_latency_ms,detection_dtc_id,detection_dtc_label,"
        "safe_state_latency_ms,first_safe_state_id,first_safe_state_label,"
        "max_coolant_temp_c,safe_mode_duration_ms,"
        "pump_tracking_error_mean_abs,pump_tracking_error_max_abs,"
        "fan_tracking_error_mean_abs,fan_tracking_error_max_abs,"
        "final_coolant_temp_c,final_safe_state_id,final_safe_state_label,"
        "final_primary_dtc_id,final_primary_dtc_label,"
        "runtime_detection_algorithm,runtime_detection_first_detection_ms,"
        "runtime_detection_latency_ms,runtime_detection_detected,"
        "runtime_detection_action,runtime_detection_action_requested,"
        "runtime_detection_requested_safe_state,runtime_detection_action_time_ms,"
        "runtime_detection_action_reason,runtime_detection_label\n"
    );

    csv_write_text(summary_file, state->experiment.experiment_id);
    fputc(',', summary_file);
    csv_write_text(summary_file, state->experiment.campaign_id);
    fputc(',', summary_file);
    csv_write_text(summary_file, state->experiment.campaign_label);
    fputc(',', summary_file);
    csv_write_text(summary_file, state->experiment.campaign_category);
    fprintf(summary_file, ",%u", state->experiment.event_count);
    fprintf(summary_file, ",%.2f", state->experiment.ambient_offset_c);
    fprintf(summary_file, ",%.3f", state->experiment.engine_load_scale);
    fprintf(summary_file, ",%.3f", state->experiment.heat_generation_bias);
    fprintf(summary_file, ",%.3f", state->experiment.ram_air_scale);
    fprintf(summary_file, ",%d", state->metrics.fault_present_in_campaign ? 1 : 0);
    fprintf(summary_file, ",%u", state->metrics.first_fault_start_ms);
    fprintf(summary_file, ",%d", state->metrics.detection_latency_ms);
    fprintf(summary_file, ",%d", (int)state->metrics.detection_dtc_id);
    fputc(',', summary_file);
    csv_write_text(summary_file, diagnostics_dtc_label(state->metrics.detection_dtc_id));
    fprintf(summary_file, ",%d", state->metrics.safe_state_latency_ms);
    fprintf(summary_file, ",%d", (int)state->metrics.first_safe_state);
    fputc(',', summary_file);
    csv_write_text(summary_file, safe_state_label(state->metrics.first_safe_state));
    fprintf(summary_file, ",%.2f", max_coolant_temp_c);
    fprintf(summary_file, ",%u", safe_mode_duration_ms);
    fprintf(summary_file, ",%.6f", pump_mean_abs);
    fprintf(
        summary_file,
        ",%.6f",
        (double)(trace_metrics.available ? trace_metrics.pump_tracking_error_max_abs :
                  state->metrics.pump_tracking_error_max_abs)
    );
    fprintf(summary_file, ",%.6f", fan_mean_abs);
    fprintf(
        summary_file,
        ",%.6f",
        (double)(trace_metrics.available ? trace_metrics.fan_tracking_error_max_abs :
                  state->metrics.fan_tracking_error_max_abs)
    );
    fprintf(summary_file, ",%.2f", state->plant.coolant_temp_true_c);
    fprintf(summary_file, ",%d", (int)state->safety.current_state);
    fputc(',', summary_file);
    csv_write_text(summary_file, safe_state_label(state->safety.current_state));
    fprintf(summary_file, ",%d", (int)state->diagnostics.primary_dtc);
    fputc(',', summary_file);
    csv_write_text(summary_file, diagnostics_dtc_label(state->diagnostics.primary_dtc));
    fputc(',', summary_file);
    csv_write_text(
        summary_file,
        detection_algorithm_name(state->detection.selected_algorithm)
    );
    fprintf(summary_file, ",%d", state->detection.first_detection_time_ms);
    fprintf(
        summary_file,
        ",%d",
        (
            state->detection.first_detection_time_ms >= 0 &&
            state->metrics.fault_present_in_campaign
        ) ?
            state->detection.first_detection_time_ms -
                (int)state->metrics.first_fault_start_ms :
            -1
    );
    fprintf(summary_file, ",%d", state->detection.detected ? 1 : 0);
    fputc(',', summary_file);
    csv_write_text(
        summary_file,
        detection_action_name(state->detection.selected_action)
    );
    fprintf(
        summary_file,
        ",%d,",
        state->detection.action_requested ? 1 : 0
    );
    csv_write_text(
        summary_file,
        state->detection.action_requested ?
            safety_monitor_state_label(state->safety.requested_state) :
            "none"
    );
    fprintf(summary_file, ",%d,", state->detection.action_time_ms);
    csv_write_text(summary_file, state->detection.action_reason);
    fputc(',', summary_file);
    csv_write_text(summary_file, state->detection.runtime_label);
    fputc('\n', summary_file);

    fclose(summary_file);
    return 0;
}
