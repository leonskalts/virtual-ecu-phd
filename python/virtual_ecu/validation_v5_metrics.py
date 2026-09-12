"""Explicit denominators, paired burdens and frozen native-C ablation replay."""
import ctypes,math,statistics,subprocess
from pathlib import Path
from .cross_layer_analysis import timestamp
from .cross_layer_safety import PROJECT_ROOT


def wilson(successes,total,z=1.959963984540054):
 if total<0 or successes<0 or successes>total:raise ValueError('Invalid binomial counts')
 if not total:return None,None
 p=successes/total;d=1+z*z/total
 center=(p+z*z/(2*total))/d;half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
 return max(0.,center-half),min(1.,center+half)


def rate(metric,values,**group):
 values=list(values);eligible=[v for v in values if v is not None]
 n=len(eligible);k=sum(v==1 for v in eligible);lo,hi=wilson(k,n)
 return {**group,'metric':metric,'numerator':k,'denominator':n,'excluded':len(values)-n,
  'percent':100*k/n if n else None,'ci95_lower_percent':100*lo if lo is not None else None,
  'ci95_upper_percent':100*hi if hi is not None else None,'interval_method':'Wilson descriptive reference',
  'scope_note':'Fixed deterministic design; not IID fleet probability; small n' if n<30 else 'Fixed deterministic design; not IID fleet probability'}


def percentile(values,p=.95):
 values=sorted(values)
 if not values:return None
 x=(len(values)-1)*p;i=int(x);return values[i]+(values[min(i+1,len(values)-1)]-values[i])*(x-i)


def duration(trace,predicate,start=None,end=None):
 total=0
 for a,b in zip(trace,trace[1:]):
  lo=int(a['time_ms']);hi=int(b['time_ms'])
  if start is not None:lo=max(lo,start)
  if end is not None:hi=min(hi,end)
  if hi>lo and predicate(a):total+=hi-lo
 return total


def intervention_cost(trace):
 active=lambda r:int(r['safe_state_id'])>0
 request=lambda r:int(r.get('runtime_safety_requested_state') or 0)>0
 end=int(trace[-1]['time_ms']);start=int(trace[0]['time_ms'])
 return {'safe_state_activations':sum(active(r) and (i==0 or not active(trace[i-1])) for i,r in enumerate(trace)),
  'safe_state_duration_ms':duration(trace,active),'limp_home_duration_ms':duration(trace,lambda r:int(r['safe_state_id'])==2),
  'precautionary_cooling_duration_ms':duration(trace,lambda r:int(r['safe_state_id'])==1),
  'shutdown_duration_ms':duration(trace,lambda r:int(r['safe_state_id'])==3),
  'policy_requested_duration_ms':duration(trace,request),
  'normalized_request_burden':duration(trace,request)/(end-start) if end>start else None,
  'incremental_policy_action_samples':int(trace[-1].get('runtime_safety_action_samples') or 0)}


def timing_metrics(rows,**group):
 violations=[r for r in rows if r['contract_violated']==1];legal=[r for r in rows if r['contract_violated']==0]
 detected=[r for r in rows if r['timing_monitor_detected']==1]
 plant=[r for r in violations if r['plant_manifestation']==1]
 out=[rate('timing_detection_coverage',[r['timing_monitor_detected'] for r in violations],**group),
  rate('timing_false_alarm_rate',[r['timing_monitor_detected'] for r in legal],**group),
  rate('specificity',[1-r['timing_monitor_detected'] for r in legal],**group),
  rate('precision',[r['contract_violated'] for r in detected],**group),
  rate('recall',[r['timing_monitor_detected'] for r in violations],**group),
  rate('miss_rate',[1-r['timing_monitor_detected'] for r in violations],**group),
  rate('plant_propagating_timing_detection',[r['timing_monitor_detected'] for r in plant],**group),
  rate('pre_plant_timing_detection',[int(r['timing_alarm_ms'] is not None and r['timing_alarm_ms']<r['propagation_plant_ms']) for r in plant],**group),
  rate('same_tick_plant_timing_detection',[int(r['timing_alarm_ms']==r['propagation_plant_ms']) for r in plant],**group)]
 lat=[r['timing_latency_ms'] for r in violations if r['timing_latency_ms'] is not None]
 for name,value in [('median_detection_latency_ms',statistics.median(lat) if lat else None),('p95_detection_latency_ms',percentile(lat))]:
  out.append({**group,'metric':name,'numerator':None,'denominator':len(lat),'excluded':len(violations)-len(lat),'percent':None,'value_ms':value,'scope_note':'Detected cases with both endpoints; latency is not a percentage'})
 return out


