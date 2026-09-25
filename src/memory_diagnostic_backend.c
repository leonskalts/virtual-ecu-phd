/* Virtual storage model for diagnostic transactions, outside inference. */
#include "memory_diagnostic_backend.h"
#include "ecu_types.h"

uint16_t cross_layer_memory_read(void *context)
{
    const ecu_state_t *state = context;
    return state->control.target_register_c;
}

void cross_layer_memory_write(void *context, uint16_t value)
{
    ecu_state_t *state = context;
    /* Device model only: an active stuck cell rejects the opposite write.
     * Normal control writes and historical scheduled injection are unchanged.
     * A past bit-flip is not a persistent inability to write. */
    if (state->cross_layer_fault.enabled && state->cross_layer_runtime.active &&
        state->cross_layer_fault.layer == FAULT_LAYER_MEMORY &&
        state->cross_layer_fault.model == FAULT_MODEL_STUCK_BIT) {
        uint16_t mask = (uint16_t)(1U << state->cross_layer_fault.bit_index);
        value = state->cross_layer_fault.stuck_polarity ?
            value | mask : value & (uint16_t)~mask;
    }
    state->control.target_register_c = value;
}

