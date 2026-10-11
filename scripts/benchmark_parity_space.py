#!/usr/bin/env python3
"""Matched host diagnostic-kernel timing; not embedded WCET."""
import json,subprocess
import run_parity_space as d
import select_parity_space as p
import numpy as np
B=d.B;O=d.O
SOURCE=r'''
#include "triplex_parity.h"
#include "memory_diagnostic.h"
#include "multirate_memory.h"
#include <stdio.h>
#include <time.h>
static unsigned short target=94;
static uint16_t read_reg(void *p){return *(uint16_t*)p;}
static void write_reg(void *p,uint16_t v){*(uint16_t*)p=v;}
static double data[10000][4];
int main(int argc,char **argv){
 if(argc!=3)return 1;FILE *f=fopen(argv[1],"r");unsigned n=0;
 while(n<10000&&fscanf(f,"%lf %lf %lf %lf",&data[n][0],&data[n][1],&data[n][2],&data[n][3])==4)n++;fclose(f);
 parity_config_t c;f=fopen(argv[2],"r");if(fscanf(f,"%lf %lf %lf %lf %lf %lf %lf %lf %lf",&c.mu[0],&c.mu[1],&c.l00,&c.l10,&c.l11,&c.tau,&c.saturation,&c.beta,&c.dominance)!=9)return 2;fclose(f);
 volatile double sink=0;
 for(unsigned rep=0;rep<7;rep++)for(unsigned m=0;m<4;m++){
  unsigned mode=rep%2?3-m:m;clock_t start=clock();unsigned probes=0;
  for(unsigned repeat=0;repeat<100;repeat++){
   parity_state_t s={0};memory_diagnostic_t mem={0};
   for(unsigned i=0;i<n;i++){
    if(i&&data[i][0]==0){probes+=mem.checks;mem=(memory_diagnostic_t){0};s=(parity_state_t){0};}
    unsigned now=(unsigned)data[i][0];if(mode>=2)mr_memory_step(&mem,now,250,read_reg,write_reg,&target);else memory_diagnostic_step(&mem,now,read_reg,write_reg,&target);
    if(mode&1){parity_input_t u={now,data[i][1],data[i][2],data[i][3]!=0};triplex_parity_step(&s,&c,&u);sink+=s.g+s.mass;}
   }probes+=mem.checks;
  }
  printf("%u,%u,%.17g,%u,%zu,%zu,%zu\n",rep,mode,((double)(clock()-start)/CLOCKS_PER_SEC)/(100*n),probes,sizeof(parity_state_t),sizeof(parity_config_t),sizeof(memory_diagnostic_t));
 }return sink<0;
}
'''
def main():
 d.verify();cases=[]
 for row,a in d.dataset('TRAIN'):
  if row['origin']=='NORMAL':cases.append(a['input'][:,:4])
  if len(cases)==8:break
 np.savetxt(B/'bench_inputs.txt',np.concatenate(cases));(B/'bench_params.txt').write_text(' '.join(map(str,p.vector(json.loads((B/'selected_parity.json').read_text())))));(B/'bench.c').write_text(SOURCE)
 subprocess.run(['gcc','-std=c11','-O2','-Iinclude',str(B/'bench.c'),'src/v7_3/triplex_parity.c','src/memory_diagnostic.c','src/v7_3/multirate_memory.c','-lm','-o',str(B/'bench')],check=True)
 result=subprocess.check_output([str(B/'bench'),str(B/'bench_inputs.txt'),str(B/'bench_params.txt')],text=True);(B/'bench.csv').write_text(result);a=np.loadtxt(B/'bench.csv',delimiter=',');times={m:float(np.median(a[a[:,1]==m,2])) for m in range(4)}
 rr=dict(seconds_per_update=times,parity_delta=times[1]-times[0],memory_delta=times[2]-times[0],combined_delta=times[3]-times[0],parity_state_bytes=int(a[0,4]),parity_config_bytes=int(a[0,5]),memory_state_bytes=int(a[0,6]),timing_repetitions=7,streams=8,repeats_per_timing=100)
 d.dump(B/'overhead.json',rr);(O/'overhead.md').write_text('# Diagnostic-kernel host overhead\n\n'+json.dumps(rr,indent=2)+'\n\nFour window scores share an eight-element ring. Two-dimensional triangular Cholesky solves; fewer than220 floating adds/multiplies/divides per fully populated update, excluding comparisons/integer bookkeeping. No runtime covariance fitting or matrix inverse. Includes existing memory diagnostic kernel; excludes DS/simulation/CSV. Seven order-balanced host timings, not embedded WCET. Baseline memory121probes/120s;250mscandidate481probes, seven operations/probe, +2520operations. Candidate reuses existing memory diagnostic state; combined incremental mutable state is parity_state_bytes. Memory model writes are atomic, restore verified; no actuation.\n');print(rr,flush=True)
if __name__=='__main__':main()
