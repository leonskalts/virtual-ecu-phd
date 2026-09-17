#!/usr/bin/env python3
"""Audit semantically redundant development settings without altering evidence."""
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.clo_dsf_development import OUTPUT,aggregate,selection_key,write_csv

def physical_key(row):
    return (row['model'],row['behavior'],row['profile'],row['start_ms'],
            None if row['behavior']=='permanent' else row['duration_ms'],
            None if row['model'] in ['deadline_miss','fan_stuck_off','baseline'] else row['magnitude'])

def run():
    specs=list(csv.DictReader((OUTPUT/'development_split_manifest.csv').open()))
    groups={}
    for row in specs:groups.setdefault(physical_key(row),[]).append(row)
    equivalents=[]
    for key,group in groups.items():
        if len(group)<2:continue
        assert len({r['partition'] for r in group})==1
        hashes=[]
        for row in group:
            with gzip.open(OUTPUT/'traces'/f"{row['run_id']}.clo_dsf.csv.gz",'rb') as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())
        assert len(set(hashes))==1,'Semantically identical scenarios must yield identical runtime evidence'
        equivalents.append(dict(group=group[0]['group'],profile=group[0]['profile'],start_ms=group[0]['start_ms'],
                                run_ids=';'.join(r['run_id'] for r in group),partition=group[0]['partition'],
                                identical_runtime_evidence_sha256=hashes[0],reason='Permanent deadline miss ignores configured duration and has no magnitude parameter'))
    write_csv(OUTPUT/'physical_equivalence_groups.csv',equivalents)
    rows=list(csv.DictReader((OUTPUT/'clo_dsf_dev_runs.csv').open()))
    for row in rows:
        for field in ['injected','detected','false_alarm','silent_plant','unknown_at_alarm','localized_correct','localization_before_plant','pre_alarm_samples','propagation_samples','high_conflict_samples','control_effect','actuator_effect','plant_manifestation']:
            row[field]=int(row[field]) if row[field] else None
        for field in ['latency_ms','mean_conflict','mean_ignorance']:row[field]=float(row[field]) if row[field] else None
    results=[]
    for part in ['development-train','development-validation']:
        for method in sorted({r['method'] for r in rows if r['partition']==part}):
            selected={physical_key(r):r for r in rows if r['partition']==part and r['method']==method}
            if method=='Timing Monitor':selected={k:r for k,r in selected.items() if r['origin'] in ['NORMAL','TIMING']}
            results.append(dict(partition=part,method=method,**aggregate(list(selected.values()))))
    write_csv(OUTPUT/'deduplicated_sensitivity.csv',results)
    candidates=[next(r for r in results if r['method']==f'candidate_{i}') for i in range(8)]
    chosen=min(range(8),key=lambda i:selection_key(candidates[i],i))
    original=json.loads((OUTPUT/'selection_record.json').read_text())['selected_candidate']
    assert chosen==original
    record={'configured_simulations':len(specs),'distinct_physical_configurations':len(groups),
            'redundant_train_executions':sum(len(g)-1 for g in groups.values()),
            'validation_redundant_executions':sum(len(g)-1 for g in groups.values() if g[0]['partition']=='development-validation'),
            'deduplicated_train_candidate':chosen,'same_selected_candidate':True,
            'interpretation':'Post-study audit/sensitivity only. Primary preregistered tables and selection are retained. Repeats are not independent evidence.'}
    (OUTPUT/'physical_equivalence_audit.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))
if __name__=='__main__':run()
