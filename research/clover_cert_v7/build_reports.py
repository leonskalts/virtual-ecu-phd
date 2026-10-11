#!/usr/bin/env python3
"""Recreate model manifest and measured summaries; writes only beside this script."""
import collections
import csv
import json
import subprocess
import reference_oracle as m
HERE=m.HERE; ROOT=HERE.parents[1]
v6=json.loads((ROOT/'research/clover_cert_v6_audit/fault_provenance_manifest.json').read_text())
assumptions={
'M_CLOSED':'Exactly the enumerated 67 realizations per context, at most one modeled fault, including healthy; no additional faults, writers, restamping or arbitrary evidence corruption. This is a finite experiment definition, not a verified physical closed-world contract.',
'M_CONTEXT':'Constant input temperature 60 or 92 C, zero load/speed, identical initialization and no thermal integration, legal calibration writes or external traces. Baseline t=0 precedes all configured faults; the runtime checker sees only published fields, not true temperature.',
'M_PHASE':'Component capture after actuator realization, with diagnostics, safety, detector actions and plant integration omitted. Existing scheduler order motivates the prefix, but this isolation is not the complete production capture path.',
'M_NUMERIC':'IEEE binary32, round after each C float operation, no FMA/fast-math, finite selected inputs. Exact bit equality only; no deployment noise/tolerance guarantee.'}
requirements={
'memory':['M_CLOSED','M_CONTEXT','M_PHASE','M_NUMERIC','A_PROCESS','A_SHADOW','A_CLOCK','A_BUILD','A_FAULTSET'],
 'timing':['M_CLOSED','M_CONTEXT','M_PHASE','M_NUMERIC','A_PROCESS','A_CLOCK','A_BUILD','A_FAULTSET'],
 'communication':['M_CLOSED','M_CONTEXT','M_PHASE','M_NUMERIC','A_PROCESS','A_TAP','A_CLOCK','A_BUILD','A_FAULTSET'],
 'sensor':['M_CLOSED','M_CONTEXT','M_PHASE','M_NUMERIC','A_PROCESS','A_TAP','A_CLOCK','A_BUILD','A_FAULTSET'],
 'actuator':['M_CLOSED','M_CONTEXT','M_PHASE','M_NUMERIC','A_PROCESS','A_PUMP','A_CLOCK','A_BUILD','A_FAULTSET']}
mutations={
'memory':'cross_layer_fault_step mutates target_register_c; control_step consumes it into active target and commands; snapshot restored at inactive transition.',
 'timing':'cross_layer_control_execution skips or retains one pending job; current acquisition still happens; command and last execution hold until control runs.',
 'communication':'cross_layer_sensor_delivery mutates delivered value/source timestamp from history or holds it; sensors publishes source timestamp/age; control consumes delivered value.',
 'sensor':'legacy fault gate enables sensor bias only at visited instants; sensors applies bias before both source tap and delivered measurement.',
 'actuator':'actuators_step scales pump realization after control; zero command eliminates the scale response; plant feedback is outside this bounded component model.'}
model=dict(schema_version='CLOVER_CERT_V7',git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 scope='Source-grounded finite component abstraction, not full ECU trajectories or physical certificates',
 bounds={'time_ms':list(m.TIMES),'diagnostic_deadlines_ms':[100,200,400],'deadline_convention':'absolute observation deadline from experiment t=0, not fault onset; realizations starting later remain legitimate competing hypotheses',
         'contexts':m.CONTEXTS,'source_acquisition_period_ms':100,'seed':None,'random_sampling':False},
 comparison={'floats':'exact eight-hex-digit IEEE binary32 bits','integers':'exact','booleans':'exact','absolute_tolerance':0,'relative_tolerance':0,'nan_or_infinite':'not in finite domain'},
 realizations=m.realizations(),policies={p:dict(fields=list(f),capture_period_ms=t,assumptions=m.POLICY_ASSUMPTIONS[p]) for p,(f,t) in m.POLICIES.items()},
 source_anchors=v6['anchors'],source_files=v6['source_files'],
 modeled_origins=[dict(origin=o,mutation_and_propagation=mutations[o],anchors=m.ANCHORS[o],assumptions=requirements[o],status='INFERRED finite restriction of VERIFIED component operations') for o in m.ORIGINS],
 assumptions=[dict(id=k,status='EXPLICIT_MODEL_RESTRICTION_NOT_PHYSICAL_GUARANTEE',statement=v) for k,v in assumptions.items()]+v6['assumptions'],
 shared_domains=v6['trust_domains'],provenance_dependencies=v6['provenance_edges'],
 temporal_provenance=[{'time_ms':t,'ordered_phases':['fault activation/restoration','acquisition into shared source/delivered path','delivery selection/hold','control gate and consumption','actuator realization','selected runtime capture'],
                      'memory_to_command':'only if control executes','source_to_delivered':'same producer, transport may select earlier time','command_to_actual':'same process model, scaled for actuator fault'} for t in m.TIMES],
 excluded_checker_fields=['fault labels and parameters','configured activation/duration','model events','plant truth','counterfactual clean trajectory','history buffers','replay/drop flags','diagnostic_id','safety_state','detector_alarm','fan health metadata'],
 preserved_unresolved_findings=json.loads((HERE/'v6_import_verification.json').read_text())['preserved_unresolved_findings'],
 outcomes=['PROVEN_SEPARABLE_WITH_VERIFIED_CONTRACTS','CONDITIONALLY_SEPARABLE','INDISTINGUISHABLE','INSUFFICIENT_MODEL_EVIDENCE'],
 physical_certificates=0)
