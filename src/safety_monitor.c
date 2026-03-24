#include "safety_monitor.h"

void safety_monitor_init(ecu_state_t *state)
{
    state->safety.limp_home_active = false;
    state->safety.emergency_cooling_active = false;
}

void safety_monitor_step(ecu_state_t *state)
{
    state->safety.limp_home_active =
        state->diagnostics.overtemp_critical ||
        state->diagnostics.cooling_performance_low;

    state->safety.emergency_cooling_active =
        state->diagnostics.overtemp_warning ||
        state->diagnostics.actuator_fault;

    if (state->safety.emergency_cooling_active) {
        state->control.pump_command = 1.0f;
        state->control.fan_command = 1.0f;
    }
}
