#include "redundant_temperature.h"
#include <math.h>
/* Sensor-model boundary is the only consumer of physical temperature. Never
 * reads primary acquisition/delivery, control estimates or injection labels. */
void redundant_temperature_init(redundant_temperature_t *s, uint32_t seed,
                                float offset, float noise)
{
    *s=(redundant_temperature_t){.offset_c=offset,.noise_c=noise,
        .random_state=seed?seed:1,.initialized=true};
}
void redundant_temperature_sample(redundant_temperature_t *s,unsigned int now,
                                  float physical_c)
{
    if(!s->initialized || (s->valid && now<=s->sample_ms))return;
    uint32_t x=s->random_state;
    x^=x<<13;x^=x>>17;x^=x<<5;s->random_state=x;
    float noise=s->noise_c*(2.0f*(float)(x&65535U)/65535.0f-1.0f);
    float measured=physical_c+s->offset_c+noise;
    s->value_c=isfinite(measured) && measured>-100000 && measured<100000 ?
        (float)(int)(measured*100.0f+(measured>=0?.5f:-.5f))/100.0f : measured;
    s->sample_ms=now;s->valid=isfinite(s->value_c);s->failed=!s->valid;
}
