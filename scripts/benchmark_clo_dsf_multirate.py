#!/usr/bin/env python3
"""Paired host timing on already-seen benign TRAIN cases, not rate selection."""
import os,json,time,statistics,shutil
from pathlib import Path
import run_clo_dsf_multirate as m
B=m.B;h=m.h

def main():
 selection=json.loads((m.O/'multirate_selection.json').read_text())
 ss=json.loads((B/'specs.json').read_text());samples=[s for s in ss if s['partition']=='TRAIN' and s['origin']=='NORMAL' and int(s['run_id'].split('_')[1])%150 in [120,130,141,147]][:8]
 w=B/'benchmark';w.mkdir();h.prepare_work(w,ss);exe=m.build(w);h.c.METHODS=['A0','A1']
 for key,name in [('TRIPLEX_LOG','triplex.csv'),('MR_LOG','mr.csv'),('MR_META','mr_meta.csv')]:os.environ[key]=str(w/name)
 os.environ['MR_VALIDATION']='1';os.environ['MR_BENCH']='1';h.c.command=lambda s,w:m.t.command(s,w,exe)
 rows=[]
 for s in samples:
  for repeat in range(3):
   pair={}
   for mode in (['baseline','both'] if repeat%2==0 else ['both','baseline']):
    os.environ['MR_SENSOR']=str(selection['sensor'] if mode=='both' else 0);os.environ['MR_MEMORY']=str(selection['memory'] if mode=='both' else 0)
    start=time.perf_counter();r=h.c.execute(s,w,False);elapsed=time.perf_counter()-start;pair[mode]=r
    rows.append(dict(run_id=s['run_id'],repeat=repeat,mode=mode,host_seconds=elapsed))
   # Includes physical plant/control logs and baseline evidence/score traces.
   for x,y in zip(pair['baseline'],pair['both']):assert x['raw_sha256']==y['raw_sha256'] and x['runtime_trace_sha256']==y['runtime_trace_sha256']
 h.write(m.O/'multirate_host_benchmark.csv',rows)
 med={mode:statistics.median(r['host_seconds'] for r in rows if r['mode']==mode) for mode in ['baseline','both']}
 result=dict(cases=len(samples),repeats=3,physical_and_baseline_trace_identical=True,median_host_seconds=med,relative_delta=med['both']/med['baseline']-1,scope='Retained baseline observers vs same plus A4; includes diagnostic CSV instrumentation and collector I/O; not embedded WCET')
 (m.O/'multirate_host_benchmark.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));shutil.rmtree(w)
if __name__=='__main__':main()
