#define _GNU_SOURCE
#include <pthread.h>
#include <sys/mman.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
/* External stack measurement: unchanged replay function, no detector instrumentation.
 * Includes pthread startup/TLS and the common replay wrapper; not per-method WCET. */
typedef void (*run_t)(unsigned,const double*,const double*,double*,double*,int);
struct args{run_t run;unsigned n;const double*p,*e;double*out,*tm;};
static void*worker(void*vp){struct args*a=vp;if(a->run)a->run(a->n,a->p,a->e,a->out,a->tm,0);return NULL;}
unsigned long watermark(run_t run,unsigned n,const double*p,const double*e,double*out,double*tm){
 const size_t length=1024*1024;unsigned char*base=mmap(NULL,length,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(base==MAP_FAILED)abort();memset(base,0xa5,length);
 pthread_attr_t at;pthread_attr_init(&at);if(pthread_attr_setstack(&at,base,length))abort();pthread_t thread;struct args a={run,n,p,e,out,tm};if(pthread_create(&thread,&at,worker,&a))abort();pthread_join(thread,NULL);pthread_attr_destroy(&at);
 size_t i=0;while(i<length&&base[i]==0xa5)i++;munmap(base,length);return length-i;
}
