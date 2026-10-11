#ifndef ANALYTICAL_THERMAL_H
#define ANALYTICAL_THERMAL_H
#include <stdbool.h>
/* Intentionally excludes all coolant readouts, plant state and injection data. */
typedef struct {unsigned ms; double load,ambient,speed,pump,fan;} analytical_input_t;
typedef struct {double coefficient[8],initial,sigma,bound;unsigned model;} analytical_config_t;
typedef struct {double temperature,previous_pump,previous_fan;unsigned ms;bool initialized;} analytical_state_t;
void analytical_thermal_step(analytical_state_t *,const analytical_config_t *,const analytical_input_t *);
/* Readouts enter consistency only; never the predictor state update. */
double analytical_consistency(const analytical_state_t *,const analytical_config_t *,const double[3],const bool[3],bool *);
#endif
