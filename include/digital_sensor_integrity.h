#ifndef DIGITAL_SENSOR_INTEGRITY_H
#define DIGITAL_SENSOR_INTEGRITY_H
#include <stdint.h>
#include <stdbool.h>
typedef struct { uint32_t channel,bits,sequence,ms,tag; } di_record_t;
typedef struct { di_record_t protected_record; bool valid; } di_witness_t;
uint32_t di_tag(const di_record_t *r);
void di_publish(di_witness_t *w,di_record_t *r,unsigned channel,float value,unsigned ms);
void di_transform(di_witness_t *w,di_record_t *r,float offset);
unsigned di_verify(const di_witness_t *w,const di_record_t *r,float value,unsigned ms);
#endif
