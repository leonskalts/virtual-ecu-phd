#include "clo_final_sparse_math.h"
#include <assert.h>
#include <string.h>
static unsigned int rng=91;
static double sample(void){rng=1664525U*rng+1013904223U;return (rng%1001)/1000.;}
int main(void) {
 for(int trial=0;trial<2000;trial++) {
  ds_mass_t a,b,x,y;ds_empty(&a);ds_empty(&b);
  for(unsigned int i=1;i<DS_SIZE;i++){a.mass[i]=sample();b.mass[i]=sample();if(trial%2&&i%3)a.mass[i]=b.mass[i]=0;}
  assert(ds_normalize(&a)&&ds_normalize(&b));double k1=0,k2=0;
  for(int rule=DS_DEMPSTER;rule<=DS_YAGER;rule++){
   bool one=ds_combine(&a,&b,(ds_rule_t)rule,&x,&k1),two=final_sparse_combine(&a,&b,(ds_rule_t)rule,&y,&k2);
   assert(one==two);assert(!memcmp(&x,&y,sizeof(x)));assert(k1==k2);
   y=a;assert(final_sparse_combine(&y,&b,(ds_rule_t)rule,&y,&k2)==one);assert(!memcmp(&x,&y,sizeof(x)));
  }
  double p[5],q[5];c2_origin_betp(&a,p);final_cached_betp(&a,q);assert(!memcmp(p,q,sizeof(p)));
 }
 ds_mass_t a,b,x,y;ds_empty(&a);ds_empty(&b);a.mass[2]=b.mass[4]=1;double k1=0,k2=0;
 assert(!ds_combine(&a,&b,DS_DEMPSTER,&x,&k1));assert(!final_sparse_combine(&a,&b,DS_DEMPSTER,&y,&k2));assert(k1==k2);assert(!memcmp(&x,&y,sizeof(x)));
 return 0;
}
