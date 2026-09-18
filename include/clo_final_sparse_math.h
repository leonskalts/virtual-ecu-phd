#ifndef CLO_FINAL_SPARSE_MATH_H
#define CLO_FINAL_SPARSE_MATH_H
#include "clo_dsf_final.h"
bool final_sparse_combine(const ds_mass_t *a,const ds_mass_t *b,ds_rule_t rule,ds_mass_t *out,double *conflict);
void final_cached_betp(const ds_mass_t *m,double scores[5]);
void clo_final_optimized_step(clo_final_t *s,const clo_final_config_t *c,const runtime_observation_t *o);
#endif
