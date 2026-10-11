#include "dynamic_consensus.h"
#include <math.h>
#include <string.h>
static double clip(double x,double a,double b){return fmax(a,fmin(b,x));}
void dynamic_consensus_step(dc_state_t *s,const dc_config_t *c,const dc_input_t *u){
 static const unsigned healthy[5]={7,6,5,3,4};
 if(s->count && u->ms<=s->previous_ms)return;
 s->stable=true;s->mass=s->origin_mass=s->q_healthy=0;s->qualified=false;
 bool ok=u->qualified;
 for(unsigned i=0;i<3;i++)ok=ok&&isfinite(u->y[i])&&isfinite(c->variance[i])&&c->variance[i]>0;
 for(unsigned i=0;i<4;i++)ok=ok&&isfinite(u->context[i]);
 if(!ok){memset(s,0,sizeof *s);s->stable=true;return;}
 if(!s->count || u->ms!=s->previous_ms+100){
  memset(s,0,sizeof *s);s->stable=true;
  for(unsigned h=0;h<5;h++){
   double z=0,w=0;for(unsigned j=0;j<3;j++)if(healthy[h]&(1U<<j)){z+=(u->y[j]-c->offset[j])/c->variance[j];w+=1/c->variance[j];}
   s->filter[h].x[0]=z/w;s->filter[h].p[0]=1/w;s->filter[h].p[2]=c->process_variance;
  }
  memcpy(s->context,u->context,sizeof s->context);s->previous_ms=u->ms;s->count=1;return;
 }
 const double dt=.1;
 double change=fabs(u->context[0]-s->context[0])+fabs(u->context[1]-s->context[1])+fabs(u->context[2]-s->context[2])+fabs(u->context[3]-s->context[3])/100.;
 double q=c->process_variance*(1+fmin(10,10*change));
 for(unsigned h=0;h<5;h++){
  dc_filter_t *f=&s->filter[h];double mean=f->x[0]+dt*f->x[1];
  double p00=f->p[0]+2*dt*f->p[1]+dt*dt*f->p[2]+q*dt*dt*dt*dt/4;
  double p01=f->p[1]+dt*f->p[2]+q*dt*dt*dt/2,p11=f->p[2]+q*dt*dt;
  double sw=0,sr=0,srr=0,ld=0,hw=0,hy=0;
  for(unsigned j=0;j<3;j++){
   double r=u->y[j]-c->offset[j]-mean,R=c->variance[j]*((healthy[h]&(1U<<j))?1:25);
   sw+=1/R;sr+=r/R;srr+=r*r/R;ld+=log(R);
   if(healthy[h]&(1U<<j)){
    double weight=c->robust?fmin(1,3*sqrt(p00+c->variance[j])/fmax(1e-12,fabs(r))):1;
    hw+=weight/c->variance[j];hy+=weight*r/c->variance[j];
   }
  }
  double nis=fmax(0,srr-p00*sr*sr/(1+p00*sw));
  double logL=-.5*(3*log(6.283185307179586)+ld+log1p(p00*sw)+nis);
  f->ell=clip(c->lambda*f->ell+clip(logL,-100,100),-5000,5000);
  double R=1/hw,v=hy/hw,S=p00+R,k0=p00/S,k1=p01/S;
  f->x[0]=mean+k0*v;f->x[1]+=k1*v;
  f->p[0]=fmax(1e-12,p00*R/S);f->p[1]=p01*R/S;f->p[2]=fmax(1e-12,p11-p01*p01/S);
  if(h==0){s->common=fabs(sr/sw)/sqrt(p00+1/sw);s->consistency=fmax(0,srr-sr*sr/sw);}
  if(!isfinite(f->x[0])||!isfinite(f->x[1])||!isfinite(f->ell)||f->p[0]*f->p[2]+1e-12<f->p[1]*f->p[1])s->stable=false;
 }
 double best=-INFINITY,second=-INFINITY;unsigned index=0;
 for(unsigned h=1;h<5;h++){double l=s->filter[h].ell;if(l>best){second=best;best=l;index=h;}else second=fmax(second,l);}
 double sum=0;for(unsigned h=1;h<5;h++)sum+=exp(s->filter[h].ell-best);
 s->D=best+log(sum)-s->filter[0].ell;s->margin=best-second;s->best=index;
 s->count++;s->qualified=s->count>=5&&s->stable;
 if(s->qualified){
  double excess=fmax(0,s->D-c->threshold);s->mass=c->alpha*(-expm1(-fmin(100,excess)));
  if(s->margin>=c->origin_margin && best>s->filter[0].ell)s->origin_mass=s->mass;
  if(s->D<=-c->healthy_margin && s->consistency<=c->consistency_bound && s->common<=c->common_bound)
   s->q_healthy=clip(1-exp(s->D),0,1);
 }
 memcpy(s->context,u->context,sizeof s->context);s->previous_ms=u->ms;
}
