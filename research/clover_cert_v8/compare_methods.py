#!/usr/bin/env python3
"""Reduction challenge: established finite methods only. No distinct method D."""
import sys
sys.dont_write_bytecode=True
import csv
import hashlib
import itertools
import json
from pathlib import Path
import platform
import statistics
import time
import tracemalloc

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
BUNDLES=[['coolant_measured_c','pump_command','pump_actual'],
 ['sample_timestamp_ms','sample_age_ms','sample_freshness_ok'],
 ['target_register_c','target_shadow_c','target_shadow_valid','control_target_c'],
 ['control_execution_ms'],['source_c','source_ms','source_valid']]
INFLUENCE={
 'healthy':set(),
 'memory':{'target_register_c','control_target_c','pump_command','pump_actual'},
 'timing':{'control_execution_ms','control_target_c','pump_command','pump_actual'},
 'communication':{'coolant_measured_c','sample_timestamp_ms','sample_age_ms','sample_freshness_ok','pump_command','pump_actual'},
 'sensor':{'coolant_measured_c','source_c','pump_command','pump_actual'},
 'actuator':{'pump_actual'}}

def load_cases():
    data=json.loads((ROOT/'research/clover_cert_v7/modeled_executions.json').read_text())
    cases=[]
    for name,worlds in data.items():
        for d in (100,200,400):
            cases.append(dict(name=name+'_'+str(d),kind='v7_component',worlds=worlds,bundles=BUNDLES,deadline=d,periods=[100,200],domains=5))
    # Explicitly synthetic, deterministic common-domain mutation patterns, not ECU data.
    # One-axis changes from the first synthetic case permit transparent scaling inspection.
    for label,origins,domains,ticks,observables in [
        ('base',4,2,3,5),('origins_8',8,2,3,5),('domains_4',4,4,3,5),
        ('timestamps_6',4,2,6,5),('observations_8',4,2,3,8),('joint',8,4,6,8)]:
        fields=['x'+str(i) for i in range(observables)]; worlds=[]
        for origin in range(origins):
            for realization in (0,1):
                rows=[]
                for tick in range(ticks):
                    row={'time_ms':100*tick}
                    for i,f in enumerate(fields):
                        # Correlation: one domain-level bit is shared by all its fields.
                        domain=i%domains
                        bit=((origin >> (tick%3)) & 1)
                        corrupted=realization==1 and domain==origin%domains and tick>0
                        row[f]=0 if corrupted else bit
                    rows.append(row)
                worlds.append({'realization':{'origin':'synthetic_'+str(origin),'start':0,'id':str(len(worlds))},'observations':rows})
        cases.append(dict(name='synthetic_'+label,kind='synthetic_not_ECU',worlds=worlds,bundles=[[f] for f in fields],
                          deadline=100*(ticks-1),periods=[100,200],domains=domains))
    return cases

def labels(case):return [w['realization']['origin'] for w in case['worlds']]

def contract_fields(case,mask):
    return tuple(f for i,b in enumerate(case['bundles']) if mask>>i&1 for f in b)

def histories(case,mask,period):
    fs=contract_fields(case,mask)
    return [tuple(tuple([r['time_ms']]+[r[f] for f in fs]) for r in w['observations']
                  if r['time_ms']<=case['deadline'] and r['time_ms']%period==0) for w in case['worlds']]

def verdict(origins):return next(iter(origins)) if len(origins)==1 else 'UNKNOWN'

def pair_decisions(hs,labs,stats):
    result=[]
    for a in hs:
        possible=set()
        for j,b in enumerate(hs):
            stats['pair_tests']+=1
            if a==b:possible.add(labs[j])
        result.append(verdict(possible))
    return result

def partition_decisions(hs,labs):
    groups={}
    for h,l in zip(hs,labs):groups.setdefault(h,set()).add(l)
    return [verdict(groups[h]) for h in hs]

def required_pairs(target,labs):
    return [(i,j) for i,t in enumerate(target) if t!='UNKNOWN' for j,l in enumerate(labs) if t!=l]

