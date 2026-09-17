#ifndef CLO_DSF_H
#define CLO_DSF_H
#include "ds_evidence.h"
#include "runtime_observation.h"
#define CLO_CHANNELS 6
#define CLO_NORMAL 1U
#define CLO_MEMORY 2U
#define CLO_TIMING 4U
#define CLO_COMMUNICATION 8U
#define CLO_SENSOR_CONTROL 16U
#define CLO_ACTUATOR 32U
#define CLO_ABNORMAL (DS_THETA ^ CLO_NORMAL)
typedef enum { CLO_DIRECT, CLO_INDIRECT, CLO_UNAVAILABLE, CLO_NOT_APPLICABLE } clo_observability_t;
typedef enum { CLO_STATE_NORMAL, CLO_STATE_SUSPECT, CLO_STATE_CONFIRMED } clo_state_t;
typedef enum { CLO_FULL, CLO_PLAIN, CLO_OBSERVABILITY, CLO_PROPAGATION, CLO_OR, CLO_WEIGHTED } clo_variant_t;
typedef struct {
    double r_direct, r_indirect, lambda_temporal, propagation_bonus;
    unsigned int propagation_window_ms;
    double alarm_threshold_suspect, alarm_threshold_confirmed;
    unsigned int confirmation_persistence;
    double localization_threshold, localization_margin_threshold, ignorance_limit;
    ds_rule_t conflict_rule;
} clo_config_t;
typedef struct {
    double strength[CLO_CHANNELS], reliability[CLO_CHANNELS];
    bool available[CLO_CHANNELS], active[CLO_CHANNELS];
    int onset_ms[CLO_CHANNELS];
    unsigned int propagation_transitions;
    double previous_temperature;
    unsigned int previous_timestamp_ms, previous_sample_timestamp_ms;
    bool initialized;
} clo_evidence_t;
typedef struct {
    clo_state_t state;
    unsigned int estimated_origin;
    double fault_belief, origin_score, origin_margin, origin_belief, origin_plausibility;
    double ignorance_mass, conflict_mass, conflict_steps[CLO_CHANNELS + 2];
    bool alarm, localization_valid, propagation_support, combination_fallback;
    int alarm_timestamp_ms, localization_timestamp_ms;
} clo_output_t;
typedef struct {
    ds_mass_t fused;
    clo_evidence_t evidence;
    clo_output_t output;
    unsigned int confirmation_count;
} clo_dsf_t;
extern const unsigned int clo_supported_subsets[CLO_CHANNELS];
extern const clo_observability_t clo_observability[CLO_CHANNELS][DS_ATOMS];
extern const char *const clo_channel_names[CLO_CHANNELS];
extern const unsigned int clo_propagation_edges[CLO_CHANNELS];
void clo_config_default(clo_config_t *config);
bool clo_config_valid(const clo_config_t *config);
void clo_dsf_init(clo_dsf_t *detector);
void clo_dsf_step(clo_dsf_t *detector, const clo_config_t *config,
                  clo_variant_t variant, const runtime_observation_t *observation);
void clo_evidence_mass(unsigned int channel, double strength, bool available, ds_mass_t *mass);
double clo_reliability(clo_observability_t kind, const clo_config_t *config);
const char *clo_origin_name(unsigned int origin);
const char *clo_state_name(clo_state_t state);
#endif
