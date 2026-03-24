#ifndef THERMAL_PLANT_H
#define THERMAL_PLANT_H

#include "ecu_types.h"

void thermal_plant_init(ecu_state_t *state);
void thermal_plant_step(ecu_state_t *state);
const char *thermal_plant_phase_label(scenario_phase_t phase);

#endif
