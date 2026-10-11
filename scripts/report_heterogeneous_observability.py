#!/usr/bin/env python3
"""Post-hoc metrics; unavailable to runtime inference."""
import sys,json,pickle,collections,subprocess,shutil
from pathlib import Path
import run_heterogeneous_observability as d
import report_comparative_benchmark as common
import numpy as np
from scipy.stats import binomtest
B=d.B;O=d.O;r=d.r;h=d.h

def benign():
 d.verify();rows=json.loads((B/'VALIDATION_BENIGN_rows.json').read_text());ids=[x['run_id'] for x in rows if x['method']=='A0'];data=[]
 for rid in ids:
  a=np.load(B/'tapes'/(rid+'.npz'))['inputs'];p=np.load(B/'tapes'/(rid+'_replay.npz'))['model'];
  for member in range(3):
   valid=(a[:,9]>0) if member==2 else np.ones(len(a),bool)
   for regime,take in [('all',np.ones(len(a),bool)),('startup',a[:,0]<1000),('qualified',a[:,0]>=1000),('high_load',a[:,1]>=.7),('low_load_coasting',a[:,1]<.3),('fan_on',a[:,5]>0),('fan_off',a[:,5]==0),('pump_on',a[:,4]>0),('pump_off',a[:,4]==0),('cold_ambient',a[:,2]<20)]:
    mask=valid&take;e=a[mask,6+member]-p[mask,1]
    if len(e):data.append((regime,member,e,p[mask,2],p[mask,3]))
 out=[]
 for reg in sorted({x[0] for x in data}):
  for member in [-1,0,1,2]:
   z=[x for x in data if x[0]==reg and (member<0 or x[1]==member)]
   if not z:continue
   error=np.concatenate([x[2] for x in z]);sig=np.concatenate([x[3] for x in z]);bound=np.concatenate([x[4] for x in z]);ae=np.abs(error)
   out.append(dict(regime=reg,member='pooled' if member<0 else 'ABC'[member],observations=len(error),rmse=float(np.sqrt(np.mean(error**2))),mae=float(ae.mean()),p95=float(np.quantile(ae,.95)),worst=float(ae.max()),one_sigma_coverage=float(np.mean(ae<=sig)),two_sigma_coverage=float(np.mean(ae<=2*sig)),diagnostic_bound_coverage=float(np.mean(ae<=bound))))
 h.write(O/'benign_model_validation.csv',out);print('BENIGN MODEL FIRST',next(x for x in out if x['regime']=='all' and x['member']=='pooled'),flush=True)
 # This evaluation does not permit modification of the frozen model, bounds or SVM.

FILTERS={**common.FILTERS,
 'independent_slow_drift':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain'] in ['A','B','C'] and x['kind']=='ramp',
 'C_only':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain']=='C',
 'global_common_mode':lambda x:x['origin']=='SENSOR_CONTROL' and x['domain']=='ABC',
 'weak_positive_steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step' and x['magnitude']==.49,
 **{d+'_only':lambda x,d=d:x['origin']=='SENSOR_CONTROL' and x['domain']==d for d in ['A','B']}}

def pair(rows,a,b):
 aa={x['run_id']:x for x in rows if x['method']==a and x['injected']};bb={x['run_id']:x for x in rows if x['method']==b and x['injected']};assert aa.keys()==bb.keys()
 both=sum(aa[k]['detected'] and bb[k]['detected'] for k in aa);onlya=sum(aa[k]['detected'] and not bb[k]['detected'] for k in aa);onlyb=sum(not aa[k]['detected'] and bb[k]['detected'] for k in aa);neither=len(aa)-both-onlya-onlyb
 return dict(a=a,b=b,both=both,a_only=onlya,b_only=onlyb,neither=neither,exact_mcnemar_p=float(binomtest(onlya,onlya+onlyb,.5).pvalue) if onlya+onlyb else 1.)

