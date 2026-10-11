#!/usr/bin/env python3
"""Post-hoc accounting only; never imported by benchmark inference."""
import sys,json,collections,math
from pathlib import Path
import run_comparative_benchmark as r
from virtual_ecu import comparative_backends as be
OUT=r.OUT;B=r.B

def stats(rows):
 s=r.summary(rows)
 if rows and rows[0]['method'].endswith('SVM'):
  for k in list(s):
   if any(x in k for x in ['localiz','unknown','runtime_']):s[k]=None
  s['localization_provided']=False
 else:s['localization_provided']=True
 s['plant_detected']=s['plant_manifestation_runs']-s['silent_plant']
 return s

FILTERS={
 **{o:lambda x,o=o:x['origin']==o for o in be.ORIGINS},
 'effective_memory':lambda x:x['origin']=='MEMORY' and x['effective_memory_corruption'],
 'dormant_memory':lambda x:x['origin']=='MEMORY' and x['initially_latent_stuck'] and not x['effective_memory_corruption'],
 'independent_slow_drift':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain'] in ['A','B'] and x['kind']=='ramp',
 'A_slow_drift':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain']=='A' and x['kind']=='ramp',
 'B_slow_drift':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain']=='B' and x['kind']=='ramp',
 'AB_common_mode':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain']=='AB',
 'weak_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step',
 'pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse',
 'excited_actuator':lambda x:x['origin']=='ACTUATOR' and x['initially_excited'],
 'initially_unexcited_actuator':lambda x:x['origin']=='ACTUATOR' and not x['initially_excited'],
 'unexcited_throughout_actuator':lambda x:x['origin']=='ACTUATOR' and not x['actuator_excited'],
 'legal_calibration':lambda x:x['origin']=='NORMAL' and x['workload']=='authorized_updates',
}

def percent(x):return '—' if x is None else f'{100*x:.2f}%'
def latency(s):return f"{s['latency_median_ms']/1000:.3g}/{s['latency_p95_ms']/1000:.3g} s" if s['latency_median_ms'] is not None else '—'

def pair(rows,a,b,endpoint):
 aa={x['run_id']:x for x in rows if x['method']==a and bool(x['injected'])==(endpoint=='fault')}
 bb={x['run_id']:x for x in rows if x['method']==b and bool(x['injected'])==(endpoint=='fault')};assert aa.keys()==bb.keys()
 key='detected' if endpoint=='fault' else 'false_alarm';counts=collections.Counter((aa[k][key],bb[k][key]) for k in aa)
 both,onlya,onlyb,neither=[counts[k] for k in [(1,1),(1,0),(0,1),(0,0)]]
 discord=onlya+onlyb
 # Two-sided exact McNemar = Binomial(n,1/2), stable integer calculation.
 p=min(1.,2*sum(math.comb(discord,k) for k in range(min(onlya,onlyb)+1))/2**discord) if discord else None
 jointly=[k for k in aa if aa[k][key] and bb[k][key]]
 diffs=sorted(aa[k]['latency_ms']-bb[k]['latency_ms'] for k in jointly) if endpoint=='fault' else []
 return dict(method_a=a,method_b=b,endpoint=endpoint,both=both,only_a=onlya,only_b=onlyb,neither=neither,discordant=discord,mcnemar_exact_p=p,mcnemar_scope='descriptive; no multiplicity adjustment',joint_detection_latency_a_faster=sum(x<0 for x in diffs),joint_detection_latency_b_faster=sum(x>0 for x in diffs),joint_detection_latency_equal=sum(x==0 for x in diffs))

