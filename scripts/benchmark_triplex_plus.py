#!/usr/bin/env python3
"""Paired host timing on eight TRAIN benign cases only; no WCET claim."""
import os,json,time,subprocess,statistics,shutil
from pathlib import Path
import run_triplex_plus as r

def main():
 r.verify();assert (r.B/'VALIDATION_complete').exists() and not (r.O/'host_overhead.json').exists()
 sel=json.loads((r.O/'architecture_selection.json').read_text());arch=sel['selected_arch'];ss=json.loads((r.B/'specs.json').read_text())
 cases=[ss[150*f+120+f*4%30] for f in range(8)];assert all(s['partition']=='TRAIN' and s['origin']=='NORMAL' for s in cases)
 w=r.B/'host_work';w.mkdir();r.h.prepare_work(w,cases);exe=r.build(w)
 for key,name in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv')]:os.environ[key]=str(w/name)
 r.h.c.METHODS=['A0'];r.h.c.command=lambda s,w:r.t.command(s,w,exe);rows=[]
 for rep in range(3):
  for i,s in enumerate(cases):
   modes=[0,arch] if (rep+i)%2 else [arch,0];pair={}
   for mode in modes:
    os.environ['PLUS_HOST_MODE']=str(mode);begin=time.perf_counter();rr=r.h.c.execute(s,w,False);elapsed=time.perf_counter()-begin
    pair[mode]=rr[0];rows.append(dict(run_id=s['run_id'],repeat=rep,architecture=mode,seconds=elapsed,raw_sha256=rr[0]['raw_sha256'],runtime_trace_sha256=rr[0]['runtime_trace_sha256']))
    for name in ['triplex.csv','plus_meta.csv','benchmark.csv']:(w/name).unlink()
   assert pair[0]['raw_sha256']==pair[arch]['raw_sha256'] and pair[0]['runtime_trace_sha256']==pair[arch]['runtime_trace_sha256']
  print('HOST repeat',rep+1,flush=True)
 old=[x['seconds'] for x in rows if x['architecture']==0];new=[x['seconds'] for x in rows if x['architecture']==arch]
 ratios=[]
 for s in cases:
  for rep in range(3):
   a=next(x['seconds'] for x in rows if x['run_id']==s['run_id'] and x['repeat']==rep and x['architecture']==0)
   b=next(x['seconds'] for x in rows if x['run_id']==s['run_id'] and x['repeat']==rep and x['architecture']==arch);ratios.append(b/a-1)
 r.h.write(r.O/'host_timing.csv',rows)
 record=dict(physical_simulations=len(rows),unique_seen_train_cases=len(cases),baseline_median_seconds=statistics.median(old),candidate_median_seconds=statistics.median(new),paired_median_delta=statistics.median(ratios),physical_and_current_trace_equal=True,scope='host paired-observer experiment; includes extra candidate observer, export and Python collection; not deployed WCET')
 r.dump(r.O/'host_overhead.json',record);shutil.rmtree(w);r.verify();print(record,flush=True)

if __name__=='__main__':main()
