#!/usr/bin/env python3
"""Report completed symmetry-audit validation, never feeds inference."""
import json,math
from pathlib import Path
import report_clo_dsf_triplex as q
B=Path('/tmp/clo-triplex-symmetry');O=q.O;h=q.h

def main():
 assert (B/'VALIDATION_complete').exists()
 rows=h.records(B/'VALIDATION_rows.csv');assert len(rows)==1200
 summary=[];sub=[]
 for m in ['A0','A1']:
  rr=[r for r in rows if r['method']==m]
  for origin in ['ALL',*h.prior.ORIGINS]:summary.append(dict(method=m,origin=origin,**q.stats([r for r in rr if origin=='ALL' or r['origin']==origin])))
  for group,fn in q.FILTERS.items():sub.append(dict(method=m,group=group,**q.stats([r for r in rr if fn(r)])))
 a={r['run_id']:r for r in rows if r['method']=='A0'}
 p=dict(both=0,A0_only=0,A1_only=0,neither=0,A_only=0,B_only=0,common_mode=0,memory=0,other=0)
 for r in rows:
  if r['method']!='A1' or not r['injected']:continue
  x=a[r['run_id']];key='both' if x['detected'] and r['detected'] else 'A0_only' if x['detected'] else 'A1_only' if r['detected'] else 'neither';p[key]+=1
  if key=='A1_only':p[{'A':'A_only','B':'B_only','AB':'common_mode'}.get(r['domain'],'memory' if r['origin']=='MEMORY' else 'other')]+=1
 n=p['A0_only']+p['A1_only'];p['mcnemar_exact_p']=min(1,2*sum(math.comb(n,j) for j in range(min(p['A0_only'],p['A1_only'])+1))/2**n) if n else 1
 b=next(r for r in summary if r['method']=='A1' and r['origin']=='ALL');ab=next(r for r in sub if r['method']=='A1' and r['group']=='AB_common')
 checks=dict(original_at_least91=b['coverage']>=.91,benign_at_most01=b['benign_false_alarm_rate']<=.01,zero_wrong=b['runtime_wrong_samples']==0,plant_at_least95=b['coverage_given_plant_manifestation']>=.95,AB_at_least90=ab['coverage']>=.90,no_unprincipled_correction=True)
 for origin in ['TIMING','COMMUNICATION','MEMORY']:
  rr=[r for r in rows if r['method']=='A1' and r['origin']==origin and (origin!='MEMORY' or r['effective_memory_corruption'])];checks[origin+'_preserved']=not any(a[r['run_id']]['detected'] and not r['detected'] for r in rr)
 checks['retained']=all(checks.values())
 h.write(O/'symmetry_validation_summary.csv',summary);h.write(O/'symmetry_subgroups.csv',sub);h.write(O/'symmetry_paired.csv',[p]);(O/'symmetry_retention.json').write_text(json.dumps(checks,indent=2))
 h.write(O/'symmetry_case_summary.csv',[{k:r[k] for k in ['run_id','method','origin','domain','kind','detected','false_alarm','effective_memory_corruption','plant_manifestation','silent_plant','latency_ms','origin_at_alarm','wrong_localized_runtime_samples','initially_excited','actuator_excited']} for r in rows])
 print(json.dumps({'overall':[r for r in summary if r['origin']=='ALL'],'paired':p,'checks':checks},indent=2))
if __name__=='__main__':main()
