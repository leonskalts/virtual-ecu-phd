#ifndef TRIPLEX_CONSISTENCY_H
#define TRIPLEX_CONSISTENCY_H
#include "clo_dsf_revised.h"
#include "diagnostic_temperature.h"
typedef struct {
 clo_revised_t ac,bc;
 double strength,ac_strength,bc_strength,aligned_c;
 unsigned samples,member_pattern;
 bool qualified,ambiguous;
} triplex_consistency_t;
void triplex_consistency_init(triplex_consistency_t *);
void triplex_consistency_step(triplex_consistency_t *,const runtime_observation_t *,const diagnostic_readout_t *);
/* Thin bridge compiled from the existing unchanged FAST/SLOW implementation. */
double clo_existing_pair_strength(clo_revised_t *,const runtime_observation_t *);
#endif
