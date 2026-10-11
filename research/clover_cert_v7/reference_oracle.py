#!/usr/bin/env python3
"""Exhaustive bounded component model; no physical certification or production imports."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ORIGINS = ('memory', 'timing', 'communication', 'sensor', 'actuator')
TIMES = tuple(range(0, 401, 100))
# All are published runtime fields. No labels, truth, reference trajectories, or tainted outputs.
VALUES = ('coolant_measured_c', 'pump_command', 'pump_actual')
STAMP = VALUES + ('sample_timestamp_ms', 'sample_age_ms', 'sample_freshness_ok')
FULL = STAMP + ('target_register_c', 'target_shadow_c', 'target_shadow_valid',
                'control_target_c', 'control_execution_ms', 'source_c', 'source_ms', 'source_valid')
POLICIES = {'values_100': (VALUES, 100), 'timestamp_100': (STAMP, 100),
            'full_100': (FULL, 100), 'full_200': (FULL, 200)}
CONTEXTS = {'zero_command': 60.0, 'positive_command': 92.0}
BASE_ASSUMPTIONS = ['M_CLOSED', 'M_CONTEXT', 'M_PHASE', 'M_NUMERIC', 'A_PROCESS', 'A_BUILD', 'A_FAULTSET', 'A_CLOCK']
POLICY_ASSUMPTIONS = {
    'values_100': BASE_ASSUMPTIONS + ['A_TAP', 'A_PUMP'],
    'timestamp_100': BASE_ASSUMPTIONS + ['A_TAP', 'A_PUMP'],
    'full_100': BASE_ASSUMPTIONS + ['A_TAP', 'A_PUMP', 'A_SHADOW'],
    'full_200': BASE_ASSUMPTIONS + ['A_TAP', 'A_PUMP', 'A_SHADOW'],
}
ANCHORS = {
    'memory': ['active_window','memory_save','flip','stuck','restore','consume','pump_cmd','obs_memory'],
    'timing': ['release','skip','delay_due','delay_complete','discard','control_call','obs_timing'],
    'communication': ['history','comm_delay','comm_drop','comm_replay','timestamp_publish','obs_timestamp','obs_age'],
    'sensor': ['legacy_window','sensor_bias','source_tap','sensor_period','delivered_publish'],
    'actuator': ['legacy_window','pump_scale','pump_publish','obs_actuator'],
    'healthy': ['acquire','control_call','pump_cmd','pump_publish'],
}

def f32(x):
    return struct.unpack('!f', struct.pack('!f', x))[0]

def bits(x):
    return struct.pack('!f', x).hex()

def clamp(x):
    return min(1.0, max(0.0, x))

def realizations():
    """Entire finite domain; each world's choices are independent. Healthy is a safeguard."""
    out = [{'origin':'healthy','kind':'healthy','start':0,'duration':0,'parameter':0,'aux':0}]
    def add(origin,kind,start,duration,p=0,aux=0):
        out.append(dict(origin=origin,kind=kind,start=start,duration=duration,parameter=p,aux=aux))
    for start, duration in itertools.product((100,200), (100,200)):
        for bit in (0,2):
            add('memory','flip',start,duration,bit)
            for polarity in (0,1): add('memory','stuck',start,duration,bit,polarity)
        if duration == 100: add('timing','skip',start,duration)
        for delay in (100,200): add('timing','delay',start,duration,delay)
        for kind in ('replay','comm_delay','drop'): add('communication',kind,start,duration,100 if kind!='drop' else 1)
        for bias in (-4,4): add('sensor','bias',start,duration,bias)
        for scale in (0.0,0.5): add('actuator','pump',start,duration,scale)
    # Sampled legacy windows: these are configured events, not proof of a physical inter-tick pulse.
    for start in (100,150):
        for bias in (-4,4): add('sensor','bias',start,25,bias)
    for i,r in enumerate(out): r['id']=f'w{i:03d}'
    return out

