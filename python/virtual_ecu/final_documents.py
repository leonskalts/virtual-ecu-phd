"""Bounded publication narrative and audit generated around source-linked claims."""
from collections import Counter
import html

from .final_evidence import markdown_table, write_json, write_csv

LIMITATIONS = [
    ('100 ms sampling', 'C1,C3,C4', 'high', 'Explicit resolution and strict pre-plant versus same-tick endpoints', 'Replay higher-resolution independent scheduling/plant traces'),
    ('Modeled execution timing', 'C1,C3,C4,C12', 'high', '1 ms occupancy bookkeeping; unchanged 100 ms thermal macrosteps', 'Measure actual execution/start/completion durations'),
    ('Trusted supervisor assumption', 'C1,C2,C3,C4', 'high', 'Separate telemetry API; no claim of hardware isolation', 'Independent clock, event loss and supervisor integrity testing'),
    ('Deterministic correlated scenario construction', 'C1,C2,C3,C5,C6,C7', 'high', 'Describe Wilson intervals as binomial references; retain pairing and profile groups', 'Independent preregistered trace/profile sample'),
    ('Limited benign timing diversity', 'C2', 'high', 'Report legal cohort count and nonzero upper confidence bound', 'Real OS/RTOS workloads and wider independent operating envelope'),
    ('No hardware WCET', 'C11,C12', 'high', 'Label host ABI and whole-process benchmark; preserve noise caveat', 'Embedded measurements and defensible worst-case timing analysis'),
    ('Legacy ground-truth dependencies', 'C5,C6,C7,C8,C13', 'high', 'Document true-state residuals and scenario-aware diagnostics/bookkeeping', 'Audit production-available signals and separate evaluation-only inputs'),
    ('Experimental hazard definition', 'C3,C8,C9', 'high', 'Keep threshold/exposure semantics unchanged and explicit', 'Calibrate against a defined item/system specification'),
    ('Experimental FTTI', 'C3,C8,C9', 'high', 'Injection-origin budget includes recovery hold; missing clocks N/A', 'Derive system-specific timing requirements independently'),
    ('No full vehicle dynamics', 'C3,C5,C6,C7,C8', 'high', 'Describe thermal/control prototype and limited consequence model', 'Independent plant/vehicle model validation'),
    ('No certified ISO 26262 process', 'C1,C8,C11', 'high', 'Explicitly reject compliance and certification claims', 'A separate qualified lifecycle, evidence and assessment effort'),
    ('No hardware-in-the-loop validation', 'C1,C3,C8,C12', 'high', 'Constrain results to simulation and trace analysis', 'HIL with instrumented timing and controlled network traffic'),
    ('Not a full digital twin', 'C1,C5,C8', 'high', 'Use research virtual ECU prototype terminology', 'Validate fidelity and synchronization to a specified physical counterpart'),
    ('Empty holdout hazard cohort', 'C3,C8', 'high', 'Hazard prevention and hazard-conditioned rates remain N/A', 'Independent system-derived hazardous operating scenarios; no tuning this holdout'),
    ('Temporal exposure/polarity mismatch', 'C10', 'medium', 'Matched target/time/profile/bit; document flip reuse and unequal permanent duration', 'Explicit corruption-opportunity/exposure controlled design'),
    ('Finite recovery horizon and selected development cases', 'C9', 'medium', 'Keep original and extended endpoints; do not infer eventual recovery', 'Independent recovery trajectories under a fixed observation protocol'),
    ('Host/compiler variability', 'C11,C12', 'medium', 'Record ABI/compiler, no-op protocol and paired samples', 'Port and measure on target hardware'),
]


