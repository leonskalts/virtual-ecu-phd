"""Follow up fixed v4 cases without changing containment or hazard definitions."""
import json,subprocess
from pathlib import Path
from .cross_layer_safety import PROJECT_ROOT,read_rows
from .cross_layer_campaign import command_for_run
from .cross_layer_analysis import timestamp,write_table
from .validation_v5_metrics import duration,intervention_cost


def horizon_row(trace,anchor,horizon):
 if anchor is None:return {'anchor_ms':None,'horizon_ms':horizon,'available':0,'containment_success':None}
 end=anchor+horizon
 if end>int(trace[-1]['time_ms']):return {'anchor_ms':anchor,'horizon_ms':horizon,'available':0,'containment_success':None}
 selected=[r for r in trace if anchor<=int(r['time_ms'])<=end]
 last=selected[-1]
 below=next((int(r['time_ms']) for r in selected if r['hazard_warning_active']=='0'),None)
 stable=None;candidate=None
 for r in selected:
  now=int(r['time_ms'])
  if r['hazard_warning_active']=='0':
   if candidate is None:candidate=now
   if now-candidate>=1000 and stable is None:stable=now
  else:candidate=stable=None
 return {'anchor_ms':anchor,'horizon_ms':horizon,'available':1,'evaluated_end_ms':end,
  'below_warning_latency_ms':below-anchor if below is not None else None,
  'stable_below_warning_latency_ms':stable-anchor if stable is not None else None,
  'containment_success':timestamp(last,'containment_success'),
  'containment_time_ms':timestamp(last,'containment_time_ms'),
  'hazard_entered':int(last['hazard_entered']),
  'critical_exposure_ms':int(last['critical_exposure_time_ms']),
  'safe_state_duration_ms':duration(trace,lambda r:int(r['safe_state_id'])>0,anchor,end),
  'post_anchor_thermal_overshoot_c':max(float(r['coolant_temp_true_c']) for r in selected)-float(selected[0]['coolant_temp_true_c'])}


def run_recovery(output,config,resume=False):
 output=Path(output);raw=output/'raw/recovery';raw.mkdir(parents=True,exist_ok=True)
 old=PROJECT_ROOT/'results/cross_layer_safety_v4'
 comm=[r for r in read_rows(old/'communication_response_runs.csv') if r['mode_id']=='protective_action' and r['fixed_cohort_containment']=='0']
 timing={}
 for r in read_rows(old/'timing_monitor_runs.csv'):
  if r['mode_id']=='combined_protect' and r['injected']=='1':timing.setdefault((r['fault_model'],r['fault_behavior']),r)
 cases=comm+list(timing.values());rows=[];final=[];commands=[]
 for original in cases:
  for policy in ['observe_only','immediate','graded']:
   profile={'id':original['operating_profile'],'duration_ms':config['recovery']['extended_end_ms'],'path':'profiles/driving/example_driving_profile.csv' if original['operating_profile']=='high_load_profile' else None}
   spec={'profile':profile,'parameters':json.loads(original['configuration']),'model':original['fault_model'],'detector':config['detector']}
   rid=original['pair_id']+'_recovery_'+policy;path=raw/(rid+'.csv')
   cmd=command_for_run(spec,config,path)+['--v5-policy',policy];commands.append(cmd)
   if not resume or not path.exists():subprocess.run(cmd,capture_output=True,check=True)
   trace=read_rows(path)
   recovery=next((int(r['time_ms']) for r in trace if r.get('current_fault_phase')=='recovered'),None)
   alarm=timestamp(trace[-1],'existing_detector_first_alarm_ms') if original['study_kind']=='communication' else timestamp(trace[-1],'timing_monitor_first_alarm_ms')
   action=timestamp(trace[-1],'runtime_safety_first_action_ms')
   original_end=120000 if profile['id']=='nominal' else 300000
   before=next(r for r in trace if int(r['time_ms'])==original_end)
   initial=timestamp(before,'containment_success');eventual=timestamp(trace[-1],'containment_success')
   category='DELAYED_RECOVERY_BEYOND_ORIGINAL_HORIZON' if initial==0 and eventual==1 else 'FAILURE_PERSISTS_AT_EXTENDED_END' if initial==0 and eventual==0 else 'ALREADY_CONTAINED' if initial==1 else 'NOT_APPLICABLE'
   final.append({'run_id':rid,'source_v4_run_id':original['run_id'],'policy':policy,'study_kind':original['study_kind'],
    'original_end_ms':original_end,'extended_end_ms':int(trace[-1]['time_ms']),'original_containment':initial,'extended_containment':eventual,
    'recovery_classification':category,'fault_recovery_ms':recovery,'alarm_ms':alarm,'action_ms':action,
    'critical_exposure_ms':int(trace[-1]['critical_exposure_time_ms']),**intervention_cost(trace)})
   for name,anchor in [('fault_recovery',recovery),('alarm',alarm),('action',action)]:
    for horizon in config['recovery']['horizons_ms']:
     rows.append({'run_id':rid,'source_v4_run_id':original['run_id'],'study_kind':original['study_kind'],'policy':policy,'anchor_kind':name,**horizon_row(trace,anchor,horizon)})
 write_table(output/'recovery_horizon_analysis.csv',rows)
 write_table(output/'summaries/recovery_final_outcomes.csv',final)
 (output/'recovery_commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 count=lambda k:sum(r['policy']=='immediate' and r['recovery_classification']==k for r in final)
 (output/'recovery_horizon_findings.md').write_text(f'''# Recovery horizon follow-up

{len(cases)} selected v4 configurations, {len(commands)} new extended simulations.
These reuse development cases and are excluded from holdout detection denominators.
Original v4 immediate-policy failures: {sum(r['policy']=='immediate' and r['original_containment']==0 for r in final)}.
Recovered beyond original horizon by 360 s: {count('DELAYED_RECOVERY_BEYOND_ORIGINAL_HORIZON')}.
Still failed at 360 s: {count('FAILURE_PERSISTS_AT_EXTENDED_END')}.
A failure persisting at 360 s is not proof that recovery will never occur. Earlier
hazard permanently fails the accepted containment contract even if temperature
later recovers. Below-warning recovery, stable temperature, effect resolution and
containment remain distinct. All five v4 protected communication failures are included.
Fixed 5/15/30/60 s horizons follow each available recovery/alarm/action anchor.
Missing anchors or unobserved horizons remain N/A. No per-case horizon was tuned.
''')
 return rows,final
