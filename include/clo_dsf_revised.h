#ifndef CLO_DSF_REVISED_H
#define CLO_DSF_REVISED_H
#include "clo_dsf_final.h"
/* Same frames/state/configuration; only actuator evidence extraction differs. */
void clo_revised_extract(clo_evidence_t *e, const runtime_observation_t *o);
void clo_revised_step(clo_final_t *s, const clo_final_config_t *c,
                      const runtime_observation_t *o);
#endif
