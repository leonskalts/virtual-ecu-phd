#!/usr/bin/env python3
"""Development selection and independent locked multi-rate validation report."""
import json,math,collections
from pathlib import Path
import run_clo_dsf_multirate as m
import report_clo_dsf_triplex as q
h=q.h;O=m.O;B=m.B

def summarize(part):
 rows=h.records(B/(part+'_rows.csv'));summary=[];sub=[]
 for method in sorted({r['method'] for r in rows}):
  rr=[r for r in rows if r['method']==method]
  for origin in ['ALL',*h.prior.ORIGINS]:summary.append(dict(partition=part,method=method,origin=origin,**q.stats([r for r in rr if origin=='ALL' or r['origin']==origin])))
  for group,fn in q.FILTERS.items():sub.append(dict(partition=part,method=method,group=group,**q.stats([r for r in rr if fn(r)])))
 h.write(O/('multirate_'+part.lower()+'_summary.csv'),summary);h.write(O/('multirate_'+part.lower()+'_subgroups.csv'),sub)
 return rows,summary,sub

def select():
 assert (B/'TRAIN_complete').exists() and (B/'CALIBRATION_complete').exists() and not (B/'VALIDATION_started').exists()
 reports={p:summarize(p) for p in ['TRAIN','CALIBRATION']};evidence={}
 for method in m.NAMES[2:]:
  evidence[method]={}
  for part,(rows,summary,_) in reports.items():
   a={r['run_id']:r for r in rows if r['method']=='A1'};rr=[r for r in rows if r['method']==method];base=next(r for r in summary if r['method']=='A1' and r['origin']=='ALL');s=next(r for r in summary if r['method']==method and r['origin']=='ALL')
   gains=sum(r['injected'] and r['detected'] and not a[r['run_id']]['detected'] for r in rr);lost=sum(r['injected'] and not r['detected'] and a[r['run_id']]['detected'] for r in rr)
   evidence[method][part]=dict(gains=gains,lost=lost,benign=s['benign_false_alarms'],wrong_runs=s['runtime_wrong_runs'],eligible=gains>0 and lost==0 and s['benign_false_alarms']<=base['benign_false_alarms'] and s['runtime_wrong_runs']<=base['runtime_wrong_runs'])
 def choose(slow,fast,slowrate,fastrate):
  eligible=lambda name:all(x['eligible'] for x in evidence[name].values())
  gain=lambda name:sum(x['gains'] for x in evidence[name].values())
  if eligible(slow) and (not eligible(fast) or gain(slow)>=.95*gain(fast)):return slowrate
  if eligible(fast):return fastrate
  return slowrate
 sensor=choose('S50','S25',50,25);memory=choose('M500','M250',500,250)
 files={str(p):m.sha(p) for p in [Path(m.__file__),Path(__file__),Path(__file__).with_name('benchmark_clo_dsf_multirate.py'),Path(h.c.CONFIG),O/'multirate_manifest.csv',O/'multirate_protocol.md',Path('include/multirate_triplex.h'),Path('include/multirate_memory.h'),Path('src/v7_3/multirate_triplex.c'),Path('src/v7_3/multirate_memory.c'),Path('tests/test_multirate_observability.py')]}
 # Also lock the retained scientific files and GUI from the original snapshot.
 initial=json.loads((B/'initial.json').read_text())
 for name,digest in initial.items():
  if 'multirate' not in name:assert m.sha(name)==digest;files[name]=digest
 selection=dict(sensor=sensor,memory=memory,evidence=evidence,files=files)
 (O/'multirate_selection.json').write_text(json.dumps(selection,indent=2));print(json.dumps(selection|{'files':'locked'},indent=2))

