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
    FAULT_MODEL_DEGRADED_ACTUATOR
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
} fault_descriptor_t;

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
} cross_layer_fault_state_t;

#endif
