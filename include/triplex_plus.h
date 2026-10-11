#ifndef TRIPLEX_PLUS_H
#define TRIPLEX_PLUS_H
#include "triplex_consistency.h"
/* Readout-only temporal alignment; no plant, controller or injection access. */
typedef struct {
 double value[6];
 unsigned ms[6], count;
 bool valid;
} plus_history_t;
typedef struct {
 plus_history_t sensor[3];
 clo_revised_t pair[3];
 unsigned used_ms[3][2];
 bool used[3];
 double strength;
 unsigned accepted_pairs, rejected_alignment, rejected_reuse;
} plus_stagger_t;
void plus_stagger_init(plus_stagger_t *);
void plus_stagger_readout(plus_stagger_t *,unsigned,const diagnostic_readout_t *);
void plus_stagger_pairs(plus_stagger_t *,unsigned);
bool plus_stagger_align(const plus_stagger_t *,unsigned,unsigned,double *,double *);
/* Closest-to-agreement point in the alignment uncertainty interval. */
double plus_conservative_difference(double,double);
#endif
