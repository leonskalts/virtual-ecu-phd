#ifndef REDUNDANT_TEMPERATURE_H
#define REDUNDANT_TEMPERATURE_H
#include <stdbool.h>
#include <stdint.h>
/* Separate ADC/reference chain: runtime state, not the counterfactual ECU. */
typedef struct {
    float value_c, offset_c, noise_c;
    uint32_t random_state;
    unsigned int sample_ms;
    bool initialized, valid, failed;
} redundant_temperature_t;
void redundant_temperature_init(redundant_temperature_t *, uint32_t, float, float);
void redundant_temperature_sample(redundant_temperature_t *, unsigned int, float);
#endif
