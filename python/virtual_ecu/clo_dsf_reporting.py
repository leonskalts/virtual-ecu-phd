"""Publication-readable DEVELOPMENT figures and candid, generated findings."""
from __future__ import annotations
import csv
import gzip
import json
import os
from pathlib import Path
from .clo_dsf_development import ORIGINS, METHODS, aggregate, write_csv, write_json, sha, ROOT, STUDY


def figures(out,rows,summaries,layers,confusion):
    os.environ.setdefault('MPLCONFIGDIR','/tmp/virtual_ecu_mpl')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    label='DEVELOPMENT RESULTS — NOT FINAL HOLDOUT'
    val=[s for s in summaries if s['partition']=='development-validation']
    selected=['Simple OR','Weighted Sum','Plain DS','CLO-DSF','Hybrid']
    lookup={s['method']:s for s in val}
    captions=[]
    def save(fig,name,caption):
        fig.suptitle(label,fontsize=12)
        fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'figures'/name,dpi=220)
        plt.close(fig);captions.append({'figure':name,'caption':caption})
    def bars(names,key,name,ylabel,percent=False):
        fig,ax=plt.subplots(figsize=(8,4.8))
        values=[lookup[n][key] for n in names]
        ax.bar(names,[(v or 0)*(100 if percent else 1) for v in values],color='#47758c')
        for i,v in enumerate(values):
            if v is None:ax.text(i,0,'N/A',ha='center')
        ax.set_ylabel(ylabel);ax.tick_params(axis='x',rotation=20);ax.grid(axis='y',alpha=.2)
        if percent:ax.set_ylim(0,105)
        save(fig,name,f'{key}; validation configuration proportions; N/A is not zero. See comparison CSV for denominators.')
    fig,ax=plt.subplots(figsize=(10,5))
    for j,method in enumerate(selected):
        values=[next(r['coverage'] for r in layers if r['partition']=='development-validation' and r['origin']==o and r['method']==method) for o in ORIGINS]
        ax.bar(np.arange(5)+(j-2)*.15,[100*(v or 0) for v in values],.15,label=method)
    ax.set_xticks(range(5),[o.replace('_','\n') for o in ORIGINS]);ax.set_ylabel('Detection coverage (%)');ax.set_ylim(0,110)
    ax.legend(ncol=3,fontsize=8);save(fig,'detection_by_origin.png','48 injected configurations per origin. Masked/no-effect injections retained.')
    bars(selected,'coverage_given_plant_manifestation','detection_given_plant_propagation.png','Detection given plant manifestation (%)',True)
    bars(selected,'benign_false_alarms','false_alarm_comparison.png','Benign runs with any alarm (of 96)')
    fig,ax=plt.subplots(figsize=(8,5))
    x=np.arange(len(selected))
    for offset,key,name in [(-.18,'latency_median_ms','Median'),(.18,'latency_p95_ms','P95')]:
        ax.bar(x+offset,[lookup[m][key] or 0 for m in selected],.36,label=name)
    ax.set_xticks(x,selected,rotation=20);ax.set_ylabel('Latency among detected runs (ms)');ax.legend()
    save(fig,'latency_comparison.png','Missed runs excluded, never assigned zero latency; sample counts in comparison CSV.')
    ab=['Plain DS','A1 Observability','A2 Propagation','CLO-DSF']
    fig,axes=plt.subplots(1,3,figsize=(12,4.5))
    for ax,key,title in zip(axes,['coverage','localization_accuracy','mean_ignorance'],['Coverage','Localization accuracy (UNKNOWN retained)','Mean ignorance']):
        ax.bar(range(4),[lookup[m][key] or 0 for m in ab],color='#47758c');ax.set_xticks(range(4),['A0','A1','A2','A3']);ax.set_ylim(0,1);ax.set_title(title,fontsize=10)
    save(fig,'ablation_results.png','Same validation runs; A0→A1 also changes conflict rule if Yager was selected. Negative contributions retained.')
    matrix=np.array([[r[o] for o in [*ORIGINS,'UNKNOWN']] for r in confusion])
    fig,ax=plt.subplots(figsize=(9,6));im=ax.imshow(matrix,cmap='Blues',vmin=0)
    for i in range(5):
        for j in range(6):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>matrix.max()/2 else 'black')
    ax.set_xticks(range(6),[s.replace('_','\n') for s in [*ORIGINS,'UNKNOWN']],rotation=25)
    ax.set_yticks(range(5),ORIGINS);ax.set_ylabel('True injected origin — EVALUATION ONLY');ax.set_xlabel('Estimated origin at first alarm; misses included as UNKNOWN')
    fig.colorbar(im,ax=ax,label='Configurations');save(fig,'localization_confusion_matrix.png','Rows are evaluator-only truth; columns include UNKNOWN and missed detections.')
    valrows=[r for r in rows if r['method']=='CLO-DSF' and r['partition']=='development-validation']
    fig,ax=plt.subplots(figsize=(7,4.8))
    ax.boxplot([[r['mean_ignorance'] for r in valrows if bool(r['injected'])==flag] for flag in [False,True]],labels=['Benign','Faulty'],showmeans=True)
    ax.set_ylabel('Per-run mean ignorance mass');save(fig,'ignorance_fault_vs_benign.png','Full-run means include pre-injection operation; not calibrated probabilities.')
    traces=[]
    for origin in [*ORIGINS,'NORMAL']:
        # First run by ID, no favorable-outcome filtering.
        row=min((r for r in valrows if r['origin']==origin),key=lambda r:r['run_id'])
        src=out/'traces'/f"{row['run_id']}.clo_dsf.csv.gz"
        with gzip.open(src,'rt') as f:trace=list(csv.DictReader(f))
        write_csv(out/'traces'/f'evidence_trace_{origin.lower()}.csv',trace)
        t=[int(r['time_ms'])/1000 for r in trace]
        fig,axes=plt.subplots(4,1,figsize=(10,9),sharex=True)
        for ch in ['timing','communication','memory_control','sensor_control','actuator','plant']:
            axes[0].plot(t,[float(r[ch+'_evidence']) for r in trace],label=ch)
        axes[0].legend(ncol=3,fontsize=8);axes[0].set_ylabel('Layer evidence')
        for key,name in [('fault_belief','Abnormal belief'),('ignorance_mass','Ignorance'),('conflict_mass','Max conflict K')]:axes[1].plot(t,[float(r[key]) for r in trace],label=name)
        axes[1].legend(ncol=3,fontsize=8);axes[1].set_ylabel('Fused evidence')
        axes[2].step(t,[['NORMAL','SUSPECT','CONFIRMED'].index(r['detector_state']) for r in trace],where='post',label='Detector state')
        axes[2].step(t,[int(r['propagation_support']) for r in trace],where='post',label='Propagation support')
        axes[2].set_yticks([0,1,2],['NORMAL','SUSPECT','CONFIRMED']);axes[2].legend(fontsize=8)
        origins=['UNKNOWN',*ORIGINS]
        axes[3].step(t,[origins.index(r['estimated_origin']) for r in trace],where='post');axes[3].set_yticks(range(6),origins,fontsize=8)
        axes[3].set_xlabel('Runtime (s)');axes[3].set_ylabel('Estimated origin')
        for ax in axes:
            if row['injected']:ax.axvline(row['start_ms']/1000,color='gray',ls=':',label='Injection (evaluation)')
            if row['propagation_plant_ms'] is not None:ax.axvline(row['propagation_plant_ms']/1000,color='#ae433d',ls='--',label='Plant manifestation (evaluation)')
            ax.grid(alpha=.15)
        axes[0].set_title(f"{row['run_id']} · {origin} · dotted: injection; dashed red: plant (evaluation only)",fontsize=10)
        name=f'evidence_trace_{origin.lower()}.png';save(fig,name,'Earliest validation run ID per origin; selection does not depend on detection success.')
        traces.append({k:row[k] for k in ['run_id','origin','model','behavior','start_ms','propagation_plant_ms','detected','origin_at_alarm']})
    write_csv(out/'traces/representative_cases_evaluation_only.csv',traces)
    write_csv(out/'figures/captions.csv',captions)


