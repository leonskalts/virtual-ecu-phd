#include "triplex_consistency.h"
#include <math.h>
#include <string.h>
void triplex_consistency_init(triplex_consistency_t *s){memset(s,0,sizeof(*s));clo_revised_init(&s->ac);clo_revised_init(&s->bc);}
void triplex_consistency_step(triplex_consistency_t *s,const runtime_observation_t *o,const diagnostic_readout_t *c)
{
 s->strength=s->ac_strength=s->bc_strength=0;s->qualified=false;s->ambiguous=false;s->member_pattern=0;
 runtime_observation_t ac=*o,bc=*o;
 bool valid=c->valid&&c->previous_valid&&!c->failed&&c->sample_ms<=o->time_ms&&o->time_ms-c->sample_ms<=100&&c->sample_ms==c->previous_ms+100;
 double projected=0;
 if(valid){projected=c->value_c+(c->value_c-c->previous_c)*(double)(o->time_ms-c->sample_ms)/(c->sample_ms-c->previous_ms);valid=isfinite(projected);}
 /* Only causal acquired C samples are projected to the A/B epoch. No physical
    state or injection metadata is available to this module. */
 ac.reference_enabled=true;ac.reference_valid=valid;ac.reference_failed=false;ac.reference_ms=o->time_ms;ac.reference_c=(float)projected;
 bc=ac;bc.source_c=o->reference_c;bc.source_valid=o->reference_valid&&!o->reference_failed;bc.source_ms=o->reference_ms;
 s->ac_strength=clo_existing_pair_strength(&s->ac,&ac);s->bc_strength=clo_existing_pair_strength(&s->bc,&bc);
 if(valid){s->samples++;s->qualified=s->samples>=5;}else s->samples=0;
 /* Explicit independently timestamped failed/stale acquisition is a diagnostic
    channel contract violation, never evidence from the injector's state. */
 bool status=o->time_ms>500&&(c->failed||(c->valid&&o->time_ms>c->sample_ms+200));
 if(s->qualified)s->strength=fmax(s->ac_strength,s->bc_strength);
 if(status)s->strength=1;
 s->aligned_c=projected;
 if(valid&&o->source_valid&&o->reference_valid){
  bool ab=fabs(o->source_c-o->reference_c)<=.90,ac_ok=fabs(o->source_c-projected)<=.90,bc_ok=fabs(o->reference_c-projected)<=.90;
  /* Pattern identifies a disagreement cut, NOT which side is actually faulty.
     1=A|BC,2=B|AC,3=C|AB,4=all mutually disagree;0=no unique cut. */
  s->member_pattern=bc_ok&&!ab&&!ac_ok?1:ac_ok&&!ab&&!bc_ok?2:ab&&!ac_ok&&!bc_ok?3:!ab&&!ac_ok&&!bc_ok?4:0;
  s->ambiguous=s->member_pattern==4;
 }
}