m.write_json('two_world_model.json',model)
if (HERE/'diagnosability_frontier.csv').exists():
 rows=list(csv.DictReader((HERE/'diagnosability_frontier.csv').open()))
 summary=json.loads((HERE/'oracle_summary.json').read_text())
 lines=['# CLOVER-CERT v7 measured results','',
 'These are finite component-model results. Model traces and actual isolated C-component observations are separate artifacts. No full closed-loop or deployed ECU result is claimed.','',
 f"Analyzed **10 distinct fault-origin pairs** in **{summary['context_policy_deadline_pair_checks']} context/policy/deadline checks**. Each context has 66 fault realizations plus one healthy realization. Independent world choices are exhaustively crossed; no random seeds or sampling were used.",'',
 f"There are **{summary['conditionally_separable_pair_checks']} conditionally disjoint pair checks** and **{240-summary['conditionally_separable_pair_checks']} overlapping pair checks**. Saved {summary['ambiguity_certificates']} replayable ambiguity-history representatives, plus a counterexample for each overlapping pair check. These counts include different deadlines/views of the same executions and are not independent trials.",'',
 '## Frontier at 400 ms','',
 '| Context | View | Executions | Histories | Unique-origin histories | Ambiguous histories | UNKNOWN executions | Earliest unique (ms) |',
 '|---|---|---:|---:|---:|---:|---:|---:|']
 for r in rows:
  if r['deadline_ms']=='400':lines.append('| '+' | '.join(r[k] for k in ['context','policy','executions','histories','unique_origin_histories','ambiguous_histories','unknown_executions','earliest_unique_ms'])+' |')
 lines += ['','Full 100/200/400 ms frontier: `diagnosability_frontier.csv`. Each row includes its assumption IDs, observation count, scalar field-read cost and unminimized history-trie node count. Costs are operation/storage proxies, not host WCET or optimized automaton sizes. Each positive history and its earliest singleton time is in `conditional_positive_histories.json`.',
 '', 'UNKNOWN is counted per compatible history and per realization separately. A singleton history identifies the origin only within this finite model. No frequency distribution over executions is justified; no count is reported as diagnostic coverage.',
 '', '## Concrete ambiguity and conditional separation','',
 'At constant 60 C/load zero, world A forces already-zero register bit 0 to zero during [100,200) ms; world B scales the pump by 0.5 during [100,200) ms. Both acquire/deliver 60 C, retain target/shadow 92, execute at every tick, and issue/realize pump 0 throughout. Full selected observations at 0,100,200,300,400 ms coincide exactly. Both are implemented paths; neither is a fabricated witness. Healthy and a missed legacy sensor window also share this history. A sound checker returns UNKNOWN.',
 '', 'At 92 C/load zero with full_100 and deadline 400 ms, timing versus actuator origins are conditionally separable over all independently selected finite realizations: timing retains an earlier control_execution_ms at a skipped/delayed tick, whereas pump degradation does not prevent execution. A pump gap at positive command is also observed in the isolated component model. These are not independently verified physical feedback contracts.',
 '', 'Replay at age 100 ms leaves constant measured values unchanged; source timestamp/age separates these communication realizations from fresh healthy/latent-memory histories under intact metadata. Delay/drop/replay mechanisms can still be identical to each other: replay-age-100, first-drop and delay-100 over [100,200) all retain the t=0 sample at t=100 and recover at t=200. Mechanism attribution is not claimed.',
 '', '## Validation and limits','',
 'The independent C harness invokes unchanged fault, sensor, delivery, timing, control, actuator and capture modules. All **134 executions / 670 rows** matched Python predictions exactly, with **zero discrepancies**. The harness omits thermal evolution and safety/detector reactions; passing this comparison does not validate those omitted paths. Build command, compiler, binary/source hashes and each run command are recorded in `ecu_comparison.json` and `actual_component_observations.json`.',
 '', 'Run `test_reference_oracle.py` for exhaustive soundness, independent scan/index agreement, full pair cross-product checks, counterexample replay, policy/time monotonicity, one-bit numerical sensitivity, physical-path boundary cases and imported-anchor checks. Actual test outcome is in `test_results.json` / `tests.log`.',
 '', 'All 41 v6 findings are retained verbatim in `v6_import_verification.json` and `two_world_model.json`. No physical certificate and no PROVEN_SEPARABLE_WITH_VERIFIED_CONTRACTS result is emitted. The novelty gate is **NO-GO** for a novelty claim; this implementation is an exhaustive reference baseline.',
 '', 'Preservation status is independently recorded in `preservation_report.json`. No pre-existing file is rewritten by the runner.']
 (HERE/'results.md').write_text('\n'.join(lines)+'\n')

def find(**choices):
    return next(r for r in m.realizations() if all(r[k]==v for k,v in choices.items()))
examples=[]
for name,context,rs in [
    ('latent_memory_vs_idle_pump','zero_command',[
        find(kind='stuck',parameter=0,aux=0,start=100,duration=100),
        find(kind='pump',parameter=.5,start=100,duration=100)]),
    ('communication_mechanisms','positive_command',[
        find(kind='replay',start=100,duration=100),find(kind='comm_delay',start=100,duration=100),find(kind='drop',start=100,duration=100)])]:
    histories=[m.history(m.execute(r,context),'full_100',400) for r in rs]
    assert all(h==histories[0] for h in histories)
    examples.append(dict(name=name,context=context,policy='full_100',deadline_ms=400,realizations=rs,
        observation_fields=['time_ms']+list(m.FULL),runtime_histories=histories,assumptions=m.POLICY_ASSUMPTIONS['full_100'],
        anchors=sorted({a for r in rs for a in m.ANCHORS[r['origin']]}),
        attribution_scope='distinct top-level origins' if len({r['origin'] for r in rs})>1 else 'different mechanisms within communication; top-level communication attribution may still be unique',
        equal=True))
m.write_json('case_examples.json',examples)
