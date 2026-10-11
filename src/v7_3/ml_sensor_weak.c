#include "ml_sensor_weak.h"
#include <math.h>
double ml_sensor_mass(ml_sensor_state_t *s,const ml_sensor_config_t *c,const ml_sensor_input_t *x,double q)
{
 if(!x->qualified||!isfinite(q)||q<0||q>1){s->consecutive=0;s->previous_ms=x->time_ms;return 0;}
 if(x->time_ms!=s->previous_ms+100)s->consecutive=0;
 s->previous_ms=x->time_ms;
 if(q>=.8){if(s->consecutive<3)s->consecutive++;}else s->consecutive=0;
 bool admitted=c->gate==0||(c->gate==1&&x->physical>0)||(c->gate==2&&x->physical>0&&q>=.8)||(c->gate==3&&s->consecutive>=3);
 return admitted?fmax(0,fmin(.2,c->alpha))*q:0;
}
double ml_sensor_margin(const ml_sensor_model_t *m,const double *x)
{
 double z[ML_SENSOR_FEATURES],margin=m->intercept;
 if(m->n_support>ML_SENSOR_MAX_SV||(m->rbf&&(!m->support||!m->dual)))return NAN;
 for(unsigned j=0;j<ML_SENSOR_FEATURES;j++){
  if(!isfinite(x[j])||!isfinite(m->scale[j])||m->scale[j]<=0)return NAN;
  z[j]=(x[j]-m->mean[j])/m->scale[j];
 }
 if(!m->rbf){for(unsigned j=0;j<ML_SENSOR_FEATURES;j++)margin+=m->weight[j]*z[j];}
 else for(unsigned i=0;i<m->n_support;i++){
  double distance=0;for(unsigned j=0;j<ML_SENSOR_FEATURES;j++){double d=z[j]-m->support[i*ML_SENSOR_FEATURES+j];distance+=d*d;}
  margin+=m->dual[i]*exp(-m->gamma*distance);
 }
 return margin;
}
double ml_sensor_confidence(const ml_sensor_model_t *m,const double *x)
{
 double score=m->platt_slope*ml_sensor_margin(m,x)+m->platt_intercept;
 if(!isfinite(score))return NAN;
 if(score>=0)return 1/(1+exp(-score));
 double e=exp(score);return e/(1+e);
}