def report():
 d.verify();assert not (O/'retention.json').exists()
 rows=json.loads((B/'VALIDATION_scored.json').read_text())+json.loads((B/'VALIDATION_BENIGN_scored.json').read_text());svm=pickle.loads((O/'fair_svm.pkl').read_bytes())
 for base in [x for x in rows if x['method']=='A3']:
  a=np.load(B/'tapes'/(base['run_id']+'_replay.npz'));e=r.be.Evidence(a['time'],a['values'],a['available'],a['subsets']);alarm=svm.predict(a['features']).astype(bool);rows.append(r.bench.score(base,e,'Fair SVM',(alarm,np.zeros(len(alarm),int))))
 sums=[dict(method=m,**common.stats([x for x in rows if x['method']==m])) for m in ['A0','A1','A2','A3','Fair SVM']];h.write(O/'validation_summary.csv',sums);h.write(O/'svm_comparison.csv',[x for x in sums if x['method'] in ['A0','A3','Fair SVM']])
 subs=[dict(method=m,subgroup=g,**common.stats([x for x in rows if x['method']==m and f(x)])) for m in ['A0','A1','A2','A3','Fair SVM'] for g,f in FILTERS.items()];h.write(O/'subgroup_summary.csv',subs)
 ablation=[]
 for part in ['TRAIN','CALIBRATION']:
  rr=json.loads((B/(part+'_scored.json')).read_text())
  ablation.extend(dict(partition=part,method=m,**common.stats([x for x in rr if x['method']==m])) for m in ['A0','A1','A2','A3'])
 ablation.extend(dict(partition='VALIDATION',**x) for x in sums if x['method']!='Fair SVM');h.write(O/'ablation_summary.csv',ablation)
 pairs=[pair(rows,a,b) for a,b in [('A2','A0'),('A3','A0'),('A1','A0'),('A3','A1'),('A3','Fair SVM')]];h.write(O/'paired_statistics.csv',pairs)
 by={m:{x['run_id']:x for x in rows if x['method']==m} for m in ['A0','A1','A2','A3']};gains=[]
 for rid,x in by['A3'].items():
  if x['detected'] and not by['A0'][rid]['detected']:
   component='memory' if by['A1'][rid]['detected'] else 'analytical'
   gains.append(dict(run_id=rid,component=component,origin=x['origin'],domain=x['domain'],kind=x['kind'],plant=x['plant_manifestation']))
 h.write(O/'gain_accounting.csv',gains)
 gates={};base=next(x for x in sums if x['method']=='A0')
 for m in ['A1','A2','A3']:
  st=next(x for x in sums if x['method']==m);regress=[]
  for group in ['TIMING','COMMUNICATION','effective_memory','AB_common_mode']:
   old=next(x for x in subs if x['method']=='A0' and x['subgroup']==group);new=next(x for x in subs if x['method']==m and x['subgroup']==group)
   if new['detected']<old['detected']:regress.append(group)
  gates[m]=dict(overall=st['coverage']>=.935,benign=st['benign_false_alarm_rate']<=.01,plant=st['coverage_given_plant_manifestation']>=.99,localization=st['runtime_wrong_runs']==0,no_critical_regression=not regress,regressed_groups=regress)
  gates[m]['passes']=all(v for k,v in gates[m].items() if k not in ['regressed_groups','passes'])
 # Simpler ablation is preferred if it meets all gates; analytical marginal gain constraint.
 gain=pair(rows,'A3','A1');analytical_gain=(gain['a_only']-gain['b_only'])/720
 important_safety=next(x for x in sums if x['method']=='A3')['silent_plant']<next(x for x in sums if x['method']=='A1')['silent_plant']
 eligible=[m for m in ['A1','A2','A3'] if gates[m]['passes'] and (m=='A1' or analytical_gain>=.01 or important_safety)]
 retained=eligible[0] if eligible else 'TRIPLEX'
 result=dict(retained=retained,ready_for_new_unseen=bool(eligible),gates=gates,comparison=sums,pairs=pairs,gain_counts=dict(collections.Counter(x['component'] for x in gains)),analytical_net_gain=analytical_gain,analytical_safety_gain=important_safety)
 d.dump(O/'retention.json',result);d.dump(B/'final_rows.json',rows)
 fields=['run_id','method','origin','domain','kind','behavior','detected','false_alarm','plant_manifestation','silent_plant','latency_ms','origin_at_alarm','alarm_samples','wrong_localized_runtime_samples','raw_sha256','runtime_trace_sha256']
 h.write(O/'validation_cases.csv',[{k:x.get(k) for k in fields} for x in rows])
 for s in sums:print(s['method'],s['detected'],s['faulty_runs'],s['benign_false_alarms'],s['plant_detected'],s['plant_manifestation_runs'],s['runtime_wrong_runs'],flush=True)
 print('RETENTION',retained,'GAINS',result['gain_counts'],flush=True)

if __name__=='__main__':
 if sys.argv[1]=='benign':benign()
 elif sys.argv[1]=='report':report()
