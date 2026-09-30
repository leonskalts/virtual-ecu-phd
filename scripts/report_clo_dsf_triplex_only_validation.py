#!/usr/bin/env python3
"""Post-completion accounting only; no detector inputs or selection changes."""
import json,math
from pathlib import Path
import report_clo_dsf_triplex as q
B=Path('/tmp/clo-triplex-only-validation');O=q.O;h=q.h

def main():
 assert (B/'VALIDATION_complete').exists() and (B/'integrity_passed').exists()
 rows=h.records(B/'VALIDATION_rows.csv')
 rows += [r for r in h.records(Path('/tmp/clo-triplex-latch/BENIGN_VALIDATION_rows.csv')) if r['method'] in ['A0','A1']]
 assert len(rows)==1200
 summary=[];sub=[];pairs=[]
 for m in ['A0','A1']:
  for space in ['ORIGINAL','EXPANDED']:
   rr=[r for r in rows if r['method']==m and (space=='EXPANDED' or r['original_space'])]
   for origin in ['ALL',*h.prior.ORIGINS]:
    ss=[r for r in rr if origin=='ALL' or r['origin']==origin]
    summary.append(dict(method=m,space=space,origin=origin,**q.stats(ss)))
   for group,fn in q.FILTERS.items():
    sub.append(dict(method=m,space=space,group=group,**q.stats([r for r in rr if fn(r)])))
 for space in ['ORIGINAL','EXPANDED']:
  a={r['run_id']:r for r in rows if r['method']=='A0' and r['injected'] and (space=='EXPANDED' or r['original_space'])}
  b={r['run_id']:r for r in rows if r['method']=='A1' and r['run_id'] in a}
  p=dict(space=space,both=0,A0_only=0,A1_only=0,neither=0,common_mode=0,weak_steps=0,pulses=0,memory=0,actuator=0,other=0)
  for k,x in a.items():
   y=b[k];key='both' if x['detected'] and y['detected'] else 'A0_only' if x['detected'] else 'A1_only' if y['detected'] else 'neither';p[key]+=1
   if key=='A1_only':
    family='common_mode' if y['domain']=='AB' else 'weak_steps' if y['kind']=='step' else 'pulses' if y['kind']=='pulse' else 'memory' if y['origin']=='MEMORY' else 'actuator' if y['origin']=='ACTUATOR' else 'other';p[family]+=1
  n=p['A0_only']+p['A1_only'];p['mcnemar_exact_p']=min(1,2*sum(math.comb(n,j) for j in range(min(p['A0_only'],p['A1_only'])+1))/2**n) if n else 1
  pairs.append(p)
 def get(m,origin='ALL',space='ORIGINAL'):return next(r for r in summary if r['method']==m and r['space']==space and r['origin']==origin)
 a=get('A0');b=get('A1');e=get('A1',space='EXPANDED')
 ab=next(r for r in sub if r['method']=='A1' and r['space']=='ORIGINAL' and r['group']=='AB_common')
 checks=dict(original_at_least91=b['coverage']>=.91,benign_at_most01=e['benign_false_alarm_rate']<=.01,zero_wrong=e['runtime_wrong_samples']==0,plant_at_least95=b['coverage_given_plant_manifestation']>=.95,AB_at_least90=ab['coverage']>=.90)
 lookup={r['run_id']:r for r in rows if r['method']=='A0'}
 for origin in ['TIMING','COMMUNICATION','MEMORY']:
  relevant=[r for r in rows if r['method']=='A1' and r['origin']==origin and (origin!='MEMORY' or r['effective_memory_corruption'])]
  checks[origin+'_no_paired_loss']=not any(lookup[r['run_id']]['detected'] and not r['detected'] for r in relevant)
 checks['retained']=all(checks.values())
 h.write(O/'triplex_only_summary.csv',summary);h.write(O/'triplex_only_subgroups.csv',sub);h.write(O/'triplex_only_paired.csv',pairs)
 (O/'triplex_only_retention.json').write_text(json.dumps(checks,indent=2))
 # Compact case sufficient statistics, no raw trajectories.
 h.write(O/'triplex_only_cases.csv',[{k:r[k] for k in ['run_id','method','origin','domain','kind','original_space','detected','false_alarm','plant_manifestation','silent_plant','latency_ms','origin_at_alarm','wrong_localized_runtime_samples','effective_memory_corruption']} for r in rows])
 print(json.dumps({'summary':[r for r in summary if r['origin']=='ALL'],'paired':pairs,'checks':checks},indent=2))
if __name__=='__main__':main()
