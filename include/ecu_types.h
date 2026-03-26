#ifndef ECU_TYPES_H
#define ECU_TYPES_H

#include "config.h"

#include <stdbool.h>
#include <stdio.h>

typedef enum {
    FAULT_NONE = 0,
    /* Sensing-path abstraction: ADC/reference/front-end offset. */
    FAULT_SENSOR_BIAS,
    /* Sensing-path abstraction: intermittent interface corruption or sampling glitch. */
    FAULT_SENSOR_INTERFACE_INTERMITTENT,
    /* Timing/communication-path abstraction: delayed sampled-data refresh so
     * the ECU consumes stale coolant measurements for multiple control steps. */
    FAULT_STALE_SENSOR_DATA,
    /* Actuation-path abstraction: weak driver, aging, or supply-droop degradation. */
    FAULT_PUMP_DEGRADED,
    /* Actuation-path abstraction: PWM, gate-driver, or power-stage stuck-off fault. */
    FAULT_FAN_STUCK_OFF,
    /* Computation/memory-path abstraction: corrupted calibration register or
     * nonvolatile control parameter affecting the ECU cooling target. */
    FAULT_CALIBRATION_MEMORY_CORRUPTION
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
    fault_mode_t mode;
    fault_behavior_t behavior;
    unsigned int start_ms;
    unsigned int duration_ms;
    float parameter;
} fault_event_t;

typedef struct {
    char experiment_id[64];
    char campaign_id[32];
    char campaign_label[96];
    char campaign_category[32];
    unsigned int event_count;
    float ambient_offset_c;
    float engine_load_scale;
    float heat_generation_bias;
    float ram_air_scale;
    fault_event_t events[ECU_MAX_FAULT_EVENTS];
} experiment_config_t;

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
    int active_event_index;
    bool enabled;
    unsigned int active_start_ms;
    unsigned int active_duration_ms;
    float active_parameter;
    float sensor_bias_c;
    float sensor_intermittent_amplitude_c;
    unsigned int sensor_update_hold_ms;
    unsigned int stale_sample_timestamp_ms;
    float stale_coolant_temp_c;
    bool stale_sample_valid;
    float pump_scale;
    float control_target_offset_c;
} fault_state_t;

typedef struct {
    bool fault_present_in_campaign;
    unsigned int first_fault_start_ms;
    diagnostic_id_t detection_dtc_id;
    safe_state_t first_safe_state;
    int detection_latency_ms;
    int safe_state_latency_ms;
    unsigned int safe_mode_duration_ms;
    float max_coolant_temp_c;
    double pump_tracking_error_abs_sum;
    double fan_tracking_error_abs_sum;
    float pump_tracking_error_max_abs;
    float fan_tracking_error_max_abs;
    unsigned int tracking_sample_count;
} experiment_metrics_t;

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
    experiment_config_t experiment;
    fault_state_t faults;
    experiment_metrics_t metrics;
    FILE *log_file;
} ecu_state_t;

#endif
