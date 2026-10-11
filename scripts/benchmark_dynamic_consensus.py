#!/usr/bin/env python3
"""Native bounded-bank kernel host timings, not WCET."""
import json,subprocess,platform
import run_dynamic_consensus as d
import select_dynamic_consensus as p
import numpy as np
B=d.B;O=d.O
SOURCE=r'''
#include "dynamic_consensus.h"
#include "memory_diagnostic.h"
#include "multirate_memory.h"
#include "triplex_consistency.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static uint16_t target=94;
static uint16_t read_reg(void *p){return *(uint16_t*)p;}
static void write_reg(void *p,uint16_t v){*(uint16_t*)p=v;}
static double data[10000][21];
static bool phases[100];
static void probe(memory_diagnostic_t *s,unsigned now){
 if(now%100||!phases[(now/100)%100]||(s->valid&&now<=s->checked_ms))return;
 uint16_t saved=read_reg(&target);write_reg(&target,0);bool fail=read_reg(&target)!=0;
 write_reg(&target,UINT16_MAX);fail=(read_reg(&target)!=UINT16_MAX)||fail;write_reg(&target,saved);fail=(read_reg(&target)!=saved)||fail;
 s->checked_ms=now;s->checks++;s->operations+=7;s->valid=true;s->failed=fail;
}
int main(int argc,char **argv){
 if(argc!=3)return 1;FILE *f=fopen(argv[1],"r");unsigned n=0;
 while(n<10000){unsigned j=0;for(;j<21;j++)if(fscanf(f,"%lf",&data[n][j])!=1)break;if(j!=21)break;n++;}fclose(f);
 double v[17];f=fopen(argv[2],"r");for(unsigned i=0;i<17;i++)if(fscanf(f,"%lf",&v[i])!=1)return 2;fclose(f);
 dc_config_t c={0};for(unsigned j=0;j<3;j++){c.offset[j]=v[j];c.variance[j]=v[3+j];}c.process_variance=v[6];c.lambda=v[7];c.threshold=v[8];c.alpha=v[9];c.healthy_margin=v[10];c.consistency_bound=v[11];c.common_bound=v[12];c.origin_margin=v[13];c.robust=(unsigned)v[14];
 for(unsigned i=0;i<10;i++)phases[11*i]=true;
 for(unsigned k=10;k<40;k++){unsigned best=0,begin=0;for(unsigned i=0;i<100;i++)if(phases[i]){unsigned gap=1;while(!phases[(i+gap)%100])gap++;if(gap>best){best=gap;begin=i;}}phases[(begin+best/2)%100]=true;}
 volatile double sink=0;
 for(unsigned rep=0;rep<7;rep++)for(unsigned m=0;m<4;m++){
  unsigned mode=rep%2?3-m:m;clock_t begin=clock();unsigned probes=0;
  for(unsigned repeat=0;repeat<100;repeat++){
   dc_state_t s={0};memory_diagnostic_t mem={0};
   for(unsigned i=0;i<n;i++){
    double *a=data[i];if(i&&a[0]==0){probes+=mem.checks;mem=(memory_diagnostic_t){0};s=(dc_state_t){0};}
    if(mode>=2){if((unsigned)v[16]==2)probe(&mem,(unsigned)a[0]);else mr_memory_step(&mem,(unsigned)a[0],250,read_reg,write_reg,&target);}else memory_diagnostic_step(&mem,(unsigned)a[0],read_reg,write_reg,&target);
    if(mode&1){dc_input_t u={.ms=(unsigned)a[0],.y={a[13],a[14],a[15]},.context={a[16],a[17],a[18],a[19]},.qualified=a[3]!=0};dynamic_consensus_step(&s,&c,&u);sink+=s.D+s.mass;}
   }probes+=mem.checks;
  }
  printf("%u,%u,%.17g,%u,%zu,%zu,%zu,%zu,%zu\n",rep,mode,((double)(clock()-begin)/CLOCKS_PER_SEC)/(100*n),probes,sizeof(dc_state_t),sizeof(dc_config_t),sizeof(memory_diagnostic_t),sizeof(clo_revised_t),sizeof(triplex_consistency_t));
 }return !isfinite(sink);
}
'''.replace('#include <time.h>','#include <time.h>\n#include <math.h>')
def main():
 d.verify();cases=[]
 for row,a in d.dataset('TRAIN'):
  if row['origin']=='NORMAL':cases.append(a['input'])
  if len(cases)==8:break
 np.savetxt(B/'bench_inputs.txt',np.concatenate(cases));(B/'bench_params.txt').write_text(' '.join(map(str,p.vector(json.loads((B/'selected.json').read_text())))));(B/'bench.c').write_text(SOURCE)
 subprocess.run(['gcc','-std=c11','-O2','-Iinclude',str(B/'bench.c'),'src/v7_3/dynamic_consensus.c','src/memory_diagnostic.c','src/v7_3/multirate_memory.c','-lm','-o',str(B/'bench')],check=True)
 text=subprocess.check_output([str(B/'bench'),str(B/'bench_inputs.txt'),str(B/'bench_params.txt')],text=True);a=np.array([[float(x) for x in line.split(',')] for line in text.splitlines()]);times={m:float(np.median(a[a[:,1]==m,2])) for m in range(4)}
 result=dict(seconds_per_update=times,dynamic_delta=times[1]-times[0],memory_delta=times[2]-times[0],combined_delta=times[3]-times[0],dynamic_state_bytes=int(a[0,4]),config_bytes=int(a[0,5]),memory_bytes=int(a[0,6]),core_bytes=int(a[0,7]),triplex_bytes=int(a[0,8]),baseline_state_bytes=int(a[0,6]+a[0,7]+a[0,8]),combined_state_bytes=int(a[0,4]+a[0,6]+a[0,7]+a[0,8]),M2_phase_storage_bytes=101,integration_scalar_bytes=24,total_persistent_including_integration_bytes=int(a[0,4]+a[0,6]+a[0,7]+a[0,8])+125,filters=5,state_dimension=2,host=platform.platform(),compiler=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],repetitions=7,streams=8,repeats=100)
 d.dump(B/'overhead.json',result);(O/'overhead.md').write_text('# Host overhead\n\n'+json.dumps(result,indent=2)+'\n\nFive2D predict/update filters; each uses three scalar measurement likelihood contributions, one rank-one determinant/solve and one healthy-set scalar update. No dense matrix inverse, dynamic allocation or temporal history arrays. Per update:15 residual/variance contributions,5 two-state predictions/covariance predictions,5 scalar posterior updates,15 variance logs and5 log1p; four fault exp terms and one logsumexp. Robust choice adds up to10 bounded healthy innovation weights/square roots. qhealthy/mass use two exponentials. Three symmetric covariance scalars/filter. Constant-velocity scalarized operations, not a physical-temperature predictor. M0 121probes/120s; M1/M2 481,7 operations/probe,+2520operations. M2 adds100boolean phase table plus one initialization flag and first-call deterministic construction, excluded from steady per-update comparison only when initialization amortized. Host timings include callback tests/state updates, exclude DS/simulation/CSV; no embedded WCET claim.\n');print(result,flush=True)
if __name__=='__main__':main()
