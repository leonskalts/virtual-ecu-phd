#include "triplex_change_point.h"
#include <math.h>
#include <string.h>
static bool whiten(const double *l,double x,double y,double *a,double *b)
{
 if(!isfinite(l[0])||!isfinite(l[1])||!isfinite(l[2])||l[0]<=0||l[2]<=0)return false;
 *a=x/l[0];*b=(y-l[1]*(*a))/l[2];return isfinite(*a)&&isfinite(*b);
}
static double empirical(const double *v,unsigned n,double score)
{
 unsigned lo=0,hi=n;while(lo<hi){unsigned m=lo+(hi-lo)/2;if(v[m]<score)lo=m+1;else hi=m;}
 return (1.+n-lo)/(n+1.);
}
double cp_combine(const double *p,const bool *available,unsigned method)
{
 unsigned n=0;double minimum=1,y=0,t=0;const double pi=3.14159265358979323846;
 for(unsigned j=0;j<3;j++)if(available[j]){
  if(!isfinite(p[j])||p[j]<=0||p[j]>1)return 0;
  n++;minimum=fmin(minimum,p[j]);y-=log(p[j]);
  /* Finite Cauchy endpoint convention, fixed independently of data. */
  double q=fmax(1e-12,fmin(1-1e-12,p[j]));t+=tan(pi*(.5-q));
 }
 if(!n)return 0;
 if(method==0)return -log(fmin(1,n*minimum));
 if(method==1){double series=1;if(n>=2)series+=y;if(n>=3)series+=y*y/2;return fmax(0,y-log(series));}
 t/=n;double tail=t>0?atan(1/t)/pi:t<0?1-atan(-1/t)/pi:.5;
 return -log(fmax(1e-15,fmin(1,tail)));
}
static double mass(double score,const cp_config_t *c)
{return score>c->threshold?fmax(0,fmin(1,c->gamma))*(-expm1(-(score-c->threshold))):0;}
void triplex_cp_step(cp_state_t *s,const cp_config_t *c,const cp_input_t *u)
{
 memset(s->raw,0,sizeof(s->raw));memset(s->available,0,sizeof(s->available));memset(s->slope,0,sizeof(s->slope));
 s->rarity=s->mass=0;for(unsigned j=0;j<3;j++){s->p[j]=1;s->isolated_mass[j]=0;}
 s->start_step=s->start_transient=s->end_transient=s->drift_window=0;s->stable=true;
 if(!u->qualified||!isfinite(u->ac)||!isfinite(u->bc)){s->count=s->next=0;s->previous_ms=u->ms;return;}
 double a,b;if(!whiten(c->chol,u->ac-c->mu[0],u->bc-c->mu[1],&a,&b)){s->stable=false;s->count=s->next=0;return;}
 if(s->count&&u->ms!=s->previous_ms+100)s->count=s->next=0;
 s->previous_ms=u->ms;unsigned current=s->next;s->history[current][0]=a;s->history[current][1]=b;s->next=(current+1)%50;if(s->count<50)s->count++;
 memset(s->interval[current],0,sizeof(s->interval[current]));double sum[2]={0};
 for(unsigned n=1;n<=s->count;n++){
  unsigned at=(s->next+50-n)%50;sum[0]+=s->history[at][0];sum[1]+=s->history[at][1];double score=(sum[0]*sum[0]+sum[1]*sum[1])/n;
  if(n>=3&&score>s->raw[0]){s->raw[0]=score;s->start_step=u->ms-100*(n-1);}
  if(n<=12)s->interval[current][n-1]=score;
 }
 s->available[0]=s->count>=3;s->available[1]=true;
 /* All intervals are fully observed; bounded recent history is not an alarm latch. */
 for(unsigned age=0;age<s->count;age++){
  unsigned at=(current+50-age)%50;unsigned limit=s->count-age;if(limit>12)limit=12;
  for(unsigned n=1;n<=limit;n++)if(s->interval[at][n-1]>s->raw[1]){s->raw[1]=s->interval[at][n-1];s->end_transient=u->ms-age*100;s->start_transient=s->end_transient-(n-1)*100;}
 }
 const unsigned windows[2]={20,50};
 for(unsigned k=0;k<2;k++)if(s->count>=windows[k]){
  unsigned w=windows[k];double weighted[2]={0};
  for(unsigned j=0;j<w;j++){unsigned at=(current+50-j)%50;double v=(w-1)*.5-j;weighted[0]+=v*s->history[at][0];weighted[1]+=v*s->history[at][1];}
  double q=(double)w*(w*w-1)/12;for(unsigned j=0;j<2;j++)s->slope[k][j]=10*weighted[j]/q;
  if(!whiten(c->slope_chol[k],s->slope[k][0]-c->slope_mu[k][0],s->slope[k][1]-c->slope_mu[k][1],&a,&b)){s->stable=false;return;}
  double score=a*a+b*b;if(score>s->raw[2]){s->raw[2]=score;s->drift_window=w;}s->available[2]=true;
 }
 for(unsigned j=0;j<3;j++)if(!isfinite(s->raw[j])){s->stable=false;return;}
 bool qualified[3];for(unsigned j=0;j<3;j++){qualified[j]=s->available[j]&&c->cdf[j]&&c->cdf_n[j]>0;if(qualified[j])s->p[j]=empirical(c->cdf[j],c->cdf_n[j],s->raw[j]);}
 s->rarity=cp_combine(s->p,qualified,c->combination);s->mass=mass(s->rarity,c);
 for(unsigned j=0;j<3;j++){
  double p[3];for(unsigned k=0;k<3;k++)p[k]=k==j?s->p[k]:c->combination==2?.5:1;
  s->isolated_mass[j]=qualified[j]?mass(cp_combine(p,qualified,c->combination),c):0;
 }
}
