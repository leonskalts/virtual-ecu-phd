#ifndef FAULT_INJECTION_H
#define FAULT_INJECTION_H

#include "ecu_types.h"

/* Hardware-origin fault abstraction layer: represents plausible automotive
 * electronics faults at sensing, timing/communication, actuation, and memory
 * interfaces without claiming circuit-level fidelity. */
void fault_injection_init(ecu_state_t *state);
void fault_injection_step(ecu_state_t *state);
const char *fault_injection_mode_label(fault_mode_t mode);
const char *fault_injection_behavior_label(fault_behavior_t behavior);
float fault_injection_default_parameter(fault_mode_t mode);

#endif
