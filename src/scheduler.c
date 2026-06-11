#include "scheduler.h"

#include "actuators.h"
#include "config.h"
#include "control.h"
#include "detection_algorithm.h"
#include "diagnostics.h"
#include "fault_injection.h"
#include "logger.h"
#include "metrics.h"
#include "safety_monitor.h"
#include "sensors.h"
#include "thermal_plant.h"

/* Scheduler module: executes the prototype as a deterministic fixed-step ECU
 * schedule so runs can be reproduced exactly across experiments. */
bool scheduler_task_due(unsigned int time_ms, unsigned int period_ms)
{
    return (time_ms % period_ms) == 0U;
}

void scheduler_init(ecu_state_t *state)
{
    state->time.tick = 0U;
    state->time.time_ms = 0U;

    /* Initialize the plant before the perception/control stack so all modules
     * begin from a coherent nominal thermal state. */
    thermal_plant_init(state);
    sensors_init(state);
    control_init(state);
    actuators_init(state);
    diagnostics_init(state);
    fault_injection_init(state);
    safety_monitor_init(state);
    metrics_init(state);
    detection_algorithm_init(
        &state->detection,
        state->detection.selected_algorithm,
        state->detection.selected_action
    );
}

void scheduler_run(ecu_state_t *state)
{
    for (state->time.time_ms = 0U;
         state->time.time_ms <= ECU_SIM_DURATION_MS;
         state->time.time_ms += ECU_DT_MS, state->time.tick++) {
        /* The order reflects an ECU research loop: inject scenario conditions,
         * sense, control, diagnose, enforce safety, log, then advance the plant. */
        fault_injection_step(state);

        if (scheduler_task_due(state->time.time_ms, ECU_SENSOR_PERIOD_MS)) {
            sensors_step(state);
        }

        if (scheduler_task_due(state->time.time_ms, ECU_CONTROL_PERIOD_MS)) {
            control_step(state);
        }

        if (scheduler_task_due(state->time.time_ms, ECU_ACTUATOR_PERIOD_MS)) {
            actuators_step(state);
        }

        if (scheduler_task_due(state->time.time_ms, ECU_DIAGNOSTIC_PERIOD_MS)) {
            diagnostics_step(state);
        }

        if (scheduler_task_due(state->time.time_ms, ECU_SAFETY_PERIOD_MS)) {
            safety_monitor_step(state);
            actuators_step(state);

            /* Re-run diagnostics after safety overrides so the logged actuator
             * residuals match the final commands applied in this time step. */
            if (scheduler_task_due(state->time.time_ms, ECU_DIAGNOSTIC_PERIOD_MS)) {
                diagnostics_step(state);
            }
        }

        detection_algorithm_step(state);

        if (safety_monitor_apply_detector_request(state)) {
            actuators_step(state);

            if (scheduler_task_due(state->time.time_ms, ECU_DIAGNOSTIC_PERIOD_MS)) {
                diagnostics_step(state);
            }
        }

        metrics_step(state);

        if (scheduler_task_due(state->time.time_ms, ECU_LOG_PERIOD_MS)) {
            logger_write(state);
        }

        thermal_plant_step(state);
    }
}
