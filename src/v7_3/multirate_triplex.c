#include "multirate_triplex.h"
#include <math.h>
#include <string.h>
/* Same FAST contract as retained core. Period changes only measured elapsed
 * time and the1-second edge-history length; noise/slew/persistence unchanged.
 * SLOW32-second evidence remains in the retained Triplex and is not rescaled. */
static double fast_pair(mr_pair_t *s,const runtime_observation_t *o,unsigned period)
{
    s->fast_strength=0;
    bool valid=o->reference_enabled && o->reference_valid && !o->reference_failed &&
        o->source_valid && o->source_ms==o->time_ms && o->reference_ms==o->source_ms &&
        isfinite(o->source_c) && isfinite(o->reference_c);
    if(!valid || (s->fast_valid && o->time_ms!=s->fast_last_ms+period)) {
        s->fast_valid=false;s->fast_active=false;s->fast_count=0;
        s->fast_index=0;s->fast_edges=0;
        s->fast_integral=0;s->fast_bound_integral=0;s->fast_integral_count=0;
        for(unsigned int i=0;i<40;i++)s->fast_edge_history[i]=0;
    }
    if(!valid)return 0;
    double delta=(double)o->source_c-o->reference_c;
    bool edge=s->fast_valid && fabs(delta-s->fast_previous)>.40+1.2*period/1000.;
    s->fast_edges-=s->fast_edge_history[s->fast_index];
    s->fast_edge_history[s->fast_index]=edge;s->fast_edges+=edge;
    s->fast_index=(s->fast_index+1)%(1000/period);
    if(s->fast_active && o->time_ms-s->fast_anchor_ms>300)s->fast_active=false;
    if(edge && !s->fast_active) {
        s->fast_anchor=s->fast_previous;s->fast_anchor_ms=s->fast_last_ms;
        s->fast_active=true;s->fast_count=0;s->fast_sign=0;
        s->fast_integral=0;s->fast_bound_integral=0;s->fast_integral_count=0;s->fast_integral_sign=0;
    }
    if(s->fast_active) {
        double h=(o->time_ms-s->fast_anchor_ms)/1000.;
        double residual=delta-s->fast_anchor;
        int sign=residual>0?1:-1;
        /* Bounded signed-window certificate: both acquisitions must exceed
         * the0.40C noise-only floor in the same direction; their mean must
         * exceed the mean original slew+noise envelope. Never carry across
         * a recovery, sign reversal, gap or expired300ms anchor. This uses
         * the existing uncertainty bounds, not a lower detection threshold. */
        if(fabs(residual)>.40 && (!s->fast_integral_count || sign==s->fast_integral_sign)) {
            s->fast_integral+=fabs(residual);s->fast_bound_integral+=.40+1.2*h;
            s->fast_integral_count++;s->fast_integral_sign=sign;
            if(s->fast_integral_count>=2 && s->fast_integral>s->fast_bound_integral)
                s->fast_strength=1;
        } else {s->fast_integral=0;s->fast_bound_integral=0;s->fast_integral_count=0;}
        if(fabs(residual)>.40+1.2*h) {
            s->fast_count=sign==s->fast_sign?s->fast_count+1:1;s->fast_sign=sign;
            if(s->fast_count>=2)s->fast_strength=1;
        } else {s->fast_active=false;s->fast_count=0;}
    }
    if(s->fast_edges>=3)s->fast_strength=1;
    s->fast_previous=delta;s->fast_last_ms=o->time_ms;s->fast_valid=true;
    return s->fast_strength;
}

void mr_triplex_init(mr_triplex_t *s,unsigned period){memset(s,0,sizeof(*s));s->period=period;}
void mr_triplex_step(mr_triplex_t *s,unsigned now,const float value[3],bool valid)
{
 s->strength=0;s->ambiguous=false;
 if(s->period!=25&&s->period!=50)return;
 if(valid)s->qualified_count++;else s->qualified_count=0;
 bool qualified=valid&&s->qualified_count*s->period>=500;
 if(qualified)s->qualified_observations++;
 const unsigned endpoints[3][2]={{0,1},{0,2},{1,2}};
 for(unsigned j=0;j<3;j++){
  runtime_observation_t o={0};o.time_ms=o.source_ms=o.reference_ms=now;
  o.source_valid=o.reference_valid=valid;o.reference_enabled=true;
  o.source_c=value[endpoints[j][0]];o.reference_c=value[endpoints[j][1]];
  double strength=fast_pair(&s->pair[j],&o,s->period);
  if(qualified)s->strength=fmax(s->strength,strength);
 }
 if(qualified)s->ambiguous=fabs(value[0]-value[1])>.90&&fabs(value[0]-value[2])>.90&&fabs(value[1]-value[2])>.90;
}
