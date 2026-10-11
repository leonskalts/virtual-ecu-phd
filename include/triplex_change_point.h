#ifndef TRIPLEX_CHANGE_POINT_H
#define TRIPLEX_CHANGE_POINT_H
#include <stdbool.h>
/* No fault labels, physical truth or final-detector decision in the input. */
typedef struct {unsigned ms;double ac,bc;bool qualified;} cp_input_t;
typedef struct {
 double mu[2],chol[3],slope_mu[2][2],slope_chol[2][3];
 const double *cdf[3];unsigned cdf_n[3];
 double threshold,gamma;unsigned combination;
} cp_config_t;
typedef struct {
 double history[50][2],interval[50][12];
 double raw[3],p[3],rarity,mass,isolated_mass[3],slope[2][2];
 unsigned count,next,previous_ms,start_step,start_transient,end_transient,drift_window;
 bool available[3],stable;
} cp_state_t;
void triplex_cp_step(cp_state_t *,const cp_config_t *,const cp_input_t *);
double cp_combine(const double *,const bool *,unsigned);
#endif
