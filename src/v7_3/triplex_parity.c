#include "triplex_parity.h"
#include <math.h>
#include <string.h>
static void solve(const parity_config_t *c,double x,double y,double *a,double *b)
{*a=x/c->l00;*b=(y-c->l10*(*a))/c->l11;}
void triplex_parity_step(parity_state_t *s,const parity_config_t *c,const parity_input_t *u)
{
 s->mass=s->origin_mass=s->g=s->m=s->current_m=0;s->window=s->direction=0;
 memset(s->directional,0,sizeof(s->directional));s->qualified=false;
 s->stable=isfinite(c->l00)&&isfinite(c->l10)&&isfinite(c->l11)&&c->l00>0&&c->l11>0&&isfinite(c->mu[0])&&isfinite(c->mu[1]);
 if(!s->stable||!u->qualified||!isfinite(u->ac)||!isfinite(u->bc)) {s->count=s->next=0;s->previous_ms=u->ms;return;}
 if(s->count&&u->ms!=s->previous_ms+100)s->count=s->next=0;
 s->previous_ms=u->ms;s->history[s->next][0]=u->ac;s->history[s->next][1]=u->bc;s->next=(s->next+1)%8;if(s->count<8)s->count++;
 s->qualified=true;double sum[2]={0},best[4]={0};unsigned win[4]={0};
 const double directions[4][2]={{1,0},{0,1},{-1,-1},{1,1}};
 double va[4],vb[4],norm[4];for(unsigned h=0;h<4;h++){solve(c,directions[h][0],directions[h][1],&va[h],&vb[h]);norm[h]=va[h]*va[h]+vb[h]*vb[h];}
 for(unsigned w=1;w<=s->count;w++){
  unsigned at=(s->next+8-w)%8;sum[0]+=s->history[at][0];sum[1]+=s->history[at][1];
  if(w!=1&&w!=2&&w!=4&&w!=8)continue;
  double a,b;solve(c,sum[0]/w-c->mu[0],sum[1]/w-c->mu[1],&a,&b);
  double m=w*(a*a+b*b);if(w==1)s->current_m=m;if(m>s->m)s->m=m;
  for(unsigned h=0;h<4;h++){double projection=va[h]*a+vb[h]*b;double g=w*projection*projection/norm[h];if(g>best[h]){best[h]=g;win[h]=w;}}
 }
 unsigned top=0;for(unsigned h=0;h<4;h++){s->directional[h]=best[h];if(best[h]>best[top])top=h;}
 s->g=best[top];s->window=win[top];double second=0;for(unsigned h=0;h<4;h++)if(h!=top&&best[h]>second)second=best[h];
 /* Opposite C / AB hypotheses tie exactly under squared GLRT. Their origin
    contribution must remain vacuous, regardless of signed displacement. */
 if(top<2&&s->g>0&&s->g>c->dominance*second)s->direction=top+1;
 if(!isfinite(s->g)||!isfinite(s->m)){s->stable=false;s->qualified=false;s->g=s->m=0;return;}
 if(isfinite(c->tau)&&c->tau>0&&c->saturation>1&&s->g>c->tau){
  double q=fmin(1,(s->g-c->tau)/((c->saturation-1)*c->tau));s->mass=fmax(0,fmin(1,c->beta))*q;
  if(s->direction)s->origin_mass=s->mass;
 }
}
