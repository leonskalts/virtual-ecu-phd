#!/usr/bin/env python3
"""Paired interleaved host wall-time; never embedded WCET."""
import csv,json,platform,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/cross_layer_safety_v7_2_confirmation'
def percentile(v,p):
 v=sorted(v);pos=(len(v)-1)*p;i=int(pos);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(pos-i)
def run():
 assert json.loads((OUT/'benchmark/equivalence.json').read_text())['status']=='PASS'
 modes=['legacy','candidate1','candidate2','final_reference','final_optimized'];samples=[]
 with tempfile.TemporaryDirectory(prefix='clo-final-benchmark-') as t:
  t=Path(t);sizes=t/'sizes.c';sizes.write_text('#include "clo_dsf_final.h"\n#include <stdio.h>\nint main(void){printf("%zu %zu %zu %zu %zu %zu\\n",sizeof(clo_final_t),sizeof(clo_dsf_t),sizeof(c2_state_t),sizeof(ds_mass_t),sizeof(clo_evidence_t),sizeof(clo_final_config_t));}\n')
  subprocess.run(['gcc','-std=c11','-Iinclude',str(sizes),'-o',str(t/'sizes')],cwd=ROOT,check=True);sizes=list(map(int,subprocess.check_output([str(t/'sizes')],text=True).split()))
  for scenario,args in [('benign',['baseline']),('timing',['baseline','--cross-layer-fault','task_delay','--fault-start-ms','30500','--fault-duration-ms','4500','--task-delay-ms','600','--fault-behavior','transient'])]:
   for repeat in range(34):
    order=modes[repeat%5:]+modes[:repeat%5]
    for mode in order:
     exe={'legacy':'virtual_ecu','candidate1':'virtual_ecu_v7','candidate2':'virtual_ecu_v7_1','final_reference':'virtual_ecu_v7_2_reference','final_optimized':'virtual_ecu_v7_2_optimized'}[mode];cmd=[str(ROOT/exe),str(t/'runtime.csv'),*args,'--detector','builtin_ecu','--detector-action','observe_only']
     if mode=='candidate1':cmd+=['--clo-config',str(ROOT/'results/cross_layer_safety_v7_dev/clo_dsf_candidate.cfg'),'--clo-evidence','/dev/null']
     if mode=='candidate2':cmd+=['--c2-config',str(ROOT/'results/cross_layer_safety_v7_1_dev/selected_config.cfg'),'--c2-evidence','/dev/null']
     if mode.startswith('final_'):cmd+=['--final-config',str(OUT/'final_reference.cfg'),'--final-evidence','/dev/null']
     start=time.perf_counter_ns();subprocess.run(cmd,cwd=ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);seconds=(time.perf_counter_ns()-start)/1e9
     if repeat>=3:samples.append(dict(scenario=scenario,repeat=repeat-3,mode=mode,seconds=seconds))
  summary=[]
  for scenario in ['benign','timing']:
   med={m:statistics.median(r['seconds'] for r in samples if r['scenario']==scenario and r['mode']==m) for m in modes}
   for mode in modes:
    values=[r['seconds'] for r in samples if r['scenario']==scenario and r['mode']==mode]
    summary.append(dict(scenario=scenario,mode=mode,n=len(values),median_seconds=med[mode],mean_seconds=statistics.mean(values),stddev_seconds=statistics.stdev(values),p95_seconds=percentile(values,.95),overhead_vs_legacy_percent=100*(med[mode]/med['legacy']-1),change_vs_final_reference_percent=100*(med[mode]/med['final_reference']-1)))
  for name,rows in [('host_samples.csv',samples),('host_summary.csv',summary)]:
   with (OUT/'benchmark'/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  names=['virtual_ecu','virtual_ecu_v7','virtual_ecu_v7_1','virtual_ecu_v7_2_reference','virtual_ecu_v7_2_optimized'];lines=subprocess.check_output(['size',*names],cwd=ROOT,text=True).splitlines()[1:];sections={mode:dict(zip(['text','data','bss'],map(int,line.split()[:3]))) for mode,line in zip(modes,lines)}
  deltas={mode:{key:sections[mode][key]-sections['legacy'][key] for key in ['text','data','bss']} for mode in modes}
  record=dict(label='Host simulation runtime overhead',embedded_WCET_claim='NONE',host=platform.platform(),compiler=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],method='31 paired/interleaved measured repetitions per mode and scenario after three warmup cycles; same physics/raw logging; each detector sidecar formatted to /dev/null; no comparison banks executed, observation replay logging off. Legacy no sidecar. Candidate 1/2 historical formatting retained, final 17-digit formatting; differences include instrumentation and process cost.',persistent_state_bytes=dict(final_reference=sizes[0],final_optimized=sizes[0],candidate1=sizes[1],candidate2=sizes[2]),detection_mass_bytes=sizes[3],localization_mass_bytes=sizes[3],evidence_bytes=sizes[4],config_bytes=sizes[5],stack_and_stdio_excluded=True,binary_sections=sections,binary_delta_vs_legacy=deltas,binary_scope='Research executables retain dormant comparison state and reference code; not isolated deployment BSS',summary=summary)
  (OUT/'benchmark/overhead.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='summary'},indent=2))
if __name__=='__main__':run()
