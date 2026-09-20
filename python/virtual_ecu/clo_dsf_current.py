"""CURRENT in-place development: one group-wise campaign, no parameter search."""
import csv, difflib, gzip, hashlib, json, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path
from .clo_dsf_development import ROOT, ORIGINS, write_csv, sha
from .clo_dsf_candidate2_development import derived, aggregate, NONLOCAL
from .clo_dsf_holdout import command as prior_command, prepare_work, profile_identity, physical, read
from .clo_dsf_final_reporting import wilson
from .cross_layer_safety import summarize_rows, read_rows

OUT = ROOT/'results/clo_dsf_current'
PRECHANGE = 'ee51591d749fbe212cfcf5c0ac95addea96c5549'
METHODS = ['Revised CLO-DSF', 'Pre-change CLO-DSF', 'Weighted Sum']
CONFIG = ROOT/'results/cross_layer_safety_v7_3_dev/revised.cfg'

def design():
    specs = []
    for family, (load, speed, ambient) in enumerate(zip([.43,.59,.71,.86,.53,.93], [71,36,21,105,56,14], [22,29,34,33,27,40])):
        cells = []
        for bit in range(5):
            for polarity in [0,1]:
                for behavior in ['transient','intermittent','permanent']:
                    cells.append(('MEMORY','stuck_bit',behavior,bit,polarity))
        for bit in [0,1]:
            for behavior in ['transient','intermittent','permanent']:
                cells.append(('MEMORY','bit_flip',behavior,bit,0))
        models = {
            'SENSOR_CONTROL': {'sensor_bias':[-1.2,1.2,4.6,8.9], 'sensor_interface_intermittent':[.5,1.5,4.1,8.1]},
            'COMMUNICATION': {'delayed_update':[100,200,500], 'dropped_update':[1,3,7], 'replayed_sample':[100,300,1300]},
            'ACTUATOR': {'pump_degraded':[.968,.69], 'fan_stuck_off':[0,0]},
            'TIMING': {'deadline_miss':[0], 'task_delay':[500]},
        }
        for origin, subtypes in models.items():
            for model, magnitudes in subtypes.items():
                for behavior in ['transient','intermittent','permanent']:
                    cells += [(origin,model,behavior,m,0) for m in magnitudes]
        cells += [('NORMAL','baseline','none',0,0)]*18
        for j, (origin,model,behavior,magnitude,polarity) in enumerate(cells):
            profile = [dict(start_ms=a,end_ms=b,vehicle_speed_kph=speed*f,engine_load=(load+j*.00017)*f,ambient_temp_c=ambient+j*.003,external_airflow_factor=0,road_slope_percent=0) for a,b,f in [(0,18100,.69),(18100,49300,1),(49300,87100,.83),(87100,120000,.95)]]
            updates = [[30000,99],[60000,92]] if (j+family)%2 else []
            s = dict(run_id=f'current_{len(specs):04}',origin=origin,model=model,behavior=behavior,magnitude=magnitude,stuck_polarity=polarity,
                     start_ms=120100 if origin=='NORMAL' else 24700+(j%8)*300,
                     duration_ms=100 if model=='deadline_miss' and behavior=='transient' else [9700,13700,18500][j%3],
                     group=f'operating_family_{family}',partition='development-train' if family<4 else 'development-validation',
                     profile=f'current_profile_{len(specs):04}',profile_json=json.dumps(profile,sort_keys=True),
                     target_updates_json=json.dumps(updates),workload='authorized_updates' if updates else 'static_target',
                     seed=1201+family*137+j,simulation_duration_ms=120000)
            s['sensor_variation']=(['0:0:6000','0.02:0:6000','0.05:0:6000','0.10:0:6000','0.02:0.6:12000','0.05:1.2:18000'][(j-105)//3] if origin=='NORMAL' else '0:0:6000')
            s['profile_semantic_sha256']=profile_identity(profile)
            s['configuration_sha256']=hashlib.sha256(json.dumps([physical(s,s['profile_semantic_sha256']),updates,polarity,s['sensor_variation']],sort_keys=True).encode()).hexdigest()
            s['initially_latent_stuck']=int(model=='stuck_bit' and ((92>>int(magnitude))&1)==polarity)
            specs.append(s)
    assert len(specs)==738 and len({s['configuration_sha256'] for s in specs})==738
    assert not {s['group'] for s in specs if s['partition']=='development-train'} & {s['group'] for s in specs if s['partition']=='development-validation'}
    return specs

def build_prechange(work, prechange_source):
    source=Path(prechange_source).read_text()
    for symbol in ['clo_revised_init','clo_revised_extract','clo_revised_step']:
        source=source.replace(symbol,symbol.replace('clo_revised','clo_prechange'))
    source=source.replace('"../v7_2/clo_dsf_final.c"',json.dumps(str(ROOT/'src/v7_2/clo_dsf_final.c')))
    path=work/'prechange.c';path.write_text(source);obj=work/'prechange.o'
    subprocess.run(['gcc','-std=c11','-O2','-I'+str(ROOT/'include'),'-c',str(path),'-o',str(obj)],check=True)
    subprocess.run(['make','-f','clo_dsf_revised.mk','-j4',f'CURRENT_BASELINE_OBJ={obj}'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    return obj

def command(s,work):
    cmd=prior_command(s,work)
    for key,value in {'--intermittent-on-ms':500,'--intermittent-off-ms':900,'--drop-every-n-updates':11}.items():
        if key in cmd:cmd[cmd.index(key)+1]=str(value)
    for ms,value in json.loads(s['target_updates_json']):cmd+=['--revised-target-update',f'{ms}:{value}']
    cmd+=['--revised-sensor-variation',s.get('sensor_variation','0:0:6000')]
    return cmd

def prepare(specs,work):
    prepare_work(work,specs)
    objects=[str(p) for p in sorted((ROOT/'src').glob('*.o')) if p.name!='main.o']
    exe=work/'check'
    subprocess.run(['gcc','-std=c11','-Iinclude','tests/holdout_configuration_check.c',*objects,'-o',str(exe)],cwd=ROOT,check=True)
    for s in specs:
        cmd=command(s,work)
        p=subprocess.run([str(exe),*cmd[2:]],capture_output=True,text=True)
        if p.returncode:raise ValueError(s['run_id']+': '+p.stderr)
        if 'custom_multi' in cmd:assert s['start_ms']+2*s['duration_ms']+1100<120000
    prior_profiles=set()
    for folder,manifest in [('cross_layer_safety_v7_dev','development_split_manifest.csv'),('cross_layer_safety_v7_1_dev','development_split_manifest.csv'),('cross_layer_safety_v7_2_confirmation','confirmation_configuration_manifest.csv'),('cross_layer_safety_v7_3_dev','development_split_manifest.csv')]:
        root=ROOT/'results'/folder
        for name in {r['profile'] for r in read(root/manifest)}:prior_profiles.add(profile_identity(read(root/'profiles'/f'{name}.csv')))
    for r in read(ROOT/'results/cross_layer_safety_v8_final_holdout/final_holdout_manifest.csv'):prior_profiles.add(r['profile_semantic_sha256'])
    assert not prior_profiles & {s['profile_semantic_sha256'] for s in specs}

def execute(s,work,retain):
    cmd=command(s,work);p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(s['run_id']+': '+p.stderr)
    raw=Path(cmd[1]);summary=summarize_rows(read_rows(raw))
    trace=read(work/'trace.csv')
    observations=read(work/'observations.csv');assert len(trace)==len(observations)
    first_consumption=-1;first_sensor=-1;first_any=-1;max_sensor=0
    for x,o in zip(trace,observations):
        now=int(x['time_ms']);assert now==int(o['time_ms'])
        if now<s['start_ms']:continue
        if first_consumption<0 and int(x['source_valid']) and int(x['source_ms'])==now and int(o['control_execution_ms'])==now and int(o['sample_expected_period_ms'])>0 and int(o['sample_timestamp_ms'])<int(x['source_ms']):first_consumption=now
        value=float(x['sensor_control_evidence']);max_sensor=max(max_sensor,value)
        if first_sensor<0 and value>0:first_sensor=now
        if first_any<0 and any(float(x[k+'_evidence'])>0 for k in ['timing','communication','memory_control','sensor_control','actuator','plant']):first_any=now
    # Post-hoc effect categorization, never passed to inference.
    effective=[r for r in trace if int(r['time_ms'])>=s['start_ms'] and int(r['target_register_c'])!=int(r['target_shadow_c'])]
    base={k:v for k,v in s.items() if k not in ['profile_json','target_updates_json']}
    base['effective_memory_corruption']=int(bool(effective)) if s['origin']=='MEMORY' else 0
    base['first_integrity_mismatch_ms']=int(effective[0]['time_ms']) if effective else -1
    base.update(first_consumption_mismatch_ms=first_consumption,first_sensor_residual_ms=first_sensor,first_positive_feature_ms=first_any,max_sensor_strength=max_sensor)
    base['raw_sha256']=sha(raw);base['runtime_trace_sha256']=sha(work/'trace.csv')
    result=[]
    for row in read(work/'metrics.csv'):
        if row['method'] not in METHODS:continue
        r={**base,**row}
        for k in row:
            if k not in ['method','origin_at_alarm','leading_at_alarm','first_origin']:r[k]=float(row[k]) if k.startswith(('mean_','origin_')) else int(row[k])
        r.update(injected=int(s['origin']!='NORMAL'))
        r['detected']=int(r['injected'] and r['first_post_alarm_ms']>=0)
        r['false_alarm']=int(not r['injected'] and r['first_alarm_ms']>=0)
        r['latency_ms']=r['first_post_alarm_ms']-s['start_ms'] if r['detected'] else None
        r['integrity_latency_ms']=r['first_post_alarm_ms']-base['first_integrity_mismatch_ms'] if r['detected'] and effective else None
        for k in ['control_effect','actuator_effect','plant_manifestation','propagation_plant_ms','propagation_control_ms','propagation_actuator_command_ms']:r[k]=summary[k]
        r['silent_plant']=int(r['injected'] and r['plant_manifestation']==1 and not r['detected'])
        r['wrong_localized_runtime_samples']=sum(r['alarm_'+o] for o in ORIGINS if o!=s['origin']) if r['method'] not in NONLOCAL else 0
        first=first_consumption if s['origin']=='COMMUNICATION' else first_sensor if s['origin']=='SENSOR_CONTROL' else first_any
        r['miss_category']=''
        if r['injected'] and not r['detected']:
            r['miss_category']='C' if first<0 else 'B' if r['propagation_plant_ms'] is not None and first>r['propagation_plant_ms'] else 'A'
        derived(r);result.append(r)
    if retain:
        with gzip.GzipFile(filename='',mode='wb',fileobj=(OUT/(s['run_id']+'_trace.csv.gz')).open('wb'),mtime=0) as f:f.write((work/'trace.csv').read_bytes())
    for path in [raw,raw.with_name(raw.stem+'_summary.csv'),work/'trace.csv',work/'observations.csv',work/'metrics.csv']:path.unlink()
    return result

def summarize(rows):
    comparisons=[];layers=[];memory=[];confusion=[]
    for part in ['development-train','development-validation']:
        for method in METHODS:
            selected=[r for r in rows if r['partition']==part and r['method']==method and (method!='Timing Monitor' or r['origin']=='TIMING')]
            for workload in ['all','static_target','authorized_updates']:
                subset=[r for r in selected if workload=='all' or r['workload']==workload]
                stats=aggregate(subset)
                stats['wrong_localized_runtime_samples']=sum(r['wrong_localized_runtime_samples'] for r in subset)
                stats['wrong_localized_runtime_cases']=sum(r['wrong_localized_runtime_samples']>0 for r in subset)
                stats['detection_ci_low'],stats['detection_ci_high']=wilson(stats['detected'],stats['faulty_runs'])
                comparisons.append(dict(partition=part,method=method,workload=workload,**stats))
            for origin in ORIGINS:
                if method=='Timing Monitor' and origin!='TIMING':continue
                subset=[r for r in selected if r['origin']==origin]
                layers.append(dict(partition=part,method=method,origin=origin,**aggregate(subset)))
                if method not in NONLOCAL:
                    confusion.append(dict(partition=part,method=method,origin=origin,**{o:sum(r['detected'] and r['origin_at_alarm']==o for r in subset) for o in ORIGINS+['UNKNOWN']},misses=sum(not r['detected'] for r in subset)))
            for latent in [0,1]:
                for effective in [0,1]:
                    subset=[r for r in selected if r['origin']=='MEMORY' and r['initially_latent_stuck']==latent and r['effective_memory_corruption']==effective]
                    memory.append(dict(partition=part,method=method,initially_latent_stuck=latent,effective_corruption=effective,**aggregate(subset)))
    write_csv(OUT/'comparison.csv',comparisons);write_csv(OUT/'origin_summary.csv',layers)
    write_csv(OUT/'memory_summary.csv',memory);write_csv(OUT/'confusion_matrix.csv',confusion)
    write_csv(OUT/'localization_summary.csv',[r for r in comparisons if r['method'] not in NONLOCAL])
    write_csv(OUT/'case_summary.csv',rows)

def run(prechange_source, replace_current=False):
    OUT.mkdir(exist_ok=True)
    prior_profiles=set()
    if (OUT/'configuration_manifest.csv').exists():
        if not replace_current:raise ValueError('Use --replace-current to rebuild CURRENT results')
        prior_profiles={r['profile_semantic_sha256'] for r in read(OUT/'configuration_manifest.csv')}
    baseline=Path(prechange_source).read_text()
    specs=design()
    with tempfile.TemporaryDirectory(prefix='clo-current-campaign-') as temporary:
        work=Path(temporary);build_prechange(work,prechange_source);prepare(specs,work)
        assert not prior_profiles & {s['profile_semantic_sha256'] for s in specs}
        if replace_current:
            for artifact in OUT.iterdir():
                if not artifact.is_file():raise ValueError('Unexpected result subdirectory; refuse deletion')
            for artifact in OUT.iterdir():artifact.unlink()
        write_csv(OUT/'configuration_manifest.csv',specs)
        identities={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/v7_3/clo_dsf_revised.c',ROOT/'src/v7_3/revised_runtime.c',ROOT/'src/sensors.c',ROOT/'src/control.c',ROOT/'src/runtime_observation.c',ROOT/'include/runtime_observation.h',ROOT/'include/ecu_types.h',ROOT/'include/clo_dsf_revised.h',CONFIG,Path(__file__),OUT/'configuration_manifest.csv']}
        (OUT/'validation_record.md').write_text('# CURRENT development validation record\n\nRegistered before outcomes: '+datetime.now(timezone.utc).isoformat()+'\n\n738 unique simulations; 492 TRAIN / 246 VALIDATION, disjoint operating families. All public C configurations validated. Zero profile/configuration overlap with previous development and holdout. No tuning or parameter search. Same physics stream for every observer. No accumulator selected: replay found no sustained bias discrepancy. Detector bytes identical to pre-change. Benign alternating jitter up to 0.10 C and triangular drift up to 1.2 C; no transport faults combined with variation. Temporary pre-change CURRENT core SHA256 '+hashlib.sha256(baseline.encode()).hexdigest()+'.\n\nProtocol: [current runtime evidence](../../docs/clo_dsf_current.md).\n\nPre-execution identities:\n```json\n'+json.dumps(identities,indent=2)+'\n```\n')
        reverse_patch=''.join(difflib.unified_diff((ROOT/'src/v7_3/clo_dsf_revised.c').read_text().splitlines(True),baseline.splitlines(True),fromfile='current.c',tofile='prechange.c'))
        with (OUT/'validation_record.md').open('a') as f:
            f.write('\nPre-change CURRENT reconstruction patch (apply to the recorded current source in temporary storage; no maintained duplicate):\n```diff\n'+reverse_patch+'```\n')
        rows=[]
        # Fixed representative selection: six origins plus two memory configurations.
        retain={next(s['run_id'] for s in specs if s['origin']==o) for o in ORIGINS+['NORMAL']}
        retain.update(next(s['run_id'] for s in specs if s['group']==f'operating_family_{family}' and s['model']=='fan_stuck_off') for family in [4,5])
        for part in ['development-train','development-validation']:
            assert all(sha(ROOT/k)==v for k,v in identities.items())
            selected=[s for s in specs if s['partition']==part]
            for i,s in enumerate(selected):
                rows+=execute(s,work,s['run_id'] in retain)
                if i%25==0:print(f'{part}: {i+1}/{len(selected)}',flush=True)
            summarize(rows)
            if part=='development-train':
                current=[r for r in rows if r['method']=='Revised CLO-DSF']
                before=[r for r in rows if r['method']=='Pre-change CLO-DSF']
                assert not any(r['false_alarm'] or r['wrong_localized_runtime_samples'] for r in current),'TRAIN rejects benign/localization regression'
                for origin in ['COMMUNICATION','SENSOR_CONTROL']:
                    assert sum(r['detected'] for r in current if r['origin']==origin)>=sum(r['detected'] for r in before if r['origin']==origin),'TRAIN detection regression: '+origin
                assert all(r['detected'] for r in current if r['origin']=='MEMORY' and r['effective_memory_corruption'])
                assert not any(r['detected'] for r in current if r['origin']=='MEMORY' and r['initially_latent_stuck'] and not r['effective_memory_corruption'])
                with (OUT/'validation_record.md').open('a') as f:f.write('\nTRAIN gate PASS: unchanged detector preserves detections; no benign alarm, wrong origin, effective-memory miss or dormant alarm. Proceed with unchanged settings.\n')
            with (OUT/'validation_record.md').open('a') as f:f.write(f'\n{part}: {len(selected)} simulations complete; no source/config change or tuning.\n')
        assert all(sha(ROOT/k)==v for k,v in identities.items())
    print('CURRENT campaign complete.',flush=True)
