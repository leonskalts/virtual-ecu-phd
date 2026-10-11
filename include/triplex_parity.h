#ifndef TRIPLEX_PARITY_H
#define TRIPLEX_PARITY_H
#include <stdbool.h>
/* Geometry labels are disagreement cuts, never claims about the faulty member. */
typedef struct {double mu[2],l00,l10,l11,tau,saturation,beta,dominance;} parity_config_t;
typedef struct {unsigned ms;double ac,bc;bool qualified;} parity_input_t;
typedef struct {
 double history[8][2],g,m,current_m,directional[4],mass,origin_mass;
 unsigned count,next,previous_ms,window,direction;
 bool qualified,stable;
} parity_state_t;
void triplex_parity_step(parity_state_t *,const parity_config_t *,const parity_input_t *);
#endif
