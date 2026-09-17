"""V7 DEVELOPMENT evaluator. Fault labels stay here and never enter CLO-DSF.

A simulation executes all comparison algorithms online in C. This module scores
outputs, selects only on TRAIN, and then runs VALIDATION exactly once.
"""
from __future__ import annotations
import csv
import gzip
import hashlib
import itertools
import json
import math
import shutil
import statistics
import subprocess
import time
from pathlib import Path
import yaml
from .cross_layer_safety import fault_options, MODEL_TARGETS, summarize_rows, read_rows

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'results/cross_layer_safety_v7_dev'
STUDY = ROOT / 'studies/clo_dsf_development_v1.yaml'
ORIGINS = ['MEMORY', 'TIMING', 'COMMUNICATION', 'SENSOR_CONTROL', 'ACTUATOR']
METHODS = ['Simple OR', 'Weighted Sum', 'Plain DS', 'A1 Observability', 'A2 Propagation', 'CLO-DSF',
           'Threshold', 'EWMA', 'CUSUM', 'Thermal Observer', 'Kalman', 'Hybrid', 'Timing Monitor']
NONLOCALIZING = {'Simple OR', 'Weighted Sum', 'Threshold', 'EWMA', 'CUSUM', 'Thermal Observer', 'Kalman', 'Hybrid', 'Timing Monitor'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(''); return
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader(); writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def candidate(index):
    return dict(r_direct=.9, r_indirect=.6, lambda_temporal=.9 if index & 2 else .8,
                propagation_bonus=.1, propagation_window_ms=3000,
                alarm_threshold_suspect=.35, alarm_threshold_confirmed=.75 if index & 4 else .65,
                confirmation_persistence=2, localization_threshold=.55,
                localization_margin_threshold=.15, ignorance_limit=.5,
                conflict_rule='dempster' if index & 1 else 'yager')


def write_runtime_config(path, cfg):
    Path(path).write_text(''.join(f'{k}={v}\n' for k, v in cfg.items()))


def profile(path, load, speed, ambient, duration):
    # Three operating segments; initial/late transitions are legitimate benign transients.
    rows = []
    for start, end, factor in [(0, 20000, .65), (20000, 80000, 1), (80000, duration, .85)]:
        rows.append(dict(start_ms=start, end_ms=end, vehicle_speed_kph=max(0, speed * factor),
                         engine_load=max(.05, min(1.0, load * factor)), ambient_temp_c=ambient,
                         external_airflow_factor=0, road_slope_percent=0))
    write_csv(path, rows)


def design(out=OUTPUT):
    cfg = yaml.safe_load(STUDY.read_text())
    specs = []
    for p in cfg['profiles']:
        profile(out/'profiles'/f"{p['name']}.csv", p['load'], p['speed'], p['ambient'], cfg['simulation_duration_ms'])
    for origin, models in cfg['models'].items():
        for model, magnitudes in models.items():
            for behavior in cfg['behaviors']:
                for severity, magnitude in enumerate(magnitudes):
                    for p in cfg['profiles']:
                        for onset in cfg['injection_times_ms']:
                            start = onset
                            if (model == 'fan_stuck_off' and behavior == 'permanent') or (model == 'deadline_miss' and behavior == 'transient'):
                                start += severity * 1000
                            specs.append(dict(origin=origin, model=model, behavior=behavior, magnitude=magnitude,
                                              severity=severity, profile=p['name'], start_ms=start,
                                              duration_ms=100 if model=='deadline_miss' and behavior=='transient' else cfg['durations_ms'][severity],
                                              group=f'{origin}/{model}/{behavior}'))
    for p in cfg['profiles']:
        for i, (load_offset, speed_offset, ambient_offset) in enumerate(itertools.product([-.09,-.03,.03,.09], [-6,-2,2,6], [-2,0,2])):
            name=f"benign_{p['name']}_{i:02}"
            profile(out/'profiles'/f'{name}.csv', p['load']+load_offset, p['speed']+speed_offset+(6 if p['speed']==0 else 0),
                    p['ambient']+ambient_offset, cfg['simulation_duration_ms'])
            specs.append(dict(origin='NORMAL', model='baseline', behavior='none', magnitude=0, severity=0,
                              profile=name, start_ms=cfg['simulation_duration_ms']+100, duration_ms=0,
                              group=f"NORMAL/{p['name']}"))
    val_groups=set()
    for origin in [*ORIGINS,'NORMAL']:
        groups=sorted({s['group'] for s in specs if s['origin']==origin},
                      key=lambda x:hashlib.sha256(f"{cfg['split_seed']}:{x}".encode()).hexdigest())
        # Four benign templates give two validation groups with ceil(0.30*4).
        val_groups.update(groups[:math.ceil(.3*len(groups))])
    for i,s in enumerate(specs):
        s.update(run_id=f'dev_{i:04}', partition='development-validation' if s['group'] in val_groups else 'development-train',
                 split_seed=cfg['split_seed'], simulation_duration_ms=cfg['simulation_duration_ms'])
    write_csv(out/'development_split_manifest.csv',specs)
    return specs


def command(spec,out,comparison,config):
    raw=out/'raw'/f"{spec['run_id']}.csv"
    model=spec['model']; start=spec['start_ms']; duration=spec['duration_ms']; behavior=spec['behavior']; magnitude=spec['magnitude']
    args=['baseline']
    if model in MODEL_TARGETS:
        options=fault_options(model,start_ms=start,duration_ms=duration,behavior=behavior,
                              bit_index=int(magnitude) if spec['origin']=='MEMORY' else 0,seed=1,
                              intermittent_on_ms=200,intermittent_off_ms=300,
                              task_delay_ms=int(magnitude) if model=='task_delay' else 200,
                              communication_delay_ms=int(magnitude) if model=='delayed_update' else 300,
                              drop_count=int(magnitude) if model=='dropped_update' else 3,
                              drop_every_n_updates=8 if model=='dropped_update' else 0,
                              replay_age_ms=int(magnitude) if model=='replayed_sample' else 500,
                              stuck_polarity=1)
    else:
        options=['--cross-layer-monitor','on']
        if model!='baseline':
            if behavior=='intermittent':
                args=['custom_multi','2',model,str(start),str(duration),'transient',str(magnitude),
                      model,str(start+duration+1000),str(duration),'transient',str(magnitude)]
            else:
                args=['custom',model,str(start),str(duration),behavior,str(magnitude)]
    return [str(ROOT/'virtual_ecu_v7'),str(raw),*args,*options,
            '--hazard-monitor','on','--timing-monitor','observe_only',
            '--driving-profile',str(out/'profiles'/f"{spec['profile']}.csv"),
            '--simulation-duration-ms',str(spec['simulation_duration_ms']),
            '--detector','builtin_ecu','--detector-action','observe_only',
            '--clo-config',str(config),'--clo-comparison',comparison,
            '--clo-evaluation-start',str(start),'--clo-evidence',str(out/'traces'/f"{spec['run_id']}.clo_dsf.csv"),
            '--clo-metrics',str(out/'metrics'/f"{spec['run_id']}.csv")]


def execute(spec,out,comparison,config):
    cmd=command(spec,out,comparison,config)
    t=time.perf_counter(); p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    if p.returncode: raise RuntimeError(f'{cmd}\n{p.stdout}\n{p.stderr}')
    elapsed=time.perf_counter()-t
    raw=Path(cmd[1]); rows=read_rows(raw); summary=summarize_rows(rows)
    values=list(csv.DictReader((out/'metrics'/f"{spec['run_id']}.csv").open()))
    result=[]
    for row in values:
        r={**spec,**row}
        for key in ['first_alarm_ms','first_post_alarm_ms','first_localization_ms','samples','alarm_samples','pre_alarm_samples','high_conflict_samples','propagation_samples']:
            r[key]=int(r[key])
        for key in ['mean_ignorance','mean_conflict','max_conflict']: r[key]=float(r[key])
        r['injected']=int(spec['origin']!='NORMAL')
        r['detected']=int(r['injected'] and r['first_post_alarm_ms']>=0)
        r['false_alarm']=int(not r['injected'] and r['first_alarm_ms']>=0)
        r['latency_ms']=r['first_post_alarm_ms']-spec['start_ms'] if r['detected'] else None
        for field in ['control_effect','actuator_effect','plant_manifestation','propagation_plant_ms','propagation_control_ms','propagation_actuator_command_ms']:
            r[field]=summary[field]
        r['silent_plant']=int(r['injected'] and r['plant_manifestation']==1 and not r['detected'])
        r['localized_correct']=int(r['detected'] and r['origin_at_alarm']==spec['origin'])
        r['unknown_at_alarm']=int(r['detected'] and r['origin_at_alarm']=='UNKNOWN')
        r['localization_before_plant']=int(r['detected'] and r['first_origin']==spec['origin'] and r['first_localization_ms']>=0 and r['propagation_plant_ms'] is not None and r['first_localization_ms']<r['propagation_plant_ms'])
        r['host_seconds']=elapsed
        result.append(r)
    # Keep exact original bytes in compressed archives, no frozen output touched.
    for path in [raw,raw.with_name(raw.stem+'_summary.csv'),out/'traces'/f"{spec['run_id']}.clo_dsf.csv"]:
        with path.open('rb') as src, path.with_suffix(path.suffix+'.gz').open('wb') as dest:
            with gzip.GzipFile(filename='',mode='wb',fileobj=dest,mtime=0) as gz: shutil.copyfileobj(src,gz)
        path.unlink()
    write_json(out/'commands'/f"{spec['run_id']}.json",cmd)
    return result


def ratio(n,d): return n/d if d else None


def quantile(values,p):
    if not values:return None
    values=sorted(values);pos=(len(values)-1)*p;low=int(pos);high=math.ceil(pos)
    return values[low]+(values[high]-values[low])*(pos-low)


def mean(values): return statistics.mean(values) if values else None


def aggregate(rows):
    f=[r for r in rows if r['injected']]; b=[r for r in rows if not r['injected']]
    detected=[r for r in f if r['detected']]; alarms=sum(r['false_alarm'] for r in b)
    localized=[r for r in detected if r['origin_at_alarm']!='UNKNOWN']
    coverage=[ratio(sum(r['detected'] for r in f if r['origin']==o),sum(r['origin']==o for r in f)) for o in ORIGINS]
    loc=[ratio(sum(r['localized_correct'] for r in detected if r['origin']==o),sum(r['origin']==o for r in detected)) for o in ORIGINS]
    result=dict(runs=len(rows),faulty_runs=len(f),benign_runs=len(b),detected=len(detected),
                coverage=ratio(len(detected),len(f)),macro_coverage=mean([v for v in coverage if v is not None]),
                silent_plant=sum(r['silent_plant'] for r in f),benign_false_alarms=alarms,
                benign_false_alarm_rate=ratio(alarms,len(b)),precision=ratio(len(detected),len(detected)+alarms),
                recall=ratio(len(detected),len(f)),latency_median_ms=quantile([r['latency_ms'] for r in detected],.5),
                latency_p95_ms=quantile([r['latency_ms'] for r in detected],.95),
                localization_accuracy=ratio(sum(r['localized_correct'] for r in detected),len(detected)),
                macro_localization_accuracy=mean([v for v in loc if v is not None]),
                localized_precision=ratio(sum(r['localized_correct'] for r in localized),len(localized)),
                unknown_rate=ratio(sum(r['unknown_at_alarm'] for r in detected),len(detected)),
                localized_before_plant=sum(r['localization_before_plant'] for r in f),
                mean_ignorance=mean([r['mean_ignorance'] for r in rows]),mean_conflict=mean([r['mean_conflict'] for r in rows]),
                high_conflict_runs=sum(r['high_conflict_samples']>0 for r in rows),
                preinjection_alarm_runs=sum(r['pre_alarm_samples']>0 for r in f),
                propagation_supported_runs=sum(r['propagation_samples']>0 for r in rows))
    for field in ['control_effect','actuator_effect','plant_manifestation']:
        subset=[r for r in f if r[field]==1]
        result[f'{field}_runs']=len(subset)
        result[f'coverage_given_{field}']=ratio(sum(r['detected'] for r in subset),len(subset))
    return result


def selection_key(s,index):
    return (s['benign_false_alarms'],-(s['macro_coverage'] or 0),s['silent_plant'],
            -(s['localization_accuracy'] or 0),s['latency_median_ms'] if s['latency_median_ms'] is not None else math.inf,
            s['high_conflict_runs'],index)


def summarize(all_rows,out):
    summaries=[];layer=[]
    for partition in ['development-train','development-validation']:
        for method in METHODS:
            rows=[r for r in all_rows if r['partition']==partition and r['method']==method]
            if method=='Timing Monitor': rows=[r for r in rows if r['origin'] in ['NORMAL','TIMING']]
            summary={'partition':partition,'method':method,**aggregate(rows)}
            if method in NONLOCALIZING:
                for k in ['localization_accuracy','macro_localization_accuracy','localized_precision','unknown_rate','mean_ignorance','mean_conflict','high_conflict_runs']: summary[k]=None
            summaries.append(summary)
            for origin in ORIGINS:
                if method=='Timing Monitor' and origin!='TIMING':continue
                layer.append({'partition':partition,'method':method,'origin':origin,**aggregate([r for r in rows if r['origin']==origin])})
    write_csv(out/'clo_dsf_dev_summary.csv',[r for r in summaries if r['method']=='CLO-DSF'])
    write_csv(out/'clo_dsf_baseline_comparison.csv',summaries)
    write_csv(out/'clo_dsf_layer_summary.csv',layer)
    write_csv(out/'clo_dsf_localization_summary.csv',[r for r in summaries if r['method']=='CLO-DSF'])
    write_csv(out/'clo_dsf_ablation.csv',[r for r in summaries if r['partition']=='development-validation' and r['method'] in ['Plain DS','A1 Observability','A2 Propagation','CLO-DSF']])
    val=[r for r in all_rows if r['partition']=='development-validation' and r['method']=='CLO-DSF']
    confusion=[]
    for origin in ORIGINS:
        rows=[r for r in val if r['origin']==origin]
        confusion.append({'true_origin_evaluation_only':origin,**{o:sum((r['origin_at_alarm'] if r['detected'] else 'UNKNOWN')==o for r in rows) for o in [*ORIGINS,'UNKNOWN']},'misses':sum(not r['detected'] for r in rows)})
    write_csv(out/'clo_dsf_origin_confusion.csv',confusion)
    uncertainty=[]
    for part in ['development-train','development-validation']:
        for cohort in ['faulty','benign']:
            rows=[r for r in all_rows if r['method']=='CLO-DSF' and r['partition']==part and bool(r['injected'])==(cohort=='faulty')]
            uncertainty.append(dict(partition=part,cohort=cohort,n=len(rows),mean_ignorance=mean([r['mean_ignorance'] for r in rows]),
                                    ignorance_p05=quantile([r['mean_ignorance'] for r in rows],.05),ignorance_median=quantile([r['mean_ignorance'] for r in rows],.5),
                                    ignorance_p95=quantile([r['mean_ignorance'] for r in rows],.95),mean_conflict=mean([r['mean_conflict'] for r in rows]),
                                    high_conflict_runs=sum(r['high_conflict_samples']>0 for r in rows)))
    write_csv(out/'clo_dsf_uncertainty_summary.csv',uncertainty)
    return summaries,layer,confusion


def run(out=OUTPUT):
    out=Path(out).resolve()
    if out!=OUTPUT.resolve():raise ValueError('Development writes are restricted to the dedicated v7 development directory')
    if (out/'selection_record.json').exists():raise ValueError('Study already selected: do not silently rerun or overwrite development evidence')
    for folder in ['raw','metrics','profiles','traces','commands','figures']: (out/folder).mkdir(parents=True,exist_ok=True)
    subprocess.run(['make'],cwd=ROOT,check=True)
    specs=design(out)
    # Detect duplicate commands before sampling; semantic equivalence is separately audited.
    commands=[command(s,out,'train',out/'initial_config.cfg') for s in specs]
    signatures=[]
    for cmd in commands:
        start=cmd.index('--clo-config')
        signatures.append(tuple(cmd[2:start]))
    if len(signatures)!=len(set(signatures)):raise ValueError('Duplicate physical configurations')
    pre={'study_sha256':sha(STUDY),'protocol_sha256':sha(ROOT/'docs/clo_dsf_development_protocol.md'),
         'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src/v7').glob('*.c'))},
         'partitions':{part:sum(s['partition']==part for s in specs) for part in ['development-train','development-validation']}}
    write_json(out/'preregistered_protocol.json',pre)
    write_runtime_config(out/'initial_config.cfg',candidate(0))
    all_rows=[]
    train=[s for s in specs if s['partition']=='development-train']
    for i,spec in enumerate(train):
        all_rows+=execute(spec,out,'train',out/'initial_config.cfg')
        if i%25==0:print(f'TRAIN {i+1}/{len(train)}',flush=True)
    search=[]
    for i in range(8):
        rows=[r for r in all_rows if r['method']==f'candidate_{i}']
        search.append({'candidate':i,**candidate(i),**aggregate(rows)})
    chosen=min(range(8),key=lambda i:selection_key(search[i],i))
    for row in search: row['selected']=int(row['candidate']==chosen)
    write_csv(out/'clo_dsf_parameter_search.csv',search)
    write_runtime_config(out/'selected_config.cfg',candidate(chosen))
    write_json(out/'selection_record.json',{'selected_candidate':chosen,'parameters':candidate(chosen),
               'criterion':yaml.safe_load(STUDY.read_text())['selection_rule'],'validation_seen':False})
    print(f'SELECTED TRAIN candidate {chosen}: {candidate(chosen)}',flush=True)
    # Selected candidate metrics already executed online on TRAIN. Replace the
    # display's initial default CLO row with those metrics, retaining candidate rows.
    all_rows=[r for r in all_rows if r['method']!='CLO-DSF']+[{**r,'method':'CLO-DSF'} for r in all_rows if r['method']==f'candidate_{chosen}']
    validation=[s for s in specs if s['partition']=='development-validation']
    for i,spec in enumerate(validation):
        all_rows+=execute(spec,out,'validation',out/'selected_config.cfg')
        if i%25==0:print(f'DEVELOPMENT-VALIDATION {i+1}/{len(validation)}',flush=True)
    write_csv(out/'clo_dsf_dev_runs.csv',all_rows)
    summaries,layer,confusion=summarize(all_rows,out)
    from .clo_dsf_reporting import figures,findings
    figures(out,all_rows,summaries,layer,confusion)
    findings(out,all_rows,summaries,chosen)
    print('Development evaluation finished. No final holdout created.',flush=True)
