#ifndef CLO_FINAL_OBSERVATION_IO_H
#define CLO_FINAL_OBSERVATION_IO_H
#include <stdio.h>
#include "runtime_observation.h"
void final_observation_header(FILE *f);
void final_observation_write(FILE *f,const runtime_observation_t *o);
/* Caller consumes the header first. Hexadecimal float CSV preserves input bits. */
int final_observation_read(FILE *f,runtime_observation_t *o);
#endif
