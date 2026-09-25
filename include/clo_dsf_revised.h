#ifndef CLO_DSF_REVISED_H
#define CLO_DSF_REVISED_H
#include "clo_dsf_final.h"
/* Runtime provenance for the current anomaly episode, separate from DS masses.
 * No fault labels or propagation scores participate. */
typedef struct {
    clo_final_t fusion;
    unsigned int direct_onset_ms, direct_origins, actuator_unresolved;
    bool sensor_established_first, ambiguous_onset;
    double previous_local_excess;
    unsigned int previous_local_ms;
    int previous_local_direction;
    bool previous_local_valid;
    /* Finite sensor-response forecast; no simulator or injector state. */
    float response_history[5];
    unsigned int response_count, response_last_ms, response_anchor_ms;
    float response_load, response_speed, response_ambient, response_target, response_fan;
    double response_anchor, response_slope, response_residual, response_strength;
    unsigned int response_streak;
    int response_sign;
    bool response_active;
    /* 32 s signed disagreement window, one correlated sensor feature. */
    double reference_window[320], reference_sum, reference_mean, reference_strength;
    unsigned int reference_count, reference_index, reference_last_ms;
    /* Fast differential contract, independent of which sensor is faulty. */
    double fast_previous, fast_anchor, fast_strength;
    unsigned int fast_last_ms, fast_anchor_ms, fast_count, fast_index, fast_edges;
    unsigned char fast_edge_history[10];
    int fast_sign;
    bool fast_valid, fast_active;
} clo_revised_t;
void clo_revised_init(clo_revised_t *s);
void clo_revised_extract(clo_evidence_t *e, const runtime_observation_t *o);
void clo_revised_step(clo_revised_t *s, const clo_final_config_t *c,
                      const runtime_observation_t *o);
#endif
