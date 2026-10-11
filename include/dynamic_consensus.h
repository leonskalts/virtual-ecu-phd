#ifndef DYNAMIC_CONSENSUS_H
#define DYNAMIC_CONSENSUS_H
#include <stdbool.h>
/* Trusted, already causally aligned runtime measurements only. */
typedef struct { unsigned ms; double y[3],context[4]; bool qualified; } dc_input_t;
typedef struct {
 double offset[3],variance[3],process_variance,lambda,threshold,alpha;
 double healthy_margin,consistency_bound,common_bound,origin_margin;
 unsigned robust;
} dc_config_t;
typedef struct { double x[2],p[3],ell; } dc_filter_t;
typedef struct {
 dc_filter_t filter[5];double context[4],D,margin,consistency,common,q_healthy,mass,origin_mass;
 unsigned previous_ms,count,best;bool stable,qualified;
} dc_state_t;
void dynamic_consensus_step(dc_state_t *,const dc_config_t *,const dc_input_t *);
#endif
