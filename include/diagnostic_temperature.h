#ifndef DIAGNOSTIC_TEMPERATURE_H
#define DIAGNOSTIC_TEMPERATURE_H
#include <stdbool.h>
#include <stdint.h>
/* Independent physical sensing chain; the observer only receives its readout. */
typedef struct {
 float value_c,previous_c;
 unsigned sample_ms,previous_ms;
 bool valid,previous_valid,failed;
} diagnostic_readout_t;
typedef struct {
 diagnostic_readout_t output;
 float offset,gain,noise,quantum,adc_reference_gain,lag_ms;
 double thermal_state,previous_physical;
 unsigned period_ms,phase_ms,next_ms,last_physical_ms;
 uint32_t random_state;
 bool initialized;
} diagnostic_temperature_t;
void diagnostic_temperature_init(diagnostic_temperature_t *,uint32_t,float,float,float,float,float,unsigned,unsigned,float);
bool diagnostic_temperature_sample(diagnostic_temperature_t *,unsigned,float);
#endif