def paired(rows):
 base={r['pair_id']:r for r in rows if r['policy']=='observe_only'}
 for r in rows:
  b=base[r['pair_id']];r['observe_plant_manifestation']=b['plant_manifestation'];r['observe_hazard']=b['attributable_hazard']
  r['observe_actuator_effect']=b.get('actuator_any_effect');r['observe_plant_ms']=b.get('propagation_plant_ms');r['observe_hazard_ms']=b.get('hazard_entry_ms')
  r['false_intervention']=r['policy_intervention'] if not r['is_perturbed'] else None
  no_downstream=b.get('actuator_any_effect')==0 and b['plant_manifestation']==0
  r['unnecessary_intervention']=r['policy_intervention'] if r['is_perturbed'] and no_downstream else None
  r['unnecessary_intervention_duration_ms']=max(0,r['safe_state_duration_ms']-b['safe_state_duration_ms']) if r['unnecessary_intervention']==1 else 0 if r['unnecessary_intervention']==0 else None
  r['unnecessary_requested_duration_ms']=r['policy_requested_duration_ms'] if r['unnecessary_intervention']==1 else 0 if r['unnecessary_intervention']==0 else None
  r['self_recovering_fault_intervention']=r['policy_intervention'] if b.get('fault_recovered')==1 else None
  r['paired_excess_safe_state_duration_ms']=r['safe_state_duration_ms']-b['safe_state_duration_ms']
  r['hazard_prevented']=int(r['attributable_hazard']==0) if b['attributable_hazard']==1 else None
  r['hazard_introduced']=int(r['attributable_hazard']==1) if b['attributable_hazard']==0 else None
  eligible=(b.get('actuator_any_effect')==1 or b['plant_manifestation']==1) and b.get('preexisting_hazard')==0
  r['fixed_containment']=r.get('containment_success') if eligible else None
  r['fixed_ftti']=r.get('ftti_met') if eligible else None
  for stage in ['plant','hazard']:
   boundary=r.get('observe_'+stage+'_ms');action=r['runtime_safety_first_action_ms']
   r['action_order_vs_'+stage]=('BEFORE' if action<boundary else 'SAME_TICK' if action==boundary else 'AFTER') if action is not None and boundary is not None else 'N/A'
  r['intervention_class']='NO_INTERVENTION' if not r['policy_intervention'] else 'FALSE_INTERVENTION' if r['false_intervention']==1 else 'UNNECESSARY_NO_ACTUATOR_PLANT' if r['unnecessary_intervention']==1 else 'OBSERVED_HAZARD_PREVENTED' if r['hazard_prevented']==1 else 'PROPAGATING_BENEFIT_UNPROVEN'
 return rows


def policy_metrics(rows,**group):
 return [rate(name,[r.get(key) for r in rows if select(r)],**group) for name,key,select in [
  ('existing_detection','detected',lambda r:r['is_perturbed']),('hazard_rate','attributable_hazard',lambda r:r['is_perturbed']),
  ('hazard_prevention','hazard_prevented',lambda r:True),('hazard_introduction','hazard_introduced',lambda r:True),
  ('containment_success','fixed_containment',lambda r:r['is_perturbed']),('experimental_ftti','fixed_ftti',lambda r:r['is_perturbed']),
  ('unnecessary_intervention','unnecessary_intervention',lambda r:True),('false_intervention','false_intervention',lambda r:True),
  ('intervention_rate','policy_intervention',lambda r:True)]]


class NativeAblation:
 def __init__(self,directory):
  directory.mkdir(parents=True,exist_ok=True);source=directory/'ablation_bridge.c';library=directory/'ablation_bridge.so'
  source.write_text('''#include "timing_safety_monitor.h"
int replay(unsigned n,const unsigned *t,const unsigned *age,const unsigned *deadline,const unsigned *missed,int evidence) {
 timing_monitor_status_t s;timing_safety_monitor_init(&s);
 for(unsigned i=0;i<n;i++){runtime_timing_observation_t o={.time_ms=t[i],.period_ms=100,.relative_deadline_ms=100,.execution_age_ms=age[i],.deadline_exceeded=deadline[i],.missed_expected_execution=missed[i]};
 timing_safety_monitor_step(&s,&o,TIMING_OBSERVE_ONLY,(timing_evidence_t)evidence);}
 return s.first_alarm_ms;
}
''')
  subprocess.run(['gcc','-std=c11','-O2','-shared','-fPIC','-I'+str(PROJECT_ROOT/'include'),str(source),str(PROJECT_ROOT/'src/timing_safety_monitor.c'),'-o',str(library)],check=True)
  self.lib=ctypes.CDLL(str(library));self.lib.replay.restype=ctypes.c_int
  self.lib.replay.argtypes=[ctypes.c_uint]+[ctypes.POINTER(ctypes.c_uint)]*4+[ctypes.c_int]
 def replay(self,trace):
  n=len(trace);array=ctypes.c_uint*n
  arrays=[array(*(int(r[k]) for r in trace)) for k in ['time_ms','trusted_execution_age_ms','trusted_deadline_exceeded','trusted_missed_expected_execution']]
  return {name:(lambda x:x if x>=0 else None)(self.lib.replay(n,*arrays,i)) for i,name in enumerate(['deadline_only','execution_age_only','combined'])}
