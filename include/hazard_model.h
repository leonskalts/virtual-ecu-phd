#ifndef HAZARD_MODEL_H
#define HAZARD_MODEL_H
#include <stdio.h>
#include "experiment_ground_truth.h"

typedef struct {
    bool enabled;
    float warning_threshold_c;
    float critical_threshold_c;
    unsigned int max_critical_exposure_ms;
    unsigned int fault_tolerant_time_interval_ms;
    unsigned int recovery_hold_ms;
} hazard_config_t;

typedef struct {
    bool warning_active, critical_active, critical_entered;
    bool hazard_active, hazard_entered;
    int critical_entry_ms, hazard_entry_ms, hazard_exit_ms;
    unsigned int critical_exposure_ms, consecutive_critical_ms;
    int previous_time_ms;
    bool previous_critical;
    int safe_candidate_ms, containment_ms;
    int containment_success, ftti_met;
    bool preexisting_hazard;
    bool recovery_seen;
    int max_propagation_stage;
    char propagation_path_signature[192];
} hazard_status_t;

void hazard_config_default(hazard_config_t *config);
void hazard_model_init(hazard_status_t *status);
void hazard_model_step(const hazard_config_t *config, hazard_status_t *status,
    const runtime_observation_t *observation, const experiment_ground_truth_t *truth);
struct ecu_state;
void hazard_csv_header(FILE *stream);
void hazard_csv_row(FILE *stream, const struct ecu_state *state);
#endif
