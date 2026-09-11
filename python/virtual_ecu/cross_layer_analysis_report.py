"""Tables, figures and evidence-linked interpretation for v3 reanalysis."""
from __future__ import annotations

import json
import hashlib
from collections import Counter

from .cross_layer_analysis import (GROUPS, SC_CLASSES, SEVERITIES, TIMING_CLASSES,
    write_table, metric_summary, sensitivity, distribution, rate, grouped_rows)
from .cross_layer_safety import PROJECT_ROOT
from .cross_layer_observability import observability_matrix, coverage_matrix, OBSERVABILITY_NOTES


def markdown_table(rows, columns):
    def value(v):
        if v is None or v == '':
            return 'N/A'
        return f'{v:.2f}' if isinstance(v, float) else str(v).replace('|', '\\|')
    return '\n'.join(['| '+' | '.join(columns)+' |', '| '+' | '.join('---' for _ in columns)+' |'] +
                     ['| '+' | '.join(value(r.get(k)) for k in columns)+' |' for r in rows])


def timing_summary(rows):
    output = []
    selected = [r for r in rows if r.get('fault_layer') == 'timing']
    for category in TIMING_CLASSES:
        runs = [r for r in selected if r['timing_consequence'] == category]
        result = {'category': category, 'total_runs': len(runs), 'detected': sum(r['detected'] == 1 for r in runs),
                  'missed': sum(r['detected'] == 0 for r in runs)}
        for name, key in (('detection', 'detected'), ('plant_propagation','plant_manifestation'), ('hazard','attributable_hazard'), ('safe_state','safe_state_reached')):
            stat = rate(name, [r.get(key) for r in runs])
            result.update({name+'_'+k: stat[k] for k in ('numerator','denominator','percent')})
        output.append(result)
    return output


def parameter_summary(rows, keys):
    output = []
    groups = sorted({tuple(str(r.get(k)) for k in keys) for r in rows})
    for values in groups:
        selected = [r for r in rows if tuple(str(r.get(k)) for k in keys) == values]
        result = {k: None if v == 'None' else v for k,v in zip(keys,values)}
        result['runs'] = len(selected)
        for name,key in (('no_effect','internal_corruption'), ('control','control_effect'), ('plant','plant_manifestation'),
                         ('hazard','attributable_hazard'), ('detected','detected'), ('contained','hardened_containment')):
            vals = [1-r[key] if name == 'no_effect' and r.get(key) is not None else r.get(key) for r in selected]
            stat = rate(name, vals)
            result[name+'_count'], result[name+'_eligible'], result[name+'_percent'] = stat['numerator'], stat['denominator'], stat['percent']
        result['internal_only_count'] = sum(r['safety_severity'] == SEVERITIES[1] for r in selected)
        result['silent_plant_count'] = sum(r['silent_plant'] == 1 for r in selected)
        output.append(result)
    return output


