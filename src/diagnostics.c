#include "diagnostics.h"

#include "config.h"

/* Diagnostics module: turns instantaneous residuals and threshold violations
 * into paper-friendly DTC states with explicit IDs, fail counters, and
 * transient/persistent/permanent classifications. */
static float abs_float(float value)
{
    return (value < 0.0f) ? -value : value;
}

static void dtc_init(dtc_status_t *status, diagnostic_id_t id)
{
    status->id = id;
    status->fail_count = 0U;
    status->pass_count = 0U;
    status->test_failed = false;
    status->pending = false;
    status->confirmed = false;
    status->permanent_latched = false;
}

static void dtc_update(dtc_status_t *status, bool fault_present, bool permanent_source)
{
    status->test_failed = fault_present;

    if (fault_present) {
        if (status->fail_count < 1000000U) {
            status->fail_count++;
        }
        status->pass_count = 0U;
        status->pending = true;

        if (status->fail_count >= ECU_DTC_CONFIRM_COUNT) {
            status->confirmed = true;
        }

        if (permanent_source && status->fail_count >= ECU_DTC_PERMANENT_COUNT) {
            status->permanent_latched = true;
        }

        return;
    }

    if (status->pass_count < 1000000U) {
        status->pass_count++;
    }

    if (status->pass_count >= ECU_DTC_CLEAR_COUNT) {
        status->fail_count = 0U;
        status->pending = false;
        status->confirmed = false;
        status->permanent_latched = false;
    }
}

diagnostic_class_t diagnostics_dtc_class(const dtc_status_t *status)
{
    if (status->permanent_latched) {
        return DIAG_CLASS_PERMANENT;
    }

    if (status->confirmed) {
        return DIAG_CLASS_PERSISTENT;
    }

    if (status->pending) {
        return DIAG_CLASS_TRANSIENT;
    }

    return DIAG_CLASS_NONE;
}

const char *diagnostics_dtc_label(diagnostic_id_t id)
{
    switch (id) {
    case DTC_ID_COOLANT_SENSOR_RATIONALITY:
        return "coolant_sensor_rationality";
    case DTC_ID_COOLANT_OVER_TEMP_WARNING:
        return "coolant_overtemp_warning";
    case DTC_ID_COOLANT_OVER_TEMP_CRITICAL:
        return "coolant_overtemp_critical";
    case DTC_ID_COOLING_PERFORMANCE_LOW:
        return "cooling_performance_low";
    case DTC_ID_PUMP_TRACKING_FAULT:
        return "pump_tracking_fault";
    case DTC_ID_FAN_TRACKING_FAULT:
        return "fan_tracking_fault";
    case DTC_ID_NONE:
    default:
        return "none";
    }
}

const char *diagnostics_class_label(diagnostic_class_t diag_class)
{
    switch (diag_class) {
    case DIAG_CLASS_TRANSIENT:
        return "transient";
    case DIAG_CLASS_PERSISTENT:
        return "persistent";
    case DIAG_CLASS_PERMANENT:
        return "permanent";
    case DIAG_CLASS_NONE:
    default:
        return "none";
    }
}

static void update_primary_dtc(ecu_state_t *state)
{
    state->diagnostics.primary_dtc = DTC_ID_NONE;

    if (state->diagnostics.overtemp_critical_dtc.pending) {
        state->diagnostics.primary_dtc = DTC_ID_COOLANT_OVER_TEMP_CRITICAL;
    } else if (state->diagnostics.coolant_sensor_dtc.pending) {
        state->diagnostics.primary_dtc = DTC_ID_COOLANT_SENSOR_RATIONALITY;
    } else if (state->diagnostics.fan_tracking_dtc.pending) {
        state->diagnostics.primary_dtc = DTC_ID_FAN_TRACKING_FAULT;
    } else if (state->diagnostics.pump_tracking_dtc.pending) {
        state->diagnostics.primary_dtc = DTC_ID_PUMP_TRACKING_FAULT;
    } else if (state->diagnostics.cooling_performance_dtc.pending) {
        state->diagnostics.primary_dtc = DTC_ID_COOLING_PERFORMANCE_LOW;
    } else if (state->diagnostics.overtemp_warning_dtc.pending) {
        state->diagnostics.primary_dtc = DTC_ID_COOLANT_OVER_TEMP_WARNING;
    }
}

