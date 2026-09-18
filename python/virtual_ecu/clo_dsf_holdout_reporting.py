"""Frozen pre-outcome reporting rules, applied only after final runtime execution."""
import collections,json,math
from pathlib import Path
from .clo_dsf_holdout import OUT,ORIGINS,METHODS,NONLOCAL,aggregate,write_csv,wilson

def summary(rows):
 s=aggregate(rows);s['wrong_localized_runtime_samples']=sum(r['wrong_localized_runtime_samples'] for r in rows)
 faults=[r for r in rows if r['injected']];detected=[r for r in faults if r['detected']];plant=[r for r in faults if r['plant_manifestation']==1];pd=[r for r in plant if r['detected']]
 s['plant_detected']=len(pd)
 s['pre_plant_alarms']=sum(r['first_post_alarm_ms']<r['propagation_plant_ms'] for r in pd)
 s['same_plant_alarms']=sum(r['first_post_alarm_ms']==r['propagation_plant_ms'] for r in pd)
 s['post_plant_alarms']=sum(r['first_post_alarm_ms']>r['propagation_plant_ms'] for r in pd)
 s['detected_without_plant_manifestation']=len(detected)-len(pd)
 s['silent_plant_rate']=s['silent_plant']/len(plant) if plant else None
 for label,k,n in [('coverage',s['detected'],s['faulty_runs']),('plant_coverage',len(pd),len(plant)),('silent_plant_rate',s['silent_plant'],len(plant)),('benign_false_alarm_rate',s['benign_false_alarms'],s['benign_runs']),('precision',s['detected'],s['detected']+s['benign_false_alarms']),('localization_coverage',s['localized'],s['detected']),('localized_accuracy',s['correct_localizations'],s['localized']),('unknown_rate',s['unknown'],s['detected']),('wrong_origin_rate',s['wrong_localizations'],s['detected']),('pre_plant_rate',s['pre_plant_alarms'],len(pd)),('localization_before_plant_rate',s['localized_before_plant'],len(plant))]:
  s[label+'_wilson_low'],s[label+'_wilson_high']=wilson(k,n)
 return s

def pair(rows,other):
 a={r['run_id']:r for r in rows if r['method']=='Revised CLO-DSF' and r['injected']};b={r['run_id']:r for r in rows if r['method']==other and r['injected']}
 assert a.keys()==b.keys()
 n11=sum(a[k]['detected'] and b[k]['detected'] for k in a);n10=sum(a[k]['detected'] and not b[k]['detected'] for k in a);n01=sum(not a[k]['detected'] and b[k]['detected'] for k in a);n00=len(a)-n11-n10-n01;n=n10+n01
 p=min(1.,2*sum(math.comb(n,k) for k in range(min(n10,n01)+1))/2**n) if n>=10 else None
 return dict(comparator=other,both_detect=n11,only_clo_dsf=n10,only_comparator=n01,neither=n00,discordant=n,exact_mcnemar_p=p,test_interpretation='Descriptive exact conditional paired test; related configurations violate IID interpretation' if n>=10 else 'Fewer than ten discordant pairs: counts only, no test')

def identities(rows,signatures):
 by={r['run_id']:r for r in rows if r['method']=='Revised CLO-DSF'};groups=[]
 for field in ['observation_history_sha256','evidence_history_sha256']:
  mapping=collections.defaultdict(list)
  for r in signatures:mapping[r[field]].append(r)
  for digest,members in mapping.items():
   origins=sorted({m['origin_evaluation_only'] for m in members if m['origin_evaluation_only']!='NORMAL'})
   normal=any(m['origin_evaluation_only']=='NORMAL' for m in members)
   if len(origins)>1 or (normal and origins):
    groups.append(dict(representation=field,history_sha256=digest,origins='|'.join(origins),contains_benign=int(normal),runs=len(members),run_ids='|'.join(m['run_id'] for m in members)))
 write_csv(OUT/'paper_tables/identifiability_groups.csv',groups if groups else [dict(representation='NONE',history_sha256='',origins='',contains_benign=0,runs=0,run_ids='')])
 latent=[r for r in signatures if r['latent_stuck_target_unchanged']]
 latent_rows=[dict(run_id=r['run_id'],model=r['model'],origin_evaluation_only=r['origin_evaluation_only'],max_target_deviation=r['max_target_deviation'],max_response_gap=r['max_response_gap'],observation_history_sha256=r['observation_history_sha256'],detected=by[r['run_id']]['detected'],silent_plant=by[r['run_id']]['silent_plant'],plant_manifestation=by[r['run_id']]['plant_manifestation']) for r in latent]
 write_csv(OUT/'paper_tables/latent_stuck_patterns.csv',latent_rows)
 return dict(full_observation_mixed_groups=sum(g['representation']=='observation_history_sha256' for g in groups),full_evidence_mixed_groups=sum(g['representation']=='evidence_history_sha256' for g in groups),latent_stuck_cases=len(latent),latent_stuck_detected=sum(by[r['run_id']]['detected'] for r in latent),latent_stuck_plant_cases=sum(by[r['run_id']]['plant_manifestation']==1 for r in latent))

