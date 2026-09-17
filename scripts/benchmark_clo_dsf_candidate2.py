#!/usr/bin/env python3
"""Host wall-time comparison, explicitly not embedded WCET."""
import json,platform,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/cross_layer_safety_v7_1_dev'
def run():
 with tempfile.TemporaryDirectory(prefix='candidate2-overhead-') as temp:
  t=Path(temp);p=t/'sizes.c';p.write_text('#include "clo_dsf_candidate2.h"\n#include <stdio.h>\nint main(void){printf("%zu %zu %zu %zu %zu %zu\\n",sizeof(c2_state_t),sizeof(clo_dsf_t),sizeof(ds_mass_t),sizeof(clo_evidence_t),sizeof(c2_output_t),sizeof(c2_config_t));}\n')
  subprocess.run(['gcc','-std=c11','-Iinclude',str(p),'-o',str(t/'sizes')],cwd=ROOT,check=True);sizes=[int(s) for s in subprocess.check_output([str(t/'sizes')],text=True).split()]
  modes=['legacy','candidate1','candidate2_disabled','candidate2'];samples={m:[] for m in modes}
  for repeat in range(33):
   for mode in modes[repeat%4:]+modes[:repeat%4]:
    exe={'legacy':'virtual_ecu','candidate1':'virtual_ecu_v7','candidate2_disabled':'virtual_ecu_v7_1','candidate2':'virtual_ecu_v7_1'}[mode];cmd=[str(ROOT/exe),str(t/'runtime.csv'),'baseline','--detector','builtin_ecu']
    if mode=='candidate1':cmd+=['--clo-config',str(ROOT/'results/cross_layer_safety_v7_dev/clo_dsf_candidate.cfg'),'--clo-evidence','/dev/null']
    if mode=='candidate2':cmd+=['--c2-config',str(OUT/'selected_config.cfg'),'--c2-evidence','/dev/null']
    start=time.perf_counter_ns();subprocess.run(cmd,cwd=ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);elapsed=(time.perf_counter_ns()-start)/1e9
    if repeat>=3:samples[mode].append(elapsed)
  lines=subprocess.check_output(['size','virtual_ecu','virtual_ecu_v7','virtual_ecu_v7_1'],cwd=ROOT,text=True).splitlines();binary={key:dict(zip(['text','data','bss'],map(int,line.split()[:3]))) for key,line in zip(['legacy','candidate1','candidate2'],lines[1:])};med={m:statistics.median(v) for m,v in samples.items()}
  result=dict(label='Host wall-time simulation overhead; NOT embedded WCET',host=platform.platform(),compiler=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],method='30 interleaved samples after three warmup cycles; 1201 scheduler samples; identical raw CSV logging; runtime evidence formatted to /dev/null; no comparison flag; no reference simulation',candidate2_state_bytes=sizes[0],candidate1_state_bytes=sizes[1],mass_bytes=sizes[2],two_frame_bytes=2*sizes[2],evidence_bytes=sizes[3],candidate2_output_bytes=sizes[4],candidate2_config_bytes=sizes[5],stack_and_stdio_excluded=True,binary_sections=binary,binary_scope='Executable includes dormant study banks and adapter; not deployable detector memory',median_seconds=med,raw_samples_seconds=samples,candidate2_over_legacy_percent=100*(med['candidate2']/med['legacy']-1),candidate2_over_candidate1_percent=100*(med['candidate2']/med['candidate1']-1))
  result['binary_delta_vs_legacy']={k:binary['candidate2'][k]-binary['legacy'][k] for k in ['text','data','bss']};result['binary_delta_vs_candidate1']={k:binary['candidate2'][k]-binary['candidate1'][k] for k in ['text','data','bss']}
  (OUT/'candidate2_overhead.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='raw_samples_seconds'},indent=2))
if __name__=='__main__':run()
