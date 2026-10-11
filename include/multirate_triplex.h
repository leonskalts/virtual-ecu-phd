#ifndef MULTIRATE_TRIPLEX_H
#define MULTIRATE_TRIPLEX_H
#include <stdbool.h>
#include "runtime_observation.h"
/* Runtime-only readout processing. No ECU state, plant truth or fault labels. */
typedef struct {
 double fast_strength,fast_previous,fast_anchor,fast_integral,fast_bound_integral;
 unsigned fast_last_ms,fast_anchor_ms,fast_count,fast_index,fast_edges,fast_integral_count;
 int fast_sign,fast_integral_sign;
 unsigned char fast_edge_history[40];
 bool fast_valid,fast_active;
} mr_pair_t;
typedef struct {
 mr_pair_t pair[3];
 unsigned period,qualified_count;
 double strength;
 bool ambiguous;
 unsigned qualified_observations;
} mr_triplex_t;
void mr_triplex_init(mr_triplex_t *,unsigned);
void mr_triplex_step(mr_triplex_t *,unsigned,const float[3],bool);
#endif
