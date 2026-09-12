"""Host simulation overhead and compiler/state sizes, never embedded WCET."""
import csv,json,statistics,subprocess,time
from pathlib import Path
from .cross_layer_safety import PROJECT_ROOT
from .cross_layer_analysis import write_table


def measure(output,repetitions=31):
 out=Path(output);directory=out/'validation/overhead';directory.mkdir(parents=True,exist_ok=True)
 source=directory/'sizes.c';binary=directory/'sizes'
 source.write_text('''#include <stdio.h>
#include "ecu_types.h"
int main(void){printf("monitor_state,%zu\\nobservation_state,%zu\\nrecorder_state,%zu\\ngraded_policy_state,%zu\\nscheduler_stress_state,%zu\\necu_state,%zu\\n",sizeof(timing_monitor_status_t),sizeof(runtime_timing_observation_t),sizeof(runtime_timing_recorder_t),sizeof(safety_policy_v5_state_t),sizeof(scheduler_stress_state_t),sizeof(ecu_state_t));}
''')
 subprocess.run(['gcc','-std=c11','-I'+str(PROJECT_ROOT/'include'),str(source),'-o',str(binary)],check=True)
 sizes=subprocess.check_output([str(binary)],text=True)
 rows=[{'metric':name,'value':int(value),'unit':'bytes','scope':'gcc Linux host ABI'} for name,value in csv.reader(sizes.splitlines())]
 rows+=[{'metric':'named_monitor_members','value':14,'unit':'members','scope':'6 bools, enum, 3 counters, 2 timestamps, history array, history count'},
        {'metric':'monitor_scalar_storage_slots','value':23,'unit':'slots','scope':'10 history entries counted individually'}]
 # V4's DISABLED mode still computes contract bookkeeping. Replace only the
 # monitor object in a separate measurement build to measure its actual cost.
 stub=directory/'monitor_omitted.c';stub_object=directory/'monitor_omitted.o';omitted=directory/'virtual_ecu_monitor_omitted'
 stub.write_text('''#include "timing_safety_monitor.h"
void timing_safety_monitor_init(timing_monitor_status_t *s){*s=(timing_monitor_status_t){.first_alarm_ms=-1,.first_violation_ms=-1};}
void timing_safety_monitor_step(timing_monitor_status_t *s,const runtime_timing_observation_t *o,timing_monitor_mode_t m,timing_evidence_t e){(void)s;(void)o;(void)m;(void)e;}
''')
 subprocess.run(['gcc','-std=c11','-O2','-I'+str(PROJECT_ROOT/'include'),'-c',str(stub),'-o',str(stub_object)],check=True)
 objects=[str(p) for p in sorted((PROJECT_ROOT/'src').glob('*.o')) if p.name!='timing_safety_monitor.o']
 subprocess.run(['gcc',*objects,str(stub_object),'-o',str(omitted)],check=True)
 samples=[]
 base=[str(PROJECT_ROOT/'virtual_ecu'),str(directory/'simulation.csv'),'baseline','--simulation-duration-ms','180000','--detector','hybrid_adaptive_kalman','--detector-action','observe_only']
 # Identical timing telemetry/schema, arguments and output bytes on the nominal
 # benchmark. Only monitor computation is removed; no holdout uses this build.
 nominal_bytes=None
 for i in range(repetitions+3):
  for mode in (['disabled','observe_only'] if i%2==0 else ['observe_only','disabled']):
   cmd=[str(omitted) if mode=='disabled' else base[0],*base[1:],'--timing-monitor','observe_only']
   start=time.perf_counter_ns();subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True);elapsed=time.perf_counter_ns()-start
   if i==0:
    blob=(directory/'simulation.csv').read_bytes()
    if nominal_bytes is None:nominal_bytes=blob
    else:assert nominal_bytes==blob,'Benchmark requires identical nominal output bytes'
   if i>=3:samples.append({'repetition':i-3,'mode':mode,'elapsed_ns':elapsed})
 medians={m:statistics.median(r['elapsed_ns'] for r in samples if r['mode']==m) for m in ['disabled','observe_only']}
 for mode,value in medians.items():rows.append({'metric':'host_runtime_'+mode,'value':value/1e6,'unit':'ms','n':repetitions,'scope':'host process + identical CSV I/O; disabled test build replaces monitor with no-op, telemetry retained'})
 rows.append({'metric':'host_median_relative_change','value':100*(medians['observe_only']/medians['disabled']-1),'unit':'percent','n':repetitions,'scope':'Median ratio; host noise can exceed monitor cost'})
 # Inspect relocatable code/data, not stripped/unstripped executable file-size artifacts.
 obj=directory/'timing_monitor.o';subprocess.run(['gcc','-std=c11','-O2','-I'+str(PROJECT_ROOT/'include'),'-c',str(PROJECT_ROOT/'src/timing_safety_monitor.c'),'-o',str(obj)],check=True)
 fields=subprocess.check_output(['size',str(obj)],text=True).splitlines()[1].split()
 rows.append({'metric':'timing_monitor_object_text','value':int(fields[0]),'unit':'bytes','scope':'gcc -O2 text section including compiler metadata; entire optional monitor object'})
 for name in ['src/timing_safety_monitor.c','src/scheduler_stress.c','src/safety_policy_v5.c']:
  rows.append({'metric':'source_lines_'+Path(name).stem,'value':len((PROJECT_ROOT/name).read_text().splitlines()),'unit':'lines','scope':'Source lines including comments/blanks; code size proxy'})
 baseline=Path('/tmp/vecu_v5_preflight/virtual_ecu_baseline')
 def size(p):return [int(x) for x in subprocess.check_output(['size',str(p)],text=True).splitlines()[1].split()[:3]]
 new=size(PROJECT_ROOT/'virtual_ecu');omitted_size=size(omitted)
 rows.append({'metric':'linked_monitor_text_delta','value':new[0]-omitted_size[0],'unit':'bytes','scope':'Production monitor versus no-op replacement in otherwise identical linked executable'})
 if baseline.exists():
  old=size(baseline)
  for name,a,b in zip(['text','data','bss'],old,new):rows.append({'metric':'v5_vs_v4_binary_'+name+'_delta','value':b-a,'unit':'bytes','scope':'Whole v5 extension, including workload scheduler/policy/logging; not monitor-only delta'})
 write_table(out/'monitor_overhead_summary.csv',rows);write_table(directory/'host_runtime_repetitions.csv',samples)
 (directory/'compiler.txt').write_text(subprocess.check_output(['gcc','--version'],text=True))
 return rows
