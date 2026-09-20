"""Post-hoc detection/localization reporting; never imported by runtime inference."""
from .clo_dsf_current import OUT, METHODS
from .clo_dsf_final_reporting import records, wilson
from .clo_dsf_development import ORIGINS, write_csv

def ratio(k,n):
    return k/n if n else None

def runtime_stats(rows):
    alarms=sum(r['alarm_samples'] for r in rows);unknown=sum(r['alarm_UNKNOWN'] for r in rows)
    correct=sum(r.get('alarm_'+r['origin'],0) for r in rows);wrong=sum(r['wrong_localized_runtime_samples'] for r in rows)
    return dict(alarm_samples=alarms,localized_samples=alarms-unknown,correct_samples=correct,wrong_samples=wrong,
                wrong_runs=sum(r['wrong_localized_runtime_samples']>0 for r in rows),unknown_samples=unknown,
                unknown_rate=ratio(unknown,alarms),accuracy_among_localized=ratio(correct,alarms-unknown),
                correct_fraction_all_alarms=ratio(correct,alarms),localization_coverage=ratio(alarms-unknown,alarms))

def generate():
    rows=records(OUT/'case_summary.csv');comparisons=records(OUT/'comparison.csv');layers=records(OUT/'origin_summary.csv')
    pairs=[];runtime=[];confusion=[];confidence=[];latency=[];classification=[]
    misses=[r for r in rows if r['injected'] and not r['detected'] and (r['origin'] in ['COMMUNICATION','SENSOR_CONTROL'] or r['silent_plant'])]
    write_csv(OUT/'miss_classification.csv',misses)
    for part in ['development-train','development-validation']:
        current={r['run_id']:r for r in rows if r['partition']==part and r['method']=='Revised CLO-DSF'}
        before={r['run_id']:r for r in rows if r['partition']==part and r['method']=='Pre-change CLO-DSF'}
        for k,a in current.items():
            assert a['detected']>=before[k]['detected'],('lost detection',k)
            assert not a['false_alarm'] and not a['wrong_localized_runtime_samples'],('correctness regression',k)
            if a['origin']=='MEMORY':
                assert a['detected']==a['effective_memory_corruption'],('memory invariant',k)
        for method in ['Pre-change CLO-DSF','Weighted Sum']:
            other={r['run_id']:r for r in rows if r['partition']==part and r['method']==method}
            for workload in ['all','static_target','authorized_updates']:
                selected=[r for r in current.values() if r['injected'] and (workload=='all' or r['workload']==workload)];counts=[0]*4
                faster=same=slower=0
                for a in selected:
                    b=other[a['run_id']];counts[0 if a['detected'] and b['detected'] else 1 if a['detected'] else 2 if b['detected'] else 3]+=1
                    if a['detected'] and b['detected']:
                        faster+=a['latency_ms']<b['latency_ms'];same+=a['latency_ms']==b['latency_ms'];slower+=a['latency_ms']>b['latency_ms']
                pairs.append(dict(partition=part,comparator=method,workload=workload,both=counts[0],only_current=counts[1],only_comparator=counts[2],neither=counts[3],current_faster=faster,same_latency=same,current_slower=slower))
        for method in METHODS:
            selected=[r for r in rows if r['partition']==part and r['method']==method]
            for group in ['COMMUNICATION','SENSOR_CONTROL','silent_plant']:
                subset=[r for r in selected if not r['detected'] and (r['silent_plant'] if group=='silent_plant' else r['origin']==group)]
                classification.append(dict(partition=part,method=method,group=group,**{c:sum(r['miss_category']==c for r in subset) for c in ['A','B','C']},cases=len(subset)))
            if method!='Weighted Sum':
                for origin in ['ALL',*ORIGINS]:
                    subset=[r for r in selected if origin=='ALL' or r['origin']==origin]
                    runtime.append(dict(partition=part,method=method,origin=origin,**runtime_stats(subset)))
                    if origin!='ALL':confusion.append(dict(partition=part,method=method,origin=origin,**{o:sum(r['alarm_'+o] for r in subset) for o in ORIGINS+['UNKNOWN']},unit='alarm samples'))
        a=next(r for r in comparisons if r['partition']==part and r['method']=='Revised CLO-DSF' and r['workload']=='all')
        for endpoint,k,n in [('detection',a['detected'],a['faulty_runs']),('plant_detection',a['plant_manifestation_runs']-a['silent_plant'],a['plant_manifestation_runs']),('benign_alarms',a['benign_false_alarms'],a['benign_runs']),('first_localized_accuracy',a['correct_localizations'],a['localized'])]:
            lo,hi=wilson(k,n);confidence.append(dict(partition=part,endpoint=endpoint,numerator=k,denominator=n,wilson95_low=lo,wilson95_high=hi))
        for r in current.values():
            if r['latency_ms'] is not None and r['latency_ms']>300:
                latency.append({k:r[k] for k in ['partition','run_id','model','behavior','start_ms','first_post_alarm_ms','latency_ms','first_integrity_mismatch_ms','integrity_latency_ms','initially_latent_stuck','effective_memory_corruption']})
    write_csv(OUT/'paired_comparison.csv',pairs);write_csv(OUT/'runtime_localization_summary.csv',runtime)
    write_csv(OUT/'runtime_confusion_matrix.csv',confusion);write_csv(OUT/'confidence_summary.csv',confidence)
    write_csv(OUT/'latency_tail_summary.csv',latency);write_csv(OUT/'miss_classification_summary.csv',classification)
    part='development-validation'
    c=next(r for r in comparisons if r['partition']==part and r['method']=='Revised CLO-DSF' and r['workload']=='all')
    old=next(r for r in comparisons if r['partition']==part and r['method']=='Pre-change CLO-DSF' and r['workload']=='all')
    ws=next(r for r in comparisons if r['partition']==part and r['method']=='Weighted Sum' and r['workload']=='all')
    allrt=next(r for r in runtime if r['partition']==part and r['method']=='Revised CLO-DSF' and r['origin']=='ALL')
    pair=next(r for r in pairs if r['partition']==part and r['comparator']=='Pre-change CLO-DSF' and r['workload']=='all')
    lines=[]
    for origin in ORIGINS:
        r=next(r for r in layers if r['partition']==part and r['method']=='Revised CLO-DSF' and r['origin']==origin)
        b=next(r for r in layers if r['partition']==part and r['method']=='Pre-change CLO-DSF' and r['origin']==origin)
        rt=next(r for r in runtime if r['partition']==part and r['method']=='Revised CLO-DSF' and r['origin']==origin)
        lines.append(f"| {origin} | {b['detected']}/{b['faulty_runs']} | {r['detected']}/{r['faulty_runs']} | {r['correct_localizations']}/{r['localized']} | {rt['correct_samples']}/{rt['localized_samples']} | {rt['unknown_samples']}/{rt['alarm_samples']} |")
    remaining=[]
    for r in classification:
        if r['partition']==part and r['method']=='Revised CLO-DSF':remaining.append(f"- {r['group']}: A/B/C = {r['A']}/{r['B']}/{r['C']}.")
    val=[r for r in rows if r['partition']==part and r['method']=='Revised CLO-DSF'];mem=[r for r in val if r['origin']=='MEMORY']
    effective=[r for r in mem if r['effective_memory_corruption']];dormant=[r for r in mem if r['initially_latent_stuck'] and not r['effective_memory_corruption']]
    latent=[r for r in effective if r['initially_latent_stuck']];stuck=[r for r in effective if r['model']=='stuck_bit']
    assert all(r['integrity_latency_ms']==0 for r in effective)
    weak=[r for r in val if r['model']=='sensor_bias' and abs(r['magnitude'])==1.2 and r['behavior']!='intermittent']
    findings=f"""# Final CURRENT development pass

No runtime accumulation was selected. The eight prior isolated weak bias misses
have equal acquisition/consumption values. Constant bias cancels from successive
samples; excess slew occurs at onset and recovery, not throughout the bias.
Six cases have exactly two nonzero excess samples; two also contain small thermal
residuals around legal target updates. A diagnostic signed accumulator with the
existing .8 decay never exceeds .481. Recycling an old impulse would manufacture
persistence. This is a sensitivity limit of current trusted evidence and decision
rules, not proof of universal unobservability. No threshold or detector logic changed.
See weak_bias_inspection.csv and the pre-registered protocol for exact evidence.
Legacy nonzero-duration sensor events end at their configured duration, including
those labeled permanent. Existing fault semantics were preserved.

738 new simulations: 492 TRAIN, 246 VALIDATION (210 fault, 36 benign), disjoint
operating families. New profiles and seeds; no unseen holdout. Benign measurement
workloads test bounded alternating jitter and slow triangular variation alongside
legal calibration updates. The envelope does not establish general noise immunity.
The adapter uses existing measured values only and defaults to zero perturbation.
Pre-change and retained CURRENT detector source are identical; the historical
CSV method name Revised CLO-DSF does not imply a new detector revision.

| Origin | Pre-change detection | Retained detection | Correct/known first origins | Correct/known runtime origins | Runtime UNKNOWN/all |
|---|---:|---:|---:|---:|---:|
"""+'\n'.join(lines)+f"""

Validation detection {c['detected']}/{c['faulty_runs']}; isolated weak bias
{sum(r['detected'] for r in weak)}/{len(weak)}. Plant detection
{c['plant_manifestation_runs']-c['silent_plant']}/{c['plant_manifestation_runs']};
silent plant {c['silent_plant']}; benign alarms {c['benign_false_alarms']}/{c['benign_runs']}.
Median/P95 {c['latency_median_ms']}/{c['latency_p95_ms']} ms.
Effective memory {sum(r['detected'] for r in effective)}/{len(effective)}, effective
stuck bits {sum(r['detected'] for r in stuck)}/{len(stuck)}, dormant alarms
{sum(r['detected'] for r in dormant)}/{len(dormant)}. Effective memory detects at
first integrity mismatch; activation-relative delay is not evidence-processing delay.

First localization {c['correct_localizations']}/{c['localized']}, UNKNOWN {c['unknown']}.
Runtime localized accuracy {allrt['correct_samples']}/{allrt['localized_samples']};
UNKNOWN {allrt['unknown_samples']}/{allrt['alarm_samples']}; wrong samples/runs
{allrt['wrong_samples']}/{allrt['wrong_runs']}. Abstentions included in the denominator:
correct fraction {allrt['correct_fraction_all_alarms']}. Causal precedence preserved.

Pre-change detection {old['detected']}/{old['faulty_runs']}, silent {old['silent_plant']},
benign {old['benign_false_alarms']}/{old['benign_runs']}, median/P95
{old['latency_median_ms']}/{old['latency_p95_ms']} ms.
Fair Weighted Sum detection {ws['detected']}/{ws['faulty_runs']}, silent {ws['silent_plant']},
benign {ws['benign_false_alarms']}/{ws['benign_runs']}, median/P95
{ws['latency_median_ms']}/{ws['latency_p95_ms']} ms. Its fixed target assumption can
alarm on authorized updates; no recalibration was performed.

No weak-bias improvement or reduction in silent plant misses is claimed. The remaining
misses are retained as a documented limit. Paired comparisons and descriptive Wilson
intervals are supplied; deterministic grouped cases are not independent population
replications. Latency-tail cases are tabulated separately. No ground truth enters
inference; post-hoc labels only score outcomes. Preservation and final regression
are recorded in validation_record.md. No commit, push or unseen validation.
"""
    (OUT/'findings.md').write_text(findings)
    return c,old,ws,allrt

if __name__=='__main__':
    for row in generate():print(row)