def generate():
 r.verify();r.check_lock();assert (B/'UNSEEN_complete').exists()
 rows=json.loads((B/'UNSEEN_rows.json').read_text());methods=sorted({x['method'] for x in rows})
 sums=[dict(method=m,**stats([x for x in rows if x['method']==m])) for m in methods]
 sub=[dict(method=m,subgroup=g,**stats([x for x in rows if x['method']==m and filt(x)])) for m in methods for g,filt in FILTERS.items()]
 r.h.write(OUT/'overall_comparison.csv',sums);r.h.write(OUT/'subgroup_comparison.csv',sub)
 r.h.write(OUT/'plant_comparison.csv',[{k:s[k] for k in ['method','plant_manifestation_runs','plant_detected','coverage_given_plant_manifestation','silent_plant','pre_plant_alarms','same_plant_alarms','post_plant_alarms']} for s in sums])
 loc=[]
 for m in methods:
  for origin in ['ALL',*be.ORIGINS,'NORMAL']:
   ss=[x for x in rows if x['method']==m and (origin=='ALL' or x['origin']==origin)];s=stats(ss)
   loc.append(dict(method=m,origin=origin,**{k:v for k,v in s.items() if any(t in k for t in ['localiz','unknown','runtime_'])}))
 r.h.write(OUT/'localization_comparison.csv',loc)
 r.h.write(OUT/'confusion_summary.csv',[dict(method=m,origin=o,**{p:sum(x['alarm_'+p] for x in rows if x['method']==m and x['origin']==o) for p in [*be.ORIGINS,'UNKNOWN']}) for m in methods if not m.endswith('SVM') for o in [*be.ORIGINS,'NORMAL']])
 pairs=[pair(rows,'C2 TRIPLEX',m,end) for m in methods if m!='C2 TRIPLEX' for end in ['fault','benign']]
 pairs += [pair(rows,'C2 '+m,'C1 '+m,'fault') for m in ['OR','Weighted Sum','Plain DS','SVM']]
 r.h.write(OUT/'paired_statistics.csv',pairs)
 r.h.write(OUT/'common_observability_table.csv',[s for s in sums if s['method'].startswith('C1')]);r.h.write(OUT/'final_architecture_table.csv',[s for s in sums if s['method'].startswith('C2')])
 fields=['run_id','method','partition','origin','model','behavior','domain','kind','subgroup','injected','detected','false_alarm','first_alarm_ms','first_post_alarm_ms','pre_alarm_samples','latency_ms','plant_manifestation','propagation_plant_ms','silent_plant','effective_memory_corruption','initially_latent_stuck','initially_excited','actuator_excited','origin_at_alarm','first_localization_ms','first_origin','localized_correct','localized_wrong','unknown_at_alarm','alarm_samples','wrong_localized_runtime_samples',*[f'alarm_{o}' for o in [*be.ORIGINS,'UNKNOWN']],'raw_sha256','runtime_trace_sha256']
 r.h.write(OUT/'case_sufficient_statistics.csv',[{k:x.get(k) for k in fields} for x in rows])
 keys={x['run_id'] for x in rows if x['injected']};misses=[]
 for k in sorted(keys):
  rr=[x for x in rows if x['run_id']==k]
  if all(not x['detected'] for x in rr):
   x=rr[0];misses.append({k:x.get(k) for k in ['run_id','origin','model','behavior','domain','kind','effective_memory_corruption','initially_latent_stuck','initially_excited','actuator_excited','plant_manifestation']})
 r.h.write(OUT/'all_method_misses.csv',misses)
 table=['# Comparative unseen: frozen methods, one physical execution per case','',
 'C1 excludes Sensor C; C2 includes C-derived evidence. All methods share frozen temporal evidence preprocessing. SVM localization is not provided. CIs and paired tests are descriptive for grouped deterministic scenarios.','',
 '| Method | Supervised | Extra C | Detection | Wilson 95% | Plant detection | Benign FPR | Precision | Median/P95 | First localized accuracy (coverage) | Runtime localized accuracy | Wrong runs/samples | Runtime UNKNOWN |',
 '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
 for s in sums:
  loc='NOT PROVIDED' if not s['localization_provided'] else f"{percent(s['accuracy_when_localized'])} ({percent(s['localization_coverage'])})"
  wrong='—' if not s['localization_provided'] else f"{s['runtime_wrong_runs']}/{s['runtime_wrong_samples']}"
  table.append(f"| {s['method']} | {'yes' if s['method'].endswith('SVM') else 'no'} | {'yes' if s['method'].startswith('C2') else 'no'} | {s['detected']}/{s['faulty_runs']} ({percent(s['coverage'])}) | {100*s['ci_low']:.2f}–{100*s['ci_high']:.2f}% | {s['plant_detected']}/{s['plant_manifestation_runs']} | {s['benign_false_alarms']}/{s['benign_runs']} ({percent(s['benign_false_alarm_rate'])}) | {percent(s['precision'])} | {latency(s)} | {loc} | {percent(s['runtime_accuracy_among_localized'])} | {wrong} | {percent(s['runtime_unknown_rate'])} |")
 (OUT/'manuscript_table.md').write_text('\n'.join(table)+'\n')
 r.dump(B/'report.json',dict(overall=sums,subgroups=sub,paired=pairs,all_miss_count=len(misses),all_miss_classes=dict(collections.Counter(x['origin']+'/'+x['model'] for x in misses))))
 print('\n'.join(table),flush=True)

if __name__=='__main__':generate()
