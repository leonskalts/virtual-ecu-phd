#include "analytical_thermal.h"
#include <math.h>
void analytical_thermal_step(analytical_state_t *s,const analytical_config_t *c,const analytical_input_t *u)
{
 if(!s->initialized){s->temperature=c->initial;s->previous_pump=u->pump;s->previous_fan=u->fan;s->ms=u->ms;s->initialized=true;return;}
 if(u->ms<=s->ms)return;
 double dt=(u->ms-s->ms)/1000.;
 double x[8]={1,u->load,u->speed,s->temperature-u->ambient,s->previous_pump+s->previous_fan,u->load*u->speed,s->previous_pump,s->previous_fan};
 double rate=0;for(unsigned j=0;j<8;j++)rate+=c->coefficient[j]*x[j];
 s->temperature+=dt*rate;s->ms=u->ms;s->previous_pump=u->pump;s->previous_fan=u->fan;
}
double analytical_consistency(const analytical_state_t *s,const analytical_config_t *c,const double value[3],const bool valid[3],bool *ambiguous)
{
 *ambiguous=false;
 if(!s->initialized||s->ms<1000||!isfinite(s->temperature)||c->bound<=0)return 0;
 double z[3],max=0;unsigned in=0,out=0;int sign=0;bool same=true;
 for(unsigned j=0;j<3;j++){
  if(!valid[j]||!isfinite(value[j]))return 0;
  z[j]=(value[j]-s->temperature)/c->bound;
  if(fabs(z[j])<=1)in++;else{out++;int d=z[j]>0?1:-1;if(sign&&d!=sign)same=false;sign=d;}
  double excess=fmax(0,fabs(z[j])-1);if(excess>max)max=excess;
 }
 /* One analytical constraint, not three independent DS votes. At least one
  * physical member agrees with the qualified model, or a coherent global
  * residual remains ambiguous. Mixed all-out disagreement => ignorance. */
 if(!in){if(out!=3||!same)return 0;*ambiguous=true;}
 return fmin(1,max);
}
