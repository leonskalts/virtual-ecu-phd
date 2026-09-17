#!/usr/bin/env python3
"""One-time conditional candidate packaging; creates no holdout scenarios."""
import csv
import hashlib
import json
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/cross_layer_safety_v7_dev'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')

def freeze():
    if (OUT/'clo_dsf_candidate_config.json').exists():raise ValueError('Candidate already frozen; do not overwrite')
    gate=json.loads((OUT/'development_gate.json').read_text())
    assert gate['development_gate_pass'],'Development continuation gate failed'
    regression=json.loads((OUT/'scientific_regression.json').read_text())
    assert regression['legacy_cases']==48 and regression['rtl_cases']==64
    assert regression['all_preexisting_result_files_unchanged']==16352
    for folder in ['gui_v62','gui_v7']:
        assert json.loads((OUT/f'validation/{folder}/desktop_checks.json').read_text())['status']=='PASS'
    tests=(OUT/'validation/complete_tests.log').read_text()
    assert tests.rstrip().endswith('OK')
    selection=json.loads((OUT/'selection_record.json').read_text())
    assert selection['validation_seen'] is False
    channels=[
        {'name':'timing','subset':['TIMING'],'class':'DIRECT','transform':'max(deadline_exceeded,missed_expected_execution,completion_after_release_deadline,clip((execution_age-period-deadline)/period))'},
        {'name':'communication','subset':['COMMUNICATION'],'class':'DIRECT','transform':'1 on freshness failure or backward received timestamp; else clip((sample_age-300)/300); future timestamp unavailable'},
        {'name':'memory_control','subset':['MEMORY'],'class':'DIRECT','transform':'clip(abs(active_target-92)/4)'},
        {'name':'sensor_control','subset':['COMMUNICATION','SENSOR_CONTROL'],'class':'INDIRECT','transform':'max(outside [-40,150],clip((abs(measured_delta)-2.5*dt_seconds)/2))'},
        {'name':'actuator','subset':['ACTUATOR'],'class':'DIRECT','transform':'clip(max(abs(fan_command-fan_actual)/0.25,abs(pump_command-pump_actual)/0.20))'},
        {'name':'plant','subset':['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR'],'class':'INDIRECT','transform':'clip((measured_temperature-108)/7)'},
    ]
    atoms=['NORMAL','MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR']
    mapping=[]
    for channel in channels:
        for origin in atoms:
            mapping.append({'channel':channel['name'],'hypothesis':origin,'observability':channel['class'] if origin in channel['subset'] else 'NOT_APPLICABLE'})
    for channel in ['independent_true_temperature_residual','injector_packet_provenance','reference_propagation']:
        for origin in atoms:mapping.append({'channel':channel,'hypothesis':origin,'observability':'UNAVAILABLE'})
    with (OUT/'runtime_observability_mapping.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['channel','hypothesis','observability']);writer.writeheader();writer.writerows(mapping)
    config={'schema_version':7,'status':'FROZEN DEVELOPMENT CANDIDATE — NOT FINAL HOLDOUT',
            'baseline_commit':'d757539df55ca5e93fe45c810d3e2c5d6fdf547b','candidate_index':selection['selected_candidate'],
            'parameters':selection['parameters'],'frame':{name:1<<i for i,name in enumerate(atoms)},'theta_mask':63,
            'abnormal_subset_mask':62,'channels':channels,
            'normal_absence':'m(NORMAL)=0.5*(1-max evidence) only when every channel is available; remainder ignorance',
            'combination_order':[c['name'] for c in channels]+['joint_normal','discounted_previous_state'],
            'propagation_edges':{c:targets for c,targets in [('timing',['sensor_control','actuator','plant']),('communication',['sensor_control','actuator','plant']),('memory_control',['sensor_control','actuator','plant']),('sensor_control',['actuator','plant']),('actuator',['plant']),('plant',[])]},
            'propagation_active_threshold':.5,'propagation_condition':'Both current episodes active; strict upstream onset < downstream onset <= now; now-upstream_onset <= window. Same-time, recovered, future, expired or reversed episodes receive no bonus.',
            'propagation_modulation':'Upstream reliability times (1+bonus), capped at 1, once regardless of edge count',
            'temporal_cadence_ms':100,'decision_score':'Bel(abnormal_subset)',
            'states':['NORMAL','SUSPECT','CONFIRMED'],'persistence':'Consecutive samples above confirmed threshold; reset below; recover immediately',
            'localization':'Confirmed only; top abnormal singleton BetP and top-minus-second margin and maximum ignorance gate. Else UNKNOWN; not Bayesian probability.',
            'unavailable_evidence':'Vacuous; nonfinite or invalid runtime channel inputs give zero reliability',
            'conflict_summary':'Maximum pairwise K per timestep, with all eight K values logged','high_conflict_threshold':.5,
            'dempster_total_conflict_epsilon':1e-12,'dempster_total_conflict_action':'Flagged vacuous fallback; log K',
            'simple_or':{'threshold':.5,'persistence':1},'weighted_sum':{'weights':[1/6]*6,'threshold':.5,'persistence':1},
            'continuation_rationale':'Preregistered gate passed; 0/96 validation benign alarms, 63.33% macro coverage, 100% localized precision; supports testing abstention/uncertainty, NOT alarm superiority. OR/plain DS coverage are higher and propagation has no measured coverage gain.',
            'study_unique_physical_configurations':896,'study_configured_simulations':912,
            'configuration_requirement':'Frozen candidate requires --clo-config results/cross_layer_safety_v7_dev/clo_dsf_candidate.cfg. Unconfigured C defaults remain exploratory candidate 0; never equate them with frozen candidate 1.'}
    write(OUT/'clo_dsf_candidate_config.json',config)
    shutil.copyfile(OUT/'selected_config.cfg',OUT/'clo_dsf_candidate.cfg')
    gate['regression_pending']=False;gate['frozen']=True;write(OUT/'development_gate.json',gate)
    files=[*sorted((ROOT/'src/v7').glob('*.c')),ROOT/'include/clo_dsf.h',ROOT/'include/ds_evidence.h',
           ROOT/'src/main.c',ROOT/'src/scheduler.c',ROOT/'src/runtime_observation.c',ROOT/'include/runtime_observation.h',
           ROOT/'include/runtime_timing_observation.h',ROOT/'include/config.h',ROOT/'GNUmakefile',
           ROOT/'studies/clo_dsf_development_v1.yaml',ROOT/'studies/cross_layer_final_evidence_lock.json',
           ROOT/'docs/clo_dsf_development_protocol.md',ROOT/'docs/clo_dsf_algorithm.md',
           OUT/'runtime_observability_mapping.csv',OUT/'clo_dsf_candidate_config.json',OUT/'clo_dsf_candidate.cfg',
           OUT/'selected_config.cfg',OUT/'development_split_manifest.csv',OUT/'selection_record.json',
           ROOT/'python/virtual_ecu/clo_dsf_development.py',ROOT/'scripts/audit_clo_dsf_development.py']
    manifest={'algorithm_parameters_may_change':False,'holdout_created':False,
              'sha256':{str(p.relative_to(ROOT)):sha(p) for p in files}}
    write(OUT/'clo_dsf_candidate_hashes.json',manifest)
    table='\n'.join(f'| `{p}` | `{h}` |' for p,h in manifest['sha256'].items())
    contract=f'''# CLO-DSF frozen candidate contract

Candidate 1 is frozen for the **next, independent holdout task**. No holdout dataset
or configuration was created here. This is a development candidate, not accepted
final safety evidence or a claim of superior detection. Do not change parameters,
mappings, sample cadence, mass rule, propagation graph, decision or localization
logic after this contract. Any such change invalidates this candidate identity.

## Required execution

```
make
python3 scripts/verify_clo_dsf_candidate.py
./virtual_ecu_v7 /tmp/example.csv baseline --detector clo_dsf --detector-action observe_only --clo-config results/cross_layer_safety_v7_dev/clo_dsf_candidate.cfg
```

The C convenience defaults are exploratory candidate 0 (Yager). The explicit CFG
above is mandatory for frozen candidate 1 (Dempster). The JSON and CFG parameters
are cross-checked by the verification script. The final legacy evidence lock must
also pass `virtual_ecu.final_evidence.verify_frozen()` before any future study.

## Frozen numerical parameters

```json
{json.dumps(selection['parameters'],indent=2,sort_keys=True)}
```

The full machine-readable contract is
`results/cross_layer_safety_v7_dev/clo_dsf_candidate_config.json`. It records every
evidence transform, subset, absence source, observability class, propagation edge,
activation threshold, cap, temporal cadence, confirmation/localization rule and
conflict fallback. Exact mathematical operations and pseudocode are in
`docs/clo_dsf_algorithm.md`; the static runtime map is in `clo_observability.c` and
its hashed CSV. No injector metadata or reference propagation is a detector input.

## Development justification and limitations

Training selected candidate 1 before validation. Validation: 152/240 detected,
0/96 benign false alarms; 110/166 plant-propagating faults detected, 56 silent;
136/152 correct origin estimates at first alarm, 16 UNKNOWN, zero wrong identified
origins. Sensor/control localization remains unresolved. Macro coverage 63.33%
trails OR (81.67%) and plain DS (65.00%); propagation changes no binary decisions.
There are 152 validation cases with at least one high-conflict step, which
is recorded instead of hidden (this cohort is not identical to the detected cohort). These findings justify testing abstention and
uncertainty on unseen data under the preregistered gate, NOT claiming a coverage
improvement over simple fusion. Weighted Sum is an uncalibrated strict baseline.

The study has 912 configuration executions, 896 distinct physical configurations:
16 redundant TRAIN deadline settings were disclosed in the semantic audit. There
are no equivalent VALIDATION configurations; deduplicated TRAIN selects the same
candidate. No repeated configurations are independent statistical evidence.
TRAIN sidecars show exploratory candidate 0; selected TRAIN candidate-1 scores
come from its actual online C bank. VALIDATION sidecars use frozen candidate 1.

Regression: 48 legacy cases, 64 RTL cases, 141 accepted source/configuration hashes,
5,866 accepted evidence-lock entries and all 16,352 pre-existing result files stay
unchanged. Hybrid/Timing Monitor/HETIA/HT1–HT4 are not retuned. Runtime integration
is additive; GUI labels mark the detector experimental and Hybrid remains default.
Host cost is in `clo_dsf_overhead.json`; embedded WCET claim: NONE.

## SHA-256 identity

| Artifact | SHA-256 |
|---|---|
{table}

All changes are intentionally unstaged. No commit or push was performed.
'''
    (ROOT/'docs/clo_dsf_frozen_candidate_contract.md').write_text(contract)
    print('Frozen candidate 1:',len(files),'hashes')
if __name__=='__main__':freeze()