def diff_mask(case,i,j,period):
    mask=0
    for b,fs in enumerate(case['bundles']):
        for a,z in zip(case['worlds'][i]['observations'],case['worlds'][j]['observations']):
            if a['time_ms']<=case['deadline'] and a['time_ms']%period==0 and any(a[f]!=z[f] for f in fs):
                mask|=1<<b;break
    return mask

def support_mask(case,i,j,period):
    if case['kind']!='v7_component':
        # No source-backed graph exists for synthetic inputs: use the safe universal bound.
        return (1<<len(case['bundles']))-1
    result=0
    for w in (case['worlds'][i],case['worlds'][j]):
        origin=w['realization']['origin'];start=w['realization']['start']
        for b,fs in enumerate(case['bundles']):
            if set(fs)&INFLUENCE[origin] and any(r['time_ms']>=start and r['time_ms']<=case['deadline'] and r['time_ms']%period==0 for r in w['observations']):result|=1<<b
    return result

def reduced_clauses(clauses):
    """Ordinary positive-clause subsumption, explicitly not a new antichain."""
    result=[]
    for c in sorted(set(clauses),key=lambda n:(n.bit_count(),n)):
        if not any(d&c==d for d in result):result.append(c)
    return result

def checker(hs,labs):
    """Acyclic Moore trie, bottom-up right-language quotient, default UNKNOWN sink."""
    nodes=[{'origins':set(),'edges':{}}]
    for h,l in zip(hs,labs):
        at=0;nodes[at]['origins'].add(l)
        for symbol in h:
            if symbol not in nodes[at]['edges']:
                nodes[at]['edges'][symbol]=len(nodes);nodes.append({'origins':set(),'edges':{}})
            at=nodes[at]['edges'][symbol];nodes[at]['origins'].add(l)
    intern={('UNKNOWN',()):0}; canonical={}; output={0:'UNKNOWN'}; edges={0:{}}
    for i in reversed(range(len(nodes))):
        arcs=tuple(sorted((s,canonical[n]) for s,n in nodes[i]['edges'].items() if canonical[n]!=0))
        key=(verdict(nodes[i]['origins']),arcs)
        if key not in intern:
            n=len(intern);intern[key]=n;output[n]=key[0];edges[n]=dict(arcs)
        canonical[i]=intern[key]
    return dict(states=len(intern),root=canonical[0],output=output,edges=edges,trie_nodes=len(nodes))

def run_checker(machine,history):
    at=machine['root']
    for symbol in history:at=machine['edges'][at].get(symbol,0)
    return machine['output'][at]

