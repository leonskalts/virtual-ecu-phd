#!/usr/bin/env python3
"""Build inside v7 and compare ALL finite executions with unchanged C components."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import reference_oracle as m
HERE=m.HERE; ROOT=HERE.parents[1]
SOURCES=['control','sensors','actuators','fault_injection','cross_layer_fault','sensor_delivery',
         'runtime_observation','runtime_timing_observation','cross_layer_config','sensor_trace','actuator_trace','calibration_trace']

def run():
    env=dict(os.environ,TMPDIR=str(HERE))
    command=['gcc','-std=c11','-O0','-Wall','-Wextra','-Werror','-ffp-contract=off','-fexcess-precision=standard',
             '-ffunction-sections','-fdata-sections','-Iinclude',str(HERE/'component_probe.c')]
    command += ['src/'+s+'.c' for s in SOURCES]+['-Wl,--gc-sections','-o',str(HERE/'component_probe')]
    p=subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True)
    (HERE/'build.log').write_text(p.stdout+p.stderr)
    report={'command':command,'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],
            'build_returncode':p.returncode,'scope':'unchanged C component execution, not a full scheduler/closed-loop run',
            'tolerance':0,'comparison':'binary32 bits and exact integer/boolean fields','discrepancies':[],'rows_compared':0,'executions_compared':0}
    if p.returncode:
        m.write_json('ecu_comparison.json',report); raise RuntimeError(p.stderr)
    raw=[]
    for context,temp in m.CONTEXTS.items():
        for r in m.realizations():
            cmd=[str(HERE/'component_probe'),r['kind'],str(r['start']),str(r['duration']),str(r['parameter']),str(r['aux']),str(temp)]
            run=subprocess.run(cmd,cwd=HERE,env=env,text=True,capture_output=True,check=True)
            lines=list(csv.reader(run.stdout.splitlines()))
            expected=m.execute(r,context)['observations']; actual=[]
            fields=('time_ms',)+m.FULL
            for values in lines:
                row={}
                for field,value in zip(fields,values):
                    row[field]=value if field in ('coolant_measured_c','pump_command','pump_actual','control_target_c','source_c') else int(value)
                    if field in ('sample_freshness_ok','target_shadow_valid','source_valid'): row[field]=bool(row[field])
                actual.append(row)
            if actual!=expected: report['discrepancies'].append({'context':context,'realization':r,'expected':expected,'actual':actual})
            raw.append({'context':context,'realization_id':r['id'],'command':cmd,'observations':actual})
            report['rows_compared']+=len(actual);report['executions_compared']+=1
    report['source_sha256']={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in ['src/'+s+'.c' for s in SOURCES]}
    report['binary_sha256']=hashlib.sha256((HERE/'component_probe').read_bytes()).hexdigest()
    report['status']='PASS' if not report['discrepancies'] else 'FAIL'
    m.write_json('actual_component_observations.json',raw);m.write_json('ecu_comparison.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('command','source_sha256','discrepancies')},indent=2))
    if report['discrepancies']: raise AssertionError('Model/C discrepancy; see report')

if __name__=='__main__':run()
