#include "logger.h"

#include <errno.h>
#include <string.h>

int logger_open(ecu_state_t *state, const char *path)
{
    state->log_file = fopen(path, "w");
    if (state->log_file == NULL) {
        fprintf(stderr, "Failed to open log file '%s': %s\n", path, strerror(errno));
        return -1;
    }

    fprintf(
        state->log_file,
        "time_ms,ambient_temp_c,engine_load,vehicle_speed_kph,"
        "coolant_temp_true_c,coolant_temp_meas_c,radiator_temp_true_c,radiator_temp_meas_c,"
        "pump_command,pump_actual,fan_command,fan_actual,"
        "fault_mode,warning,critical,sensor_implausible,cooling_performance_low,"
        "actuator_fault,limp_home,emergency_cooling\n"
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
        "%u,%.2f,%.3f,%.2f,%.2f,%.2f,%.2f,%.2f,%.3f,%.3f,%.3f,%.3f,%d,%d,%d,%d,%d,%d,%d,%d\n",
        state->time.time_ms,
        state->plant.ambient_temp_c,
        state->plant.engine_load,
        state->plant.vehicle_speed_kph,
        state->plant.coolant_temp_true_c,
        state->sensors.coolant_temp_meas_c,
        state->plant.radiator_temp_true_c,
        state->sensors.radiator_temp_meas_c,
        state->control.pump_command,
        state->actuators.pump_actual,
        state->control.fan_command,
        state->actuators.fan_actual,
        (int)state->faults.active_mode,
        state->diagnostics.overtemp_warning ? 1 : 0,
        state->diagnostics.overtemp_critical ? 1 : 0,
        state->diagnostics.sensor_implausible ? 1 : 0,
        state->diagnostics.cooling_performance_low ? 1 : 0,
        state->diagnostics.actuator_fault ? 1 : 0,
        state->safety.limp_home_active ? 1 : 0,
        state->safety.emergency_cooling_active ? 1 : 0
    );
}

void logger_close(ecu_state_t *state)
{
    if (state->log_file != NULL) {
        fclose(state->log_file);
        state->log_file = NULL;
    }
}
