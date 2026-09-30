#!/usr/bin/env python3
"""Post-hoc expanded/original-space accounting, no inference dependencies."""
import sys,json,math,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_clo_dsf_triplex as t
h=t.h;B=t.B;O=t.OUT
FILTERS={
 'A_only':lambda r:r['domain']=='A','B_only':lambda r:r['domain']=='B','C_only':lambda r:r['domain']=='C',
 'AB_common':lambda r:r['domain']=='AB','AB_slow':lambda r:r['domain']=='AB' and r['kind']=='ramp','AB_steps':lambda r:r['domain']=='AB' and r['kind']=='step','AB_pulses':lambda r:r['domain']=='AB' and r['kind']=='pulse',
 'ABC_global':lambda r:r['domain']=='ABC','ABC_slow':lambda r:r['domain']=='ABC' and r['kind']=='ramp','AC_correlated':lambda r:r['domain']=='AC','BC_correlated':lambda r:r['domain']=='BC',
 'independent_slow':lambda r:r['domain'] in ['A','B','C'] and r['kind']=='ramp','weak_steps':lambda r:r['kind']=='step','pulses':lambda r:r['kind']=='pulse','stuck':lambda r:r['kind']=='stuck','C_acquisition':lambda r:r['kind']=='freeze',
 'excited_actuator':lambda r:r['origin']=='ACTUATOR' and r['initially_excited'],'initially_unexcited_actuator':lambda r:r['origin']=='ACTUATOR' and not r['initially_excited'],'unexcited_throughout':lambda r:r['origin']=='ACTUATOR' and not r['actuator_excited'],
 'effective_memory':lambda r:r['origin']=='MEMORY' and r['effective_memory_corruption'],'dormant_memory':lambda r:r['origin']=='MEMORY' and r['model']=='stuck_bit' and not r['effective_memory_corruption'],
 'S1_original_sensor':lambda r:r['origin']=='SENSOR_CONTROL' and r['original_space'],'S2_expanded_sensor':lambda r:r['origin']=='SENSOR_CONTROL'}
def stats(rr):
 a=h.aggregate(rr);lo,hi=h.wilson(a['detected'],a['faulty_runs']);rt=h.runtime_stats(rr)
 return {**a,'wilson95_low':lo,'wilson95_high':hi,**{'runtime_'+k:v for k,v in rt.items()},**{k:sum(r[k] for r in rr) for k in ['pattern_A_BC','pattern_B_AC','pattern_C_AB','pattern_all_disagree']}}
def report(parts):
 summary=[];sub=[];paired=[];account=[];allrows=[]
 for part in parts:
  rows=h.records(B/(part+'_rows.csv'));allrows+=rows
  for method in ['A0','A1']:
   rr=[r for r in rows if r['method']==method]
   for space in ['ORIGINAL','EXPANDED']:
    subset=[r for r in rr if space=='EXPANDED' or r['original_space']]
    for origin in ['ALL',*h.prior.ORIGINS]:
     ss=[r for r in subset if origin=='ALL' or r['origin']==origin];summary.append(dict(partition=part,method=method,space=space,origin=origin,**stats(ss)))
   for group,fn in FILTERS.items():sub.append(dict(partition=part,method=method,group=group,**stats([r for r in rr if fn(r)])))
  a0={r['run_id']:r for r in rows if r['method']=='A0'}
  for space in ['ORIGINAL','EXPANDED']:
   rr=[r for r in rows if r['method']=='A1' and (space=='EXPANDED' or r['original_space'])];p=dict(partition=part,space=space,both=0,A0_only=0,A1_only=0,neither=0,AB_additional=0,actuator_additional=0)
   for r in rr:
    if not r['injected']:continue
    a=a0[r['run_id']];key='both' if a['detected'] and r['detected'] else 'A0_only' if a['detected'] else 'A1_only' if r['detected'] else 'neither';p[key]+=1
    if key=='A1_only':p['AB_additional']+=r['domain']=='AB';p['actuator_additional']+=r['origin']=='ACTUATOR'
   n=p['A0_only']+p['A1_only'];k=min(p['A0_only'],p['A1_only']);p['mcnemar_exact_p']=min(1.,2*sum(math.comb(n,j) for j in range(k+1))/2**n) if n else 1.;paired.append(p)
  for r in rows:
   if r['injected'] and not r['detected']:
    account.append({k:r[k] for k in ['partition','run_id','method','original_space','origin','domain','kind','behavior','start_ms','duration_ms','magnitude','detected','plant_manifestation','silent_plant','miss_limit','first_positive_feature_ms','triplex_peak','triplex_qualified_samples','initially_excited','actuator_excited']})
  print(part,[(r['method'],r['space'],r['detected'],r['faulty_runs'],r['benign_false_alarms']) for r in summary if r['partition']==part and r['origin']=='ALL'],flush=True)
 t.write(O/'validation_summary.csv',summary);t.write(O/'subgroup_summary.csv',sub);t.write(O/'observability_accounting.csv',account);t.write(O/'ablation_summary.csv',paired)
 if 'VALIDATION' in parts:
  def val(m,space='ORIGINAL'):return next(r for r in summary if r['partition']=='VALIDATION' and r['method']==m and r['space']==space and r['origin']=='ALL')
  a,b,e=val('A0'),val('A1'),val('A1','EXPANDED');ab=next(r for r in sub if r['partition']=='VALIDATION' and r['method']=='A1' and r['group']=='AB_common')
  checks=dict(original_at_least95=b['coverage']>=.95,expanded_at_least95=e['coverage']>=.95,AB_at_least80=ab['coverage']>=.8,benign_at_most01=e['benign_false_alarm_rate']<=.01,zero_wrong=e['runtime_wrong_samples']==0,plant_no_loss=b['silent_plant']<=a['silent_plant'])
  for origin in ['TIMING','COMMUNICATION']:
   aa=next(r for r in summary if r['partition']=='VALIDATION' and r['method']=='A0' and r['space']=='ORIGINAL' and r['origin']==origin);bb=next(r for r in summary if r['partition']=='VALIDATION' and r['method']=='A1' and r['space']=='ORIGINAL' and r['origin']==origin);checks[origin+'_preserved']=bb['detected']>=aa['detected']
  aa=next(r for r in sub if r['partition']=='VALIDATION' and r['method']=='A0' and r['group']=='effective_memory');bb=next(r for r in sub if r['partition']=='VALIDATION' and r['method']=='A1' and r['group']=='effective_memory');checks['effective_memory_preserved']=bb['detected']>=aa['detected'];checks['retained']=all(checks.values());(B/'retention.json').write_text(json.dumps(checks,indent=2));print('RETENTION',checks)
if __name__=='__main__':report(['TRAIN','CALIBRATION']+(['VALIDATION'] if len(sys.argv)>1 and sys.argv[1]=='final' else []))
