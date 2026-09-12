#ifndef SAFETY_POLICY_V5_H
#define SAFETY_POLICY_V5_H
#include "runtime_safety_policy.h"
typedef enum { V5_OBSERVE, V5_IMMEDIATE, V5_GRADED } safety_policy_v5_mode_t;
typedef struct { bool enabled; safety_policy_v5_mode_t mode; } safety_policy_v5_config_t;
typedef struct { int communication_streak_start_ms; } safety_policy_v5_state_t;
void safety_policy_v5_step(runtime_safety_status_t *s, safety_policy_v5_state_t *v,
    const runtime_safety_config_t *c, safety_policy_v5_mode_t mode,
    const runtime_observation_t *o, const timing_monitor_status_t *timing);
struct ecu_state;
int validation_v5_parse_options(int *argc, char **argv, struct ecu_state *state);
void validation_v5_csv_header(struct ecu_state *state);
void validation_v5_csv_row(const struct ecu_state *state);
#endif