def execute(r, context):
    """Finite open-loop environment, source-backed component ordering, no safety/plant call."""
    temp=f32(CONTEXTS[context]); reg=shadow=92; target=f32(92)
    cmd=f32(.25); last_exec=-1; previous=False; saved=reg; pending=None
    delivered=temp; source_time=0; history={}; observations=[]; events=[]; active_count=0
    for t in TIMES:
        active=r['kind']!='healthy' and r['start']<=t<r['start']+r['duration']
        if active and not previous:
            active_count=0
            if r['origin']=='memory':
                saved=reg
                if r['kind']=='flip': reg ^= 1 << r['parameter']
        if previous and not active and r['origin']=='memory': reg=saved
        if active and r['kind']=='stuck':
            mask=1<<r['parameter']; reg=(reg|mask) if r['aux'] else (reg & ~mask)
        # Physical input is only used to generate sensor measurements, never passed to checker.
        source=f32(temp + r['parameter']) if active and r['kind']=='bias' else temp
        history[t]=source; delivered_now=True
        if r['origin']=='communication':
            stamp=t
            if active:
                active_count+=1
                if r['kind']=='comm_delay':
                    delivered_now=t-r['start']>=r['parameter']; stamp=t-r['parameter']
                elif r['kind']=='drop': delivered_now=active_count>r['parameter']
                elif r['kind']=='replay': stamp=t-r['parameter']
            if delivered_now and stamp in history: delivered=history[stamp]; source_time=stamp
            else: delivered_now=False
        else: delivered=source; source_time=t
        run=True
        if r['kind']=='delay':
            if pending is not None:
                run=t>=pending
                if run: pending=None
            elif active: pending=t+r['parameter']; run=False
        elif r['kind']=='skip' and active: run=False
        pre_target=target
        if run:
            target=f32(reg); last_exec=t
            error=f32(delivered-target)
            cmd=f32(clamp(f32(f32(f32(.30)+f32(f32(.025)*error))+f32(f32(.35)*0.0))))
        actual=f32(cmd*r['parameter']) if active and r['kind']=='pump' else cmd
        row=dict(time_ms=t,coolant_measured_c=bits(delivered),pump_command=bits(cmd),pump_actual=bits(actual),
                 sample_timestamp_ms=source_time,sample_age_ms=t-source_time,sample_freshness_ok=t-source_time<300,
                 target_register_c=reg,target_shadow_c=shadow,target_shadow_valid=True,
                 control_target_c=bits(target),control_execution_ms=last_exec,source_c=bits(source),source_ms=t,source_valid=True)
        observations.append(row)
        events.append(dict(time_ms=t,configured_active=active,acquired=True,delivery_event=delivered_now,
                           control_executed=run,register_after_injection=reg,target_before_control=bits(pre_target),
                           pending_due_ms=pending,anchors=ANCHORS[r['origin']]))
        previous=active
    return {'realization':r,'context':context,'observations':observations,'model_events_not_checker_input':events}

def history(execution,policy,deadline):
    fields,period=POLICIES[policy]
    return tuple(tuple([r['time_ms']]+[r[f] for f in fields]) for r in execution['observations'] if r['time_ms']<=deadline and r['time_ms']%period==0)

def compatibility_index(executions,policy,deadline):
    index={}
    for e in executions: index.setdefault(history(e,policy,deadline),[]).append(e)
    return index

def decide(observed_history,index):
    """Checker accepts runtime history only. Labels appear solely in the offline model relation."""
    origins={e['realization']['origin'] for e in index.get(observed_history,[])}
    return next(iter(origins)) if len(origins)==1 else 'UNKNOWN'

def brute_compatible(observed_history,executions,policy,deadline):
    """Independent scan: no hash index, history helper, or decision implementation."""
    fields,period=POLICIES[policy]; compatible=set()
    for e in executions:
        rows=[r for r in e['observations'] if r['time_ms']<=deadline and r['time_ms']%period==0]
        if len(rows)!=len(observed_history): continue
        match=True
        for row,observed in zip(rows,observed_history):
            if row['time_ms']!=observed[0]: match=False; break
            for j,field in enumerate(fields,1):
                if row[field]!=observed[j]: match=False; break
            if not match: break
        if match: compatible.add(e['realization']['origin'])
    return compatible

