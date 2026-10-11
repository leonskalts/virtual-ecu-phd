#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include "clo_dsf_revised.h"
#include "sensor_confirmation.h"
#include "model.h"
#include "ages.h"
static int timing;
static uint64_t boundary;
static uint64_t ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC_RAW,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
static void native_boundary(void){if(timing)boundary=ns();}
double triplex_extra_strength,dc_mass,dc_origin,dc_discount,ba_provider[7];
bool triplex_extra_ambiguous;
static const double *packet;
static sensor_confirmation_t gate;
static unsigned alarm,origin;
void benchmark_capture(unsigned a,const clo_revised_t*s,const runtime_observation_t*o,double q,double l){(void)a;(void)s;(void)o;(void)q;(void)l;}
void ba_capture(const clo_revised_t*s,const runtime_observation_t*o,double q){
 const clo_evidence_t*e=&s->fusion.evidence;unsigned other=0;
 for(unsigned i=0;i<6;i++)if(i!=3&&e->available[i]&&e->strength[i]>0)other|=1U<<i;
 alarm=sensor_confirmation_step(&gate,o->time_ms,packet[61]==7&&!packet[62]&&!packet[66],other||s->direct_origins,q,s->fusion.output.alarm,3,.5);
 origin=alarm?s->fusion.output.estimated_origin>>1:0;
}
#include "core.inc"
static const clo_final_config_t config={1,.8,.35,.5,.55,.15,.5,1};
static clo_revised_t state;
static double history[50][6],availability[50][6];
static unsigned head;
static void feature(const double*p,const double*e,double*x){
 for(int i=0;i<66;i++)x[i]=p[i+1];
 for(unsigned i=0;i<sizeof(age_columns)/sizeof(*age_columns);i++){int k=age_columns[i];if(x[k]>=0)x[k]=p[0]-x[k];}
 for(int i=0;i<66;i++){x[66+i]=isfinite(x[i]);if(!isfinite(x[i]))x[i]=0;}
 for(int i=0;i<6;i++){double v=e[6+i]?e[i]:0;x[132+i]=v;x[138+i]=e[6+i];x[144+i]=e[12+i];history[head][i]=v;availability[head][i]=e[6+i];}
 for(int w=0;w<2;w++){int width=w?50:10;for(int j=0;j<6;j++){double sum=0,count=0,max=0;for(int k=0;k<width;k++){unsigned idx=(head+51-width+k)%50;sum+=history[idx][j];count+=availability[idx][j];if(history[idx][j]>max)max=history[idx][j];}x[150+w*12+j]=count?sum/count:0;x[156+w*12+j]=max;}}
 head=(head+1)%50;
}
static void infer(const double*x,double*p,unsigned*a,unsigned*o){
 float xf[174];for(int i=0;i<174;i++)xf[i]=(float)x[i];memset(p,0,6*sizeof(double));
 for(int t=0;t<200;t++){int k=roots[t];while(nodes[k].left>=0)k=xf[nodes[k].feature]<=nodes[k].threshold?nodes[k].left:nodes[k].right;for(int j=0;j<6;j++)p[j]+=nodes[k].p[j];}
 for(int j=0;j<6;j++)p[j]/=200;
 double fault=1-p[0],best=-1,second=-1;unsigned top=0;
 for(int j=0;j<5;j++){double v=fault>0?p[j+1]/fault:0;if(v>best){second=best;best=v;top=j;}else if(v>second)second=v;}
 *a=fault>0.9155568509788313;*o=*a&&best>=.7&&best-second>=0?1U<<top:0;
}
/* output: 6 probabilities, RF alarm/origin, CLOVER alarm/origin.
 * times: replayable CLOVER upstream/core-decision, RF features/inference, full core.
 * Both methods reset at every call (one case). No outcome is consumed. */
void replay(unsigned n,const double*packets,const double*evidence,double*out,double*times,int measure){
 timing=measure;clo_triplex_core_init(&state);memset(&gate,0,sizeof(gate));memset(history,0,sizeof(history));memset(availability,0,sizeof(availability));head=0;
 for(unsigned i=0;i<n;i++){
  const double*p=packets+67*i;packet=p;runtime_observation_t o={0};
#include "assign.inc"
  triplex_extra_strength=p[55];triplex_extra_ambiguous=p[56];dc_mass=dc_origin=p[66];
  uint64_t t0=measure?ns():0;clo_triplex_core_step(&state,&config,&o);uint64_t t1=measure?ns():0;
  out[10*i+8]=alarm;out[10*i+9]=origin;
  double x[174];uint64_t t2=measure?ns():0;feature(p,evidence+18*i,x);uint64_t t3=measure?ns():0;unsigned a,b;infer(x,out+10*i,&a,&b);uint64_t t4=measure?ns():0;
  out[10*i+6]=a;out[10*i+7]=b;
  if(measure){times[5*i]=boundary-t0;times[5*i+1]=t1-boundary;times[5*i+2]=t3-t2;times[5*i+3]=t4-t3;times[5*i+4]=t1-t0;}
 }
}
void sizes(unsigned long*out){out[0]=sizeof(state);out[1]=sizeof(gate);out[2]=sizeof(history)+sizeof(availability)+sizeof(head);out[3]=sizeof(nodes)+sizeof(roots);}
