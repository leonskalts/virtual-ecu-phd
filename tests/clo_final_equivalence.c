/* Streaming replay of archived allowlisted observations; no injector or truth. */
#include "clo_final_sparse_math.h"
#include "clo_final_observation_io.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv) {
 if(argc!=9)return 2;
 clo_final_config_t c={strtod(argv[1],NULL),strtod(argv[2],NULL),strtod(argv[3],NULL),strtod(argv[4],NULL),strtod(argv[5],NULL),strtod(argv[6],NULL),strtod(argv[7],NULL),(unsigned int)strtoul(argv[8],NULL,10)};
 if(!clo_final_config_valid(&c))return 2;
 clo_final_t reference,optimized;clo_final_init(&reference);clo_final_init(&optimized);
 char header[4096];if(!fgets(header,sizeof(header),stdin))return 2;
 runtime_observation_t o;unsigned long rows=0;int status;
 while((status=final_observation_read(stdin,&o))>0) {
  clo_final_step(&reference,&c,&o);clo_final_optimized_step(&optimized,&c,&o);
  clo_final_diagnostic(&reference.evidence,o.time_ms,3000);clo_final_diagnostic(&optimized.evidence,o.time_ms,3000);
  if(memcmp(&reference,&optimized,sizeof(reference))){fprintf(stderr,"Bit mismatch at %u ms\n",o.time_ms);return 1;}rows++;
 }
 if(status<0)return 2;
 printf("%lu\n",rows);return 0;
}
