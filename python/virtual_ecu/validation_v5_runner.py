"""Execute the frozen v5 protocol; preserve accepted evidence and all commands."""
import hashlib,json,subprocess
from pathlib import Path
from .validation_v5_design import OUTPUT,STUDY,expand,freeze,load_config
from .validation_v5_metrics import NativeAblation,intervention_cost,paired
from .cross_layer_safety import PROJECT_ROOT,read_rows,summarize_rows
from .cross_layer_campaign import command_for_run
from .cross_layer_analysis import analyze_run,write_table,timestamp
from .runtime_safety_study import runtime_summary


def command(spec,config,output):
 path=output/'raw'/(spec['run_id']+'.csv')
 cmd=command_for_run(spec,config,path)+['--v5-policy',spec['policy'],'--timing-evidence','combined']
 if spec.get('stress'):
  cmd+=['--scheduler-stress',spec['stress_kind'],'--scheduler-events',str(output/'raw'/(spec['run_id']+'_events.csv'))]
  for key,value in spec['stress'].items():cmd+=['--scheduler-'+key.replace('_','-'),str(value)]
 return cmd


def summarize(spec,trace,reference,raw):
 summary={'run_id':spec['run_id'],'raw_csv':str(raw),'operating_profile':spec['profile']['id'],
  'detector':'hybrid_adaptive_kalman','detector_action':'observe_only','configuration':json.dumps(spec['parameters'],sort_keys=True),**summarize_rows(trace)}
 row,_=analyze_run(summary,trace,reference);row.update(runtime_summary(trace));row.update(intervention_cost(trace))
 row.update({k:spec.get(k) for k in ['study_kind','pair_id','policy','behavior','timing_magnitude','timing_pattern','match_id','polarity']})
 row['is_perturbed']=int(spec['model']!='baseline' or spec.get('stress_kind')=='overload')
 row['scheduler_workload']=spec.get('stress_kind','legacy_dispatcher');row['configured_model']=spec['model']
 row['stress_configuration']=json.dumps(spec.get('stress',{}),sort_keys=True)
 row['contract_violation_ms']=timestamp(trace[-1],'scheduler_first_violation_ms') if spec.get('stress') else timestamp(trace[-1],'timing_first_violation_ms')
 row['contract_violated']=int(row['contract_violation_ms'] is not None)
 row['timing_latency_ms']=row['timing_alarm_ms']-row['contract_violation_ms'] if row['timing_alarm_ms'] is not None and row['contract_violation_ms'] is not None else None
 row['timing_severity']=('critical_absence' if any(r['timing_monitor_severity']=='critical_execution_absence' for r in trace) else 'repeated' if any(r['timing_monitor_severity']=='repeated' for r in trace) else 'single_transient' if row['contract_violated'] else 'legal')
 if spec.get('stress'):
  # Workload is not mislabeled as a direct injected fault. Use full-precision plant comparator.
  start=spec['stress'].get('stress_start_ms',0)
  plant=next((int(r['time_ms']) for r in trace if int(r['time_ms'])>=start and abs(float(r['plant_coolant_deviation_c']))>=.01),None)
  row['propagation_plant_ms']=plant;row['plant_manifestation']=int(plant is not None)
  row['actuator_any_effect']=None if spec['stress_kind']=='overload' else 0
  row['fault_layer']='timing_workload';row['fault_model']=spec['stress_kind'];row['preexisting_hazard']=int(any(r['hazard_entered']=='1' for r in trace if int(r['time_ms'])<=start))
  row['attributable_hazard']=int(trace[-1]['hazard_entered']) if row['preexisting_hazard']==0 else None
  row['containment_success']=None;row['ftti_met']=None
 else:
  # Baseline has no attributable injected hazard but supports absolute benign checks.
  if not row['is_perturbed']:row['attributable_hazard']=int(trace[-1]['hazard_entered'])
 row['combined_detected']=int(row.get('detected')==1 or row['timing_monitor_detected']==1)
 return row


def run(output=OUTPUT,resume=False):
 output=Path(output).resolve()
 for i in range(1,5):
  p=(PROJECT_ROOT/f'results/cross_layer_safety_v{i}').resolve()
  if output==p or output in p.parents or p in output.parents:raise ValueError('Output overlaps accepted evidence')
 config=load_config();freeze(output)
 for name in ['raw','summaries','figures','validation']: (output/name).mkdir(parents=True,exist_ok=True)
 subprocess.run(['make'],cwd=PROJECT_ROOT,check=True)
 specs=expand(config);ablation=NativeAblation(output/'contracts')
 references={};allcommands=[];manifest=[];rows=[];ablations=[]
 for p in config['profiles']:
  spec={'run_id':'reference_'+p['id'],'profile':p,'model':'baseline','parameters':{'seed':42},'detector':config['detector'],'policy':'observe_only'}
  cmd=command(spec,config,output);allcommands.append(cmd)
  if not resume or not Path(cmd[1]).exists():subprocess.run(cmd,capture_output=True,check=True)
  references[p['id']]={int(r['time_ms']):r for r in read_rows(Path(cmd[1]))}
 for index,spec in enumerate(specs,1):
  cmd=command(spec,config,output);allcommands.append(cmd);raw=Path(cmd[1])
  if not resume or not raw.exists():
   proc=subprocess.run(cmd,capture_output=True,text=True)
   if proc.returncode:raise RuntimeError(f"{spec['run_id']}: {proc.stderr or proc.stdout}")
  trace=read_rows(raw);row=summarize(spec,trace,references[spec['profile']['id']],raw);rows.append(row)
  if spec['study_kind']=='timing' and spec['policy']=='observe_only':
   alarms=ablation.replay(trace)
   assert alarms['combined']==row['timing_alarm_ms'],('Native replay mismatch',spec['run_id'])
   for name,time in alarms.items():ablations.append({**row,'ablation':name,'timing_alarm_ms':time,'timing_monitor_detected':int(time is not None),
    'timing_latency_ms':time-row['contract_violation_ms'] if time is not None and row['contract_violation_ms'] is not None else None})
  manifest.append({**{k:row[k] for k in ['run_id','study_kind','pair_id','policy','operating_profile','configured_model','is_perturbed','scheduler_workload','configuration','stress_configuration']},
   'raw_csv':str(raw),'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'command':json.dumps(cmd)})
  if index%100==0 or index==len(specs):print(f'Completed {index}/{len(specs)} frozen v5 runs',flush=True)
 paired(rows)
 (output/'commands.json').write_text(json.dumps(allcommands,indent=2)+'\n')
 (output/'study_config.json').write_text(json.dumps(config,indent=2)+'\n')
 write_table(output/'v5_run_manifest.csv',manifest)
 write_table(output/'summaries/all_runs.csv',rows)
 write_table(output/'summaries/ablation_runs.csv',ablations)
 for kind,name in [('timing','timing_holdout_runs.csv'),('communication','communication_validation_runs.csv'),('cross_layer','cross_layer_holdout_runs.csv'),('matched','stuck_dynamic_runs.csv')]:
  write_table(output/name,[r for r in rows if r['study_kind']==kind])
 return rows,ablations
