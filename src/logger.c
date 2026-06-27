#include "logger.h"

#include <errno.h>
#include <string.h>

#include "diagnostics.h"
#include "detection_algorithm.h"
#include "fault_injection.h"
#include "safety_monitor.h"
#include "thermal_plant.h"

/* Logger module: emits analysis-oriented CSV rows with explicit experiment
 * metadata so campaign outputs can be compared directly across runs. */
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

static const fault_event_t *event_or_null(const ecu_state_t *state, unsigned int index)
{
    if (index >= state->experiment.event_count || index >= ECU_MAX_FAULT_EVENTS) {
        return NULL;
    }

    return &state->experiment.events[index];
}

static const dtc_status_t *primary_dtc_status(const ecu_state_t *state)
{
    switch (state->diagnostics.primary_dtc) {
    case DTC_ID_COOLANT_SENSOR_RATIONALITY:
        return &state->diagnostics.coolant_sensor_dtc;
    case DTC_ID_COOLANT_OVER_TEMP_WARNING:
        return &state->diagnostics.overtemp_warning_dtc;
    case DTC_ID_COOLANT_OVER_TEMP_CRITICAL:
        return &state->diagnostics.overtemp_critical_dtc;
    case DTC_ID_COOLING_PERFORMANCE_LOW:
        return &state->diagnostics.cooling_performance_dtc;
    case DTC_ID_PUMP_TRACKING_FAULT:
        return &state->diagnostics.pump_tracking_dtc;
    case DTC_ID_FAN_TRACKING_FAULT:
        return &state->diagnostics.fan_tracking_dtc;
    case DTC_ID_NONE:
    default:
        return &state->diagnostics.overtemp_warning_dtc;
    }
}

static void write_campaign_event(FILE *stream, const fault_event_t *event)
{
    fprintf(stream, ",%d,", event != NULL ? (int)event->mode : (int)FAULT_NONE);
    csv_write_text(stream, fault_injection_mode_label(event != NULL ? event->mode : FAULT_NONE));
    fprintf(stream, ",%d,", event != NULL ? (int)event->behavior : (int)FAULT_BEHAVIOR_NONE);
    csv_write_text(
        stream,
        fault_injection_behavior_label(event != NULL ? event->behavior : FAULT_BEHAVIOR_NONE)
    );
    fprintf(
        stream,
        ",%u,%u,%.3f",
        event != NULL ? event->start_ms : 0U,
        event != NULL ? event->duration_ms : 0U,
        event != NULL ? event->parameter : 0.0f
    );
}

