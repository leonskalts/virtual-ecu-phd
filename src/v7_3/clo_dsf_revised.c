#include "clo_dsf_revised.h"
#include "config.h"
#include <math.h>

/* Contract: actuators_step realizes clamp(command) synchronously before this
 * scheduler's detector call. Adjacent representable floats are conservatively
 * accepted, avoiding a fitted physical tolerance. This is a virtual-ECU
 * contract, not an assumed physical actuator model or a calibrated probability.
 * Non-finite or off-cadence observations contribute no actuator evidence. */
static bool outside_response_contract(float command, float actual)
{
    const float expected = fminf(1.0f, fmaxf(0.0f, command));
    return actual < nextafterf(expected, -INFINITY) ||
           actual > nextafterf(expected, INFINITY);
}
void clo_revised_extract(clo_evidence_t *e, const runtime_observation_t *o)
{
    c2_extract(e, o);
    e->available[4] = e->available[4] && o->time_ms % ECU_ACTUATOR_PERIOD_MS == 0;
    e->strength[4] = e->available[4] &&
        (outside_response_contract(o->pump_command, o->pump_actual) ||
         outside_response_contract(o->fan_command, o->fan_actual)) ? 1.0 : 0.0;
}

/* Reuse the frozen algorithm verbatim, substituting only its extractor.
 * The independent frames, temporal fusion, uncertainty, UNKNOWN gates and
 * diagnostic isolation remain the exact v7.2 implementation. */
#define c2_extract clo_revised_extract
#define clo_final_step clo_revised_step
#define clo_final_init clo_revised_unused_init
#define clo_final_config_valid clo_revised_unused_config_valid
#define clo_final_diagnostic clo_revised_unused_diagnostic
#include "../v7_2/clo_dsf_final.c"
