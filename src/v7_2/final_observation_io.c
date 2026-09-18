/* Explicit runtime allowlist; no unused diagnosis/safety/detector or truth fields. */
#include "clo_final_observation_io.h"
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
typedef enum {UINT_FIELD,INT_FIELD,FLOAT_FIELD,BOOL_FIELD} field_type_t;
typedef struct {const char *name;size_t offset;field_type_t type;} field_t;
#define FIELD(name,type) {#name,offsetof(runtime_observation_t,name),type}
static const field_t fields[]={
 FIELD(time_ms,UINT_FIELD),FIELD(coolant_measured_c,FLOAT_FIELD),FIELD(sample_timestamp_ms,UINT_FIELD),FIELD(sample_age_ms,UINT_FIELD),FIELD(control_target_c,FLOAT_FIELD),
 FIELD(pump_command,FLOAT_FIELD),FIELD(fan_command,FLOAT_FIELD),FIELD(pump_actual,FLOAT_FIELD),FIELD(fan_actual,FLOAT_FIELD),FIELD(control_execution_ms,INT_FIELD),
 FIELD(engine_load,FLOAT_FIELD),FIELD(ambient_c,FLOAT_FIELD),FIELD(vehicle_speed_kph,FLOAT_FIELD),FIELD(sample_freshness_ok,BOOL_FIELD),FIELD(sample_expected_period_ms,UINT_FIELD),
 FIELD(timing.task_id,UINT_FIELD),FIELD(timing.time_ms,UINT_FIELD),FIELD(timing.period_ms,UINT_FIELD),FIELD(timing.relative_deadline_ms,UINT_FIELD),FIELD(timing.release_sequence,UINT_FIELD),FIELD(timing.execution_sequence,UINT_FIELD),
 FIELD(timing.current_release_ms,INT_FIELD),FIELD(timing.job_release_ms,INT_FIELD),FIELD(timing.actual_start_ms,INT_FIELD),FIELD(timing.actual_completion_ms,INT_FIELD),FIELD(timing.last_successful_execution_ms,INT_FIELD),FIELD(timing.execution_age_ms,UINT_FIELD),FIELD(timing.job_outstanding,BOOL_FIELD),FIELD(timing.missed_expected_execution,BOOL_FIELD),FIELD(timing.deadline_exceeded,BOOL_FIELD),FIELD(timing.cancelled_release_count,UINT_FIELD)};
#define COUNT (sizeof(fields)/sizeof(fields[0]))
void final_observation_header(FILE *f) {for(size_t i=0;i<COUNT;i++)fprintf(f,"%s%s",i?",":"",fields[i].name);fputc('\n',f);}
void final_observation_write(FILE *f,const runtime_observation_t *o)
{
 for(size_t i=0;i<COUNT;i++) {
  const void *p=(const char *)o+fields[i].offset;if(i)fputc(',',f);
  switch(fields[i].type) {
   case UINT_FIELD:fprintf(f,"%u",*(const unsigned int *)p);break;
   case INT_FIELD:fprintf(f,"%d",*(const int *)p);break;
   case FLOAT_FIELD:fprintf(f,"%a",(double)*(const float *)p);break;
   case BOOL_FIELD:fprintf(f,"%d",*(const bool *)p);break;
  }
 }fputc('\n',f);
}
int final_observation_read(FILE *f,runtime_observation_t *o)
{
 char line[4096];if(!fgets(line,sizeof(line),f))return ferror(f)?-1:0;
 memset(o,0,sizeof(*o));char *token=strtok(line,",\n\r");
 for(size_t i=0;i<COUNT;i++) {
  if(!token)return -1;
  void *p=(char *)o+fields[i].offset;char *end;errno=0;
  if(fields[i].type==FLOAT_FIELD){*(float *)p=strtof(token,&end);}
  else if(fields[i].type==INT_FIELD){long v=strtol(token,&end,10);if(v<INT_MIN||v>INT_MAX)return -1;*(int *)p=(int)v;}
  else {unsigned long v=strtoul(token,&end,10);if(*token=='-'||v>UINT_MAX)return -1;if(fields[i].type==BOOL_FIELD){if(v>1)return -1;*(bool *)p=v!=0;}else *(unsigned int *)p=(unsigned int)v;}
  if(errno||*end)return -1;
  token=strtok(NULL,",\n\r");
 }return token?-1:1;
}