int logger_open(ecu_state_t *state, const char *path)
{
    unsigned int i;

    state->log_file = fopen(path, "w");
    if (state->log_file == NULL) {
        fprintf(stderr, "Failed to open log file '%s': %s\n", path, strerror(errno));
        return -1;
    }

    fprintf(
        state->log_file,
        "experiment_id,campaign_id,campaign_label,campaign_category,campaign_event_count,"
        "campaign_ambient_offset_c,campaign_engine_load_scale,campaign_heat_generation_bias,campaign_ram_air_scale,"
        "tick,time_ms,time_s,"
        "phase_id,phase_label,"
        "active_event_index,active_fault_start_ms,active_fault_duration_ms,active_fault_parameter,"
        "fault_mode_id,fault_mode_label,fault_behavior_id,fault_behavior_label,"
        "safe_state_id,safe_state_label,requested_safe_state_id,requested_safe_state_label,"
        "primary_dtc_id,primary_dtc_label,primary_dtc_class,"
        "ambient_temp_c,engine_speed_rpm,engine_load,vehicle_speed_kph,"
        "coolant_temp_true_c,coolant_temp_meas_c,coolant_sensor_residual_c,"
        "coolant_sensor_last_update_ms,coolant_sensor_update_age_ms,"
        "coolant_sensor_expected_period_ms,coolant_sensor_freshness_score,"
        "coolant_sensor_freshness_ok,"
        "radiator_temp_true_c,radiator_temp_meas_c,"
        "pump_command,pump_actual,pump_tracking_error,"
        "fan_command,fan_actual,fan_tracking_error,"
        "overtemp_warning,overtemp_critical,coolant_sensor_fault,cooling_performance_low,"
        "pump_tracking_fault,fan_tracking_fault,"
        "coolant_sensor_fail_count,pump_fail_count,fan_fail_count,cooling_perf_fail_count,"
        "safe_state_transitions,max_cooling_active,torque_derate_active,shutdown_requested"
    );

    for (i = 0U; i < ECU_MAX_FAULT_EVENTS; i++) {
        fprintf(
            state->log_file,
            ",campaign_event_%u_mode_id,campaign_event_%u_mode_label,"
            "campaign_event_%u_behavior_id,campaign_event_%u_behavior_label,"
            "campaign_event_%u_start_ms,campaign_event_%u_duration_ms,campaign_event_%u_parameter",
            i + 1U, i + 1U, i + 1U, i + 1U, i + 1U, i + 1U, i + 1U
        );
    }

    fprintf(
        state->log_file,
        ",runtime_detection_algorithm,runtime_detection_score,"
        "runtime_detection_alarm,runtime_detection_detected,"
        "runtime_detection_first_detection_ms,runtime_detection_latency_ms,"
        "runtime_detection_false_positive_count,runtime_detection_label,"
        "runtime_detection_action,runtime_detection_action_requested,"
        "runtime_detection_requested_safe_state,runtime_detection_action_time_ms,"
        "runtime_detection_action_reason\n"
    );
    return 0;
}

