#ifndef EXPERIMENT_GROUND_TRUTH_H
#define EXPERIMENT_GROUND_TRUTH_H
#include "runtime_observation.h"
#include "fault_model.h"
#include "propagation_monitor.h"

/* Evaluation-only snapshot. Never accepted by a runtime detector interface. */
typedef struct {
    fault_descriptor_t fault;
    bool fault_active;
    float coolant_true_c;
    float reference_coolant_true_c;
    runtime_observation_t reference_observation;
    propagation_monitor_t propagation;
} experiment_ground_truth_t;

void experiment_ground_truth_capture(const struct ecu_state *state,
    const struct ecu_state *reference, experiment_ground_truth_t *truth);
#endif
