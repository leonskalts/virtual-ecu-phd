"""Traceable v6 tables, claims and figures derived only from frozen evidence."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .final_evidence import (ROOT, V5, GENERATOR, records, metric, write_json, write_csv,
                            table_forms, markdown_table, final_configuration)

TIMING = 'timing_holdout_summary.csv'
CROSS = 'cross_layer_holdout_summary.csv'
COST = 'intervention_cost_summary.csv'
RECOVERY = 'summaries/recovery_final_outcomes.csv'
MATCHED = 'stuck_dynamic_matched_comparison.csv'
OVERHEAD = 'monitor_overhead_summary.csv'


def source(name):
    return 'results/cross_layer_safety_v5/' + name


def fraction(row):
    if not row['denominator']:
        return 'N/A (empty eligible cohort)'
    return f"{row['numerator']}/{row['denominator']} ({row['percent']:.2f}%)"


def interval(row):
    lo, hi = row.get('ci95_lower_percent'), row.get('ci95_upper_percent')
    return f'{lo:.2f}–{hi:.2f}%' if lo is not None and hi is not None else None


def create_tables(out):
    folder = out / 'paper_tables'
    folder.mkdir(exist_ok=True)
    tables = {}
    tables['table_1_models_observables'] = records(V5 / 'tables/table_A_models_observables.csv')
    names = ['timing_detection_coverage', 'timing_false_alarm_rate', 'plant_propagating_timing_detection',
             'pre_plant_timing_detection', 'same_tick_plant_timing_detection', 'median_detection_latency_ms', 'p95_detection_latency_ms']
    tables['table_2_timing_holdout'] = [dict(metric=name, numerator=(r := metric(TIMING, name))['numerator'],
        denominator=r['denominator'], percent=r['percent'], ci95_lower_percent=r.get('ci95_lower_percent'),
        ci95_upper_percent=r.get('ci95_upper_percent'), latency_ms=r.get('value_ms')) for name in names]
    runs = [r for r in records(V5 / 'cross_layer_holdout_runs.csv') if r['is_perturbed'] == 1]
    consequence = []
    for layer in ['all'] + sorted({r['fault_layer'] for r in runs}):
        group = [r for r in runs if layer == 'all' or r['fault_layer'] == layer]
        plant = [r for r in group if r['plant_manifestation'] == 1]
        detected = sum(r['combined_detected'] == 1 for r in group)
        dp = sum(r['combined_detected'] == 1 for r in plant)
        consequence.append({'fault_layer': layer, 'runs': len(group), 'detected': detected,
                            'plant_propagation': len(plant), 'detected_given_plant': dp,
                            'silent_plant_propagation': len(plant) - dp})
    tables['table_3_observability_by_consequence'] = consequence
    tables['table_4_timing_ablation'] = [
        {'evidence': r['ablation'], 'detected': f"{r['timing_detection_coverage_numerator']}/{r['contract_violations']}",
         'legal_alarms': f"{r['false_positives']}/{r['timing_false_alarm_rate_denominator']}",
         'median_ms': r['median_detection_latency_ms'], 'p95_ms': r['p95_detection_latency_ms'],
         'pre_plant': f"{r['pre_plant_timing_detection_numerator']}/{r['pre_plant_timing_detection_denominator']}"}
        for r in records(V5 / 'timing_ablation_holdout.csv')]
    tables['table_5_communication_tradeoff'] = [
        {'policy': r['policy'], 'hazards': f"{r['hazards']}/{r['injected_or_overload_runs']}",
         'critical_ms': r['critical_exposure_ms'], 'contained': f"{r['contained']}/{r['containment_eligible']}",
         'unnecessary': f"{r['unnecessary_interventions']}/{r['unnecessary_eligible']}",
         'false_actions': f"{r['false_interventions']}/{r['benign_runs']}",
         'safe_state_s': r['safe_state_duration_ms_total']/1000, 'limp_home_s': r['limp_home_duration_ms_total']/1000}
        for r in records(V5 / COST) if r['study_kind'] == 'communication']
    for name, rows in tables.items():
        table_forms(folder / name, rows)
    return tables


def create_claims(out):
    claims = []
    limitation = 'Designed deterministic, correlated scenarios; Wilson intervals are descriptive binomial references, not fleet probabilities.'
    def add(cid, category, text, csv, table, filters, columns, numerator=None, denominator=None, value=None, ci=None,
            limits=limitation, forbidden='Universal automotive detection or reliability.', level='SUPPORTED WITH LIMITATION'):
        claims.append({'claim_id': cid, 'claim_text': text, 'claim_category': category, 'source_study': 'v5 holdout' if cid != 'C9' else 'v5 follow-up of v4 development cases',
                       'source_table': table, 'source_csv': source(csv), 'source_columns': json.dumps(columns),
                       'filters_applied': filters, 'numerator': numerator, 'denominator': denominator, 'value': value,
                       'confidence_interval_95': ci, 'support_level': level, 'limitations': limits,
                       'allowed_wording': text, 'prohibited_stronger_wording': forbidden})
    for cid, name, label, forbidden in [
        ('C1', 'timing_detection_coverage', 'The frozen combined monitor detected', 'The monitor eliminates timing misses universally.'),
        ('C2', 'timing_false_alarm_rate', 'Alarms were observed in', 'The timing monitor has zero false-positive probability.'),
        ('C3', 'pre_plant_timing_detection', 'Strictly pre-plant detection occurred in', 'Detection guarantees timely hazard prevention.')]:
        r = metric(TIMING, name)
        noun = 'legal holdout timing workloads' if cid == 'C2' else 'plant-propagating timing violations' if cid == 'C3' else 'configured holdout timing violations'
        add(cid, 'primary', f'{label} {fraction(r)} {noun}; Wilson 95% interval {interval(r)}.', TIMING,
            'paper_tables/table_2_timing_holdout.csv', f'metric={name}',
            ['metric', 'numerator', 'denominator', 'percent', 'ci95_lower_percent', 'ci95_upper_percent'],
            r['numerator'], r['denominator'], r['percent'], interval(r), forbidden=forbidden)
    ab = records(V5 / 'timing_ablation_holdout.csv')
    abtext = '; '.join(f"{r['ablation']}: {r['timing_detection_coverage_numerator']}/{r['contract_violations']}, median/p95 {r['median_detection_latency_ms']:g}/{r['p95_detection_latency_ms']:g} ms" for r in ab)
    add('C4', 'primary', abtext + '. Combined retains deadline-only coverage and improves p95 latency in these paired traces.',
        'timing_ablation_holdout.csv', 'paper_tables/table_4_timing_ablation.csv', 'All three frozen ablations; same primary traces',
        list(ab[0]), value=abtext, level='SUPPORTED', limits='Specific paired coverage/latency result; no additional pre-plant coverage, no specialized smaller implementation measured.',
        forbidden='Combined improves every metric or necessarily outperforms all simpler implementations.')
    for cid, name, label in [('C5', 'combined_detection', 'Observed-union cross-layer detection'),
                              ('C6', 'detection_given_plant', 'Detection conditional on plant propagation'),
                              ('C7', 'silent_plant_propagation', 'Silent plant propagation')]:
        r = metric(CROSS, name, dimension='overall', group='all')
        add(cid, 'primary', label + ': ' + fraction(r) + '.', CROSS,
            'paper_tables/table_3_observability_by_consequence.csv', f'dimension=overall; group=all; metric={name}',
            ['dimension', 'group', 'metric', 'numerator', 'denominator', 'percent', 'ci95_lower_percent', 'ci95_upper_percent'],
            r['numerator'], r['denominator'], r['percent'], interval(r),
            limits=limitation + ' Fault origins are not matched in physical severity; existing detectors retain simulation truth dependencies.',
            forbidden='Fault origin alone causally determines detection probability; silent plant effect always means hazard.')
    comm = [r for r in records(V5 / COST) if r['study_kind'] == 'communication']
    immediate, graded = [next(r for r in comm if r['policy'] == policy) for policy in ['immediate', 'graded']]
    delta = immediate['limp_home_duration_ms_total'] - graded['limp_home_duration_ms_total']
    ct = '; '.join(f"{r['policy']}: containment {r['contained']}/{r['containment_eligible']}, unnecessary actions {r['unnecessary_interventions']}/{r['unnecessary_eligible']}, hazards {r['hazards']}/{r['injected_or_overload_runs']}" for r in comm)
    ct += f". Graded replaces {delta:,} ms of limp-home with cooling; both action arms have {graded['safe_state_duration_ms_total']:,} ms total safe-state time."
    add('C8', 'secondary', ct, COST, 'paper_tables/table_5_communication_tradeoff.csv', 'study_kind=communication; policy matched',
        list(comm[0]), value=ct, limits='No baseline hazards: prevention is N/A. Fixed no-action consequence eligibility. No reduction in unnecessary count or total safe-state duration. Only three benign cases per policy.',
        forbidden='Communication action generalizes hazard prevention, or graded action reduces unnecessary intervention count.')
    confidence = [r for r in records(V5/'communication_policy_summary.csv')
                  if r['metric'] in ['containment_success','unnecessary_intervention','false_intervention','hazard_prevention']]
    claims[-1]['confidence_interval_95'] = '; '.join(f"{r['policy']}.{r['metric']}={interval(r) or 'N/A (empty cohort)'}" for r in confidence)
    claims[-1]['confidence_source_csv'] = source('communication_policy_summary.csv')
    claims[-1]['confidence_source_columns'] = json.dumps(['policy','metric','numerator','denominator','ci95_lower_percent','ci95_upper_percent'])
    rec = [r for r in records(V5 / RECOVERY) if r['study_kind'] == 'communication' and r['policy'] == 'immediate' and r['original_containment'] == 0]
    recovered = sum(r['extended_containment'] == 1 for r in rec)
    end = {r['extended_end_ms'] for r in rec}
    assert len(end) == 1
    add('C9', 'secondary', f'{recovered}/{len(rec)} selected v4 protected communication containment failures satisfy the unchanged contract by {next(iter(end)) / 1000:g} s.',
        RECOVERY, 'Accepted v5 recovery final outcomes', 'study_kind=communication; policy=immediate; original_containment=0',
        ['study_kind', 'policy', 'original_containment', 'extended_containment', 'extended_end_ms'], recovered, len(rec),
        100 * recovered / len(rec), limits='Exhaustive follow-up of the five development failures, not independent holdout or proof of eventual recovery.',
        forbidden='All containment failures eventually recover; horizon extension establishes safety universally.')
    triples = records(V5 / MATCHED)
    diff = {mode: sum(r[mode + '_detected'] != r['permanent_detected'] for r in triples) for mode in ['flip', 'intermittent']}
    mt = f"Detection differs in {diff['flip']}/{len(triples)} flip/permanent and {diff['intermittent']}/{len(triples)} intermittent/permanent polarity triples."
    add('C10', 'secondary', mt, MATCHED, 'Accepted v5 matched polarity triples', 'All matched triples; flip traces reused across polarities',
        ['match_id', 'polarity', 'flip_detected', 'permanent_detected', 'intermittent_detected'], value=mt,
        limits='Targets/bits/profile/time matched; exposure duration and corruption opportunity are unequal. Shared flip traces are not independent.',
        forbidden='Dynamic faults are harder, better, worse or superior to stuck-at faults.')
    overhead = {r['metric']: r for r in records(V5 / OVERHEAD)}
    keys = ['monitor_state', 'observation_state', 'recorder_state', 'linked_monitor_text_delta', 'v5_vs_v4_binary_text_delta', 'v5_vs_v4_binary_data_delta']
    size_text = '; '.join(f"{key}={overhead[key]['value']} B" for key in keys)
    add('C11', 'supporting', 'Recorded gcc/Linux ABI sizes: ' + size_text + '.', OVERHEAD, 'Accepted v5 overhead summary',
        'metric in ' + ','.join(keys), ['metric', 'value', 'unit', 'scope'], value=size_text, level='SUPPORTED',
        limits='Compiler/ABI-specific. Whole-extension and isolated monitor deltas are distinct; no portable embedded memory guarantee.',
        forbidden='These are guaranteed footprints on every embedded target.')
    host = '; '.join(f"{key}={overhead[key]['value']} {overhead[key]['unit']}" for key in ['host_runtime_disabled', 'host_runtime_observe_only', 'host_median_relative_change'])
    add('C12', 'supporting', f"Accepted paired host-process benchmark ({overhead['host_runtime_disabled']['n']} repetitions per variant): {host}. The difference is within measurement noise.",
        OVERHEAD, 'Accepted v5 overhead summary', 'metric in host_runtime_disabled,host_runtime_observe_only,host_median_relative_change',
        ['metric', 'value', 'unit', 'n', 'scope'], denominator=overhead['host_runtime_disabled']['n'], value=host,
        limits='Includes process launch, simulation and CSV I/O; no-op measurement build; no precise isolated runtime cost, embedded WCET or speedup inference.',
        forbidden='Negligible embedded overhead or measured ECU WCET.')
    primary = [r for r in records(V5 / 'timing_holdout_runs.csv') if r['policy'] == 'observe_only' and r['contract_violated'] == 1]
    old = sum(r['detected'] == 1 for r in primary)
    add('C13', 'primary', f'Existing detector observation detects {old}/{len(primary)} timing violations in the same primary holdout; the frozen timing monitor detects all evaluated violations (C1).',
        'timing_holdout_runs.csv', 'paper_figures/figure_1_timing_validation.png', 'policy=observe_only; contract_violated=1',
        ['policy', 'contract_violated', 'detected', 'timing_monitor_detected'], old, len(primary), 100 * old / len(primary),
        limits='Paired configured trajectories, unchanged existing detector. Legacy physical/residual evidence is simulation-dependent; no universal generic-detector comparison.',
        forbidden='All generic physical detectors necessarily miss these faults in production.')
    write_csv(out / 'claim_evidence_matrix.csv', claims)
    (out / 'claim_evidence_matrix.md').write_text('# Claim–evidence matrix\n\nPaths are repository-relative unless prefixed paper_tables/paper_figures (relative to this package). CSV filters and source columns identify each calculation.\n\n' + markdown_table(claims))
    return claims


def create_figures(out, tables):
    os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'vecu-matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'savefig.dpi': 300})
    folder = out / 'paper_figures'
    folder.mkdir(exist_ok=True)
    traces = []
    def save(fig, name, csvs, columns, filters, ids, caption):
        fig.tight_layout()
        fig.savefig(folder / name, metadata={'Description': caption + ' Sources: ' + '; '.join(csvs), 'Software': GENERATOR})
        plt.close(fig)
        traces.append({'artifact_name': 'paper_figures/' + name, 'generation_script': GENERATOR,
                       'source_csv': json.dumps(csvs), 'source_columns': json.dumps(columns), 'filters_applied': filters,
                       'claim_ids': ','.join(ids), 'caption': caption})
    primary = [r for r in records(V5 / 'timing_holdout_runs.csv') if r['policy'] == 'observe_only' and r['contract_violated'] == 1]
    false = metric(TIMING, 'timing_false_alarm_rate')
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.8), gridspec_kw={'width_ratios': [1.4, 1]})
    values = [sum(r['detected'] == 1 for r in primary), sum(r['timing_monitor_detected'] == 1 for r in primary)]
    axes[0].bar(['Existing detector', 'Timing monitor'], [100 * x / len(primary) for x in values], color=['#777777', '#176a93'])
    axes[0].set(ylabel='Detected violations (%)', ylim=(0, 113), title='Paired timing holdout')
    axes[0].set_yticks([0, 25, 50, 75, 100])
    for i, v in enumerate(values): axes[0].text(i, 100 * v / len(primary) + 2, f'{v}/{len(primary)}', ha='center')
    axes[1].errorbar([0], [false['percent']], yerr=[[0], [false['ci95_upper_percent']]], fmt='o', capsize=6, color='#176a93')
    axes[1].set(xticks=[0], xticklabels=['Legal workloads'], ylabel='Alarm rate (%)', ylim=(-.2, 5), title='Legal timing: Wilson 95%')
    axes[1].text(0, 3.5, f"{false['numerator']}/{false['denominator']} alarms\n95% CI {interval(false)}", ha='center')
    save(fig, 'figure_1_timing_validation.png', [source('timing_holdout_runs.csv'), source(TIMING)],
         ['policy', 'contract_violated', 'detected', 'timing_monitor_detected', 'metric', 'percent', 'ci95_upper_percent'],
         'Left: observe_only and violated; right: timing_false_alarm_rate', ['C1', 'C2', 'C13'],
         'Unchanged detector versus added timing observation; distinct legal-alarm axis. Descriptive confidence bounds, not fleet probabilities.')
    rows = tables['table_3_observability_by_consequence'][1:]
    rows = [{**r, 'detection_percent': 100*r['detected']/r['runs'],
             'detection_given_plant_percent': 100*r['detected_given_plant']/r['plant_propagation'] if r['plant_propagation'] else None} for r in rows]
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    x = np.arange(len(rows)); width = .35
    ax.bar(x-width/2, [r['detection_percent'] for r in rows], width, label='All injections', color='#777777')
    ax.bar(x+width/2, [r['detection_given_plant_percent'] or 0 for r in rows], width, label='Given plant propagation', color='#176a93')
    for i, r in enumerate(rows):
        ax.text(i-width/2, r['detection_percent']+1, f"{r['detected']}/{r['runs']}", ha='center', fontsize=8)
        ax.text(i+width/2, (r['detection_given_plant_percent'] or 0)+1, f"{r['detected_given_plant']}/{r['plant_propagation']}" if r['plant_propagation'] else 'N/A', ha='center', fontsize=8)
    ax.set(xticks=x, xticklabels=[r['fault_layer'].replace('_', '\n') for r in rows], ylabel='Detected (%)', ylim=(0, 120))
    ax.set_yticks([0,25,50,75,100]);ax.legend(loc='upper center', bbox_to_anchor=(.5,1.16), ncol=2, frameon=False)
    save(fig, 'figure_2_conditional_observability.png', [source('cross_layer_holdout_runs.csv')],
         ['is_perturbed', 'fault_layer', 'combined_detected', 'plant_manifestation'], 'is_perturbed=1; group by fault_layer', ['C5','C6','C7'],
         'Consequence-conditioned detection with explicit denominators. Origins are not physically severity-matched; no causal ranking follows.')
    rows = records(V5/'timing_ablation_holdout.csv')
    fig, axes = plt.subplots(1,2,figsize=(7.6,3.8))
    labels = ['Deadline', 'Age/missed', 'Combined']
    axes[0].bar(labels,[r['timing_detection_coverage_percent'] for r in rows],color=['#777777','#b76c25','#176a93'])
    axes[0].set(ylabel='Detected violations (%)',ylim=(0,114));axes[0].set_yticks([0,25,50,75,100])
    for i,r in enumerate(rows):axes[0].text(i, r['timing_detection_coverage_percent']+2, f"{r['timing_detection_coverage_numerator']}/{r['contract_violations']}",ha='center',fontsize=9)
    axes[1].bar(labels,[r['p95_detection_latency_ms'] for r in rows],color=['#777777','#b76c25','#176a93'])
    axes[1].set(ylabel='p95 detection latency (ms)',ylim=(0,125))
    for i,r in enumerate(rows):axes[1].text(i,r['p95_detection_latency_ms']+3,f"{r['p95_detection_latency_ms']:g} ms",ha='center')
    save(fig,'figure_3_timing_ablation.png',[source('timing_ablation_holdout.csv')],
         ['ablation','contract_violations','timing_detection_coverage_numerator','timing_detection_coverage_percent','p95_detection_latency_ms'],
         'All three ablations; same traces, latency among detected violations', ['C4'],
         'Same trace cohort; age/missed has fewer detected latency endpoints. Median latency is 0 ms for each; all detect 33/33 plant cases before manifestation.')
    rows = [r for r in records(V5/COST) if r['study_kind']=='communication']
    fig, axes = plt.subplots(1,2,figsize=(7.6,3.9));labels=['Observe','Immediate','Graded']
    axes[0].bar(labels,[100*r['contained']/r['containment_eligible'] for r in rows],color=['#777777','#b76c25','#176a93'])
    axes[0].set(ylabel='Containment (%)',ylim=(0,105))
    for i,r in enumerate(rows):axes[0].text(i,100*r['contained']/r['containment_eligible']+2,f"{r['contained']}/{r['containment_eligible']}",ha='center')
    cooling=[r['precautionary_cooling_duration_ms_total']/1000 for r in rows]
    limp=[r['limp_home_duration_ms_total']/1000 for r in rows]
    axes[1].bar(labels,limp,label='Limp-home',color='#b76c25');axes[1].bar(labels,cooling,bottom=limp,label='Cooling',color='#176a93')
    axes[1].set(ylabel='Aggregate safe-state time (s)',ylim=(0,max(a+b for a,b in zip(limp,cooling))*1.3))
    axes[1].legend(frameon=False,fontsize=9)
    save(fig,'figure_4_communication_tradeoff.png',[source(COST)],list(rows[0]),'study_kind=communication; three paired policies',['C8'],
         '108 injections and three benign profiles per policy. No hazards or critical exposure in any arm; prevention is N/A. Both action arms retain 11/15 unnecessary actions and equal total safe-state time.')
    sources = [('table_1_models_observables', 'tables/table_A_models_observables.csv', 'All frozen model/observable rows', ['C5']),
               ('table_2_timing_holdout', TIMING, 'Seven named primary timing metrics', ['C1','C2','C3']),
               ('table_3_observability_by_consequence', 'cross_layer_holdout_runs.csv', 'is_perturbed=1; group by fault_layer plus all', ['C5','C6','C7']),
               ('table_4_timing_ablation', 'timing_ablation_holdout.csv', 'All paired ablations', ['C4']),
               ('table_5_communication_tradeoff', COST, 'study_kind=communication', ['C8'])]
    for name,csv,filters,ids in sources:
        columns = {
            'table_1_models_observables': ['layer','models','runtime_observables'],
            'table_2_timing_holdout': ['metric','numerator','denominator','percent','ci95_lower_percent','ci95_upper_percent','value_ms'],
            'table_3_observability_by_consequence': ['is_perturbed','fault_layer','combined_detected','plant_manifestation'],
            'table_4_timing_ablation': ['ablation','timing_detection_coverage_numerator','contract_violations','false_positives',
                'timing_false_alarm_rate_denominator','median_detection_latency_ms','p95_detection_latency_ms',
                'pre_plant_timing_detection_numerator','pre_plant_timing_detection_denominator'],
            'table_5_communication_tradeoff': ['study_kind','policy','hazards','injected_or_overload_runs','critical_exposure_ms',
                'contained','containment_eligible','unnecessary_interventions','unnecessary_eligible','false_interventions',
                'benign_runs','safe_state_duration_ms_total','limp_home_duration_ms_total'],
        }[name]
        for extension in ['csv','md','tex']:
            traces.append({'artifact_name':f'paper_tables/{name}.{extension}','generation_script':GENERATOR,
                           'source_csv':json.dumps([source(csv)]),'source_columns':json.dumps(columns),'filters_applied':filters,
                           'claim_ids':','.join(ids),'caption':'Generated from frozen evidence; N/A retains unavailable/empty endpoints.'})
    write_csv(out/'paper_artifact_traceability.csv',traces)
    return traces


def validate_traceability(out):
    claims=records(out/'claim_evidence_matrix.csv');ids={r['claim_id'] for r in claims}
    for claim in claims:
        path=ROOT/claim['source_csv']
        columns=set(records(path)[0])
        if not set(json.loads(claim['source_columns']))<=columns:raise ValueError('Claim source columns do not resolve: '+claim['claim_id'])
        if claim.get('confidence_source_csv'):
            ci_columns=set(records(ROOT/claim['confidence_source_csv'])[0])
            if not set(json.loads(claim['confidence_source_columns']))<=ci_columns:raise ValueError('Confidence source columns do not resolve')
    for row in records(out/'paper_artifact_traceability.csv'):
        if not (out/row['artifact_name']).is_file():raise ValueError('Missing paper artifact: '+row['artifact_name'])
        columns=set()
        for name in json.loads(row['source_csv']):columns.update(records(ROOT/name)[0])
        if not set(json.loads(row['source_columns']))<=columns:raise ValueError('Unresolved paper source columns: '+row['artifact_name'])
        if not set(row['claim_ids'].split(','))<=ids:raise ValueError('Unresolved claim IDs')
    return len(claims)


def generate(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    write_json(out/'manifests/final_configuration.json',final_configuration())
    tables=create_tables(out);claims=create_claims(out);traces=create_figures(out,tables)
    from .final_documents import generate_documents
    generate_documents(out,claims,tables,traces)
    validate_traceability(out)
    return claims