void logger_write(ecu_state_t *state)
{
    const dtc_status_t *primary_status = primary_dtc_status(state);

    if (state->log_file == NULL) {
        return;
    }

    csv_write_text(state->log_file, state->experiment.experiment_id);
    fputc(',', state->log_file);
    csv_write_text(state->log_file, state->experiment.campaign_id);
    fputc(',', state->log_file);
    csv_write_text(state->log_file, state->experiment.campaign_label);
    fputc(',', state->log_file);
    csv_write_text(state->log_file, state->experiment.campaign_category);
    fprintf(
        state->log_file,
        ",%u,%.2f,%.3f,%.3f,%.3f"
        ",%u,%u,%.3f"
        ",%d,",
        state->experiment.event_count,
        state->experiment.ambient_offset_c,
        state->experiment.engine_load_scale,
        state->experiment.heat_generation_bias,
        state->experiment.ram_air_scale,
        state->time.tick,
        state->time.time_ms,
        (float)state->time.time_ms / 1000.0f,
        (int)state->plant.scenario_phase
    );
    csv_write_text(state->log_file, thermal_plant_phase_label(state->plant.scenario_phase));
    fprintf(
        state->log_file,
        ",%d,%u,%u,%.3f,%d,",
        state->faults.active_event_index,
        state->faults.active_start_ms,
        state->faults.active_duration_ms,
        state->faults.active_parameter,
        (int)state->faults.active_mode
    );
    csv_write_text(state->log_file, fault_injection_mode_label(state->faults.active_mode));
    fprintf(state->log_file, ",%d,", (int)state->faults.active_behavior);
    csv_write_text(state->log_file, fault_injection_behavior_label(state->faults.active_behavior));
    fprintf(state->log_file, ",%d,", (int)state->safety.current_state);
    csv_write_text(state->log_file, safety_monitor_state_label(state->safety.current_state));
    fprintf(state->log_file, ",%d,", (int)state->safety.requested_state);
    csv_write_text(state->log_file, safety_monitor_state_label(state->safety.requested_state));
    fprintf(state->log_file, ",%d,", (int)state->diagnostics.primary_dtc);
    csv_write_text(state->log_file, diagnostics_dtc_label(state->diagnostics.primary_dtc));
    fputc(',', state->log_file);
    csv_write_text(state->log_file, diagnostics_class_label(diagnostics_dtc_class(primary_status)));
    fprintf(
        state->log_file,
        ",%.2f,%.2f,%.3f,%.2f"
        ",%.2f,%.2f,%.2f"
        ",%u,%u,%u,%.3f,%d"
        ",%.2f,%.2f"
        ",%.3f,%.3f,%.3f"
        ",%.3f,%.3f,%.3f"
        ",%d,%d,%d,%d,%d,%d"
        ",%u,%u,%u,%u"
        ",%u,%d,%d,%d",
        state->plant.ambient_temp_c,
        state->plant.engine_speed_rpm,
        state->plant.engine_load,
        state->plant.vehicle_speed_kph,
        state->plant.coolant_temp_true_c,
        state->sensors.coolant_temp_meas_c,
        state->sensors.coolant_temp_meas_c - state->plant.coolant_temp_true_c,
        state->sensors.coolant_sensor_last_update_ms,
        state->sensors.coolant_sensor_update_age_ms,
        state->sensors.coolant_sensor_expected_period_ms,
        state->sensors.coolant_sensor_freshness_score,
        state->sensors.coolant_sensor_freshness_ok ? 1 : 0,
        state->plant.radiator_temp_true_c,
        state->sensors.radiator_temp_meas_c,
        state->control.pump_command,
        state->actuators.pump_actual,
        state->control.pump_command - state->actuators.pump_actual,
        state->control.fan_command,
        state->actuators.fan_actual,
        state->control.fan_command - state->actuators.fan_actual,
        state->diagnostics.overtemp_warning ? 1 : 0,
        state->diagnostics.overtemp_critical ? 1 : 0,
        state->diagnostics.coolant_sensor_rationality_fault ? 1 : 0,
        state->diagnostics.cooling_performance_low ? 1 : 0,
        state->diagnostics.pump_tracking_fault ? 1 : 0,
        state->diagnostics.fan_tracking_fault ? 1 : 0,
        state->diagnostics.coolant_sensor_dtc.fail_count,
        state->diagnostics.pump_tracking_dtc.fail_count,
        state->diagnostics.fan_tracking_dtc.fail_count,
        state->diagnostics.cooling_performance_dtc.fail_count,
        state->safety.transition_count,
        state->safety.max_cooling_active ? 1 : 0,
        state->safety.torque_derate_active ? 1 : 0,
        state->safety.shutdown_requested ? 1 : 0
    );

    write_campaign_event(state->log_file, event_or_null(state, 0U));
    write_campaign_event(state->log_file, event_or_null(state, 1U));
    write_campaign_event(state->log_file, event_or_null(state, 2U));
    write_campaign_event(state->log_file, event_or_null(state, 3U));
    fputc(',', state->log_file);
    csv_write_text(
        state->log_file,
        detection_algorithm_name(state->detection.selected_algorithm)
    );
    fprintf(
        state->log_file,
        ",%.6f,%d,%d,%d,%d,%u,",
        state->detection.current_score,
        state->detection.alarm_active ? 1 : 0,
        state->detection.detected ? 1 : 0,
        state->detection.first_detection_time_ms,
        (
            state->detection.first_detection_time_ms >= 0 &&
            state->metrics.fault_present_in_campaign
        ) ?
            state->detection.first_detection_time_ms -
                (int)state->metrics.first_fault_start_ms :
            -1,
        state->detection.false_positive_count
    );
    csv_write_text(state->log_file, state->detection.runtime_label);
    fputc(',', state->log_file);
    csv_write_text(
        state->log_file,
        detection_action_name(state->detection.selected_action)
    );
    fprintf(
        state->log_file,
        ",%d,",
        state->detection.action_requested ? 1 : 0
    );
    csv_write_text(
        state->log_file,
        state->detection.action_requested ?
            safety_monitor_state_label(state->safety.requested_state) :
            "none"
    );
    fprintf(state->log_file, ",%d,", state->detection.action_time_ms);
    csv_write_text(state->log_file, state->detection.action_reason);
    fprintf(state->log_file, "\n");
}

void logger_close(ecu_state_t *state)
{
    if (state->log_file != NULL) {
        fclose(state->log_file);
        state->log_file = NULL;
    }
}
