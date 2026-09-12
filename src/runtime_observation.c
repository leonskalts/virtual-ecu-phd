#include "runtime_observation.h"
#include "experiment_ground_truth.h"
#include "ecu_types.h"

void runtime_observation_capture(const ecu_state_t *s, runtime_observation_t *o)
{
    *o = (runtime_observation_t){
        .time_ms = s->time.time_ms, .coolant_measured_c = s->sensors.coolant_temp_meas_c,
        .sample_timestamp_ms = s->sensors.coolant_sensor_last_update_ms,
        .sample_age_ms = s->sensors.coolant_sensor_update_age_ms,
        .control_target_c = s->control.active_control_target_c,
        .pump_command = s->control.pump_command, .fan_command = s->control.fan_command,
        .pump_actual = s->actuators.pump_actual, .fan_actual = s->actuators.fan_actual,
        .control_execution_ms = s->control.last_execution_ms,
        .diagnostic_id = s->diagnostics.primary_dtc, .safety_state = s->safety.current_state,
        .detector_alarm = s->detection.alarm_active, .engine_load = s->plant.engine_load,
        .ambient_c = s->sensors.ambient_temp_meas_c,
        .vehicle_speed_kph = s->sensors.vehicle_speed_meas_kph,
        .sample_freshness_ok = s->sensors.coolant_sensor_freshness_ok,
        .sample_expected_period_ms = s->sensors.coolant_sensor_expected_period_ms,
        .timing = s->timing_recorder.observation
    };
}

void experiment_ground_truth_capture(const ecu_state_t *s, const ecu_state_t *reference,
    experiment_ground_truth_t *truth)
{
    *truth = (experiment_ground_truth_t){ .fault = s->cross_layer_fault,
        .fault_active = s->cross_layer_runtime.active || s->faults.enabled,
        .coolant_true_c = s->plant.coolant_temp_true_c,
        .reference_coolant_true_c = reference->plant.coolant_temp_true_c,
        .propagation = s->propagation };
    if (!truth->fault.enabled && s->experiment.event_count) {
        switch (s->experiment.events[0].mode) {
        case FAULT_PUMP_DEGRADED: case FAULT_FAN_STUCK_OFF:
            truth->fault.layer = FAULT_LAYER_ACTUATOR; break;
        case FAULT_CALIBRATION_MEMORY_CORRUPTION:
            truth->fault.layer = FAULT_LAYER_MEMORY; break;
        case FAULT_STALE_SENSOR_DATA:
            truth->fault.layer = FAULT_LAYER_COMMUNICATION; break;
        default: truth->fault.layer = FAULT_LAYER_SENSING_CONTROL; break;
        }
    }
    runtime_observation_capture(reference, &truth->reference_observation);
}
