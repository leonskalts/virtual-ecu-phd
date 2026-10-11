#include "triplex_plus.h"
#include <math.h>
#include <string.h>
void plus_stagger_init(plus_stagger_t *s){
 memset(s,0,sizeof(*s));for(unsigned i=0;i<3;i++)clo_revised_init(&s->pair[i]);
}
void plus_stagger_readout(plus_stagger_t *s,unsigned member,const diagnostic_readout_t *r){
 if(member>=3)return;
 plus_history_t *h=&s->sensor[member];
 if(!r->valid||r->failed||!isfinite(r->value_c)){h->valid=false;h->count=0;return;}
 if(h->count && r->sample_ms<=h->ms[h->count-1])return;
 if(h->count && r->sample_ms!=h->ms[h->count-1]+100)h->count=0;
 if(h->count==6){memmove(h->value,h->value+1,5*sizeof(double));memmove(h->ms,h->ms+1,5*sizeof(unsigned));h->count=5;}
 h->value[h->count]=r->value_c;h->ms[h->count]=r->sample_ms;h->count++;h->valid=true;
}
bool plus_stagger_align(const plus_stagger_t *s,unsigned member,unsigned now,double *value,double *uncertainty){
 if(member>=3)return false;
 const plus_history_t *h=&s->sensor[member];
 if(!h->valid||h->count<6||h->ms[5]>now||now-h->ms[5]>100)return false;
 /* Slope uses ONLY the five observations preceding the newest conversion;
  * an abrupt newest offset is not itself extrapolated as a thermal slope. */
 double slopes[10];unsigned n=0;
 for(unsigned i=0;i<5;i++)for(unsigned j=i+1;j<5;j++)
  slopes[n++]=(h->value[j]-h->value[i])/((h->ms[j]-h->ms[i])/1000.);
 for(unsigned i=1;i<10;i++){double x=slopes[i];unsigned j=i;while(j&&slopes[j-1]>x){slopes[j]=slopes[j-1];j--;}slopes[j]=x;}
 double slope=.5*(slopes[4]+slopes[5]);
 double age=(now-h->ms[5])/1000.;
 if(!isfinite(slope)||fabs(slope)>2.5)return false;
 *value=h->value[5]+slope*age;
 /* Six of ten slopes span >=.2s: +/- .1C conversion noise gives <=1C/s
  * median slope uncertainty. The oldest slope midpoint is <.5s old; the
  * existing3C/s^2 curvature adds <=1.5C/s. Existing pair floors still cover
  * readout noise. Alignment uncertainty is additional, not a lower threshold. */
 *uncertainty=2.5*age+1.5*age*age;
 return isfinite(*value)&&*uncertainty<=.265000001;
}
double plus_conservative_difference(double delta,double uncertainty){
 return copysign(fmax(0.,fabs(delta)-uncertainty),delta);
}
void plus_stagger_pairs(plus_stagger_t *s,unsigned now){
 const unsigned endpoints[3][2]={{0,1},{0,2},{1,2}};
 for(unsigned j=0;j<3;j++){
  unsigned a=endpoints[j][0],b=endpoints[j][1];
  plus_history_t *ha=&s->sensor[a],*hb=&s->sensor[b];
  if(!ha->count||!hb->count)continue;
  unsigned ta=ha->ms[ha->count-1],tb=hb->ms[hb->count-1];
  /* Reusing a held conversion cannot count as another persistence witness. */
  if(s->used[j]&&(ta<=s->used_ms[j][0]||tb<=s->used_ms[j][1])){s->rejected_reuse++;continue;}
  s->used[j]=true;s->used_ms[j][0]=ta;s->used_ms[j][1]=tb;
  double va=0,vb=0,ua=0,ub=0;
  bool valid=plus_stagger_align(s,a,now,&va,&ua)&&plus_stagger_align(s,b,now,&vb,&ub);
  runtime_observation_t o={0};o.time_ms=o.source_ms=o.reference_ms=now;
  o.source_valid=o.reference_valid=valid;o.reference_enabled=true;
  o.source_c=(float)plus_conservative_difference(va-vb,ua+ub);o.reference_c=0;
  double e=clo_existing_pair_strength(&s->pair[j],&o);
  if(valid){s->accepted_pairs++;s->strength=fmax(s->strength,e);}else s->rejected_alignment++;
 }
}
