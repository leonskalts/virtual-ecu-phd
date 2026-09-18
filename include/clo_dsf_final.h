#ifndef CLO_DSF_FINAL_H
#define CLO_DSF_FINAL_H
#include "clo_dsf_candidate2.h" /* Frozen feature/DS types and logical origin mapping. */
/* No origin discount or propagation modulation parameter exists here. */
typedef struct {
    double r_detection, lambda_temporal, suspect_threshold, confirmed_threshold;
    double localization_threshold, localization_margin_threshold, ignorance_limit;
    unsigned int confirmation_persistence;
} clo_final_config_t;
typedef struct {
    ds_mass_t detection_mass, origin_mass;
    clo_evidence_t evidence;
    c2_output_t output;
    unsigned int confirmation_count, previous_time_ms;
    bool has_previous_time;
} clo_final_t;
void clo_final_init(clo_final_t *s);
bool clo_final_config_valid(const clo_final_config_t *c);
void clo_final_step(clo_final_t *s,const clo_final_config_t *c,const runtime_observation_t *o);
/* Diagnostic update only. It cannot read/write masses, output or decisions. */
void clo_final_diagnostic(clo_evidence_t *e,unsigned int now,unsigned int window_ms);
#endif
