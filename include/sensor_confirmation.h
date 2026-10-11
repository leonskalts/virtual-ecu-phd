#ifndef SENSOR_CONFIRMATION_H
#define SENSOR_CONFIRMATION_H
#include <stdbool.h>
typedef struct {unsigned previous_ms,count;bool initialized,last;} sensor_confirmation_t;
/* Only legacy sensor-only evidence with a complete PASS witness is eligible.
 * Any current cross-layer support or retained direct-origin provenance bypasses.
 * This operates on the output alarm; DS masses and origins are never rewritten. */
bool sensor_confirmation_step(sensor_confirmation_t *,unsigned ms,bool integrity_pass,
 bool independent_support,double qualified_strength,bool base_alarm,unsigned required,double threshold);
#endif
