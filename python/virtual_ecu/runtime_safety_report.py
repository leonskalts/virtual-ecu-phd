"""Separate mechanism coverage, paired interventions and scientific trade-offs."""
from collections import Counter
import hashlib
import json

from .cross_layer_analysis import write_table
from .cross_layer_analysis_report import markdown_table
from .cross_layer_safety import PROJECT_ROOT
from .runtime_safety_study import study_statistics, ablation_summary


def write_package(output,rows):
    timing=[r for r in rows if r['study_kind']=='timing']
    comm=[r for r in rows if r['study_kind']=='communication']
    ts=study_statistics(timing);cs=study_statistics(comm);ablation=ablation_summary(timing)
    write_table(output/'timing_monitor_runs.csv',timing)
    write_table(output/'timing_monitor_summary.csv',ts)
    write_table(output/'timing_monitor_ablation.csv',ablation)
    write_table(output/'timing_false_positive_summary.csv',[r for r in ts if r['metric'] in ('timing_false_alarm_rate','existing_false_alarm_rate','false_intervention_rate')])
    write_table(output/'communication_response_runs.csv',comm)
    write_table(output/'communication_response_summary.csv',cs)
    attribution=('run_id','study_kind','mode_id','pair_id','v3_run_id','existing_alarm_ms','timing_alarm_ms',
                 'first_detection_mechanism','first_alarm_ms','communication_first_alarm_ms','timing_first_request_ms',
                 'communication_first_request_ms','runtime_safety_first_request_ms','runtime_safety_first_action_ms',
                 'propagation_safe_state_ms','intervention_class')
    write_table(output/'mechanism_attribution.csv',rows,attribution)
    write_table(output/'intervention_summary.csv',rows,('run_id','study_kind','mode_id','injected','observe_consequence',
        'policy_intervention','intervention_class','false_intervention','unnecessary_intervention',
        'unnecessary_transient_intervention','safety_action_requested','runtime_safety_first_action_ms',
        'intervention_order_vs_plant','intervention_order_vs_hazard','observe_hazard','attributable_hazard',
        'observe_critical_exposure_ms','critical_exposure_time_ms','hazard_prevented','hazard_introduced',
        'observe_containment','fixed_cohort_containment','fixed_cohort_injection_ftti'))
    tradeoffs=[]
    for kind,selected in (('timing',timing),('communication',comm)):
        for mode in sorted({r['mode_id'] for r in selected}):
            group=[r for r in selected if r['mode_id']==mode]
            injected=[r for r in group if r['injected']==1]
            counts=Counter(r['intervention_class'] for r in group)
            tradeoffs.append({'study_kind':kind,'mode_id':mode,'total_runs':len(group),'injected_runs':len(injected),
                'intervention_count':sum(r['policy_intervention']==1 for r in group),
                'true_protective_hazard_mitigated':counts['TRUE_PROTECTIVE_HAZARD_MITIGATED'],
                'unnecessary_interventions':counts['UNNECESSARY_NO_DOWNSTREAM'],
                'false_interventions':counts['FALSE_INTERVENTION'],
                'propagating_fault_responses_benefit_unproven':counts['RESPONSE_TO_PROPAGATING_FAULT_BENEFIT_UNPROVEN'],
                'hazards':sum(r['attributable_hazard']==1 for r in injected),
                'hazards_prevented':sum(r['hazard_prevented']==1 for r in injected),
                'hazards_introduced':sum(r['hazard_introduced']==1 for r in injected),
                'critical_exposure_total_ms':sum(r['critical_exposure_time_ms'] for r in injected),
                'contained':sum(r['fixed_cohort_containment']==1 for r in injected),
                'containment_eligible':sum(r['fixed_cohort_containment'] is not None for r in injected),
                'benign_runs':sum(r['injected']==0 for r in group),
                'no_downstream_injected_runs':sum(r['unnecessary_intervention'] is not None for r in injected)})
    write_table(output/'safety_tradeoff_summary.csv',tradeoffs)
    grouped=[]
    for kind,selected in (('timing',timing),('communication',comm)):
        for mode in sorted({r['mode_id'] for r in selected}):
            for dimension in ('fault_model','fault_behavior','operating_profile','observe_consequence'):
                grouped.extend({'study_kind':kind,'mode_id':mode,**r} for r in study_statistics([r for r in selected if r['mode_id']==mode],dimension))
    write_table(output/'runtime_safety_grouped_summary.csv',grouped)
    previous=[r for r in timing if r['mode_id']=='combined_observe' and r['v3_run_id'] is not None]
    write_table(output/'previous_timing_misses.csv',[r for r in previous if r['v3_detector_miss']==1])
    generate_figures(output,timing,comm,ts,ablation,tradeoffs)
    write_findings(output,timing,comm,ts,cs,ablation,tradeoffs,previous)
    for filename in ('runtime_timing_observability.md','runtime_safety_response_v4.md'):
        path=PROJECT_ROOT/'docs'/filename
        if path.is_file():(output/filename).write_text(path.read_text())
    sources=[*sorted((PROJECT_ROOT/'src').glob('*.c')),*sorted((PROJECT_ROOT/'include').glob('*.h')),
             *sorted((PROJECT_ROOT/'python/virtual_ecu').glob('runtime_safety*.py')),
             PROJECT_ROOT/'scripts/run_runtime_safety_studies.py',PROJECT_ROOT/'scripts/export_paper_evidence_security_v1.py']
    (output/'implementation_sha256.json').write_text(json.dumps({str(p.relative_to(PROJECT_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},sort_keys=True,indent=2)+'\n')


def generate_figures(output,timing,comm,summary,ablation,tradeoffs):
    import os
    os.environ.setdefault('MPLCONFIGDIR','/tmp/virtual_ecu_mpl')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    directory=output/'figures';directory.mkdir(exist_ok=True);captions=[]
    def save(fig,name,caption):
        fig.tight_layout();fig.savefig(directory/name,dpi=220);plt.close(fig)
        captions.append({'figure':name,'caption':caption})
    observed=[r for r in timing if r['mode_id']=='combined_observe' and r['injected']==1]
    fig,ax=plt.subplots(figsize=(7,4.5))
    columns=('detected','timing_monitor_detected','combined_observational_detected')
    counts=[sum(r[k]==1 for r in observed) for k in columns]
    ax.bar(range(3),[100*n/len(observed) for n in counts],color=['#7c8996','#287b9c','#508661'])
    ax.set_xticks(range(3),[label+f'\n{n}/{len(observed)}' for label,n in zip(('Existing detector','Timing monitor','Combined observation'),counts)])
    ax.set_ylim(0,110);ax.set_ylabel('Injected timing-run coverage (%)')
    save(fig,'timing_monitor_coverage.png','Same observe-only trajectories, distinct existing/timing alarms. Combined is their union, never an extra detector or intervention count.')
    consequences=('NO_DOWNSTREAM','CONTROL_ONLY','ACTUATOR_ONLY','PLANT','HAZARD')
    fig,ax=plt.subplots(figsize=(9,4.8))
    for offset,key,label,color in ((-.2,'detected','Existing','#7c8996'),(.2,'timing_monitor_detected','Timing','#287b9c')):
        values=[];labels=[]
        for category in consequences:
            group=[r for r in observed if r['observe_consequence']==category]
            n=sum(r[key]==1 for r in group);values.append(100*n/len(group) if group else 0)
            labels.append(f'{n}/{len(group)}' if group else 'N/A')
        positions=[i+offset for i in range(len(consequences))]
        ax.bar(positions,values,width=.38,label=label,color=color)
        for x,y,text in zip(positions,values,labels):ax.text(x,y+2,text,ha='center',fontsize=8)
    ax.set_xticks(range(len(consequences)),['No downstream','Control only','Actuator only','Plant','Hazard'])
    ax.set_ylim(0,115);ax.set_ylabel('Coverage within consequence class (%)');ax.legend(loc='upper center',bbox_to_anchor=(.5,1.16),ncol=2)
    save(fig,'timing_detection_by_consequence.png','Exclusive furthest consequence from the no-action reference. Control-only includes changed execution timestamps without actuator/plant change. Empty cohorts are N/A.')
    fig,ax=plt.subplots(figsize=(8,4.5))
    ax.bar(range(3),[100*r['detected']/r['injected_runs'] for r in ablation],color='#287b9c')
    ax.set_xticks(range(3),[r['mode_id'].replace('_',' ')+f"\n{r['detected']}/{r['injected_runs']}; FP {r['false_alarms']}/{r['benign_runs']}" for r in ablation])
    ax.set_ylabel('Injected timing-run coverage (%)');ax.set_ylim(0,110)
    save(fig,'timing_monitor_ablation.png','Same fault matrix and global contract. Execution-age-only includes missed-execution/cancellation evidence. Equal coverage does not imply equal alarm latency.')
    fig,ax=plt.subplots(figsize=(8,4.8))
    data=[];labels=[]
    for a in ablation:
        values=[r['timing_detection_latency_ms'] for r in timing if r['mode_id']==a['mode_id'] and r['injected']==1 and r['timing_detection_latency_ms'] is not None]
        data.append(values);labels.append(a['mode_id'].replace('_',' ')+f'\n(n={len(values)})')
    ax.boxplot(data,labels=labels,showmeans=True);ax.set_ylabel('First timing violation → timing alarm (ms)')
    save(fig,'timing_detection_latency.png','Observed first contract violation is the common clock origin for every ablation. Absent endpoints excluded; same-tick zero latency is valid.')
    ctr=[r for r in tradeoffs if r['study_kind']=='communication']
    ctr.sort(key=lambda r:r['mode_id']!='observe_only')
    fig,axes=plt.subplots(1,3,figsize=(11,4.5))
    for ax,key,ylabel in zip(axes,('hazards','critical_exposure_total_ms','contained'),('Hazard runs','Total critical exposure (ms)','Contained / eligible runs')):
        ax.bar(range(2),[r[key] for r in ctr],color=['#7c8996','#287b9c'])
        ax.set_xticks(range(2),['Observe only','Protective action'],rotation=15)
        ax.set_ylabel(ylabel);ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        for i,r in enumerate(ctr):
            text=f"{r[key]}/{r['containment_eligible']}" if key=='contained' else f"{r[key]}/{r['injected_runs']}" if key=='hazards' else str(r[key])
            ax.annotate(text,(i,r[key]),xytext=(0,5),textcoords='offset points',ha='center')
        ax.margins(y=.2)
    save(fig,'communication_safety_response.png','48 paired faults per mode plus two no-fault profiles. Containment denominator fixed to the no-action actuator/plant cohort; hazard prevention is not containment.')
    interventions=[r for r in tradeoffs if r['mode_id'] in ('combined_protect','protective_action')]
    fig,ax=plt.subplots(figsize=(9,5))
    bottom=[0]*len(interventions)
    for key,label,color in (('true_protective_hazard_mitigated','Observed hazard mitigated','#508661'),
                             ('propagating_fault_responses_benefit_unproven','Propagating fault; benefit unproven','#287b9c'),
                             ('unnecessary_interventions','No actuator/plant effect without action','#d2a25c'),
                             ('false_interventions','No-fault intervention','#b05249')):
        values=[r[key] for r in interventions]
        ax.bar(range(len(interventions)),values,bottom=bottom,label=label,color=color)
        for index,(count,base) in enumerate(zip(values,bottom)):
            if count:ax.text(index,base+count/2,str(count),ha='center',va='center',color='black' if key=='unnecessary_interventions' else 'white',fontsize=9)
        bottom=[a+b for a,b in zip(bottom,values)]
    ax.set_xticks(range(len(interventions)),[r['study_kind']+f"\n{r['intervention_count']}/{r['total_runs']} runs intervened" for r in interventions])
    ax.set_ylabel('Intervened runs');ax.yaxis.set_major_locator(MaxNLocator(integer=True));ax.legend(loc='upper center',bbox_to_anchor=(.5,1.35),fontsize=9,ncol=2)
    save(fig,'intervention_tradeoff.png','Exclusive categories among actual incremental policy interventions. A response to plant propagation is not automatically credited as beneficial. Denominators include both faults and no-fault runs.')
    write_table(directory/'figure_caption_data.csv',captions)


def write_findings(output,timing,comm,ts,cs,ablation,tradeoffs,previous):
    observed=[r for r in timing if r['mode_id']=='combined_observe' and r['injected']==1]
    misses=[r for r in previous if r['v3_detector_miss']==1]
    plantmiss=[r for r in previous if r['v3_plant_propagating_miss']==1]
    benign=[r for r in timing if r['mode_id']=='combined_observe' and r['injected']==0]
    comm_observe=next(r for r in tradeoffs if r['study_kind']=='communication' and r['mode_id']=='observe_only')
    comm_protect=next(r for r in tradeoffs if r['study_kind']=='communication' and r['mode_id']=='protective_action')
    timing_protect=next(r for r in tradeoffs if r['study_kind']=='timing' and r['mode_id']=='combined_protect')
    oldhazards=[r for r in comm if r['mode_id']=='protective_action' and r['observe_hazard']==1]
    text=f'''# V4: timing observability and communication safety response

Baseline: 8dcefbe, accepted v3. Existing Hybrid and every other detector remain
unchanged. Two independent opt-in mechanisms are evaluated: a scheduler-only
timing monitor and a safety policy consuming existing alarm plus freshness status.
All legacy/default outputs remain reproducible. This is experimental safety action
in a test-enabled Virtual ECU, not ISO 26262 certification.

## Study design

Timing: {len(timing)} simulator runs across five modes. Each mode has
{len(observed)} injected cases and {len(benign)} no-fault operating profiles. The
72-case matrix balances model, behavior and profile counts, retains all 42 v2
timing cases, and adds permanent absence/delay and extra deadline injection times.
To avoid artificial duplicates, deadline transient/permanent use six injection
times; task-delay uses three times and two magnitudes. These grids differ, so
pooled between-model comparisons are not matched causal estimates. Ablations and
action modes are exactly matched within each case. All faults are deterministic;
one seed avoids pretending repetition provides stochastic confidence.

Communication: {len(comm)} simulator runs, pairing every one of the 48 accepted
communication cases and both no-fault profiles under two policies. Existing
detector action stays observe_only; the new policy makes its own explicit request.

## 1. Does direct timing observation improve detection?

Existing detection reaches {sum(r['detected']==1 for r in observed)}/{len(observed)}
timing injections. The combined timing monitor reaches
{sum(r['timing_monitor_detected']==1 for r in observed)}/{len(observed)}. Actual
timing-contract violations occur in {sum(r['timing_contract_violation_observed']==1 for r in observed)}
of those cases. The observational union reaches
{sum(r['combined_observational_detected']==1 for r in observed)}/{len(observed)}.
No action is credited as detection, and the existing detector's waveform is
unchanged in observation-only comparisons. Some newly detected timing violations
have negligible downstream consequence, which remains explicit in the tables.
The no-action timing cohort has {sum(r['attributable_hazard']==1 for r in observed)}/{len(observed)}
hazards, including the added permanent cases; timing coverage conditional on hazard
is therefore N/A. This campaign establishes no timing-hazard prevention benefit.

## 2. The previous 35 timing misses

Exact parameter/profile matching finds {len(misses)} prior misses. Now detected:
{sum(r['timing_monitor_detected']==1 for r in misses)}; still missed:
{sum(r['timing_monitor_detected']==0 for r in misses)}.
`previous_timing_misses.csv` retains the v3 run IDs and per-run timings.

## 3. The previous 14 silent plant-propagating timing cases

Matched cases: {len(plantmiss)}. Now detected:
{sum(r['timing_monitor_detected']==1 for r in plantmiss)}; strictly before plant:
{sum(r['timing_alarm_before_plant']==1 for r in plantmiss)}; same tick:
{sum(r['timing_alarm_order_vs_plant']=='SAME_TICK' for r in plantmiss)}; after plant:
{sum(r['timing_alarm_order_vs_plant']=='AFTER' for r in plantmiss)}.
Deferred jobs are legitimate until their deadline or a cancelled release is
observed. A same-tick alarm is not relabeled as pre-plant success. These timestamps
have 100 ms resolution and compare against the unchanged no-action trajectory.

## 4. Benign/legal behavior and false alarms

Combined timing false alarms: {sum(r['timing_monitor_detected']==1 for r in benign)}/{len(benign)}
no-fault profiles, covering normal repeated scheduling and profile transitions.
Timing protective-mode false interventions: {timing_protect['false_interventions']}/{timing_protect['benign_runs']}.
Communication protective-mode false interventions: {comm_protect['false_interventions']}/{comm_protect['benign_runs']}.
These are finite run proportions, not operational false-alarm probabilities.
The simulator has 100 ms ticks and instantaneous control computations. It cannot
produce meaningful sub-period execution jitter without changing accepted scheduling
semantics. Legal jitter/deadline-boundary behavior is tested with explicitly
synthetic scheduler-event fixtures, not fabricated as campaign runs.

## 5. Which timing evidence adds value?

{markdown_table(ablation,list(ablation[0]))}

Execution-age-only includes missed expected execution/cancellation evidence. It
must not be interpreted as an ablation of age alone. The combined monitor can
observe cancellation immediately, while deadline-only waits for the cancelled
job's deadline. The current one-job dispatcher couples pending overruns with
rejected releases; independent evidence contributions are therefore limited by
this scheduler design. Equal coverage is a valid negative ablation result.

## 6. Is a separate monitor justified?

Yes for direct timing-contract observability: the same physical trajectories
expose real scheduler events that existing residual/thermal mechanisms do not
consume. This does not establish that every deadline alarm warrants intervention.
In protective mode, isolated single anomalies remain observational; repeated
violating periods request precautionary cooling, and critical execution absence
requests limp-home. Global thresholds are expressed in task periods/deadlines,
not configured separately per injected scenario.

## 7. Communication action, hazards and exposure

Observe-only hazards: {comm_observe['hazards']}/{comm_observe['injected_runs']}.
Protective-action hazards: {comm_protect['hazards']}/{comm_protect['injected_runs']}.
Observed hazards prevented: {comm_protect['hazards_prevented']}; introduced hazards:
{comm_protect['hazards_introduced']}. Total critical exposure changes from
{comm_observe['critical_exposure_total_ms']} to {comm_protect['critical_exposure_total_ms']} ms.
Containment changes from {comm_observe['contained']}/{comm_observe['containment_eligible']}
to {comm_protect['contained']}/{comm_protect['containment_eligible']} on the **same**
no-action actuator/plant cohort. Action-generated cooling differences do not
enlarge the denominator. Hazard avoidance and final-tail containment are distinct;
earlier protection need not satisfy the existing reference-resolution contract.

Previously hazardous pairs:

{markdown_table(oldhazards,['run_id','existing_alarm_ms','runtime_safety_first_action_ms','observe_hazard_ms','observe_critical_exposure_ms','critical_exposure_time_ms','attributable_hazard','fixed_cohort_containment'])}

## 8. Cost and unnecessary interventions

Timing protective interventions: {timing_protect['intervention_count']}/{timing_protect['total_runs']}.
Of these, {timing_protect['unnecessary_interventions']} occur where the matched
observe-only fault has no actuator/plant consequence; denominator
{timing_protect['no_downstream_injected_runs']} such injected runs.
Communication unnecessary interventions: {comm_protect['unnecessary_interventions']}/
{comm_protect['no_downstream_injected_runs']} such runs. No-fault interventions are
reported separately above. A response to a propagating but nonhazardous fault has
unproven benefit, rather than being automatically labeled true protection.
The classification is horizon-limited and uses the accepted small propagation
tolerances; it is not a vehicle-level harm/cost assessment. Load derating and
cooling changes are real existing safety mechanisms, not direct plant edits.

## 9. Separate semantic mechanisms

Timing uses trusted release/admission/cancellation/start/completion bookkeeping.
Communication policy consumes an already-active existing detector alarm together
with existing failed freshness status. Neither consumes fault ID/model/activity,
known injected delay, reference trajectory or future hazard. They remain separate
from Hybrid and from one another. Policy request, incremental applied response,
old alarm and timing alarm timestamps are separate. Ties are SIMULTANEOUS, and
earlier old-detector alarms are never credited to the new monitor.

## 10. Research direction

The evidence strengthens Cross-Layer Fault Observability through a controlled
addition of the missing originating-layer channel. Communication pairs separately
demonstrate that detection and containment are different problems. Timing coverage
alone is insufficient: before-plant limits, benign testing scope, unnecessary
interventions, coupled ablation evidence and final-tail containment failures remain
explicit. Literature novelty and ECU/vehicle generalization are not established.

Next: evaluate an independent scheduler with measured execution duration, legal
jitter and overload, retaining the frozen monitor rules initially. Add matched
action-cost experiments and longer post-recovery horizons to explain containment
failures before changing that contract. Keep Hybrid and HETIA baselines frozen.

## Reproduction and package

Run `python3 scripts/run_runtime_safety_studies.py`. Captured configurations,
commands, raw SHA-256 manifest, implementation hashes, six figures and denominator-
explicit tables are included. Original v1/v2/v3 evidence is never overwritten.
The runtime trust and policy contracts are documented in the accompanying Markdown
files. Synthetic unit tests are not included among real campaign evidence.
'''
    (output/'v4_findings.md').write_text(text)
