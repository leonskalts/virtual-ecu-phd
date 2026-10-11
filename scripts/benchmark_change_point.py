#!/usr/bin/env python3
"""Matched host diagnostic-kernel timing; not embedded WCET."""
import json,subprocess,platform
import run_change_point as d
import select_change_point as p
import numpy as np
B=d.B;O=d.O
SOURCE=r'''
#include "triplex_change_point.h"
#include "memory_diagnostic.h"
#include "multirate_memory.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static unsigned short target=94;
static uint16_t read_reg(void *p){return *(uint16_t*)p;}
static void write_reg(void *p,uint16_t v){*(uint16_t*)p=v;}
static double data[10000][4];
int main(int argc,char **argv){
 if(argc!=3)return 1;FILE *f=fopen(argv[1],"r");unsigned n=0;
 while(n<10000&&fscanf(f,"%lf %lf %lf %lf",&data[n][0],&data[n][1],&data[n][2],&data[n][3])==4)n++;fclose(f);
 cp_config_t c={0};double v[18];f=fopen(argv[2],"r");for(unsigned i=0;i<18;i++)if(fscanf(f,"%lf",&v[i])!=1)return 2;fclose(f);
 for(unsigned i=0;i<2;i++)c.mu[i]=v[i];for(unsigned i=0;i<3;i++)c.chol[i]=v[2+i];for(unsigned k=0;k<2;k++){for(unsigned i=0;i<2;i++)c.slope_mu[k][i]=v[5+5*k+i];for(unsigned i=0;i<3;i++)c.slope_chol[k][i]=v[7+5*k+i];}c.threshold=v[15];c.gamma=v[16];c.combination=(unsigned)v[17];
 f=fopen(getenv("CP_CDF"),"rb");if(!f)return 3;for(unsigned j=0;j<3;j++){if(fread(&c.cdf_n[j],4,1,f)!=1)return 4;double *x=malloc(c.cdf_n[j]*sizeof(double));if(!x||fread(x,sizeof(double),c.cdf_n[j],f)!=c.cdf_n[j])return 5;c.cdf[j]=x;}fclose(f);
 volatile double sink=0;
 for(unsigned rep=0;rep<7;rep++)for(unsigned m=0;m<4;m++){
  unsigned mode=rep%2?3-m:m;clock_t start=clock();unsigned probes=0;
  for(unsigned repeat=0;repeat<100;repeat++){
   cp_state_t s={0};memory_diagnostic_t mem={0};
   for(unsigned i=0;i<n;i++){
    if(i&&data[i][0]==0){probes+=mem.checks;mem=(memory_diagnostic_t){0};s=(cp_state_t){0};}
    unsigned now=(unsigned)data[i][0];if(mode>=2)mr_memory_step(&mem,now,250,read_reg,write_reg,&target);else memory_diagnostic_step(&mem,now,read_reg,write_reg,&target);
    if(mode&1){cp_input_t u={now,data[i][1],data[i][2],data[i][3]!=0};triplex_cp_step(&s,&c,&u);sink+=s.rarity+s.mass;}
   }probes+=mem.checks;
  }
  printf("%u,%u,%.17g,%u,%zu,%zu,%zu\n",rep,mode,((double)(clock()-start)/CLOCKS_PER_SEC)/(100*n),probes,sizeof(cp_state_t),sizeof(cp_config_t),sizeof(memory_diagnostic_t));
 }return sink<0;
}
'''
def main():
 d.verify();cases=[]
 for row,a in d.dataset('TRAIN'):
  if row['origin']=='NORMAL':cases.append(a['input'][:,:4])
  if len(cases)==8:break
 np.savetxt(B/'bench_inputs.txt',np.concatenate(cases));(B/'bench_params.txt').write_text(' '.join(map(str,p.vector(json.loads((B/'selected_cp.json').read_text())))));(B/'bench.c').write_text(SOURCE)
 subprocess.run(['gcc','-std=c11','-O2','-Iinclude',str(B/'bench.c'),'src/v7_3/triplex_change_point.c','src/memory_diagnostic.c','src/v7_3/multirate_memory.c','-lm','-o',str(B/'bench')],check=True)
 result=subprocess.check_output([str(B/'bench'),str(B/'bench_inputs.txt'),str(B/'bench_params.txt')],text=True,env=dict(d.os.environ,CP_CDF=str(B/'cdf.bin')));(B/'bench.csv').write_text(result);a=np.loadtxt(B/'bench.csv',delimiter=',');times={m:float(np.median(a[a[:,1]==m,2])) for m in range(4)}
 rr=dict(seconds_per_update=times,cp_delta=times[1]-times[0],memory_delta=times[2]-times[0],combined_delta=times[3]-times[0],cp_state_bytes=int(a[0,4]),cp_config_bytes=int(a[0,5]),memory_state_bytes=int(a[0,6]),timing_repetitions=7,streams=8,repeats_per_timing=100)
 rr['host_platform']=platform.platform();rr['compiler']=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0];rr['cdf_readonly_bytes']=(B/'cdf.bin').stat().st_size
 d.dump(B/'overhead.json',rr);(O/'overhead.md').write_text('# Diagnostic-kernel host overhead\n\n'+json.dumps(rr,indent=2)+'\n\nH1:50 two-dimensional cumulative additions and squared norms/divisions (~300 floating operations),48 onset comparisons. H2:reuses first12 interval scores, scans534 fully populated recent intervals (comparisons and indexing); no recomputed interval sums. H3:70 weighted two-dimensional terms, two slope fits and two triangular solves (~300 floating operations). Empirical tails:three binary searches,≤ceil(log2(N+1)) comparisons each; combination/mapping includes logs, expm1 and fixed Cauchy terms. Finite recent interval history is not an alarm latch. CDF immutable storage is separate from bounded mutable rolling state. No runtime covariance fitting or inverse. Seven order-balanced host timings, not embedded WCET; excludes DS/simulation/CSV. Baseline memory121probes/120s;250mscandidate481probes, seven operations/probe, +2520operations. Candidate reuses existing memory state. Atomic save/test/restore; no actuation.\n');print(rr,flush=True)
if __name__=='__main__':main()
