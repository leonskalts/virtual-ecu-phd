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

typedef enum {
    FAULT_BEHAVIOR_NONE = 0,
    FAULT_BEHAVIOR_TRANSIENT,
    FAULT_BEHAVIOR_PERMANENT
} fault_behavior_t;

typedef enum {
    SCENARIO_PHASE_WARMUP = 0,
    SCENARIO_PHASE_HIGHWAY,
    SCENARIO_PHASE_URBAN_TRAFFIC,
    SCENARIO_PHASE_HOT_IDLE
} scenario_phase_t;

typedef enum {
    DIAG_CLASS_NONE = 0,
    DIAG_CLASS_TRANSIENT,
    DIAG_CLASS_PERSISTENT,
    DIAG_CLASS_PERMANENT
} diagnostic_class_t;

typedef enum {
    DTC_ID_NONE = 0,
    DTC_ID_COOLANT_SENSOR_RATIONALITY = 1001,
    DTC_ID_COOLANT_OVER_TEMP_WARNING = 2001,
    DTC_ID_COOLANT_OVER_TEMP_CRITICAL = 2002,
    DTC_ID_COOLING_PERFORMANCE_LOW = 3001,
    DTC_ID_PUMP_TRACKING_FAULT = 3002,
    DTC_ID_FAN_TRACKING_FAULT = 3003
} diagnostic_id_t;

typedef enum {
    SAFE_STATE_NORMAL = 0,
    SAFE_STATE_PRECAUTIONARY_COOLING,
    SAFE_STATE_LIMP_HOME,
    SAFE_STATE_CONTROLLED_SHUTDOWN
} safe_state_t;

typedef struct {
    scenario_phase_t scenario_phase;
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
    diagnostic_id_t id;
    unsigned int fail_count;
    unsigned int pass_count;
    bool test_failed;
    bool pending;
    bool confirmed;
    bool permanent_latched;
} dtc_status_t;

typedef struct {
    bool overtemp_warning;
    bool overtemp_critical;
    bool coolant_sensor_rationality_fault;
    bool cooling_performance_low;
    bool pump_tracking_fault;
    bool fan_tracking_fault;
    dtc_status_t coolant_sensor_dtc;
    dtc_status_t overtemp_warning_dtc;
    dtc_status_t overtemp_critical_dtc;
    dtc_status_t cooling_performance_dtc;
    dtc_status_t pump_tracking_dtc;
    dtc_status_t fan_tracking_dtc;
    diagnostic_id_t primary_dtc;
} diagnostic_flags_t;

typedef struct {
    safe_state_t current_state;
    safe_state_t requested_state;
    unsigned int recovery_counter;
    unsigned int transition_count;
    bool max_cooling_active;
    bool torque_derate_active;
    bool shutdown_requested;
    float load_limit_scale;
} safety_status_t;

typedef struct {
    fault_mode_t active_mode;
    fault_behavior_t active_behavior;
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
