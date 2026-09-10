#ifndef FAULT_MODEL_H
#define FAULT_MODEL_H

#include <stdbool.h>
#include <stdint.h>

/* Preserve the numeric legacy behavior values. */
typedef enum {
    FAULT_BEHAVIOR_NONE = 0,
    FAULT_BEHAVIOR_TRANSIENT,
    FAULT_BEHAVIOR_PERMANENT,
    FAULT_BEHAVIOR_INTERMITTENT
} fault_behavior_t;

typedef enum {
    FAULT_LAYER_HARDWARE = 0, FAULT_LAYER_MEMORY, FAULT_LAYER_TIMING,
    FAULT_LAYER_COMMUNICATION, FAULT_LAYER_SENSING_CONTROL, FAULT_LAYER_ACTUATOR
} fault_layer_t;

typedef enum {
    FAULT_MODEL_LEGACY = 0, FAULT_MODEL_BIT_FLIP, FAULT_MODEL_STUCK_BIT,
    FAULT_MODEL_DEADLINE_MISS, FAULT_MODEL_TASK_DELAY, FAULT_MODEL_STALE_DATA,
    FAULT_MODEL_DROPPED_UPDATE, FAULT_MODEL_VALUE_CORRUPTION,
    FAULT_MODEL_DEGRADED_ACTUATOR, FAULT_MODEL_DELAYED_UPDATE, FAULT_MODEL_REPLAYED_SAMPLE
} fault_model_t;

typedef enum {
    FAULT_TARGET_NONE = 0, FAULT_TARGET_CONTROL_TARGET_REGISTER,
    FAULT_TARGET_CONTROL_TASK, FAULT_TARGET_COOLANT_SENSOR,
    FAULT_TARGET_PUMP, FAULT_TARGET_FAN
} fault_target_t;

typedef struct {
    bool enabled;
    unsigned int fault_id;
    fault_layer_t layer;
    fault_model_t model;
    fault_behavior_t behavior;
    fault_target_t target;
    unsigned int start_ms;
    unsigned int duration_ms;
    float parameter;
    unsigned int bit_index;
    uint32_t seed;
    unsigned int intermittent_on_ms;
    unsigned int intermittent_off_ms;
    unsigned int stuck_polarity;
    unsigned int communication_delay_ms;
    unsigned int drop_count;
    unsigned int drop_every_n_updates;
    unsigned int replay_age_ms;
    unsigned int task_delay_ms;
} fault_descriptor_t;

typedef enum {
    FAULT_PHASE_DISABLED = 0, FAULT_PHASE_WAITING, FAULT_PHASE_ACTIVE,
    FAULT_PHASE_INACTIVE, FAULT_PHASE_RECOVERED
} fault_phase_t;

#define CROSS_LAYER_HISTORY_SAMPLES 256U

typedef struct {
    bool active;
    bool injected;
    bool memory_values_valid;
    uint16_t memory_original_value;
    uint16_t memory_corrupted_value;
    bool execution_skipped;
    bool execution_recovered;
    bool previous_execution_skipped;
    int expected_execution_ms;
    int actual_execution_ms;
    fault_phase_t phase;
    unsigned int activation_count;
    int last_activation_ms;
    int last_recovery_ms;
    bool pending_job;
    int nominal_release_ms;
    int job_due_ms;
    int deadline_ms;
    bool deadline_missed;
    bool release_discarded;
    unsigned int actual_delay_ms;
    float history[CROSS_LAYER_HISTORY_SAMPLES];
    unsigned int history_timestamps[CROSS_LAYER_HISTORY_SAMPLES];
    bool history_valid[CROSS_LAYER_HISTORY_SAMPLES];
    float generated_value;
    float delivered_value;
    unsigned int generated_ms;
    unsigned int delivered_source_ms;
    int delivered_ms;
    int replay_source_ms;
    bool update_generated;
    bool update_delivered;
    bool update_dropped;
    bool update_delayed;
    bool replay_active;
    unsigned int active_update_count;
    unsigned int consecutive_drops;
    unsigned int total_drops;
} cross_layer_fault_state_t;

#endif
