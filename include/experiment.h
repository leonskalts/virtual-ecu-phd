#ifndef EXPERIMENT_H
#define EXPERIMENT_H

#include <stdio.h>

#include "ecu_types.h"

void experiment_init_default(ecu_state_t *state);
int experiment_configure_campaign(ecu_state_t *state, const char *campaign_id);
int experiment_configure_custom_single_fault(
    ecu_state_t *state,
    const char *campaign_id,
    fault_mode_t mode,
    fault_behavior_t behavior,
    unsigned int start_ms,
    unsigned int duration_ms,
    float parameter
);
fault_mode_t experiment_fault_mode_from_string(const char *text);
fault_behavior_t experiment_fault_behavior_from_string(const char *text);
const char *experiment_campaign_usage(void);
void experiment_list_campaigns(FILE *stream);

#endif