void diagnostics_init(ecu_state_t *state)
{
    state->diagnostics.overtemp_warning = false;
    state->diagnostics.overtemp_critical = false;
    state->diagnostics.coolant_sensor_rationality_fault = false;
    state->diagnostics.cooling_performance_low = false;
    state->diagnostics.pump_tracking_fault = false;
    state->diagnostics.fan_tracking_fault = false;

    dtc_init(&state->diagnostics.coolant_sensor_dtc, DTC_ID_COOLANT_SENSOR_RATIONALITY);
    dtc_init(&state->diagnostics.overtemp_warning_dtc, DTC_ID_COOLANT_OVER_TEMP_WARNING);
    dtc_init(&state->diagnostics.overtemp_critical_dtc, DTC_ID_COOLANT_OVER_TEMP_CRITICAL);
    dtc_init(&state->diagnostics.cooling_performance_dtc, DTC_ID_COOLING_PERFORMANCE_LOW);
    dtc_init(&state->diagnostics.pump_tracking_dtc, DTC_ID_PUMP_TRACKING_FAULT);
    dtc_init(&state->diagnostics.fan_tracking_dtc, DTC_ID_FAN_TRACKING_FAULT);
    state->diagnostics.primary_dtc = DTC_ID_NONE;
}

void diagnostics_step(ecu_state_t *state)
{
    float measured = state->sensors.coolant_temp_meas_c;
    float sensor_residual = state->sensors.coolant_temp_meas_c - state->plant.coolant_temp_true_c;
    float cooling_gap = state->control.pump_command - state->actuators.pump_actual;
    float fan_gap = state->control.fan_command - state->actuators.fan_actual;
    bool permanent_injected_fault = state->faults.active_behavior == FAULT_BEHAVIOR_PERMANENT;

    state->diagnostics.overtemp_warning = measured >= ECU_WARN_COOLANT_TEMP_C;
    state->diagnostics.overtemp_critical = measured >= ECU_CRITICAL_COOLANT_TEMP_C;
    state->diagnostics.coolant_sensor_rationality_fault =
        (measured < ECU_SENSOR_IMPLAUSIBLE_LOW_C) ||
        (measured > ECU_SENSOR_IMPLAUSIBLE_HIGH_C) ||
        (abs_float(sensor_residual) >= ECU_SENSOR_RATIONALITY_RESIDUAL_C);

    state->diagnostics.cooling_performance_low =
        (measured > ECU_TARGET_COOLANT_TEMP_C + 10.0f) &&
        (state->actuators.pump_actual > 0.80f) &&
        ((state->actuators.fan_actual > 0.80f) || (state->control.fan_command > 0.80f));

    state->diagnostics.pump_tracking_fault = cooling_gap > 0.25f;
    state->diagnostics.fan_tracking_fault = fan_gap > 0.25f;

    dtc_update(
        &state->diagnostics.coolant_sensor_dtc,
        state->diagnostics.coolant_sensor_rationality_fault,
        permanent_injected_fault && state->faults.active_mode == FAULT_SENSOR_BIAS
    );
    dtc_update(&state->diagnostics.overtemp_warning_dtc, state->diagnostics.overtemp_warning, permanent_injected_fault);
    dtc_update(&state->diagnostics.overtemp_critical_dtc, state->diagnostics.overtemp_critical, permanent_injected_fault);
    dtc_update(
        &state->diagnostics.cooling_performance_dtc,
        state->diagnostics.cooling_performance_low,
        permanent_injected_fault
    );
    dtc_update(
        &state->diagnostics.pump_tracking_dtc,
        state->diagnostics.pump_tracking_fault,
        permanent_injected_fault && state->faults.active_mode == FAULT_PUMP_DEGRADED
    );
    dtc_update(
        &state->diagnostics.fan_tracking_dtc,
        state->diagnostics.fan_tracking_fault,
        permanent_injected_fault && state->faults.active_mode == FAULT_FAN_STUCK_OFF
    );

    update_primary_dtc(state);
}