def findings(out,rows,summaries,chosen):
    val={r['method']:r for r in summaries if r['partition']=='development-validation'}
    train=next(r for r in summaries if r['partition']=='development-train' and r['method']=='CLO-DSF')
    c=val['CLO-DSF'];f=[r for r in rows if r['method']=='CLO-DSF' and r['partition']=='development-validation' and r['injected']]
    gate=train['benign_false_alarms']==0 and (c['macro_coverage'] or 0)>=.5 and (c['localized_precision'] or 0)>=.7
    def pct(v):return 'N/A' if v is None else f'{100*v:.2f}%'
    pairs={}
    for r in f:
        if r['detected'] and r['origin_at_alarm'] not in ['UNKNOWN',r['origin']]:
            key=r['origin']+' → '+r['origin_at_alarm'];pairs[key]=pairs.get(key,0)+1
    text=f'''# CLO-DSF development findings

DEVELOPMENT RESULTS — NOT FINAL HOLDOUT. No final safety, universality, WCET,
ISO 26262 or Bayesian probability claim is supported. Dempster–Shafer itself and
Yager's rule are established methods, not claimed contributions.

1. **Macro coverage versus simple baselines:** CLO-DSF {pct(c['macro_coverage'])};
   OR {pct(val['Simple OR']['macro_coverage'])}; Weighted Sum {pct(val['Weighted Sum']['macro_coverage'])};
   Plain DS {pct(val['Plain DS']['macro_coverage'])}. The table reports actual results;
   richer outputs alone do not establish improved detection.
2. **Observability contribution:** A0 coverage {pct(val['Plain DS']['coverage'])},
   A1 {pct(val['A1 Observability']['coverage'])}; localization accuracy
   {pct(val['Plain DS']['localization_accuracy'])} → {pct(val['A1 Observability']['localization_accuracy'])}.
   If Yager is selected, this comparison also changes conflict handling and does
   not isolate discounting alone. TRAIN paired candidate results compare rules.
3. **Propagation contribution:** A1 → A2 coverage
   {pct(val['A1 Observability']['coverage'])} → {pct(val['A2 Propagation']['coverage'])};
   supported in {c['propagation_supported_runs']} validation runs. No guarantee of benefit.
4. **Temporal contribution:** A2 → full coverage
   {pct(val['A2 Propagation']['coverage'])} → {pct(c['coverage'])}; latency medians
   {val['A2 Propagation']['latency_median_ms']} → {c['latency_median_ms']} ms.
5. **Difficult layers:** see the complete per-origin denominators in
   clo_dsf_layer_summary.csv. Sensor/control lacks independent true-temperature
   evidence, mild communication faults can remain fresh, masked memory writes
   can have no effect, and fan-off can be hidden by low commanded duty.
6. **Silent plant propagation:** {c['silent_plant']} / {c['plant_manifestation_runs']} plant-manifesting faults.
7. **Benign false alarms:** {c['benign_false_alarms']} / {c['benign_runs']}; pre-injection
   alarms on faulty runs: {c['preinjection_alarm_runs']}. Benign conditions are diverse
   deterministic profiles, not an estimated operational distribution.
8. **Localization:** {pct(c['localization_accuracy'])} of all detected runs correct at first
   alarm; macro {pct(c['macro_localization_accuracy'])}; localized-only precision
   {pct(c['localized_precision'])}. Later localization does not repair first-alarm errors.
9. **Confused origin pairs:** {json.dumps(pairs,sort_keys=True)}. See full matrix including misses.
10. **UNKNOWN:** {pct(c['unknown_rate'])} of credited alarms. Abstention prevents forced
    predictions; no counterfactual number of 'correct UNKNOWNs' is identifiable
    without specifying a forced classifier. UNKNOWNs are not scored as correct origins.
11. **Hybrid:** coverage {pct(val['Hybrid']['coverage'])}, macro {pct(val['Hybrid']['macro_coverage'])},
    benign alarms {val['Hybrid']['benign_false_alarms']}; uses frozen legacy evidence,
    including simulator-truth-dependent residuals. This is not an equal-observability comparison.
12. **Timing Monitor:** {val['Timing Monitor']['detected']} / {val['Timing Monitor']['faulty_runs']}
    timing cases; other injected layers are N/A. It retains its specialized contract.
13. **Value beyond OR:** explicit ignorance/conflict, conservative localization,
    runtime evidence provenance and temporal persistence. Compare coverage/latency/FP
    directly; interpretability does not prove alarm superiority.
14. **Largest alarm-coverage ablation change:**
    {max([('observability/rule',val['A1 Observability']['coverage']-val['Plain DS']['coverage']),('propagation',val['A2 Propagation']['coverage']-val['A1 Observability']['coverage']),('temporal',c['coverage']-val['A2 Propagation']['coverage'])],key=lambda x:abs(x[1]))}.
    Signed effects, ignorance and conflict remain in clo_dsf_ablation.csv.
15. **Promising for independent validation:** {'YES, subject to the final isolation/regression checks' if gate else 'NO under the preregistered gate'}.
    TRAIN selected candidate {chosen}; validation never selects or retunes it.
    {'A freeze is permission to test an unchanged candidate on unseen data, not a claim of superiority.' if gate else 'Do not force a candidate freeze. Address the failed gate through a separately preregistered development revision before an independent holdout.'}

Full counts: validation {c['runs']} runs, {c['faulty_runs']} faults, {c['benign_runs']} benign.
Coverage {pct(c['coverage'])}; plant-conditional coverage {pct(c['coverage_given_plant_manifestation'])};
precision {pct(c['precision'])}; recall {pct(c['recall'])}; median/p95 latency
{c['latency_median_ms']}/{c['latency_p95_ms']} ms. Mean ignorance {c['mean_ignorance']:.6f},
mean max-step conflict {c['mean_conflict']:.6f}; {c['high_conflict_runs']} high-conflict runs.

A0–A3 use exactly the same validation trajectories and global decision rules;
localization is a readout and cannot change alarms. The single-fault frame cannot
represent simultaneous independent origins as conjunctions of truths: subsets
express uncertainty over alternatives. Channel and time dependence remain a
scientific limitation despite reliability discounts and finite retention.
'''
    (out/'clo_dsf_development_findings.md').write_text(text)
    write_json(out/'development_gate.json',{'development_gate_pass':gate,'candidate':chosen,'regression_pending':True,'confused_pairs':pairs})