def figures(output, rows, metrics, ftti, timing, matrix):
    import os
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/virtual_ecu_mpl')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    directory = output/'figures'
    directory.mkdir(exist_ok=True)
    captions = []
    def save(fig, name, caption):
        fig.tight_layout()
        fig.savefig(directory/name, dpi=220)
        plt.close(fig)
        captions.append({'figure': name, 'caption': caption})
    overall = {m['metric']:m for m in metrics if m['dimension'] == 'overall'}
    labels = ('internal_corruption','control_effect','actuator_effect','plant_propagation','hazard')
    stats = [overall['detection_coverage_given_'+k] for k in labels]
    fig,ax = plt.subplots(figsize=(8,4.5))
    ax.bar(range(5), [s['percent'] if s['percent'] is not None else 0 for s in stats], color='#347aa3')
    ax.set_xticks(range(5), [k.replace('_',' ')+'\n'+(f"{s['numerator']}/{s['denominator']}" if s['denominator'] else 'N/A') for k,s in zip(labels,stats)])
    ax.set_ylim(0,110); ax.set_ylabel('Differential alarm coverage (%)')
    save(fig,'detection_coverage_by_propagation_stage.png','Conditional subsets overlap; bars are separate rates, not additive. Counts are detected / reached stage. Hazard n=2 is not a reliability estimate.')
    count = Counter(r['silent_corruption_class'] for r in rows if r.get('injected') == 1)
    fig,ax = plt.subplots(figsize=(7,4.5))
    ax.bar(SC_CLASSES,[count[k] for k in SC_CLASSES],color='#bd7438')
    for k in SC_CLASSES: ax.text(k,count[k]+.4,str(count[k]),ha='center')
    ax.set_ylabel('Runs'); ax.set_xlabel(f"Silent severity cases n={sum(count[k] for k in SC_CLASSES)}; excludes detected and no-effect cases")
    save(fig,'silent_corruption_severity.png','SC0 internal-only, SC1 sensing/control-visible, SC2 actuator/plant without hazard, SC3 no alarm before hazard. SC3 may include late alarms. Zero is an observed count.')
    fig,ax = plt.subplots(figsize=(8,4.8))
    ax.bar(range(5),[r['detected'] for r in timing],label='Detected',color='#347aa3')
    ax.bar(range(5),[r['missed'] for r in timing],bottom=[r['detected'] for r in timing],label='Missed',color='#bd7438')
    ax.set_xticks(range(5),[r['category'].replace('_',' ')+'\n(n='+str(r['total_runs'])+')' for r in timing],rotation=15,ha='right')
    ax.set_ylabel('Timing runs'); ax.yaxis.set_major_locator(MaxNLocator(integer=True)); ax.legend()
    save(fig,'timing_fault_outcomes.png','42 mutually exclusive runs at furthest consequence. Control-only includes last-execution timestamp deviation; these 21 runs have no actuator/plant effect.')
    from .cross_layer_observability import CHANNELS
    codes = {'NOT APPLICABLE':0,'NOT AVAILABLE':1,'INDIRECT':2,'DIRECT':3}
    colors = ['#eeeeee','#a9a9a9','#9dc4db','#24729b']
    fig,ax = plt.subplots(figsize=(12,6.6))
    ax.imshow([[codes[r[k]] for k in CHANNELS] for r in matrix],cmap=ListedColormap(colors),vmin=0,vmax=3,aspect='auto')
    ax.set_yticks(range(len(matrix)),[r['fault_model'].replace('_',' ') for r in matrix])
    ax.set_xticks(range(len(CHANNELS)),[k.replace('_',' ') for k in CHANNELS],rotation=45,ha='right')
    ax.legend(handles=[Patch(color=colors[v],label=k) for k,v in codes.items()],bbox_to_anchor=(.5,1.14),loc='upper center',ncol=4,fontsize=9)
    save(fig,'observability_heatmap.png','Reviewed runtime availability, not empirical detector coverage. Deadline contract and independent truth residual unavailable; last execution and received age available. See observability_analysis.md.')
    layers = sorted({r['fault_layer'] for r in rows if r.get('injected') == 1})
    outcomes = ('No actuator/plant propagation','Actuator only, uncontained','Plant, uncontained','Safe containment','Hazard')
    def outcome(r):
        if r['attributable_hazard'] == 1:return outcomes[4]
        if r['hardened_containment'] == 1:return outcomes[3]
        if r['plant_manifestation'] == 1:return outcomes[2]
        if r['actuator_any_effect'] == 1:return outcomes[1]
        return outcomes[0]
    fig,ax = plt.subplots(figsize=(9,5.4)); bottom=[0]*len(layers)
    for name,color in zip(outcomes,('#d7dce0','#d2ac69','#c88545','#458d9f','#a94442')):
        values=[sum(outcome(r)==name for r in rows if r.get('fault_layer')==layer and r.get('injected')==1) for layer in layers]
        ax.bar(range(len(layers)),values,bottom=bottom,label=name,color=color)
        bottom=[a+b for a,b in zip(bottom,values)]
    ax.set_xticks(range(len(layers)),[k.replace('_',' ')+'\n(n='+str(n)+')' for k,n in zip(layers,bottom)])
    ax.set_ylabel('Injected runs');ax.legend(loc='upper center',bbox_to_anchor=(.5,1.28),ncol=2,fontsize=9)
    save(fig,'safety_outcome_by_fault_layer.png','Mutually exclusive priority: hazard, hardened safe containment, remaining plant, remaining actuator, no actuator/plant propagation. Contained cases may previously reach plant; no double counting.')
    fig,ax = plt.subplots(figsize=(8,4.8))
    for clock,marker in (('injection','o'),('manifestation','s')):
        selected=[r for r in ftti if r['dimension']=='overall' and r['metric']==clock+'_based_experimental_ftti']
        ax.plot([r['ftti_budget_ms']/1000 for r in selected],[float('nan') if r['percent'] is None else r['percent'] for r in selected],marker=marker,label=clock+' clock')
        for r in selected:
            if r['percent'] is not None:ax.annotate(f"{r['numerator']}/{r['denominator']}",(r['ftti_budget_ms']/1000,r['percent']),xytext=(0,8),textcoords='offset points',ha='center',fontsize=9)
    maximum=max((r['percent'] for r in ftti if r['dimension']=='overall' and r['percent'] is not None),default=0)
    ax.set_xlabel('Global experimental time budget (s)');ax.set_ylabel('FTTI pass rate (%)');ax.set_xticks([1,2,5,10]);ax.set_ylim(0,max(20,maximum*1.4));ax.legend()
    save(fig,'ftti_sensitivity.png','Global 1/2/5/10 s budgets with unchanged runs. Injection uses legacy eligibility; manifestation uses hardened eligibility. Denominator change confounds a direct clock comparison; matched-cohort table is also provided.')
    write_table(directory/'figure_caption_data.csv',captions)


