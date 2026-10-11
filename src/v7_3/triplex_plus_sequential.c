#include "triplex_plus_sequential.h"
#include <math.h>
#include <string.h>
void plus_oq_init(plus_oq_t *s){memset(s,0,sizeof(*s));}
bool plus_oq_step(plus_oq_t *s,const double e[6],const unsigned char available[6],const double llr[60],double decay,double boundary){
 static const double edges[9]={1e-6,.01,.025,.05,.1,.2,.35,.5,.75};
 bool alarm=false;
 for(unsigned i=0;i<6;i++){
  bool qualified=available[i]&&isfinite(e[i])&&e[i]>=0&&e[i]<=1;
  double increment=0;
  if(qualified){unsigned bin=0;while(bin<9&&e[i]>=edges[bin])bin++;increment=fmax(-4.,fmin(4.,llr[10*i+bin]));}
  s->score[i]=fmin(32.,fmax(0.,decay*s->score[i]+increment));
  if(qualified&&s->score[i]>=boundary)alarm=true;
 }
 return alarm;
}
void plus_oq_series(unsigned n,const double *values,const unsigned char *available,const double *llr,double decay,double boundary,double *scores,unsigned char *alarm){
 plus_oq_t s;plus_oq_init(&s);
 for(unsigned t=0;t<n;t++){
  alarm[t]=plus_oq_step(&s,values+6*t,available+6*t,llr,decay,boundary);
  memcpy(scores+6*t,s.score,sizeof(s.score));
 }
}