def save(fig,name):
 fig.canvas.draw();bottom=fig.get_tightbbox(fig.canvas.get_renderer()).y0
 fig.text(.5,(bottom-.16)/fig.get_figheight(),'FINAL UNSEEN HOLDOUT · frozen v7.3 · designed virtual-ECU cases',ha='center',va='top',fontsize=8,color='#555555')
 for suffix in ['png','pdf']:fig.savefig(OUT/'paper_figures'/f'{name}.{suffix}',dpi=180,bbox_inches='tight')
 import matplotlib.pyplot as plt
 plt.close(fig)

def figures(by,layers,confusion,paired,subgroups):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 selected=[r for r in layers if r['method']=='Revised CLO-DSF']
 fig,ax=plt.subplots(figsize=(8,4));values=[r['coverage']*100 for r in selected];lo=[(r['coverage']-r['coverage_wilson_low'])*100 for r in selected];hi=[(r['coverage_wilson_high']-r['coverage'])*100 for r in selected]
 ax.bar(ORIGINS,values,yerr=[lo,hi],capsize=4,color='#176b87');ax.set(ylim=(0,105),ylabel='Detected faults (%)',title='240 faults per origin; nominal Wilson 95% intervals');ax.tick_params(axis='x',rotation=15);save(fig,'detection_by_origin')
 names=['Simple OR','Weighted Sum','Plain DS','v7.2 CLO-DSF','Revised CLO-DSF','Hybrid']
 fig,axes=plt.subplots(1,2,figsize=(11,4));axes[0].bar(names,[100*by[n]['coverage'] for n in names],color='#176b87');axes[0].set(ylabel='Detected faults (%)',ylim=(0,105));axes[1].bar(names,[by[n]['silent_plant'] for n in names],color='#9c485b');axes[1].set(ylabel='Silent plant-propagating faults')
 for ax in axes:ax.tick_params(axis='x',rotation=30)
 save(fig,'baseline_detection_and_silent_plant')
 selected=[r for r in confusion if r['method']=='Revised CLO-DSF'];cols=ORIGINS+['UNKNOWN','misses'];matrix=[[r[c] for c in cols] for r in selected]
 fig,ax=plt.subplots(figsize=(9,4));ax.imshow(matrix,cmap='Blues');ax.set_xticks(range(7),cols,rotation=25,ha='right');ax.set_yticks(range(5),ORIGINS);ax.set(title='First-alarm origin; misses remain separate',ylabel='True origin (evaluation only)')
 for i,row in enumerate(matrix):
  for j,n in enumerate(row):ax.text(j,i,str(n),ha='center',va='center',color='white' if n>=120 else 'black')
 save(fig,'origin_confusion')
 selected=[r for r in subgroups if r['comparator']=='v7.2 CLO-DSF' and r['origin']=='ACTUATOR']
 fig,ax=plt.subplots(figsize=(9,4));ax.bar([r['model']+' / '+r['behavior'] for r in selected],[r['only_clo_dsf']-r['only_comparator'] for r in selected],color='#176b87');ax.set(ylabel='Net additional detections versus v7.2',title='Actuator generalization by subtype and behavior');ax.tick_params(axis='x',rotation=25);save(fig,'actuator_generalization')

