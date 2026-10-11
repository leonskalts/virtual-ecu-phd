#ifndef ML_SENSOR_WEAK_H
#define ML_SENSOR_WEAK_H
#include <stdbool.h>
#define ML_SENSOR_FEATURES 12
#define ML_SENSOR_MAX_SV 256
/* Sensor-derived features only; no origin, injection, alarm or plant fields. */
typedef struct {unsigned time_ms;double value[ML_SENSOR_FEATURES],physical;bool qualified;} ml_sensor_input_t;
typedef struct {unsigned consecutive;unsigned previous_ms;} ml_sensor_state_t;
typedef struct {double alpha;unsigned gate;} ml_sensor_config_t;
/* Returns abnormal simple-support mass; remaining mass is ignorance. */
double ml_sensor_mass(ml_sensor_state_t *,const ml_sensor_config_t *,const ml_sensor_input_t *,double);
/* Frozen compact inference, trained/scaled/calibrated offline. */
typedef struct {
 unsigned rbf,n_support;
 double mean[ML_SENSOR_FEATURES],scale[ML_SENSOR_FEATURES],weight[ML_SENSOR_FEATURES];
 const double *support,*dual;
 double intercept,gamma,platt_slope,platt_intercept;
} ml_sensor_model_t;
double ml_sensor_margin(const ml_sensor_model_t *,const double *);
double ml_sensor_confidence(const ml_sensor_model_t *,const double *);

#endif