def write_package(output, all_rows, transitions):
    rows=[r for r in all_rows if r.get('injected')==1]
    metrics=metric_summary(all_rows); ftti=sensitivity(all_rows)
    timing=timing_summary(rows); matrix=observability_matrix(); coverage=coverage_matrix(rows)
    write_table(output/'campaign_scientific_reanalysis.csv',all_rows)
    write_table(output/'scientific_metric_summary.csv',metrics)
    write_table(output/'safety_relevant_detection_summary.csv',[m for m in metrics if 'detection' in m['metric'] or 'silent' in m['metric']])
    write_table(output/'silent_corruption_severity.csv',rows)
    write_table(output/'silent_corruption_grouped_summary.csv',distribution(rows,'silent_corruption_class',SC_CLASSES))
    misses=[r for r in rows if r['detected']==0]
    run_columns=list(dict.fromkeys(k for r in all_rows for k in r))
    write_table(output/'miss_diagnosis.csv',misses, run_columns)
    write_table(output/'miss_reason_summary.csv',distribution(misses,'miss_reason'))
    write_table(output/'timing_fault_analysis.csv',[r for r in rows if r['fault_layer']=='timing'],run_columns)
    write_table(output/'timing_fault_summary.csv',timing)
    comm=[r for r in rows if r['fault_layer']=='communication']
    memory=[r for r in rows if r['fault_layer']=='memory']
    write_table(output/'communication_fault_analysis.csv',comm)
    write_table(output/'memory_fault_analysis.csv',memory)
    cs=parameter_summary(comm,['fault_model','parameter_communication_delay_ms','parameter_replay_age_ms','parameter_drop_count','parameter_drop_every_n_updates','fault_behavior','operating_profile','fault_injection_ms'])
    ms=parameter_summary(memory,['fault_model','parameter_bit_index','parameter_stuck_polarity','fault_behavior','parameter_duration_ms','parameter_intermittent_on_ms','operating_profile'])
    write_table(output/'communication_parameter_summary.csv',cs)
    write_table(output/'memory_parameter_summary.csv',ms)
    write_table(output/'observability_matrix.csv',matrix)
    wide_coverage=[]
    for model in sorted({r['fault_model'] for r in coverage}):
        wide_coverage.append({'fault_model':model, **{r['mechanism']:r['classification'] for r in coverage if r['fault_model']==model}})
    write_table(output/'detector_coverage_matrix.csv',wide_coverage)
    write_table(output/'detector_coverage_evidence.csv',coverage)
    write_table(output/'ftti_sensitivity.csv',ftti)
    # Hold cohort fixed to separate origin-clock change from eligibility change.
    matched=[r for r in rows if r['hardened_containment'] is not None]
    write_table(output/'ftti_sensitivity_matched_cohort.csv',sensitivity(matched))
    write_table(output/'containment_hardened_summary.csv',[m for m in metrics if 'containment' in m['metric']])
    write_table(output/'containment_class_summary.csv',distribution(rows,'containment_class'))
    write_table(output/'safety_severity_summary.csv',distribution(rows,'safety_severity',SEVERITIES))
    write_table(output/'hazard_state_transitions.csv',transitions,('run_id','time_ms','hazard_state','critical_exposure_ms','consecutive_critical_ms'))
    labels=Counter(r['first_alarm_evidence_label'] for r in rows if r['detected']==1)
    write_table(output/'first_alarm_evidence_summary.csv',[{'label':k,'count':v,'denominator':sum(labels.values())} for k,v in sorted(labels.items())])
    figures(output,all_rows,metrics,ftti,timing,matrix)
    write_narratives(output,rows,metrics,ftti,timing,coverage,cs,ms,labels)
    (output/'scientific_contract.md').write_text((PROJECT_ROOT/'docs/cross_layer_safety_v3.md').read_text())
    sources = [*sorted((PROJECT_ROOT/'src').glob('*.c')), *sorted((PROJECT_ROOT/'include').glob('*.h')),
               *sorted((PROJECT_ROOT/'python/virtual_ecu').glob('cross_layer_*.py')),
               PROJECT_ROOT/'python/virtual_ecu/cross_layer_observability.py',
               PROJECT_ROOT/'python/virtual_ecu/detection_algorithms.py',
               PROJECT_ROOT/'scripts/export_paper_evidence_security_v1.py',
               PROJECT_ROOT/'scripts/analyze_cross_layer_safety.py']
    (output/'implementation_manifest.json').write_text(json.dumps({str(p.relative_to(PROJECT_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2,sort_keys=True)+'\n')


def write_narratives(output,rows,metrics,ftti,timing,coverage,cs,ms,labels):
    overall={m['metric']:m for m in metrics if m['dimension']=='overall'}
    def fraction(key):
        s=overall[key]
        return f"{s['numerator']}/{s['denominator']} ({s['percent']:.2f}%)" if s['denominator'] else 'N/A (0 eligible)'
    misses=[r for r in rows if r['detected']==0]
    counts=Counter(r['silent_corruption_class'] for r in rows)
    tm=[r for r in misses if r['fault_layer']=='timing']
    comm=[r for r in rows if r['fault_layer']=='communication']
    mem=[r for r in rows if r['fault_layer']=='memory']
    hazard=[r for r in rows if r['attributable_hazard']==1]
    table=markdown_table([m for m in metrics if m['dimension']=='overall'],['metric','numerator','denominator','percent'])
    (output/'observability_analysis.md').write_text(OBSERVABILITY_NOTES+'\n\n'+markdown_table(coverage,['fault_model','mechanism','classification','numerator','denominator'])+'\n')
    (output/'ftti_sensitivity.md').write_text('''# Experimental timing sensitivity

The fixed global candidates are 1000, 2000, 5000 and 10000 ms. They span the
1000 ms containment hold through twice the accepted 5000 ms study contract;
they were not optimized per scenario. Outcomes reuse the same final stable-tail
containment confirmation and observed hazard. No simulator or detector is retuned.
Both clocks include the hold. A hazard means failure even if containment is later
observed. No containment and an unexpired observation horizon means N/A.

Injection eligibility preserves v2 internal-only cases. Manifestation eligibility
requires actual applied actuator or plant evidence. Therefore compare
`ftti_sensitivity_matched_cohort.csv` to isolate a clock shift; the main rates
otherwise mix a changed origin with a changed denominator. The baseline study
is descriptive, deterministic and unbalanced; these are not reliability estimates.

'''+markdown_table([r for r in ftti if r['dimension']=='overall'],['metric','ftti_budget_ms','numerator','denominator','excluded_count','percent'])+'\n')
    reason_counts=Counter(r['miss_reason'] for r in misses)
    (output/'miss_diagnosis.md').write_text(f'''# Per-run detector miss audit

All {len(misses)} original misses remain misses. `miss_diagnosis.csv` retains
every run, configuration, propagation timestamp, maximum absolute physical
deviation, runtime score/age/target/feedback observations, DTCs, protection and
fault recovery. Source fields beginning `legacy_truth` or reference deviations
are evaluation evidence, never proposed detector inputs.

Reason counts: {dict(sorted(reason_counts.items()))}.

Reason priority: no effective corruption; timing event absent from current
detector consumption; internal-only; combined score below the fixed 0.900 Hybrid
confirmation floor; otherwise UNRESOLVED. Timing rows also show the score maxima.
This establishes a missing channel and/or unsatisfied aggregate score condition,
not which unlogged Kalman support branch caused it. No persistence/threshold cause
is guessed from injected duration. The accepted CSV does not log every component
or confirmation counter. `raw_alarm_seen_after_injection` distinguishes the raw
alarm waveform from the differential campaign alarm if a baseline also alarms.

'''+markdown_table(misses,['run_id','fault_layer','fault_model','safety_severity','max_physical_deviation_c','max_runtime_detection_score','miss_reason'])+'\n')
    (output/'timing_fault_analysis.md').write_text(f'''# Timing consequences and the 35 misses

All 42 timing runs are in `timing_fault_analysis.csv`; categories are exclusive
by furthest consequence, not by injection type. The v2 control stage includes a
changed last-execution timestamp. Consequently {sum(r['timing_metadata_only'] for r in tm)} missed
control-only runs have scheduler metadata deviation with no changed applied
actuator command/feedback or plant trajectory. They are low-impact masking within
these observed horizons, not proof a missed deadline is universally harmless.

The other {sum(r['plant_manifestation']==1 for r in tm)} timing misses reach the plant;
none reaches the defined hazard. Their physical deviations are small but real.
All timing misses have a combined detector score below 0.900. The existing detector
does not consume last-execution time, and the safety monitor has no timing contract.
This is a combination of masking, absent timing consumption, and insufficient
existing aggregate physical evidence. It does not establish that a timing safety
intervention would improve hazard outcomes: the timing cohort contains no hazards.

'''+markdown_table(timing,list(timing[0]))+'\n')
    (output/'communication_fault_analysis.md').write_text(f'''# Communication evidence

48 runs cover received delays, drops and timestamp-preserving replay. The full
per-run table includes delay/replay age/drop count and period, behavior, operating
profile and injection timestamp. `communication_parameter_summary.csv` gives
explicit counts at each combination; no aggregation hides injection timing.

Detected before plant (both stages observed): {sum(r['detected_before_plant_v3']==1 for r in comm)}.
Silent plant propagation: {sum(r['silent_plant']==1 for r in comm)}.
Defined hazards: {sum(r['attributable_hazard']==1 for r in comm)}.
Recovered without actuator/plant consequence: {sum(r['recovered_without_actuator_or_plant']==1 for r in comm)}.

The hazard cases are a 10000 ms delayed update and a 15000 ms replay at 90100 ms
in the nominal profile. Both alarm before hazard yet fail containment. The study
uses observe_only detector action, and sensor-only DTCs do not request cooling.
This supports examining the evidence-to-protection policy; it does not demonstrate
missing communication detection in the hazardous cases. Short drops are the
communication detection gap. Freshness already provides direct consumed runtime
evidence, so adding a redundant generic communication detector is not justified
by these hazards alone. There is no untrusted/re-written timestamp replay here.

'''+markdown_table(cs,list(cs[0]))+'\n')
    memgroups=parameter_summary(mem,['fault_model','fault_behavior','parameter_bit_index','parameter_stuck_polarity'])
    (output/'memory_fault_analysis.md').write_text(f'''# Memory and stuck-at consequences

72 runs: 36 transient bit flips, 24 permanent stuck constraints and 12 intermittent
stuck-at-1 runs. No-op constraints count as no effective corruption, not success
or detector failure requiring containment. Nominal target is integer 92: bit 3
is already 1 and bit 5 already 0, explaining the 12 matching permanent constraints.
Other studied bits/temporal modes affect real control state; the complete table
retains bit position, polarity, ON interval, duration, profile and injection time.

No effective corruption: {sum(r['safety_severity']=='S0_NO_EFFECT' for r in mem)};
plant propagation: {sum(r['plant_manifestation']==1 for r in mem)};
hazards: {sum(r['attributable_hazard']==1 for r in mem)};
detected: {sum(r['detected']==1 for r in mem)}.

Bit position changes numerical target magnitude and direction, while duration
and profile change propagation and recoverability. This is not an equal-severity
comparison of stuck-at and dynamic faults: permanent/intermittent cases use a
different bit grid and duration distribution. Matching those dimensions is a
necessary next experiment before a superiority claim. Negative results and
non-effective stuck constraints must remain in the injection inventory.

'''+markdown_table(memgroups,list(memgroups[0]))+'\n')
    fsummary=markdown_table([r for r in ftti if r['dimension']=='overall'],['metric','ftti_budget_ms','numerator','denominator','percent'])
    findings=f'''# Cross-layer safety v3 scientific findings

Accepted baseline: 97f18ce (v1 9299c04, v2 e89c27b). This package reads the
182 accepted runs (180 injections, two baselines); it does not change their
detectors, actions, physics, fault semantics, alarms or source evidence.
All conclusions are horizon-limited case proportions from an unequal deterministic
matrix, not population estimates or ISO 26262/OEM-certified safety claims.

## 1. Raw coverage versus consequence

Overall coverage remains {fraction('overall_detection_coverage')}. It is incomplete
as a safety metric: conditioned on plant propagation it is
{fraction('detection_coverage_given_plant_propagation')}, and conditioned on hazard
it is {fraction('detection_coverage_given_hazard')}. Two detected hazards still fail
containment, so better conditional detection does not establish safety.

{table}

Silent plant rate uses plant-propagating runs as denominator; silent hazard rate
uses hazard runs. Separate incidence metrics use all eligible injections. N/A is
excluded, with explicit counts. Control and actuator stage subsets overlap.

## 2. What undetected faults actually reach

Among {len(misses)} misses: no-effect {sum(r['safety_severity']=='S0_NO_EFFECT' for r in misses)};
strict internal-only {sum(r['safety_severity']=='S1_INTERNAL_ONLY' for r in misses)};
control reached {sum(r['control_effect']==1 for r in misses)};
actuator command/feedback reached {sum(r['actuator_any_effect']==1 for r in misses)};
plant reached {sum(r['plant_manifestation']==1 for r in misses)};
hazard reached {sum(r['attributable_hazard']==1 for r in misses)}.
Reached-stage counts overlap. Exclusive silent classes:
{', '.join(k+'='+str(counts[k]) for k in SC_CLASSES)}.
Delivered sample/age corruption is sensing-visible even if the v2 control stage
is absent, so it belongs to SC1, not latent SC0. SC3 allows a late alarm; none is
observed here. All 81 legacy silent cases remain explicitly recorded.

## 3. Timing misses

{sum(r['timing_metadata_only'] for r in tm)}/35 misses are masked at actuator/plant level;
{sum(r['plant_manifestation']==1 for r in tm)}/35 have plant propagation. Thus a majority
has low downstream impact in this study, but it is incorrect to call all 35 harmless.
All timing runs record a control timing effect. No timing hazard is observed.
The timing input gap and sub-confirmation physical scores coexist.

## 4. Communication gaps

The three silent plant communication runs are dropped updates. Delayed updates
and replay each produce one sustained hazard despite pre-hazard alarms. These are
response-policy/containment limitations under observe_only, not hazardous detection
misses. Full parameter/profile/timing rows are in communication_fault_analysis.csv.

## 5. Stuck-at versus dynamic corruption

12 stuck constraints have no effective corruption. Memory otherwise reaches
plant in 54/72 injections, with 26/72 detected and no hazards. Polarity, bit magnitude,
duration and profile matter. The unequal grids cannot establish a generic advantage
of one fault model; matched factorial experiments are still required.

## 6. Global FTTI sensitivity

{fsummary}

Pass rates change mainly between 1 and 2 seconds, and then plateau: the
manifestation rate is unchanged from 2 through 10 seconds, while the legacy
injection rate stops improving at 5 seconds. On the matched 119-run cohort, both
clocks give 6/119 at 2, 5 and 10 seconds; only at 1 second do four fan cases pass
with the later manifestation origin. The lower 5-second manifestation headline
rate therefore comes from cohort selection, not a stricter clock. Outcomes depend on final stable-tail
recovery. Short-lived perturbations can retain thermal differences for seconds;
fault recovery is not equivalent to containment. Fixed budgets are applied globally.

## 7. Manifestation-based interpretation

First applied actuator command/feedback difference (C tolerance 1e-6), or first
plant difference (0.01 C), is a conservative operational safety-relevance proxy.
It is real observed propagation, not a certified danger boundary. It includes
protective command changes and tiny perturbations, which are identified as a
limitation. No actuator/plant effect means N/A origin and no containment required.
This origin is more specific than injection for a safety pathway, but the two
rates also use different cohorts. The matched-cohort sensitivity CSV isolates
clock changes. Signed detection delays preserve alarms preceding manifestation.

## 8. Highest-coverage evidence channels

Fan faults are detected in 6/6 runs, delay and replay each in 12/12, sensor bias in
12/12. Freshness, fan feedback and legacy truth-based sensor evidence are consumed;
timing timestamps are not. First-alarm branch counts: {dict(sorted(labels.items()))}.
Fan health self-test is generated by the accepted fault model even before a
command/actual discrepancy; its 6/6 detection is conditional on that optimistic
feedback model. Healthy actuators follow commands exactly, so wrong commands can
change cooling without any command-minus-actual residual. These are dominant
labels, not independent signal coverage. No channel ablation
was run; claiming innovation or freshness caused all detections would overstate data.

## 9. Missing direct runtime evidence

The last actual execution timestamp exists, but no independent release/deadline
contract is exposed to snapshot monitors or consumed by current safety logic.
Independent true sensor residual is unavailable outside legacy simulator exceptions.
Undelivered sample and replay-injector provenance are evaluation-only. Received
age already supplies a communication signal in the accepted timestamp-preserving protocol.

## 10. Strongest supported research story

Primary: B, Cross-Layer Fault Observability. Fault origin and realized consequence
jointly explain measured coverage and expose a timing interface gap. Backup: C,
Fault Propagation and Safety Containment. The two alarmed hazards and separate
containment clocks support this, but hazard diversity is currently weak. Neither
story has demonstrated literature novelty or production ECU generalization yet.

Hazard runs:
{markdown_table(hazard,['run_id','propagation_detector_ms','hazard_entry_ms','hazard_exit_ms','critical_exposure_time_ms','hardened_containment'])}

Legacy containment: {fraction('legacy_v2_containment')}. Hardened containment:
{fraction('hardened_containment_rate')}. Removing unnecessary containment changes
the denominator; old values are retained verbatim. See docs/cross_layer_safety_v3.md
for the exact hazard, timing, recovery and censoring contracts.
'''
    (output/'scientific_findings.md').write_text(findings)
    (output/'recommended_research_direction.md').write_text('''# Evidence-ranked research directions

| Rank / candidate | Evidence strength | Novelty potential | Additional implementation | Required experiments | Main risk | Current data support |
| --- | --- | --- | --- | --- | --- | --- |
| 1 / B: Cross-Layer Fault Observability | 93 misses diagnosed; 35 timing misses split into 21 masked and 14 plant-propagating; explicit availability/consumption boundary | Potentially useful joint origin/consequence accounting; literature novelty not evaluated | Read-only component telemetry, trusted scheduler observation contract; later isolated timing monitor | Matched fault severities, operating profiles, frozen-detector channel ablations and negative controls | Existing legacy truth inputs and unbalanced grids can confound origin comparisons | Descriptive observability claim yes; general superiority no |
| 2 / C: Fault Propagation and Safety Containment | Two pre-hazard alarms fail containment; stable-tail clocks and hardened denominators are auditable | Potential methodological contribution in propagation-to-response evaluation | Separate experimental response-policy harness, keeping accepted Hybrid frozen | More hazard profiles, longer horizons, protective-policy A/B, FTTI and hold sensitivity | Only two hazards; experimental thresholds and proxy safety origin | Prototype methodological case study yes; calibrated safety assurance no |
| 3 / A: Beyond Stuck-at Faults | 72 memory cases include 12 no-op constraints and 54 plant outcomes, versus timing/communication propagation | Comparative dynamic propagation study possible | Matched campaign specification, not new detector | Match bit positions/polarities, effective magnitudes, duty cycles, durations and operating points | Current stuck/dynamic grids are unequal; easy but invalid superiority claim | Motivation yes; controlled comparison not yet |
| 4 / D: Timing and Communication Fault Monitoring | Timing consumption gap demonstrated; communication hazardous cases already detected | Future monitor plus response-policy contribution possible | Independent runtime timing monitor using trusted timestamps/contracts; communication work only after identified freshness/response gaps | Baseline false alarms, benign timing jitter, masked faults, propagating faults, response interventions and ablations | No timing hazards; generic communication detector duplicates existing freshness; no improvement evidence yet | Justification for targeted experiment yes; effective new monitoring method no |

Primary B, backup C. Next implement only an opt-in, independent timing observation
and monitor path with trusted scheduler release/completion/deadline inputs, no fault
labels, injection flags or reference trajectories. Initially observe_only. Validate
the 21 masked and 14 silent plant timing cases separately; preserve all Hybrid and
HETIA outputs. This is justified by a consumed-evidence gap, not a promise to prevent
hazards (none occurred in the timing cohort). Do not count alarming every harmless
deadline as a safety improvement.

For communication, first test an opt-in protective response to already available
freshness evidence, alongside a baseline/no-fault false-intervention study. The two
hazards alarmed before hazard under observe_only, so changing detection thresholds
does not address their demonstrated failure. Short-drop silent propagation needs
duration/physical-significance experiments before tightening freshness sensitivity.

Suggested next implementation prompt: Add an isolated, disabled-by-default runtime
timing monitor accepting only a trusted scheduler observation contract. Preserve
existing detectors and safety behavior by default; never feed injector provenance.
Compare detection and false interventions by actual consequence, using matched
benign jitter, masked timing faults and plant-propagating faults. Keep HETIA evidence
unchanged and report safety outcomes separately from deadline coverage. In a separate
experiment, evaluate protective policy for already-detected stale samples without
retuning Hybrid. Do not make an OEM/ISO safety claim.
''')
