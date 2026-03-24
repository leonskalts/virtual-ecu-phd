#include "logger.h"

#include <errno.h>
#include <string.h>

#include "diagnostics.h"
#include "fault_injection.h"
#include "safety_monitor.h"
#include "thermal_plant.h"

/* Logger module: emits analysis-oriented CSV rows with categorical IDs, human-
 * readable labels, and fault counters suited to plots, tables, and scripts. */
int logger_open(ecu_state_t *state, const char *path)
{
    state->log_file = fopen(path, "w");
    if (state->log_file == NULL) {
        fprintf(stderr, "Failed to open log file '%s': %s\n", path, strerror(errno));
        return -1;
    }

    fprintf(
        state->log_file,
        "tick,time_ms,time_s,"
        "phase_id,phase_label,"
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
        "safe_state_transitions,max_cooling_active,torque_derate_active,shutdown_requested\n"
    );

    return 0;
}

void logger_write(ecu_state_t *state)
{
    if (state->log_file == NULL) {
        return;
    }

    fprintf(
        state->log_file,
        "%u,%u,%.3f,%d,%s,%d,%s,%d,%s,%d,%s,%d,%s,%d,%s,%s,"
        "%.2f,%.2f,%.3f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,"
        "%d,%d,%d,%d,%d,%d,%u,%u,%u,%u,%u,%d,%d,%d\n",
        state->time.tick,
        state->time.time_ms,
        (float)state->time.time_ms / 1000.0f,
        (int)state->plant.scenario_phase,
        thermal_plant_phase_label(state->plant.scenario_phase),
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
        diagnostics_class_label(
            diagnostics_dtc_class(
                state->diagnostics.primary_dtc == DTC_ID_COOLANT_SENSOR_RATIONALITY ?
                    &state->diagnostics.coolant_sensor_dtc :
                state->diagnostics.primary_dtc == DTC_ID_COOLANT_OVER_TEMP_WARNING ?
                    &state->diagnostics.overtemp_warning_dtc :
                state->diagnostics.primary_dtc == DTC_ID_COOLANT_OVER_TEMP_CRITICAL ?
                    &state->diagnostics.overtemp_critical_dtc :
                state->diagnostics.primary_dtc == DTC_ID_COOLING_PERFORMANCE_LOW ?
                    &state->diagnostics.cooling_performance_dtc :
                state->diagnostics.primary_dtc == DTC_ID_PUMP_TRACKING_FAULT ?
                    &state->diagnostics.pump_tracking_dtc :
                state->diagnostics.primary_dtc == DTC_ID_FAN_TRACKING_FAULT ?
                    &state->diagnostics.fan_tracking_dtc :
                    &state->diagnostics.overtemp_warning_dtc
            )
        ),
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
}

void logger_close(ecu_state_t *state)
{
    if (state->log_file != NULL) {
        fclose(state->log_file);
        state->log_file = NULL;
    }
}