def generate_documents(out, claims, tables, traces):
    c={r['claim_id']:r for r in claims}
    audits=[{'claim_id':r['claim_id'],'statement':r['claim_text'],'classification':r['support_level'],
             'defensible_wording':r['allowed_wording'],'evidence':r['source_csv'],'limits':r['limitations']} for r in claims]
    rejected=[
        ('The timing monitor eliminates timing misses.', 'C1', c['C1']['allowed_wording']),
        ('The timing monitor achieved 100% coverage.', 'C1', 'Scope the statement to the frozen configured holdout. '+c['C1']['allowed_wording']),
        ('The timing monitor has no false positives.', 'C2', c['C2']['allowed_wording']),
        ('Cross-layer monitoring prevents hazards.', 'C3', 'Timing observation improves measured coverage and provides pre-plant alarms in evaluated cases; no timing-hazard prevention is established.'),
        ('Communication safety action prevents hazards.', 'C8', 'V4 development evidence contains avoided hazards, but the v5 holdout contains no baseline communication hazards. Generalized prevention is unestablished; report the observed containment and intervention trade-off.'),
        ('Dynamic faults are harder than stuck-at faults.', 'C10', c['C10']['allowed_wording']+' This does not establish superiority or a universal difficulty ranking.'),
        ('The platform is ISO 26262 compliant.', 'C11', 'This research prototype explores experimental safety metrics and makes no compliance or certification claim.'),
        ('The system is a digital twin.', 'C5', 'The system is a research virtual ECU thermal/control simulation; fidelity to a specific physical counterpart has not been established.'),
        ('The monitor has negligible embedded overhead.', 'C12', c['C12']['allowed_wording']+' Embedded runtime/WCET is not measured.'),
    ]
    for i,(statement,cid,wording) in enumerate(rejected,1):
        audits.append({'claim_id':f'A{i}','statement':statement,'classification':'NOT SUPPORTED',
                       'defensible_wording':wording,'evidence':c[cid]['source_csv'],
                       'limits':'Unqualified wording exceeds the evaluated scope. See '+cid})
    write_csv(out/'claim_audit.csv',audits)
    counts=dict(Counter(r['classification'] for r in audits));write_json(out/'claim_audit_summary.json',counts)
    (out/'claim_audit.md').write_text('''# Claim audit

An unqualified statement is rejected even where its explicitly bounded replacement
is supported. These are wording judgments, not additional experiments. In particular,
“100% coverage” requires its evaluated cohort and uncertainty limits.

Historical evidence was checked as part of the immutable artifact inventory:
[v1 framework](../cross_layer_safety_v1/cross_layer_safety_summary.md),
[v2 campaign](../cross_layer_safety_v2/campaign_runs.csv),
[v3 observability analysis](../cross_layer_safety_v3/scientific_findings.md),
[v4 timing/response development](../cross_layer_safety_v4/v4_findings.md), and
[v5 holdout](../cross_layer_safety_v5/v5_scientific_findings.md).
The earlier development cohorts are not pooled with the holdout, and their prior
hazards do not fill an empty v5 hazard denominator. All versions remain indexed
and byte-preserved, including inconvenient findings and superseded design records.

'''+markdown_table(audits))
    limits=[dict(zip(['limitation','affected_claims','severity','current_mitigation','future_validation_needed'],r)) for r in LIMITATIONS]
    (out/'limitations_register.md').write_text('# Limitations register\n\n'+markdown_table(limits))
    story=f'''# Final research story: Cross-Layer Fault Observability

The primary result concerns the availability of evidence at the originating layer.
Different fault origins expose different observables. This platform demonstrates
that its unchanged legacy physical/residual detector evidence does not cover the
same configured timing violations as trusted scheduler telemetry. It does not prove
that fault origin alone causes the measured cross-layer coverage differences.

{c['C13']['allowed_wording']}

{c['C1']['allowed_wording']}

{c['C2']['allowed_wording']}

{c['C3']['allowed_wording']}

{c['C4']['allowed_wording']}

Keep the combined monitor because its paired coverage/latency trade-off supports
the complete timing contract. Do not claim additional coverage over deadline-only
or additional pre-plant detection over either ablation.

{c['C5']['allowed_wording']} {c['C6']['allowed_wording']} {c['C7']['allowed_wording']}

Not every injection produces actual corruption, plant propagation or a hazard.
Raw injected-case detection and consequence-conditioned detection answer different
questions. Layer severities are not physically matched; do not turn grouped results
into causal origin rankings. Legacy detectors retain true-state/scenario dependencies.

Detection is distinct from containment, and action is distinct from detection.
{c['C8']['allowed_wording']}
No communication holdout hazard occurred, so generalized hazard prevention is N/A.
Observe-only remains the research action default; graded action remains experimental.

{c['C9']['allowed_wording']} This is development-case follow-up at a finite endpoint.
{c['C10']['allowed_wording']} Unequal exposure and polarity opportunity preclude
superiority claims. These are supporting findings, not competing primary stories.

The evidence supports the primary direction with these qualifications. It contradicts
stronger narratives of universal coverage, zero population false-positive probability,
generalized hazard prevention or reduced unnecessary-action count from graded action.
This package freezes those negative findings alongside the positive timing result.
'''
    (out/'final_research_story.md').write_text(story)
    sections=[
        ('1. Introduction','Why can physical/residual monitoring omit originating-layer evidence?', 'C1,C2,C13','Timing holdout runs and summary','Figure 1','0.5','Feature inventory and unrelated HETIA performance'),
        ('2. Cross-Layer Fault and Observability Model','Which stages and consequence-conditioned denominators separate injection from relevance?', 'C5,C6,C7','Cross-layer run table; frozen propagation contract','Table 1 compact; Table 3','0.6','All parameter grids and simulator field listings'),
        ('3. Test-Enabled Virtual ECU Platform','What can this model represent and where is evaluation truth used?', 'C11,C13','Final configuration; canonical architecture; observability boundary','Architecture in documentation; optional compact schematic replacing Table 1','0.5','GUI screenshots, full module catalogue, HETIA/RTL study results'),
        ('4. Runtime Timing Observability','What frozen evidence/rules distinguish legal operation from violated contracts?', 'C1,C2,C3,C4','Timing contract, C monitor source, paired ablation CSV','Table 4','0.6','Implementation listing and unsupported embedded overhead estimates'),
        ('5. Experimental Methodology','How were development/holdout separation, legal envelope and uncertainty defined?', 'C1,C2,C3,C4,C5,C10,C12','v5 YAML and frozen contract; v6 preset/lock; sample manifests','Table 2','0.6','Full recovery/temporal grids, raw CSV schemas'),
        ('6. Results','Does originating-layer timing evidence close the measured gap without legal alarms?', 'C1,C2,C3,C4,C5,C6,C7,C8','Claim matrix C1–C8 and C13; exact accepted summary/run tables','Figures 1–3; Tables 2–4; choose figure/table alternatives','1.3','Redundant plots; communication Figure 4/Table 5 normally supplement'),
        ('7. Discussion and Limitations','Which conclusions remain model-, horizon- and evidence-dependent?', 'C8,C9,C10,C11,C12','Limits register; recovery/matched/overhead source artifacts','Supplement: Figure 4 and Table 5','0.7','Universal safety claims, certification, novelty or superiority assertions'),
        ('8. Conclusion','What is the strongest bounded result and required independent validation?', 'C1,C2,C4','Claim audit and independent validation roadmap','No new artifact','0.2','New numerical claims or deployment recommendations'),
    ]
    outline='''# Bounded six-page-oriented outline

Planning allocation: 5.0 pages of body plus about 1.0 page for references/layout.
This is an internal planning budget, not a verified conference page rule. Adjust
only after selecting a venue and checking its current author instructions.

## Title candidates

- Cross-Layer Fault Observability in a Virtual ECU: Closing a Measured Timing Coverage Gap
- Trusted Timing Evidence for Cross-Layer Fault Observability in a Virtual ECU

Avoid a title implying causal fault-origin superiority or demonstrated vehicle safety.

## Abstract skeleton (not a drafted abstract)

Problem: physical/residual evidence may omit originating-layer timing behavior.
Method: source-frozen monitor, distinct development and holdout designs, legal stress,
explicit modeled overload, unchanged legacy detector and consequence-conditioned metrics.
Result slots: C1, C2, C3 and the metric-specific C4 comparison; fill from the claim matrix.
Boundary: deterministic simulation, no timing-hazard prevention or embedded WCET claim.
Implication: independent scheduler/target validation is required for stronger claims.

'''
    outline+=markdown_table([dict(zip(['section','main_question','claim_ids','exact_evidence','candidate_figure_table','body_pages','omit_for_space'],r)) for r in sections])
    outline+='''
## Artifact selection for the main paper

Prioritize Table 2 and Table 3, Figure 1 and Figure 2. Use either Table 4 or Figure 3
for ablation, depending on layout; avoid duplicating the same values in both.
Table 1 may be compressed into the model section. Table 5 and Figure 4 belong in
supplementary material unless the venue permits enough space for intervention costs.
Recovery, matched temporal and host overhead retain source-linked supplementary
claims. No complete paper or literature-novelty claim is generated in this pass.
'''
    (out/'paper_outline.md').write_text(outline)
    plant_detection=next(r for r in tables['table_2_timing_holdout'] if r['metric']=='plant_propagating_timing_detection')
    summary={
        'Timing Holdout Coverage':c['C1']['value'], 'Timing Coverage 95% CI':c['C1']['confidence_interval_95'],
        'Legal Timing Alarms':f"{c['C2']['numerator']}/{c['C2']['denominator']}",
        'Legal Timing False-Alarm 95% CI':c['C2']['confidence_interval_95'],
        'Plant-Propagating Timing Detection':f"{plant_detection['numerator']}/{plant_detection['denominator']}; pre-plant {c['C3']['numerator']}/{c['C3']['denominator']}",
        'Cross-Layer Detection':f"{c['C5']['numerator']}/{c['C5']['denominator']} ({c['C5']['value']:.2f}%)",
        'Detection Given Plant Propagation':f"{c['C6']['numerator']}/{c['C6']['denominator']} ({c['C6']['value']:.2f}%)",
        'Silent Plant Propagation':f"{c['C7']['numerator']}/{c['C7']['denominator']}",
        'Current Recommended Timing Monitor':'Combined', 'Current Default Safety Policy':'Observe only (research preset)'}
    summary['Timing Holdout Coverage']=f"{c['C1']['numerator']}/{c['C1']['denominator']} ({c['C1']['value']:.2f}%)"
    write_json(out/'research_summary.json',{'schema_version':6,'fields':summary,'claim_ids':list(c),
               'scope':'Frozen simulation evidence. Descriptive confidence intervals; no generalized hazard-prevention or embedded WCET claim.'})
    report='''# Cross-Layer Safety v6 final evidence report

Accepted scientific baseline: 0da05cc. V6 changes reporting, traceability,
reproducibility orchestration and GUI presentation only. Scientific sources and
accepted v1–v5/HETIA evidence are locked by SHA-256; no raw evidence is duplicated
for analysis-only regeneration.

## Recommended research configuration

Combined timing monitor, observe-only action default; immediate and graded actions
remain explicit experimental comparators. Legacy CLI defaults are preserved.
Exact constants and rule sources are in manifests/final_configuration.json.

## Audited claims

'''+ '\n\n'.join('**'+r['claim_id']+' — '+r['support_level']+'**\n\n'+r['allowed_wording']+'\n\nLimitation: '+r['limitations'] for r in claims)
    report+='''

## Reproducibility and review

Use `python3 scripts/run_cross_layer_reproducibility_package.py --quick-check`
and `--analysis-only`. `--full` reruns the selected accepted v5 workflows in an
isolated v6 reproduction directory and may execute many simulations. It is not
the default. Accepted folders are never output destinations.

The claim matrix records source rows/columns/filters. paper_artifact_traceability.csv
covers every curated figure and table form. manifests/artifact_manifest.csv indexes
immutable raw evidence in place and hashes final artifacts, excluding itself and
explicitly transient execution/GUI/mode logs. No unstable timestamps are inserted.

See claim_audit.md, final_research_story.md, paper_outline.md and limitations_register.md.
Verification records are in validation/: these are separate from reproducible
analysis content. Host measurements are retained from accepted v5; analysis does
not collect a more favorable new benchmark.

## Readiness

The platform evidence supports beginning a bounded paper draft after the recorded
software/reproducibility checks pass. No new detector or simulator implementation
is required for those bounded simulation claims. Literature/novelty positioning and
venue requirements still need author review. Stronger ECU, vehicle, hardware timing,
WCET or safety claims require the independent validation roadmap.
'''
    (out/'final_report.md').write_text(report)
    # A standalone local document, with no remote resources or Javascript.
    (out/'final_report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Cross-Layer Safety v6</title><style>body{max-width:900px;margin:3em auto;padding:0 1em;font:16px/1.55 sans-serif}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}</style><body><pre>'+html.escape(report)+'</pre></body></html>\n')
