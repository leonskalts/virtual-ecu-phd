"""One-command checks and isolated replay of accepted research evidence."""
from __future__ import annotations

import json
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .final_evidence import (ROOT, V5, OUTPUT, read_lock, safe_output, sha256, records,
                            verify_frozen, write_json, artifact_manifest, verify_artifact_manifest)
from .final_reporting import generate, validate_traceability


def checked(command, log=None):
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        Path(log).write_text(process.stdout + process.stderr)
    if process.returncode:
        raise RuntimeError(f'Command failed: {command}\n{process.stdout}\n{process.stderr}')
    return process.stdout + process.stderr


def relocate(command, destination):
    """Rebase archived absolute repository paths and replace every output path."""
    old_root = str(Path(command[0]).parent)
    result = [str(ROOT) + arg[len(old_root):] if arg.startswith(old_root + '/') else arg for arg in command]
    result[0] = str(ROOT / 'virtual_ecu')
    result[1] = str(destination)
    if '--scheduler-events' in result:
        result[result.index('--scheduler-events')+1] = str(destination.with_name(destination.stem+'_events.csv'))
    return result


def representative_replay(out):
    manifest = records(V5 / 'v5_run_manifest.csv')
    predicates = [
        lambda r: r['scheduler_workload'] == 'legal' and json.loads(r['stress_configuration'])['execution_ms'] == 0,
        lambda r: r['scheduler_workload'] == 'legal' and json.loads(r['stress_configuration'])['execution_ms'] == 98,
        lambda r: r['scheduler_workload'] == 'legal' and json.loads(r['stress_configuration'])['execution_ms'] == 100,
        lambda r: r['scheduler_workload'] == 'overload',
        lambda r: r['configured_model'] == 'task_delay',
        lambda r: r['configured_model'] == 'delayed_update' and r['policy'] == 'graded',
        lambda r: r['configured_model'] == 'stuck_bit',
        lambda r: r['configured_model'] == 'pump_degraded',
    ]
    selected = [next(r for r in manifest if predicate(r)) for predicate in predicates]
    destination = out / 'validation/quick_runs'
    destination.mkdir(parents=True, exist_ok=True)
    for row in selected:
        original = V5 / 'raw' / Path(row['raw_csv']).name
        target = destination / original.name
        checked(relocate(json.loads(row['command']), target))
        for suffix in ['', '_summary', '_events']:
            old = original.with_name(original.stem + suffix + '.csv')
            new = target.with_name(target.stem + suffix + '.csv')
            if old.exists() and (not new.is_file() or sha256(old) != sha256(new)):
                raise ValueError('Representative trace mismatch: '+old.name)
    return [r['run_id'] for r in selected]


def analysis(out, verify=True):
    out = safe_output(out)
    if verify:
        print('Verifying immutable accepted source and evidence hashes...', flush=True)
        verify_frozen()
    generate(out)
    print('Indexing accepted evidence in place and hashing final artifacts...', flush=True)
    manifest = artifact_manifest(out)
    count = verify_artifact_manifest(out)
    validate_traceability(out)
    write_json(out/'validation/analysis_check.json', {'status':'PASS','claims':13,'paper_tables':5,'paper_figures':4,
               'indexed_artifacts':count,'accepted_evidence_modified':False,
               'source':'Frozen accepted evidence, no simulation or host benchmark rerun'})
    return manifest


def quick(out):
    out = safe_output(out)
    (out/'validation').mkdir(parents=True,exist_ok=True)
    checked(['make'], out/'validation/quick_build.log')
    checked([sys.executable,'-m','unittest','discover','-s','tests'],out/'validation/quick_tests.log')
    print('Build and test suite passed. Verifying accepted evidence...',flush=True)
    frozen = verify_frozen()
    selected = representative_replay(out)
    # Bootstrap a missing local report; never require generated files in Git.
    if not (out/'manifests/artifact_manifest.csv').exists():
        analysis(out,verify=False)
    else:
        validate_traceability(out)
        verify_artifact_manifest(out)
    write_json(out/'validation/quick_check.json', {'status':'PASS','representative_runs':selected,
                'frozen':frozen,'build':'PASS','tests':'PASS','claim_sources':'PASS','artifact_manifest':'PASS'})
    print(f'Quick check passed: {len(selected)} deterministic representative replays, tests and manifest/claim checks.',flush=True)