def validation():
 assert (B/'VALIDATION_complete').exists();selection=json.loads((O/'multirate_selection.json').read_text());assert all(m.sha(p)==v for p,v in selection['files'].items())
 rows,summary,sub=summarize('VALIDATION');a={r['run_id']:r for r in rows if r['method']=='A1'}
 pair=dict(both=0,A1_only=0,A4_only=0,neither=0,recovered_plant=0,memory=0,sensor=0,actuator=0,A_only=0,B_only=0,common_mode=0,weak_steps=0,pulses=0,other_sensor=0,effective_memory=0,dormant_memory=0,transient_memory=0,intermittent_memory=0,permanent_memory=0)
 for r in rows:
  if r['method']!='A4' or not r['injected']:continue
  x=a[r['run_id']];key='both' if x['detected'] and r['detected'] else 'A1_only' if x['detected'] else 'A4_only' if r['detected'] else 'neither';pair[key]+=1
  if key=='A4_only':
   pair['recovered_plant']+=r['plant_manifestation']==1
   if r['origin']=='SENSOR_CONTROL':
    pair['sensor']+=1;pair[{'A':'A_only','B':'B_only','AB':'common_mode'}[r['domain']]]+=1;pair['weak_steps' if r['kind']=='step' else 'pulses' if r['kind']=='pulse' else 'other_sensor']+=1
   if r['origin']=='MEMORY':pair['memory']+=1;pair['effective_memory' if r['effective_memory_corruption'] else 'dormant_memory']+=1;pair[r['behavior']+'_memory']+=1
   if r['origin']=='ACTUATOR':pair['actuator']+=1
 n=pair['A1_only']+pair['A4_only'];pair['mcnemar_exact_p']=min(1,2*sum(math.comb(n,j) for j in range(min(pair['A1_only'],pair['A4_only'])+1))/2**n) if n else 1
 h.write(O/'multirate_paired.csv',[pair])
 roots=[]
 for origin in ['SENSOR_CONTROL','MEMORY']:
  counts=collections.Counter(r['temporal_miss_cause'] for r in rows if r['method']=='A1' and r['origin']==origin and not r['detected']);roots.append(dict(origin=origin,**{k:counts[k] for k in ['A','B','C','D','E']}))
 h.write(O/'multirate_miss_causes.csv',roots)
 def overall(method):return next(s for s in summary if s['method']==method and s['origin']=='ALL')
 base=overall('A1');checks={}
 for method in ['A2','A3','A4']:
  s=overall(method);rr=[r for r in rows if r['method']==method];checks[method]=dict(overall94=s['coverage']>=.94,gain2pp=s['coverage']-base['coverage']>=.02,benign=s['benign_false_alarm_rate']<=.01,zero_wrong=s['runtime_wrong_runs']==0,plant98=s['coverage_given_plant_manifestation']>=.98)
  for label,fn in {'timing':lambda r:r['origin']=='TIMING','communication':lambda r:r['origin']=='COMMUNICATION','effective_memory':lambda r:r['origin']=='MEMORY' and r['effective_memory_corruption'],'AB':lambda r:r['domain']=='AB'}.items():checks[method][label+'_preserved']=not any(fn(r) and a[r['run_id']]['detected'] and not r['detected'] for r in rr)
  checks[method]['eligible']=all(checks[method].values())
 retained='TRIPLEX'
 if checks['A4']['eligible']:retained='BOTH'
 for method,name in [('A3','MEMORY-MULTIRATE'),('A2','SENSOR-MULTIRATE')]:
  if checks[method]['eligible'] and (not checks['A4']['eligible'] or overall(method)['detected']-base['detected']>=.95*(overall('A4')['detected']-base['detected'])):retained=name;break
 result=dict(retained=retained,checks=checks,paired=pair,roots=roots,overall=[s for s in summary if s['origin']=='ALL']);(O/'multirate_retention.json').write_text(json.dumps({'retained':retained,'checks':checks},indent=2));(B/'report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 h.write(O/'multirate_case_summary.csv',[{k:r[k] for k in ['run_id','method','origin','domain','kind','behavior','detected','false_alarm','effective_memory_corruption','plant_manifestation','silent_plant','latency_ms','origin_at_alarm','wrong_localized_runtime_samples','temporal_miss_cause','observations_in_fault','old_probes_in_fault']} for r in rows])
 overhead=[]
 for r in rows:
  if r['method']!='A4':continue
  sr=selection['sensor'];mr=selection['memory'];overhead.append(dict(run_id=r['run_id'],extra_sensor_acquisitions=r['extra_acquisitions'+str(sr)],extra_memory_probes=r['extra_probe_count'+str(mr)],extra_memory_operations=7*r['extra_probe_count'+str(mr)],old_probe_count=r['old_probe_count'],diagnostic_cpu_seconds=r['sensor_cpu'+str(sr)]+r['memory_cpu'+str(mr)],triplex_core_cpu_seconds=r['triplex_cpu'],host_ablation_seconds=r['host_run_seconds'],extra_provider_state_bytes=r['extra_state_bytes']))
 h.write(O/'multirate_overhead.csv',overhead)
if __name__=='__main__':
 if __import__('sys').argv[1]=='select':select()
 else:validation()