def solve(case,method):
    start=time.perf_counter_ns();labs=labels(case);n=len(labs);k=len(case['bundles']);full=(1<<k)-1
    # Same reference requirements in every method, preparation included in all timings.
    target=partition_decisions(histories(case,full,100),labs); req=required_pairs(target,labs)
    stats=dict(configurations=0,pair_tests=0,boolean_tests=0,oracle_calls=0,solver_calls=0,
               preprocessing_pair_visits=0,learned_clauses=0,checker_builds=0,support_pruned=0)
    feasible=[];costs={};best=None;best_contracts=[];tables={};learned={};support={}
    for period in case['periods']:
        learned[period]=[]
        if method=='B_boolean':
            clauses=reduced_clauses(diff_mask(case,i,j,period) for i,j in req)
            stats['preprocessing_pair_visits']+=len(req)
            admissible=(1<<(1<<k))-1
            for clause in clauses:
                satisfying=0
                for assignment in range(1<<k):
                    stats['boolean_tests']+=1
                    if assignment&clause:satisfying|=1<<assignment
                admissible &= satisfying
            tables[period]=admissible
        if method=='C_coi_cuts':
            support[period]=reduced_clauses(support_mask(case,i,j,period) for i,j in req)
            stats['preprocessing_pair_visits']+=len(req)
        for mask in range(1<<k):
            stats['configurations']+=1;answer=None;ok=True
            if method=='B_boolean':
                # Generic propositional clauses: each diff mask encodes OR(selected bundle).
                stats['boolean_tests']+=1
                ok=bool(tables[period]>>mask&1)
            else:
                if method=='C_coi_cuts':
                    for c in support[period]:
                        stats['boolean_tests']+=1
                        if mask&c==0:ok=False;stats['support_pruned']+=1;break
                if ok and method in ('C_cuts','C_coi_cuts'):
                    for c in learned[period]:
                        stats['boolean_tests']+=1
                        if mask&c==0:ok=False;break
                if ok:
                    hs=histories(case,mask,period);stats['oracle_calls']+=1
                    answer=pair_decisions(hs,labs,stats);ok=answer==target
                    if not ok and method in ('C_cuts','C_coi_cuts'):
                        i,j=next((i,j) for i,j in req if hs[i]==hs[j])
                        learned[period].append(diff_mask(case,i,j,period));stats['learned_clauses']+=1
            if ok:
                hs=histories(case,mask,period);machine=checker(hs,labs);stats['checker_builds']+=1
                assert [run_checker(machine,h) for h in hs]==target
                reads=len(contract_fields(case,mask))*len(hs[0]);cost=reads+machine['states']
                key=f'{period}:{mask}';feasible.append(key);costs[key]={'reads':reads,'states':machine['states'],'objective':cost}
                if best is None or cost<best:best=cost;best_contracts=[key]
                elif cost==best:best_contracts.append(key)
    stats['runtime_ns']=time.perf_counter_ns()-start
    return dict(method=method,feasible=feasible,costs=costs,best_objective=best,best_contracts=best_contracts,
                reference_decisions=target,stats=stats)

METHODS=('A_pairs','B_boolean','C_cuts','C_coi_cuts')

def benchmark():
    cases=load_cases();results=[];rows=[]
    for case in cases:
        reference=None
        for method in METHODS:
            runs=[solve(case,method) for _ in range(3)]
            tracemalloc.start(); measured=solve(case,method);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            r=runs[-1];r['case']=case['name'];r['kind']=case['kind'];r['peak_python_bytes']=peak
            r['runtime_samples_ns']=[x['stats']['runtime_ns'] for x in runs];r['median_runtime_ns']=int(statistics.median(r['runtime_samples_ns']))
            signature=(r['feasible'],r['costs'],r['best_objective'],r['best_contracts'],r['reference_decisions'])
            if reference is None:reference=signature
            assert signature==reference,(case['name'],method,'method disagreement')
            assert (measured['feasible'],measured['costs'],measured['best_objective'],measured['best_contracts'],measured['reference_decisions'])==reference
            results.append(r)
            row=dict(case=case['name'],kind=case['kind'],method=method,origins=len(set(labels(case))),worlds=len(labels(case)),
                     domains=case['domains'],timestamps=sum(r['time_ms']<=case['deadline'] for r in case['worlds'][0]['observations']),
                     candidate_bundles=len(case['bundles']),deadline_ms=case['deadline'],feasible_contracts=len(r['feasible']),
                     best_objective=r['best_objective'],median_runtime_ms=r['median_runtime_ns']/1e6,peak_python_bytes=peak,
                     **{k:v for k,v in r['stats'].items() if k!='runtime_ns'})
            rows.append(row)
        print(case['name'],'all methods agree',flush=True)
    (HERE/'comparison_results.json').write_text(json.dumps(results,indent=2)+'\n')
    with (HERE/'comparison_metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (HERE/'benchmark_environment.json').write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),seed=None,
        repeats=3,memory='separate tracemalloc run; Python allocations excluding preloaded input, not RSS or deployed checker memory',
        runtime='perf_counter_ns; includes target requirements, method preprocessing and feasible checker generation; excludes disk import',
        SMT_available=False,symbolic_backend='explicit finite propositional bit-mask evaluation, not SMT or BDD performance',
        D='NOT_IMPLEMENTED_NO_DISTINCT_RULE',data_sha256=hashlib.sha256((ROOT/'research/clover_cert_v7/modeled_executions.json').read_bytes()).hexdigest()),indent=2)+'\n')

if __name__=='__main__':benchmark()
