#include "diagnostic_temperature.h"
#include <math.h>
void diagnostic_temperature_init(diagnostic_temperature_t *s,uint32_t seed,float offset,float gain,float noise,float quantum,float reference,unsigned period,unsigned phase,float lag)
{
 *s=(diagnostic_temperature_t){.random_state=seed?seed:1,.offset=offset,.gain=gain,.noise=noise,.quantum=quantum,.adc_reference_gain=reference,.period_ms=period,.phase_ms=phase,.next_ms=phase,.lag_ms=lag};
}
bool diagnostic_temperature_sample(diagnostic_temperature_t *s,unsigned now,float physical)
{
 if(!s->period_ms || !(s->quantum>0) || !isfinite(physical)){s->output.failed=true;s->output.valid=false;return false;}
 if(!s->initialized){s->previous_physical=physical;s->thermal_state=physical;s->last_physical_ms=now;s->initialized=true;}
 bool acquired=false;
 while(s->next_ms<=now){
  unsigned t=s->next_ms;s->next_ms+=s->period_ms;
  double w=now>s->last_physical_ms?((double)t-s->last_physical_ms)/(now-s->last_physical_ms):1;
  if(w<0)w=0;
  if(w>1)w=1;
  double at_sample=s->previous_physical+w*(physical-s->previous_physical);
  double alpha=s->lag_ms>0?1-exp(-(double)s->period_ms/s->lag_ms):1;
  s->thermal_state+=alpha*(at_sample-s->thermal_state);
  uint32_t x=s->random_state;x^=x<<13;x^=x>>17;x^=x<<5;s->random_state=x;
  double noise=s->noise*(2.*(x&65535U)/65535.-1);
  double measured=((1+s->gain)*s->thermal_state+s->offset+noise)*(1+s->adc_reference_gain);
  s->output.previous_c=s->output.value_c;s->output.previous_ms=s->output.sample_ms;s->output.previous_valid=s->output.valid;
  s->output.value_c=(float)(round(measured/s->quantum)*s->quantum);s->output.sample_ms=t;s->output.valid=isfinite(measured);s->output.failed=!s->output.valid;acquired=true;
 }
 s->previous_physical=physical;s->last_physical_ms=now;return acquired;
}
