#include "sensor_confirmation.h"
#include <math.h>
bool sensor_confirmation_step(sensor_confirmation_t *s,unsigned ms,bool pass,
 bool other,double strength,bool alarm,unsigned required,double threshold)
{
 if(!required)return alarm;
 /* FAIL and UNKNOWN never permit suppression, including duplicate timestamps. */
 if(!pass||other){s->count=0;s->previous_ms=ms;s->initialized=true;s->last=alarm;return alarm;}
 if(s->initialized&&ms<=s->previous_ms)return alarm&&s->last;
 if(!s->initialized||ms-s->previous_ms!=100)s->count=0;
 s->initialized=true;s->previous_ms=ms;
 if(isfinite(strength)&&strength>0&&strength>=threshold){if(s->count<required)s->count++;}
 else s->count=0;
 s->last=alarm&&s->count>=required;return s->last;
}
