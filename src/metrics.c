#include "metrics.h"

#include <errno.h>
#include <string.h>

#include "diagnostics.h"
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
    double pump_mean_abs = 0.0;
    double fan_mean_abs = 0.0;

    derive_summary_path(log_path, summary_path, summary_path_size);

    if (state->metrics.tracking_sample_count > 0U) {
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
        "experiment_id,campaign_id,campaign_label,campaign_event_count,"
        "fault_present_in_campaign,first_fault_start_ms,"
        "detection_latency_ms,detection_dtc_id,detection_dtc_label,"
        "safe_state_latency_ms,first_safe_state_id,first_safe_state_label,"
        "max_coolant_temp_c,safe_mode_duration_ms,"
        "pump_tracking_error_mean_abs,pump_tracking_error_max_abs,"
        "fan_tracking_error_mean_abs,fan_tracking_error_max_abs,"
        "final_coolant_temp_c,final_safe_state_id,final_safe_state_label,"
        "final_primary_dtc_id,final_primary_dtc_label\n"
    );

    fprintf(
        summary_file,
        "%s,%s,%s,%u,%d,%u,%d,%d,%s,%d,%d,%s,%.2f,%u,%.6f,%.6f,%.6f,%.6f,%.2f,%d,%s,%d,%s\n",
        state->experiment.experiment_id,
        state->experiment.campaign_id,
        state->experiment.campaign_label,
        state->experiment.event_count,
        state->metrics.fault_present_in_campaign ? 1 : 0,
        state->metrics.first_fault_start_ms,
        state->metrics.detection_latency_ms,
        (int)state->metrics.detection_dtc_id,
        diagnostics_dtc_label(state->metrics.detection_dtc_id),
        state->metrics.safe_state_latency_ms,
        (int)state->metrics.first_safe_state,
        safe_state_label(state->metrics.first_safe_state),
        state->metrics.max_coolant_temp_c,
        state->metrics.safe_mode_duration_ms,
        pump_mean_abs,
        state->metrics.pump_tracking_error_max_abs,
        fan_mean_abs,
        state->metrics.fan_tracking_error_max_abs,
        state->plant.coolant_temp_true_c,
        (int)state->safety.current_state,
        safe_state_label(state->safety.current_state),
        (int)state->diagnostics.primary_dtc,
        diagnostics_dtc_label(state->diagnostics.primary_dtc)
    );

    fclose(summary_file);
    return 0;
}
