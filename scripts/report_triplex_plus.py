#!/usr/bin/env python3
"""Post-hoc development reporting, never part of a runtime evidence provider."""
import json,sys,collections,math,time
from pathlib import Path
import run_triplex_plus as r
import select_triplex_plus as s
import report_comparative_benchmark as common
import numpy as np
import pickle
B=r.B;O=r.O

def stats(rows):return common.stats(rows)
def delta(a,b):
 aa={x['run_id']:x for x in a};bb={x['run_id']:x for x in b};assert aa.keys()==bb.keys()
 return [bb[k] for k in aa if bb[k]['detected'] and not aa[k]['detected']],[aa[k] for k in aa if aa[k]['detected'] and not bb[k]['detected']]

def validation():
 r.verify();assert (B/'VALIDATION_complete').exists() and not (B/'validation_replay_complete').exists()
 lock=json.loads((O/'validation_lock.json').read_text());arch=lock['architecture']['selected_arch'];use=lock['oq_set'].get('selected',False)
 oq=json.loads((O/'oq_set.json').read_text()) if use else None
 model=pickle.loads((O/'fair_svm.pkl').read_bytes());allrows=s.part_rows('VALIDATION');out=[]
 for row,e,y,base in s.dataset('VALIDATION',arch):
  state,seq=s.oq_states(e,oq) if use else (None,None)
  x=s.features(e,state/oq['boundary'] if use else None);unique,inverse=np.unique(x,axis=0,return_inverse=True)
  alarm=model.predict(unique)[inverse].astype(bool)
  out.append(r.bench.score(row,e,'Fair SVM',(alarm,np.zeros(len(alarm),int))))
  if use:
   basealarm=base[:,0].astype(bool);origin=np.where(basealarm,base[:,1]>>1,0)
   out.append(r.bench.score(row,e,'Triplex-Plus',(basealarm|seq,origin)))
  else:out.append(dict(row,method='Triplex-Plus'))
 out += [dict(x,method='Retained Triplex') for x in allrows if x['method']=='A0']
 r.dump(B/'validation_final_rows.json',out);(B/'validation_replay_complete').write_text(r.now())
 sums=[dict(method=m,**stats([x for x in out if x['method']==m])) for m in ['Retained Triplex','Fair SVM','Triplex-Plus']]
 r.h.write(O/'validation_comparison.csv',sums)
 subs=[dict(method=m,subgroup=g,**stats([x for x in out if x['method']==m and f(x)])) for m in ['Retained Triplex','Fair SVM','Triplex-Plus'] for g,f in common.FILTERS.items()]
 r.h.write(O/'validation_subgroups.csv',subs)
 pair=common.pair(out,'Triplex-Plus','Fair SVM','fault');benignpair=common.pair(out,'Triplex-Plus','Fair SVM','benign');r.h.write(O/'paired_comparison.csv',[pair,benignpair,common.pair(out,'Triplex-Plus','Retained Triplex','fault')])
 aa=[x for x in out if x['method']=='Retained Triplex'];pp=[x for x in out if x['method']=='Triplex-Plus'];g,l=delta(aa,pp)
 account=[]
 subgroup={
 'Memory dormant':lambda x:x['origin']=='MEMORY' and x['initially_latent_stuck'] and not x['effective_memory_corruption'],
 'Memory other':lambda x:x['origin']=='MEMORY' and not(x['initially_latent_stuck'] and not x['effective_memory_corruption']),
 **{d:lambda x,d=d:x['origin']=='SENSOR_CONTROL' and x['domain']==d for d in ['A','B','AB']},
 'Weak steps':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='step',
 'Pulses':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind']=='pulse',
 'Other sensor':lambda x:x['origin']=='SENSOR_CONTROL' and x['kind'] not in ['step','pulse'],
 **{o:lambda x,o=o:x['origin']==o for o in ['TIMING','COMMUNICATION','ACTUATOR']}}
 for name,f in subgroup.items():account.append(dict(group=name,additional=sum(f(x) for x in g),lost=sum(f(x) for x in l)))
 r.h.write(O/'gain_subgroups.csv',account)
 memory=lock['architecture']['memory_arch'];memrows=[x for x in allrows if x['method']==r.NAMES[memory]]
 selected=[x for x in allrows if x['method']==r.NAMES[arch]]
 components=[]
 for name,a,b in [('memory',aa,memrows),('staggered sensor',memrows,selected),('sequential',selected,pp)]:
  gain,lost=delta(a,b);components.append(dict(component=name,additional=len(gain),lost=len(lost),net=len(gain)-len(lost)))
 r.h.write(O/'gain_components.csv',components)
 critical=s.gates(pp,aa);p=next(x for x in sums if x['method']=='Triplex-Plus');v=next(x for x in sums if x['method']=='Fair SVM')
 promote=p['detected']>v['detected'] and p['coverage_given_plant_manifestation']>=.99 and critical
 result=dict(promoted=promote,retained='TRIPLEX-PLUS' if promote else 'TRIPLEX',ready_for_new_unseen=promote,validation_cases=900,comparison=sums,subgroups=subs,paired=pair,components=components,additional=len(g),lost=len(l),gain_subgroups=account,benign_gate=p['benign_false_alarm_rate']<=.01 and p['runtime_wrong_runs']==0,detection_margin=p['coverage']-v['coverage'])
 r.dump(O/'retention.json',result)
 fields=['run_id','method','origin','model','behavior','domain','kind','injected','detected','false_alarm','first_post_alarm_ms','latency_ms','plant_manifestation','propagation_plant_ms','silent_plant','effective_memory_corruption','initially_latent_stuck','initially_excited','actuator_excited','origin_at_alarm','alarm_samples','wrong_localized_runtime_samples',*[f'alarm_{o}' for o in [*r.be.ORIGINS,'UNKNOWN']],'raw_sha256','runtime_trace_sha256']
 r.h.write(O/'validation_cases.csv',[{k:x.get(k) for k in fields} for x in out])
 print(json.dumps({k:v for k,v in result.items() if k not in ['subgroups','comparison','gain_subgroups']},indent=2),flush=True)
 for x in sums:print(x['method'],x['detected'],x['faulty_runs'],x['benign_false_alarms'],x['runtime_wrong_runs'],flush=True)
 r.verify()

if __name__=='__main__':validation()
