#ifndef RUNTIME_SAFETY_POLICY_H
#define RUNTIME_SAFETY_POLICY_H
#include "runtime_observation.h"
#include "timing_safety_monitor.h"

typedef struct {
    bool enabled, communication_protective_action;
    timing_monitor_mode_t timing_mode;
    timing_evidence_t timing_evidence;
} runtime_safety_config_t;

typedef struct {
    bool communication_alarm, timing_request, communication_request, action_applied;
    int requested_state;
    int first_communication_alarm_ms, first_existing_alarm_ms;
    int first_timing_request_ms, first_communication_request_ms, first_request_ms, first_action_ms;
    unsigned int request_samples, action_samples;
} runtime_safety_status_t;

void runtime_safety_policy_init(runtime_safety_status_t *s);
void runtime_safety_policy_step(runtime_safety_status_t *s, const runtime_safety_config_t *c,
    const runtime_observation_t *o, const timing_monitor_status_t *timing);
struct ecu_state;
int runtime_safety_parse_options(int *argc, char **argv, struct ecu_state *state);
void runtime_safety_csv_header(struct ecu_state *state);
void runtime_safety_csv_row(const struct ecu_state *state);
#endif
