#ifndef ECU_TYPES_H
#define ECU_TYPES_H

#include <stdbool.h>
#include <stdio.h>

typedef enum {
    FAULT_NONE = 0,
    FAULT_SENSOR_BIAS,
    FAULT_PUMP_DEGRADED,
    FAULT_FAN_STUCK_OFF
} fault_mode_t;

typedef struct {
    float ambient_temp_c;
    float engine_load;
    float engine_speed_rpm;
    float vehicle_speed_kph;
    float coolant_temp_true_c;
    float radiator_temp_true_c;
} plant_state_t;

typedef struct {
    float coolant_temp_meas_c;
    float radiator_temp_meas_c;
    float ambient_temp_meas_c;
    float vehicle_speed_meas_kph;
} sensor_data_t;

typedef struct {
    float pump_command;
    float fan_command;
} control_output_t;

typedef struct {
    float pump_actual;
    float fan_actual;
} actuator_feedback_t;

typedef struct {
    bool overtemp_warning;
    bool overtemp_critical;
    bool sensor_implausible;
    bool cooling_performance_low;
    bool actuator_fault;
} diagnostic_flags_t;

typedef struct {
    bool limp_home_active;
    bool emergency_cooling_active;
} safety_status_t;

typedef struct {
    fault_mode_t active_mode;
    bool enabled;
    float sensor_bias_c;
    float pump_scale;
} fault_state_t;

typedef struct {
    unsigned int tick;
    unsigned int time_ms;
} scheduler_time_t;

typedef struct {
    scheduler_time_t time;
    plant_state_t plant;
    sensor_data_t sensors;
    control_output_t control;
    actuator_feedback_t actuators;
    diagnostic_flags_t diagnostics;
    safety_status_t safety;
    fault_state_t faults;
    FILE *log_file;
} ecu_state_t;

#endif