def legacy_regression(out):
    """Compile the accepted C tree, then compare all 48 legacy configurations."""
    destination=Path(out)/'validation/legacy';destination.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vecu-v6-baseline-') as temporary:
        baseline=Path(temporary);(baseline/'src').mkdir();(baseline/'include').mkdir()
        commit=read_lock()['baseline_commit']
        for name in read_lock()['source_sha256']:
            if name.startswith(('src/','include/')) and name.endswith(('.c','.h')):
                (baseline/name).write_bytes(subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=ROOT))
        exe=baseline/'virtual_ecu'
        checked(['gcc','-std=c11','-O2','-I'+str(baseline/'include'),*[str(p) for p in sorted((baseline/'src').glob('*.c'))],'-o',str(exe)])
        detectors=['builtin_ecu','threshold','ewma','cusum','thermal_observer','kalman_filter','adaptive_kalman_filter','hybrid_adaptive_kalman']
        models={'baseline':None,'sensor_bias':'6','stale_sensor_data':'500','pump_degraded':'.4','fan_stuck_off':'0','calibration_memory_corruption':'16'}
        for model,parameter in models.items():
            for detector in detectors:
                args=['baseline'] if model=='baseline' else ['custom',model,'45000','10000','transient',parameter]
                old=baseline/f'{model}_{detector}.csv';new=destination/old.name
                for executable,path in [(exe,old),(ROOT/'virtual_ecu',new)]:
                    checked([str(executable),str(path),*args,'--detector',detector])
                for suffix in ['', '_summary']:
                    if sha256(old.with_name(old.stem+suffix+'.csv'))!=sha256(new.with_name(new.stem+suffix+'.csv')):
                        raise ValueError('Legacy regression mismatch: '+new.name)
    write_json(destination/'verification.json',{'status':'PASS','cases':48,'comparison':'Raw and C summary bytes against compiled accepted commit '+commit})
    return 48


def rtl_regression(out):
    destination=Path(out)/'validation/rtl'
    checked([sys.executable,'scripts/run_rtl_hardware_trojan_study.py','--output-dir',str(destination)],Path(out)/'validation/rtl.log')
    accepted=ROOT/'results/rtl_hardware_trojan_study_v1'
    old=records(accepted/'detector_comparison.csv');new=records(destination/'detector_comparison.csv')
    if len(old)!=64 or len(new)!=64:raise ValueError('Expected 64 RTL cases')
    for left,right in zip(old,new):
        for key in left:
            if key not in ['raw_csv','summary_csv'] and left[key]!=right[key]:raise ValueError('RTL metric mismatch: '+key)
        for key in ['raw_csv','summary_csv']:
            # Archived result paths can refer to a prior checkout location.
            a=accepted/'raw'/Path(left[key]).name;b=destination/'raw'/Path(right[key]).name
            compare_historical_csv(a,b)
    write_json(destination/'verification.json',{'status':'PASS','cases':64,'HT1':'unchanged','HT2':'unchanged','HT3':'unchanged','HT4':'unchanged',
               'comparison':'Every historical raw/C-summary field identical; current schema appends cross-layer columns. All comparison metrics identical excluding relocated paths.'})
    return 64


def compare_historical_csv(accepted,current):
    """Preserve all historical strings and rows; explicitly allow appended fields."""
    with Path(accepted).open(newline='') as a, Path(current).open(newline='') as b:
        left=csv.DictReader(a);right=csv.DictReader(b)
        if not set(left.fieldnames)<=set(right.fieldnames):raise ValueError('Historical CSV columns removed')
        from itertools import zip_longest
        for index,(x,y) in enumerate(zip_longest(left,right)):
            if x is None or y is None or any(y.get(k)!=v for k,v in x.items()):
                raise ValueError(f'Historical CSV value mismatch: {accepted}, row {index}')


def full(out):
    out=safe_output(out)
    print('FULL executes many simulations: 1,869 v5 study/reference runs, 48 paired legacy cases and 64 RTL cases. Accepted evidence remains read-only.',flush=True)
    checked(['make'])
    verify_frozen()
    legacy_regression(out);rtl_regression(out)
    from .validation_v5_runner import run
    from .validation_v5_recovery import run_recovery
    from .validation_v5_design import load_config
    from .validation_v5_report import write_package
    destination=out/'full_reproduction/v5'
    rows,ablations=run(destination,resume=False)
    run_recovery(destination,load_config(),resume=False)
    # A repeat does not replace the accepted host measurement with a new noisy value.
    shutil.copyfile(V5/'monitor_overhead_summary.csv',destination/'monitor_overhead_summary.csv')
    write_package(destination,rows,ablations)
    accepted=json.loads((V5/'raw_sha256.json').read_text())
    for name,digest in accepted.items():
        if sha256(destination/name)!=digest:raise ValueError('Full v5 raw mismatch: '+name)
    outputs=['timing_holdout_summary.csv','timing_ablation_holdout.csv','timing_benign_summary.csv',
             'communication_policy_summary.csv','cross_layer_holdout_summary.csv','stuck_dynamic_matched_comparison.csv',
             'intervention_cost_summary.csv','statistical_confidence_summary.csv','recovery_horizon_analysis.csv']
    for name in outputs:
        actual=(destination/name).read_bytes().replace(str(destination).encode(),str(V5).encode())
        if actual!=(V5/name).read_bytes():raise ValueError('Full v5 analysis mismatch: '+name)
    write_json(out/'validation/full_check.json',{'status':'PASS','v5_simulations':1869,'raw_csv_hashes':len(accepted),
               'legacy_cases':48,'rtl_cases':64,'host_benchmark':'Accepted measurement retained; not re-collected',
               'scientific_metrics':'Unchanged'})
    analysis(out)