def generate():
    worlds={c:[execute(r,c) for r in realizations()] for c in CONTEXTS}
    frontier=[]; ambiguities=[]; pairs=[]; positives=[]
    for context,executions in worlds.items():
        for policy in POLICIES:
            for deadline in (100,200,400):
                index=compatibility_index(executions,policy,deadline)
                unique=[h for h in index if decide(h,index)!='UNKNOWN']
                earliest=[]
                for e in executions:
                    at=next((t for t in TIMES if t<=deadline and decide(history(e,policy,t),compatibility_index(executions,policy,t))!='UNKNOWN'),None)
                    if at is not None: earliest.append(at)
                frontier.append(dict(context=context,policy=policy,deadline_ms=deadline,executions=len(executions),
                    fault_executions=len(executions)-1,histories=len(index),unique_origin_histories=len(unique),
                    ambiguous_histories=len(index)-len(unique),unknown_executions=sum(len(es) for h,es in index.items() if decide(h,index)=='UNKNOWN'),
                    earliest_unique_ms=min(earliest) if earliest else '',assumptions=';'.join(POLICY_ASSUMPTIONS[policy]),
                    physical_certificates=0,observation_rows=sum(t<=deadline and t%POLICIES[policy][1]==0 for t in TIMES),
                    field_reads=len(POLICIES[policy][0])*sum(t<=deadline and t%POLICIES[policy][1]==0 for t in TIMES),
                    prefix_trie_nodes=1+len({history(e,policy,t) for e in executions for t in TIMES if t<=deadline})))
                # A replayable pair for EACH ambiguous history, including healthy alternatives.
                for h,es in index.items():
                    labels=sorted({e['realization']['origin'] for e in es})
                    if len(labels)>1:
                        a=es[0]; b=next(e for e in es if e['realization']['origin']!=a['realization']['origin'])
                        ambiguities.append(dict(context=context,policy=policy,deadline_ms=deadline,
                            compatible_origins=labels,world_a=a['realization'],world_b=b['realization'],
                            observation_fields=['time_ms']+list(POLICIES[policy][0]),runtime_history=h,
                            anchors=sorted(set(ANCHORS[a['realization']['origin']]+ANCHORS[b['realization']['origin']])),
                            assumptions=POLICY_ASSUMPTIONS[policy],result='INDISTINGUISHABLE',decision='UNKNOWN',
                            explanation='Different permitted origins produce exactly the same selected runtime history; an origin-specific answer would be wrong in at least one world.'))
                for a,b in itertools.combinations(ORIGINS,2):
                    ea=[e for e in executions if e['realization']['origin']==a]; eb=[e for e in executions if e['realization']['origin']==b]
                    overlap=next(((x,y) for x in ea for y in eb if history(x,policy,deadline)==history(y,policy,deadline)),None)
                    pairs.append(dict(context=context,policy=policy,deadline_ms=deadline,origin_a=a,origin_b=b,
                        independent_realization_pairs=len(ea)*len(eb),result='INDISTINGUISHABLE' if overlap else 'CONDITIONALLY_SEPARABLE',
                        witness_ids=[x['realization']['id'] for x in overlap] if overlap else [],
                        counterexample=({'world_a':overlap[0]['realization'],'world_b':overlap[1]['realization'],
                            'runtime_history':history(overlap[0],policy,deadline),
                            'observation_fields':['time_ms']+list(POLICIES[policy][0]),
                            'anchors':sorted(set(ANCHORS[a]+ANCHORS[b])),
                            'decision':'UNKNOWN','explanation':'Independent realizations of distinct origins agree exactly through the deadline.'} if overlap else None),
                        assumptions=POLICY_ASSUMPTIONS[policy]))
                for h in unique:
                    positives.append(dict(context=context,policy=policy,deadline_ms=deadline,origin=decide(h,index),
                        runtime_history=h,earliest_unique_ms=next(t for t in TIMES if t<=deadline and decide(history(index[h][0],policy,t),compatibility_index(executions,policy,t))!='UNKNOWN'),
                        assumptions=POLICY_ASSUMPTIONS[policy],status='CONDITIONALLY_SEPARABLE',physical_certificate=False))
    write_json('modeled_executions.json',worlds)
    write_json('competing_fault_worlds.json',{'scope':'bounded component model only','ambiguities':ambiguities,'pair_results':pairs})
    write_json('conditional_positive_histories.json',positives)
    with (HERE/'diagnosability_frontier.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(frontier[0])); w.writeheader(); w.writerows(frontier)
    summary=dict(origin_pairs=10,context_policy_deadline_pair_checks=len(pairs),executions_per_context=len(realizations()),
                 total_executions=sum(map(len,worlds.values())),ambiguity_certificates=len(ambiguities),
                 conditionally_separable_pair_checks=sum(p['result']=='CONDITIONALLY_SEPARABLE' for p in pairs),
                 physical_certificates=0,frontier_rows=len(frontier),seed=None,numerical_tolerance=0)
    write_json('oracle_summary.json',summary)
    print(json.dumps(summary,indent=2))

def write_json(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2)+'\n')

if __name__=='__main__': generate()
