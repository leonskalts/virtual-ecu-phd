#!/usr/bin/env python3
"""Matched diagnostic-kernel host timing, not embedded WCET."""
import json,subprocess,statistics
from pathlib import Path
import run_heterogeneous_observability as d
import numpy as np
B=d.B;O=d.O
SOURCE=r'''
#include "analytical_thermal.h"
#include "memory_diagnostic.h"
#include "multirate_memory.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static unsigned short target=94;
static uint16_t read_reg(void *p){return *(uint16_t *)p;}
static void write_reg(void *p,uint16_t v){*(uint16_t *)p=v;}
static double data[10000][10];
int main(int argc,char **argv){
 if(argc!=3)return 1;FILE *f=fopen(argv[1],"r");unsigned n=0;
 while(n<10000&&fscanf(f,"%lf %lf %lf %lf %lf %lf %lf %lf %lf %lf",&data[n][0],&data[n][1],&data[n][2],&data[n][3],&data[n][4],&data[n][5],&data[n][6],&data[n][7],&data[n][8],&data[n][9])==10)n++;fclose(f);
 analytical_config_t p={0};f=fopen(argv[2],"r");if(fscanf(f,"%u %lf %lf %lf",&p.model,&p.initial,&p.sigma,&p.bound)!=4)return 2;for(unsigned j=0;j<8;j++)if(fscanf(f,"%lf",&p.coefficient[j])!=1)return 3;fclose(f);
 volatile double sink=0;
 for(unsigned rep=0;rep<5;rep++)for(unsigned m=0;m<4;m++){
  unsigned mode=rep%2?3-m:m;clock_t begin=clock();unsigned checks=0,ops=0;
  for(unsigned repeat=0;repeat<100;repeat++){
   analytical_state_t s={0};memory_diagnostic_t mem={0};
   for(unsigned i=0;i<n;i++){
    if(i&&data[i][0]==0){checks+=mem.checks;ops+=mem.operations;mem=(memory_diagnostic_t){0};s=(analytical_state_t){0};}
    analytical_input_t u={(unsigned)data[i][0],data[i][1],data[i][2],data[i][3],data[i][4],data[i][5]};
    if(mode&1)mr_memory_step(&mem,u.ms,250,read_reg,write_reg,&target);else memory_diagnostic_step(&mem,u.ms,read_reg,write_reg,&target);
    if(mode>=2){analytical_thermal_step(&s,&p,&u);double v[3]={data[i][6],data[i][7],data[i][8]};bool valid[3]={true,true,data[i][9]>0},amb; sink+=analytical_consistency(&s,&p,v,valid,&amb);}
   }
   checks+=mem.checks;ops+=mem.operations;
  }
  printf("%u,%u,%.17g,%u,%u,%zu,%zu,%zu\n",rep,mode,((double)(clock()-begin)/CLOCKS_PER_SEC)/(100*n),checks,ops,sizeof(analytical_state_t),sizeof(analytical_config_t),sizeof(memory_diagnostic_t));
 }
 return sink<0;
}
'''
def main():
 d.verify();ss=json.loads((B/'specs.json').read_text());cases=[next(s for s in ss if s['group']==f'hetero_family_{f}' and s['origin']=='NORMAL') for f in range(8)]
 data=np.concatenate([np.load(B/'tapes'/(s['run_id']+'.npz'))['inputs'][:,:10] for s in cases]);np.savetxt(B/'bench_inputs.txt',data)
 (B/'bench.c').write_text(SOURCE);subprocess.run(['gcc','-std=c11','-O2','-Iinclude',str(B/'bench.c'),'src/v7_3/analytical_thermal.c','src/memory_diagnostic.c','src/v7_3/multirate_memory.c','-lm','-o',str(B/'bench')],check=True)
 output=subprocess.check_output([str(B/'bench'),str(B/'bench_inputs.txt'),str(B/'parameters.txt')],text=True);(B/'bench.csv').write_text(output);a=np.loadtxt(B/'bench.csv',delimiter=',');times={m:float(np.median(a[a[:,1]==m,2])) for m in range(4)}
 result=dict(seconds_per_update=times,analytical_delta=times[2]-times[0],memory_delta=times[1]-times[0],combined_delta=times[3]-times[0],predictor_state_bytes=int(a[0,5]),config_bytes=int(a[0,6]),memory_state_bytes=int(a[0,7]),scope='matched diagnostic kernels on 8 seen TRAIN benign streams, 5 order-balanced repetitions, 100 repeats per timing; excludes DS/simulation/CSV; no embedded WCET')
 d.dump(O/'overhead.json',result);(O/'overhead.md').write_text('# Host diagnostic-kernel overhead\n\n'+json.dumps(result,indent=2)+'\n\n10Hz updates. Predictor: bounded eight multiply-accumulates plus input transformations/Euler update; consistency: three normalized residuals and bounded comparisons, no matrix solver at runtime. Parameters identified offline. Baseline memory mean1000ms/max1100ms; candidate mean250ms/max300ms. Over120s baseline121probes847operations; candidate481probes3367operations, +2520operations. Four reads/three writes per atomic probe, including restoration verification. Existing memory state is reused; analytical mutable state is additional. Config is read-only. This is incremental host diagnostic-kernel timing, not full-controller timing or embedded WCET.\n')
 print(result,flush=True)
if __name__=='__main__':main()
