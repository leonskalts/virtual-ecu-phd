#!/usr/bin/env python3
"""Reproducible host simulation measurement; never an embedded WCET estimate."""
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/cross_layer_safety_v7_dev'

def run():
    with tempfile.TemporaryDirectory(prefix='clo-overhead-') as temp:
        temp=Path(temp)
        source=temp/'sizes.c'
        source.write_text('#include "clo_dsf.h"\n#include <stdio.h>\nint main(void){printf("%zu %zu %zu %zu\\n",sizeof(clo_dsf_t),sizeof(ds_mass_t),sizeof(clo_evidence_t),sizeof(clo_output_t));}\n')
        subprocess.run(['gcc','-std=c11','-Iinclude',str(source),'-o',str(temp/'sizes')],cwd=ROOT,check=True)
        sizes=[int(x) for x in subprocess.check_output([str(temp/'sizes')],text=True).split()]
        measurements={k:[] for k in ['legacy','adapter_disabled','candidate_shadow','candidate_primary']}
        for repeat in range(33):
            order=list(measurements)
            order=order[repeat%4:]+order[:repeat%4]
            for mode in order:
                exe='virtual_ecu' if mode=='legacy' else 'virtual_ecu_v7'
                cmd=[str(ROOT/exe),str(temp/'runtime.csv'),'baseline','--detector','clo_dsf' if mode=='candidate_primary' else 'builtin_ecu']
                if mode.startswith('candidate_'):
                    cmd+=['--clo-config',str(OUT/'selected_config.cfg'),'--clo-evidence','/dev/null']
                start=time.perf_counter_ns()
                subprocess.run(cmd,cwd=ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                seconds=(time.perf_counter_ns()-start)/1e9
                if repeat>=3:measurements[mode].append(seconds)
        size_lines=subprocess.check_output(['size','virtual_ecu','virtual_ecu_v7'],cwd=ROOT,text=True).splitlines()
        baseline=[int(v) for v in size_lines[1].split()[:3]]
        current=[int(v) for v in size_lines[2].split()[:3]]
        medians={k:statistics.median(v) for k,v in measurements.items()}
        result={'label':'host-evaluated simulation overhead','embedded_WCET_claim':'NONE',
                'host':platform.platform(),'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],
                'method':'30 interleaved samples per mode after 3 warmup cycles; 1201 scheduler steps; same raw CSV I/O; candidate sidecar formatted to /dev/null; no comparison bank; no reference simulation',
                'persistent_detector_state_bytes':sizes[0],'mass_function_state_bytes':sizes[1],'evidence_state_bytes':sizes[2],
                'output_state_bytes':sizes[3],'config_bytes_excluded':True,'stack_and_stdio_buffers_excluded':True,
                'binary_text_delta':current[0]-baseline[0],'binary_data_delta':current[1]-baseline[1],'binary_bss_delta':current[2]-baseline[2],
                'binary_scope':'v7 executable includes development comparison bank and CLI/evaluation adapter, not just one deployable detector',
                'median_seconds':medians,'raw_samples_seconds':measurements,
                'candidate_shadow_over_legacy_percent':100*(medians['candidate_shadow']/medians['legacy']-1),
                'candidate_primary_over_legacy_percent':100*(medians['candidate_primary']/medians['legacy']-1)}
        (OUT/'clo_dsf_overhead.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='raw_samples_seconds'},indent=2))
if __name__=='__main__':run()
