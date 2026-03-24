#include "logger.h"

#include <errno.h>
#include <string.h>

#include "diagnostics.h"
#include "fault_injection.h"
#include "safety_monitor.h"
#include "thermal_plant.h"

/* Logger module: emits analysis-oriented CSV rows with explicit experiment
 * metadata so campaign outputs can be compared directly across runs. */
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
    fprintf(
        stream,
        ",%d,%s,%d,%s,%u,%u,%.3f",
        event != NULL ? (int)event->mode : (int)FAULT_NONE,
        fault_injection_mode_label(event != NULL ? event->mode : FAULT_NONE),
        event != NULL ? (int)event->behavior : (int)FAULT_BEHAVIOR_NONE,
        fault_injection_behavior_label(event != NULL ? event->behavior : FAULT_BEHAVIOR_NONE),
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
        "experiment_id,campaign_id,campaign_label,campaign_event_count,"
        "tick,time_ms,time_s,"
        "phase_id,phase_label,"
        "active_event_index,active_fault_start_ms,active_fault_duration_ms,active_fault_parameter,"
        "fault_mode_id,fault_mode_label,fault_behavior_id,fault_behavior_label,"
        "safe_state_id,safe_state_label,requested_safe_state_id,requested_safe_state_label,"
        "primary_dtc_id,primary_dtc_label,primary_dtc_class,"
        "ambient_temp_c,engine_speed_rpm,engine_load,vehicle_speed_kph,"
        "coolant_temp_true_c,coolant_temp_meas_c,coolant_sensor_residual_c,"
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

    fprintf(state->log_file, "\n");
    return 0;
}

void logger_write(ecu_state_t *state)
{
    const dtc_status_t *primary_status = primary_dtc_status(state);

    if (state->log_file == NULL) {
        return;
    }

    fprintf(
        state->log_file,
        "%s,%s,%s,%u,"
        "%u,%u,%.3f,"
        "%d,%s,"
        "%d,%u,%u,%.3f,"
        "%d,%s,%d,%s,"
        "%d,%s,%d,%s,"
        "%d,%s,%s,"
        "%.2f,%.2f,%.3f,%.2f,"
        "%.2f,%.2f,%.2f,"
        "%.2f,%.2f,"
        "%.3f,%.3f,%.3f,"
        "%.3f,%.3f,%.3f,"
        "%d,%d,%d,%d,%d,%d,"
        "%u,%u,%u,%u,"
        "%u,%d,%d,%d",
        state->experiment.experiment_id,
        state->experiment.campaign_id,
        state->experiment.campaign_label,
        state->experiment.event_count,
        state->time.tick,
        state->time.time_ms,
        (float)state->time.time_ms / 1000.0f,
        (int)state->plant.scenario_phase,
        thermal_plant_phase_label(state->plant.scenario_phase),
        state->faults.active_event_index,
        state->faults.active_start_ms,
        state->faults.active_duration_ms,
        state->faults.active_parameter,
        (int)state->faults.active_mode,
        fault_injection_mode_label(state->faults.active_mode),
        (int)state->faults.active_behavior,
        fault_injection_behavior_label(state->faults.active_behavior),
        (int)state->safety.current_state,
        safety_monitor_state_label(state->safety.current_state),
        (int)state->safety.requested_state,
        safety_monitor_state_label(state->safety.requested_state),
        (int)state->diagnostics.primary_dtc,
        diagnostics_dtc_label(state->diagnostics.primary_dtc),
        diagnostics_class_label(diagnostics_dtc_class(primary_status)),
        state->plant.ambient_temp_c,
        state->plant.engine_speed_rpm,
        state->plant.engine_load,
        state->plant.vehicle_speed_kph,
        state->plant.coolant_temp_true_c,
        state->sensors.coolant_temp_meas_c,
        state->sensors.coolant_temp_meas_c - state->plant.coolant_temp_true_c,
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
    fprintf(state->log_file, "\n");
}

void logger_close(ecu_state_t *state)
{
    if (state->log_file != NULL) {
        fclose(state->log_file);
        state->log_file = NULL;
    }
}
