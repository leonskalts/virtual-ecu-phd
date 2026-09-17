#include "clo_dsf.h"
/* Columns NORMAL, MEMORY, TIMING, COMMUNICATION, SENSOR_CONTROL, ACTUATOR.
 * Architectural capability only: never indexed using an injected origin. */
#define D CLO_DIRECT
#define I CLO_INDIRECT
#define U CLO_UNAVAILABLE
#define N CLO_NOT_APPLICABLE
const clo_observability_t clo_observability[CLO_CHANNELS][DS_ATOMS] = {
    {N,N,D,N,N,N}, {N,N,N,D,N,N}, {N,D,N,N,N,N},
    {N,N,N,I,I,N}, {N,N,N,N,N,D}, {N,I,I,I,I,I}
};
const unsigned int clo_supported_subsets[CLO_CHANNELS] = {
    CLO_TIMING, CLO_COMMUNICATION, CLO_MEMORY,
    CLO_SENSOR_CONTROL | CLO_COMMUNICATION, CLO_ACTUATOR, CLO_ABNORMAL
};
const char *const clo_channel_names[CLO_CHANNELS] = {
    "timing", "communication", "memory_control", "sensor_control", "actuator", "plant"
};
/* Edges use CHANNEL indices. Skipped intermediate stages are allowed.
 * Command tracking cannot prove propagation of a corrupted command; hence
 * an absent actuator mismatch is never required for a plant transition. */
const unsigned int clo_propagation_edges[CLO_CHANNELS] = {
    (1U<<3)|(1U<<4)|(1U<<5), (1U<<3)|(1U<<4)|(1U<<5),
    (1U<<3)|(1U<<4)|(1U<<5), (1U<<4)|(1U<<5), (1U<<5), 0
};
double clo_reliability(clo_observability_t kind, const clo_config_t *c)
{
    return kind == CLO_DIRECT ? c->r_direct : kind == CLO_INDIRECT ? c->r_indirect : 0;
}
