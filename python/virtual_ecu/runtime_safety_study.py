"""Paired v4 runtime-monitor and response-policy experiments.

Fault truth is used only here for evaluation/cohort attribution, never by the C
monitor or response policy. Existing alarms are kept separate from timing alarms.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import statistics
import subprocess
from pathlib import Path

from .cross_layer_safety import PROJECT_ROOT, read_rows, summarize_rows
from .cross_layer_campaign import read_study, command_for_run, PARAMETERS
from .cross_layer_analysis import analyze_run, typed, timestamp, write_table, rate

DEFAULT_OUTPUT = PROJECT_ROOT/'results/cross_layer_safety_v4'
TIMING_STUDY = PROJECT_ROOT/'studies/timing_monitor_validation_v1.yaml'
COMMUNICATION_STUDY = PROJECT_ROOT/'studies/communication_safety_response_v1.yaml'


def expand_cases(config):
    cases=[]
    for profile in config['profiles']:
        if config.get('include_baseline',True):
            cases.append({'profile':profile,'case_id':'baseline','model':'baseline','parameters':{'seed':config['seeds'][0]}})
        for case in config['fault_cases']:
            grid={'start_ms':profile.get(case.get('injection_schedule','injection_times_ms'),config['injection_times_ms']),
                  'seed':config['seeds'],'behavior':[case.get('behavior','transient')],**case.get('grid',{})}
            fixed=case.get('parameters',{})
            if (set(grid)|set(fixed))-PARAMETERS or set(grid)&set(fixed):
                raise ValueError('Unknown or overlapping study parameters')
            if any(not isinstance(values,list) or not values for values in grid.values()):
                raise ValueError('Study grid dimensions must be nonempty lists')
            for values in itertools.product(*grid.values()):
                cases.append({'profile':profile,'case_id':case['id'],'model':case['model'],
                              'parameters':{**fixed,**dict(zip(grid,values))}})
    # One frozen existing detector per matched study. No implicit detector tuning.
    if len(config['detectors']) != 1:
        raise ValueError('V4 paired study expects one fixed existing detector')
    for index,case in enumerate(cases):
        case['detector']=config['detectors'][0]
        case['pair_id']=f"{config['study_kind']}_{index:04d}_{case['profile']['id']}_{case['case_id']}"
    return cases


def timing_signature(model,profile,params):
    behavior=params.get('behavior','transient')
    return (model,profile,behavior,params.get('start_ms'),
            params.get('duration_ms',100) if behavior!='permanent' else None,
            params.get('intermittent_on_ms') if behavior=='intermittent' else None,
            params.get('intermittent_off_ms') if behavior=='intermittent' else None,
            params.get('task_delay_ms') if model=='task_delay' else None)


def mechanism_attribution(existing_ms,timing_ms):
    if existing_ms is None and timing_ms is None:return 'NONE',None
    if existing_ms is None:return 'timing_safety_monitor',timing_ms
    if timing_ms is None:return 'existing_detector',existing_ms
    if existing_ms==timing_ms:return 'SIMULTANEOUS',existing_ms
    return ('existing_detector',existing_ms) if existing_ms<timing_ms else ('timing_safety_monitor',timing_ms)


def runtime_summary(trace):
    """Small shared loader; absent v4 instrumentation stays N/A for old results."""
    last=trace[-1]
    fields=('timing_monitor_mode','timing_evidence_mode','communication_safety_response',
            'timing_first_violation_ms','timing_monitor_first_alarm_ms','timing_monitor_detected',
            'existing_detector_first_alarm_ms','communication_first_alarm_ms',
            'timing_first_request_ms','communication_first_request_ms','runtime_safety_first_request_ms',
            'runtime_safety_first_action_ms','runtime_safety_request_samples','runtime_safety_action_samples')
    result=typed({k:last.get(k) for k in fields})
    available=last.get('runtime_safety_enabled')=='1'
    result['timing_contract_violation_observed']=int(result['timing_first_violation_ms'] is not None) if available else None
    result['timing_alarm_ms']=result['timing_monitor_first_alarm_ms']
    result['existing_alarm_ms']=result['existing_detector_first_alarm_ms']
    result['existing_detector_alarm_observed']=int(result['existing_alarm_ms'] is not None) if available else None
    result['first_detection_mechanism'],result['first_alarm_ms']=mechanism_attribution(result['existing_alarm_ms'],result['timing_alarm_ms']) if available else ('N/A',None)
    result['safety_action_requested']=int(result['runtime_safety_first_request_ms'] is not None) if available else None
    result['policy_intervention']=int(result['runtime_safety_first_action_ms'] is not None) if available else None
    result['intervention_class']='N/A_REQUIRES_MATCHED_OBSERVE_RUN'
    return result


def consequence(row):
    if row.get('attributable_hazard')==1:return 'HAZARD'
    if row.get('plant_manifestation')==1:return 'PLANT'
    if row.get('actuator_any_effect')==1:return 'ACTUATOR_ONLY'
    if row.get('control_effect')==1:return 'CONTROL_ONLY'
    return 'NO_DOWNSTREAM'


def intervention_classification(row,observe):
    if row.get('policy_intervention') != 1:return 'NO_INTERVENTION'
    if row.get('injected')==0:return 'FALSE_INTERVENTION'
    if observe.get('actuator_any_effect')==0 and observe.get('plant_manifestation')==0:
        return 'UNNECESSARY_NO_DOWNSTREAM'
    if observe.get('attributable_hazard')==1 and (row.get('attributable_hazard')==0 or
        row.get('critical_exposure_time_ms',0)<observe.get('critical_exposure_time_ms',0)):
        return 'TRUE_PROTECTIVE_HAZARD_MITIGATED'
    return 'RESPONSE_TO_PROPAGATING_FAULT_BENEFIT_UNPROVEN'


def pair_outcomes(rows):
    observed={r['pair_id']:r for r in rows if r['mode_id'] in ('combined_observe','observe_only')}
    for row in rows:
        base=observed[row['pair_id']]
        row['observe_consequence']=consequence(base)
        for label,key in (('observe_control_effect','control_effect'),('observe_actuator_effect','actuator_any_effect'),
                          ('observe_plant_manifestation','plant_manifestation'),('observe_hazard','attributable_hazard'),
                          ('observe_plant_ms','propagation_plant_ms'),('observe_hazard_ms','hazard_entry_ms'),
                          ('observe_containment','hardened_containment'),('observe_critical_exposure_ms','critical_exposure_time_ms')):
            row[label]=base.get(key)
        eligible=base.get('first_safety_relevant_manifestation_ms') is not None and base.get('preexisting_hazard')==0
        row['fixed_cohort_containment']=row.get('containment_success') if eligible else None
        row['fixed_cohort_injection_ftti']=row.get('ftti_met') if eligible else None
        row['intervention_class']=intervention_classification(row,base)
        row['false_intervention']=row['policy_intervention'] if row['injected']==0 else None
        unnecessary=base.get('actuator_any_effect')==0 and base.get('plant_manifestation')==0 and row['injected']==1
        row['unnecessary_intervention']=row['policy_intervention'] if unnecessary else None
        row['unnecessary_transient_intervention']=row['policy_intervention'] if unnecessary and row.get('fault_behavior')=='transient' else None
        row['hazard_prevented']=int(row['attributable_hazard']==0) if base.get('attributable_hazard')==1 else None
        row['hazard_introduced']=int(row.get('attributable_hazard')==1) if base.get('attributable_hazard')==0 else None
        row['critical_exposure_reduction_ms']=(base['critical_exposure_time_ms']-row['critical_exposure_time_ms']) if row['injected']==1 else None
        row['timing_alarm_to_plant_order']=None
        for label,time in (('timing_alarm',row['timing_alarm_ms']),('intervention',row['runtime_safety_first_action_ms'])):
            for stage,key in (('plant','observe_plant_ms'),('hazard','observe_hazard_ms')):
                boundary=row[key]
                row[label+'_before_'+stage]=int(time is not None and time<boundary) if boundary is not None else None
                row[label+'_order_vs_'+stage]=('BEFORE' if time<boundary else 'SAME_TICK' if time==boundary else 'AFTER') if time is not None and boundary is not None else 'N/A'
        first=row['timing_alarm_ms'];violation=row['timing_first_violation_ms']
        row['timing_detection_latency_ms']=first-violation if first is not None and violation is not None else None
        row['combined_observational_detected']=int(row['detected']==1 or row['timing_monitor_detected']==1)
    return rows


def study_statistics(rows,dimension='mode_id'):
    output=[]
    for value in sorted({str(r.get(dimension) or 'N/A') for r in rows}):
        selected=[r for r in rows if str(r.get(dimension) or 'N/A')==value]
        injected=[r for r in selected if r['injected']==1]
        benign=[r for r in selected if r['injected']==0]
        metrics={
            'raw_timing_detection_coverage':[r['timing_monitor_detected'] for r in injected],
            'actual_contract_violation_coverage':[r['timing_monitor_detected'] for r in selected if r['timing_contract_violation_observed']==1],
            'existing_detection_coverage':[r['detected'] for r in injected],
            'combined_observational_coverage':[r['combined_observational_detected'] for r in injected],
            'timing_coverage_given_control':[r['timing_monitor_detected'] for r in injected if r['observe_control_effect']==1],
            'timing_coverage_given_plant':[r['timing_monitor_detected'] for r in injected if r['observe_plant_manifestation']==1],
            'timing_coverage_given_hazard':[r['timing_monitor_detected'] for r in injected if r['observe_hazard']==1],
            'timing_detection_before_plant':[r['timing_alarm_before_plant'] for r in injected if r['observe_plant_manifestation']==1],
            'timing_false_alarm_rate':[r['timing_monitor_detected'] for r in benign],
            'existing_false_alarm_rate':[int(r['existing_alarm_ms'] is not None) for r in benign],
            'false_intervention_rate':[r['false_intervention'] for r in benign],
            'unnecessary_intervention_rate':[r['unnecessary_intervention'] for r in injected],
            'safe_state_activation_rate':[r['safe_state_reached'] for r in injected],
            'hazard_rate':[r['attributable_hazard'] for r in injected],
            'fixed_cohort_containment_rate':[r['fixed_cohort_containment'] for r in injected],
            'fixed_cohort_injection_ftti_rate':[r['fixed_cohort_injection_ftti'] for r in injected],
            'policy_intervention_rate':[r['policy_intervention'] for r in injected],
            'hazard_prevention_rate':[r['hazard_prevented'] for r in injected],
        }
        for label,values in metrics.items():
            output.append({**rate(label,values,dimension,value),'run_count':len(selected),'injected_runs':len(injected),'benign_runs':len(benign)})
    return output


def ablation_summary(rows):
    output=[]
    for mode in ('deadline_only','execution_age_only','combined_observe'):
        selected=[r for r in rows if r['mode_id']==mode]
        injected=[r for r in selected if r['injected']==1]
        negative=[r for r in selected if r['injected']==0]
        values=[r['timing_detection_latency_ms'] for r in injected if r['timing_detection_latency_ms'] is not None]
        output.append({'mode_id':mode,'detected':sum(r['timing_monitor_detected']==1 for r in injected),
                       'injected_runs':len(injected),'contract_violations':sum(r['timing_contract_violation_observed']==1 for r in injected),
                       'false_alarms':sum(r['timing_monitor_detected']==1 for r in negative),'benign_runs':len(negative),
                       'plant_propagating_timing_misses':sum(r['observe_plant_manifestation']==1 and r['timing_monitor_detected']==0 for r in injected),
                       'detected_before_plant':sum(r['timing_alarm_before_plant']==1 for r in injected),
                       'plant_runs':sum(r['observe_plant_manifestation']==1 for r in injected),
                       'latency_n':len(values),'median_detection_latency_ms':statistics.median(values) if values else None})
    return output


def run_studies(timing_path=TIMING_STUDY,communication_path=COMMUNICATION_STUDY,output=DEFAULT_OUTPUT):
    output=Path(output).resolve()
    protected=[(PROJECT_ROOT/'results'/f'cross_layer_safety_v{i}').resolve() for i in (1,2,3)]
    if any(output==p or p in output.parents or output in p.parents for p in protected):
        raise ValueError('Runtime study output must be separate from accepted v1/v2/v3 evidence')
    configs=[read_study(Path(p)) for p in (timing_path,communication_path)]
    work=[]
    for config in configs:
        cases=expand_cases(config)
        if not cases or len(cases)*len(config['modes'])>config.get('max_runs',1000):raise ValueError('Invalid v4 campaign size')
        for mode in config['modes']:
            for case in cases:
                spec={**case,'run_id':case['pair_id']+'_'+mode['id']}
                path=output/'raw'/(spec['run_id']+'.csv')
                command=command_for_run(spec,config,path)+['--timing-monitor',mode['timing_monitor'],
                    '--timing-evidence',mode['timing_evidence'],'--communication-safety-response',mode['communication_response']]
                work.append((config,mode,spec,command))
    subprocess.run(['make'],cwd=PROJECT_ROOT,check=True)
    (output/'raw').mkdir(parents=True,exist_ok=True)
    (output/'commands.json').write_text(json.dumps([command for _,_,_,command in work],indent=2)+'\n')
    (output/'study_configs.json').write_text(json.dumps(configs,indent=2)+'\n')
    previous=read_rows(PROJECT_ROOT/'results/cross_layer_safety_v3/campaign_scientific_reanalysis.csv')
    previous_timing={timing_signature(r['fault_model'],r['operating_profile'],json.loads(r['configuration'])):r for r in previous if r['fault_layer']=='timing'}
    references={};rows=[]
    for index,(config,mode,spec,command) in enumerate(work,1):
        completed=subprocess.run(command,cwd=PROJECT_ROOT,capture_output=True,text=True)
        if completed.returncode:raise RuntimeError(f"{spec['run_id']}: {completed.stderr or completed.stdout}")
        trace=read_rows(Path(command[1]))
        key=(config['study_kind'],mode['id'],spec['profile']['id'])
        if spec['model']=='baseline':references[key]={int(r['time_ms']):r for r in trace}
        summary={'run_id':spec['run_id'],'raw_csv':command[1],'operating_profile':spec['profile']['id'],
                 'detector':spec['detector']['algorithm'],'detector_action':spec['detector']['action'],
                 'configuration':json.dumps(spec['parameters'],sort_keys=True),**summarize_rows(trace)}
        row,_=analyze_run(summary,trace,references[key])
        row.update(runtime_summary(trace))
        row.update(study_kind=config['study_kind'],mode_id=mode['id'],pair_id=spec['pair_id'])
        old=previous_timing.get(timing_signature(spec['model'],spec['profile']['id'],spec['parameters']))
        row['v3_run_id']=old['run_id'] if old else None
        row['v3_detector_miss']=int(old['detected']=='0') if old else None
        row['v3_plant_propagating_miss']=int(old['detected']=='0' and old['plant_manifestation']=='1') if old else None
        rows.append(row)
        if index%50==0 or index==len(work):print(f'Completed {index}/{len(work)} runtime safety runs',flush=True)
    pair_outcomes(rows)
    from .runtime_safety_report import write_package
    write_package(output,rows)
    hashes={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((output/'raw').glob('*.csv'))}
    (output/'raw_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return rows
