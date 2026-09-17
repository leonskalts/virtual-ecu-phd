#ifndef CLO_DSF_CANDIDATE2_H
#define CLO_DSF_CANDIDATE2_H
#include "clo_dsf.h"
/* Partition embeddings preserve union/intersection and Theta=63 in the frozen
 * DS core. Origin BetP counts FIVE logical blocks, never six storage bits. */
#define C2_D_NORMAL 1U
#define C2_D_ABNORMAL 62U
#define C2_ORIGIN_RELIABILITY 1U
#define C2_PROPAGATION 2U
#define C2_TEMPORAL 4U
#define C2_DETECTION_RELIABILITY 8U
#define C2_FULL 15U
extern const unsigned int c2_origin_blocks[5];
extern const unsigned int c2_origin_support[CLO_CHANNELS];
typedef struct {
    clo_config_t common; /* r_direct/r_indirect apply ONLY to origin evidence. */
    double r_detection;
} c2_config_t;
typedef struct {
    clo_state_t state;
    double anomaly_belief, anomaly_plausibility, anomaly_decision_score, anomaly_ignorance;
    double detection_conflict, localization_conflict;
    double detection_conflict_steps[7], localization_conflict_steps[7];
    double origin_score, origin_belief, origin_plausibility, origin_margin, origin_ignorance;
    double origin_scores[5];
    unsigned int estimated_origin, leading_origin;
    bool alarm, localization_valid, propagation_support, detection_fallback, localization_fallback;
    int alarm_timestamp_ms, localization_timestamp_ms;
} c2_output_t;
typedef struct {
    ds_mass_t detection_mass, origin_mass;
    clo_evidence_t evidence;
    double detection_reliability[CLO_CHANNELS], origin_reliability[CLO_CHANNELS];
    c2_output_t output;
    unsigned int confirmation_count, previous_time_ms;
    bool has_previous_time;
} c2_state_t;
void c2_config_default(c2_config_t *c);
bool c2_config_valid(const c2_config_t *c);
void c2_init(c2_state_t *s);
void c2_extract(clo_evidence_t *e, const runtime_observation_t *o);
void c2_propagation(clo_evidence_t *e, const clo_config_t *c, unsigned int now);
unsigned int c2_encode_origin_subset(unsigned int logical_mask);
void c2_origin_betp(const ds_mass_t *m, double scores[5]);
void c2_step(c2_state_t *s, const c2_config_t *c, unsigned int extensions,
             const runtime_observation_t *o);
#endif