def report(rows,signatures):
 comparisons=[];layers=[];confusion=[]
 for method in METHODS:
  subset=[r for r in rows if r['method']==method and (method!='Timing Monitor' or r['origin'] in ['NORMAL','TIMING'])]
  s=dict(method=method,**summary(subset))
  if method in NONLOCAL:
   for k in s:
    if any(word in k for word in ['localiz','unknown','ignorance','conflict','wrong_origin']):s[k]=None
  comparisons.append(s)
  for origin in ORIGINS:
   if method=='Timing Monitor' and origin!='TIMING':continue
   group=[r for r in subset if r['origin']==origin];layers.append(dict(method=method,origin=origin,**summary(group)))
   if method not in NONLOCAL:
    confusion.append(dict(method=method,true_origin=origin,**{o:sum(r['detected'] and r['origin_at_alarm']==o for r in group) for o in ORIGINS+['UNKNOWN']},misses=sum(not r['detected'] for r in group)))
 by={r['method']:r for r in comparisons};a=by['Revised CLO-DSF'];w=by['Weighted Sum'];old=by['v7.2 CLO-DSF']
 write_csv(OUT/'final_baseline_comparison.csv',comparisons)
 write_csv(OUT/'final_detection_summary.csv',[dict(origin='ALL',**a),*[r for r in layers if r['method']=='Revised CLO-DSF']])
 loc_keys=['runs','faulty_runs','detected','localized','localization_coverage','accuracy_when_localized','correct_localizations','wrong_localizations','unknown','unknown_rate','localized_before_plant','plant_manifestation_runs','wrong_localized_runtime_samples','macro_localization_accuracy']
 loc_keys+=[k for k in a if ('wilson' in k and any(word in k for word in ['localiz','unknown','wrong_origin']))]
 write_csv(OUT/'final_localization_summary.csv',[dict(method=r['method'],origin=r.get('origin','ALL'),**{k:r[k] for k in loc_keys}) for r in [a,*layers] if r['method']=='Revised CLO-DSF'])
 write_csv(OUT/'final_origin_confusion.csv',confusion);write_csv(OUT/'paper_tables/per_origin_comparison.csv',layers)
 pairs=[pair(rows,other) for other in ['Weighted Sum','v7.2 CLO-DSF']];write_csv(OUT/'final_paired_comparison.csv',pairs)
 subgroups=[];severity=[];subtype=[]
 for origin in ORIGINS:
  models=sorted({r['model'] for r in rows if r['origin']==origin})
  for model in models:
   for method in METHODS:
    group=[r for r in rows if r['origin']==origin and r['model']==model and r['method']==method]
    if method=='Timing Monitor' and origin!='TIMING':continue
    subtype.append(dict(origin=origin,model=model,method=method,**summary(group)))
   for behavior in ['transient','intermittent','permanent']:
    group=[r for r in rows if r['origin']==origin and r['model']==model and r['behavior']==behavior]
    for other in ['Weighted Sum','v7.2 CLO-DSF']:subgroups.append(dict(origin=origin,model=model,behavior=behavior,**pair(group,other)))
    for magnitude in sorted({r['magnitude'] for r in group}):
     sub=[r for r in group if r['magnitude']==magnitude]
     for other in ['Weighted Sum','v7.2 CLO-DSF']:severity.append(dict(origin=origin,model=model,behavior=behavior,magnitude=magnitude,**pair(sub,other)))
 write_csv(OUT/'paper_tables/subtype_performance.csv',subtype);write_csv(OUT/'paper_tables/paired_by_model_behavior.csv',subgroups);write_csv(OUT/'paper_tables/paired_by_severity.csv',severity)
 ident=identities(rows,signatures)
 generalized=any(r['comparator']=='v7.2 CLO-DSF' and r['only_clo_dsf']>r['only_comparator'] and not(r['origin']=='ACTUATOR' and r['behavior']=='intermittent') for r in subgroups)
 p=pairs[0];superior=p['only_clo_dsf']>p['only_comparator'] and p['exact_mcnemar_p'] is not None and p['exact_mcnemar_p']<.05 and a['benign_false_alarms']<=w['benign_false_alarms']
 write_csv(OUT/'paper_tables/holdout_conclusions.csv',[dict(generalized_beyond_intermittent_actuator=generalized,binary_advantage_on_this_modeled_holdout=superior,additional_localization_capability=a['correct_localizations']>0,**ident)])
 figures(by,layers,confusion,pairs,subgroups)
 pct=lambda v:'N/A' if v is None else f'{100*v:.2f}%'
 ci=lambda r,k:f"{pct(r[k+'_wilson_low'])}–{pct(r[k+'_wilson_high'])}"
 table='\n'.join(f"| {r['method']} | {r['detected']}/{r['faulty_runs']} | {pct(r['coverage'])} | {r['silent_plant']} | {r['benign_false_alarms']}/{r['benign_runs']} | {r['latency_median_ms']:g}/{r['latency_p95_ms']:g} |" for r in comparisons)
 per='\n'.join(f"| {r['origin']} | {r['detected']}/{r['faulty_runs']} | {pct(r['coverage'])} | {ci(r,'coverage')} | {r['localized']} | {r['unknown']} | {r['wrong_localizations']} |" for r in layers if r['method']=='Revised CLO-DSF')
 gains='\n'.join(f"| {r['origin']} | {r['model']} | {r['behavior']} | {r['only_clo_dsf']} | {r['only_comparator']} |" for r in subgroups if r['comparator']=='v7.2 CLO-DSF')
 text=f'''# Final unseen holdout findings

The frozen v7.3 binary/configuration was evaluated once on 1,500 preregistered,
previously unused configurations: 1,200 faults, 300 benign, 240 faults per origin.
Zero exact configuration overlap with Candidate 1/2, v7.2 or v7.3 development.
All registered cases completed; no scientific parameters, baselines, fault
semantics or sampling decisions changed after outcomes. Exact configuration
novelty is not independence from the shared simulator/fault-family assumptions.

## Detection and frozen baselines

| Method | Detected | Coverage | Silent plant | Benign alarms | Median/P95 ms |
|---|---:|---:|---:|---:|---:|
{table}

v7.3 coverage {a['detected']}/{a['faulty_runs']} = {pct(a['coverage'])}; nominal
Wilson 95% CI {ci(a,'coverage')}. Macro detection {pct(a['macro_coverage'])}.
Recall {pct(a['recall'])}; precision {pct(a['precision'])}, interval {ci(a,'precision')}.
Plant-propagating detection {a['plant_detected']}/{a['plant_manifestation_runs']} =
{pct(a['coverage_given_plant_manifestation'])}, interval {ci(a,'plant_coverage')}.
Silent plant {a['silent_plant']}/{a['plant_manifestation_runs']}, interval
{ci(a,'silent_plant_rate')}. Benign alarm interval {ci(a,'benign_false_alarm_rate')}.

Of detected plant-propagating cases: {a['pre_plant_alarms']} pre-plant,
{a['same_plant_alarms']} same-tick and {a['post_plant_alarms']} post-plant.
Another {a['detected_without_plant_manifestation']} detected faults had no plant
manifestation and are not classified as pre-plant. Pre-injection alarm runs:
{a['preinjection_alarm_runs']}. Latency statistics exclude misses.

| Origin | Detection | Coverage | Wilson 95% | Localized | UNKNOWN | Wrong |
|---|---:|---:|---|---:|---:|---:|
{per}

## Localization and UNKNOWN

Coverage {a['localized']}/{a['detected']} = {pct(a['localization_coverage'])},
interval {ci(a,'localization_coverage')}. Accuracy conditional on localization
{a['correct_localizations']}/{a['localized']} = {pct(a['accuracy_when_localized'])},
interval {ci(a,'localized_accuracy')}. UNKNOWN {a['unknown']}/{a['detected']} =
{pct(a['unknown_rate'])}, interval {ci(a,'unknown_rate')}.
Wrong non-UNKNOWN at first alarm: {a['wrong_localizations']}; wrong localized
runtime samples: {a['wrong_localized_runtime_samples']}. Correct localization
before plant manifestation: {a['localized_before_plant']}/{a['plant_manifestation_runs']}
plant-propagating faults. All origin confusion tables retain UNKNOWN and misses
separately. UNKNOWN is valid abstention, not a confident localization error.

## Paired comparison and inference limits

v7.3 versus Weighted Sum: both {p['both_detect']}, only v7.3 {p['only_clo_dsf']},
only Weighted Sum {p['only_comparator']}, neither {p['neither']}.
Exact McNemar p: {p['exact_mcnemar_p']}; {p['test_interpretation']}.
Silent plant comparison: {a['silent_plant']} versus {w['silent_plant']}.
Benign alarms: {a['benign_false_alarms']} versus {w['benign_false_alarms']}.
Median/P95: {a['latency_median_ms']:g}/{a['latency_p95_ms']:g} versus
{w['latency_median_ms']:g}/{w['latency_p95_ms']:g} ms.

Binary advantage under the preregistered rule on THIS modeled holdout: {superior}.
Do not generalize this to a population guarantee, physical hardware, or a unique
advantage of DS mathematics. Weighted Sum retained its frozen original evidence;
a pool augmented with the same actuator contract was not tested. Designed
families share profiles/mechanisms and are correlated; the nominal Wilson
intervals and IID-conditional McNemar p do not account for that dependence.

## Does the v7.3 gain generalize?

Beyond intermittent actuator cases versus v7.2: {generalized}.
Report the actual contributing subtypes below, not a blanket all-origin claim.

| Origin | Subtype | Behavior | Only v7.3 | Only v7.2 |
|---|---|---|---:|---:|
{gains}

Full subtype rates and severity-level paired counts are retained in paper_tables.
The v7.3 change affects only actuator conformance. Its validity rests on the
simulator's synchronous noiseless clamp(command) response. A physical actuator
requires trustworthy feedback plus a validated error/dynamics envelope; the
one-ULP rule is not a hardware tolerance. Historical Hybrid retains its original
feedback inputs, including the simulator's label-derived fan self-test; that
signal is not supplied to revised CLO-DSF.

## Post-hoc identifiability and latent memory faults

Analysis was performed offline after runtime, never fed into inference.
Mixed-origin complete allowed-observation-history groups: {ident['full_observation_mixed_groups']}.
Mixed-origin complete extracted-evidence-history groups: {ident['full_evidence_mixed_groups']}.
Group members and exact signatures are retained; complete observation equivalence
and representation-induced equivalence are distinct. No rounded similarity
criterion or alleged universal identifiability theorem is introduced.

Stuck-bit runs whose runtime target remained exactly nominal: {ident['latent_stuck_cases']}.
Detected among these: {ident['latent_stuck_detected']}; plant-propagating among them:
{ident['latent_stuck_plant_cases']}. These test the same dormant-defect pattern as
the 36 historical observability-limited v7.2 cases, under new configurations.
A stuck-at bit agreeing with the current value produces no passive value error;
trusted active memory testing, not an unchanged-value checksum, would be needed.
No no-effect faults were excluded from detection denominators.

## Manuscript use and integrity

These are final unseen configuration holdout results for this virtual-ECU model.
They support bounded claims about measured detection, selective localization and
the specific actuator evidence contract. Additional origin output is implemented
capability beyond the evaluated binary Weighted Sum, not proof that weighted
pooling cannot be extended to localize. Preserve conditional accuracy alongside
coverage and report silent plant misses and abstentions. No production,
compliance, embedded WCET, calibration or physical transfer claim is justified.

Frozen identities were verified before design/execution and after all runtime
cases. Final regression and preservation results are in validation_record.md.
The protocol, exact manifest, per-run results, commands and artifact hashes allow
reproduction without duplicate raw logs. Nothing was tuned after holdout.

Method references: [NIST Wilson intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm),
[paired McNemar definition](https://www.stat.ethz.ch/R-manual/R-devel/library/stats/html/mcnemar.test.html),
[exact paired binomial calculation](https://pdixon.stat.iastate.edu/stat511/notes/part%202b.pdf).
'''
 (OUT/'final_holdout_findings.md').write_text(text)
