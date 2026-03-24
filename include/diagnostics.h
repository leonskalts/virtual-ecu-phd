#ifndef DIAGNOSTICS_H
#define DIAGNOSTICS_H

#include "ecu_types.h"

void diagnostics_init(ecu_state_t *state);
void diagnostics_step(ecu_state_t *state);
diagnostic_class_t diagnostics_dtc_class(const dtc_status_t *status);
const char *diagnostics_dtc_label(diagnostic_id_t id);
const char *diagnostics_class_label(diagnostic_class_t diag_class);

#endif
