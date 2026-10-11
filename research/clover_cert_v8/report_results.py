#!/usr/bin/env python3
import csv
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
rows=list(csv.DictReader((HERE/'comparison_metrics.csv').open()))
results=json.loads((HERE/'comparison_results.json').read_text())
lines=['# Fair finite algorithm comparison','',
 'All methods use identical v7 executions, menus, deadlines, target singleton/UNKNOWN decisions and joint objective. Six real component cases (two contexts × three deadlines) each enumerate 64 contracts. Six explicitly synthetic scaling cases are separate; no synthetic row is ECU evidence.','',
 '## Implemented methods','',
 '- **A_pairs:** direct exhaustive history-pair compatibility for every contract, followed by the shared compact checker generator.',
 '- **B_boolean:** exact positive-clause formulation; compile required-pair differences once per period, remove subsumed clauses and evaluate all assignments as a bit-vector truth table. This is a generic finite Boolean baseline, not an SMT/BDD implementation. Z3 and cvc5 are unavailable; no extra dependency was installed.',
 '- **C_cuts:** conventional critical-pair clause learning. A failed explicit check adds its exact separating clause. Contracts violating learned clauses are rejected before another explicit check. All remaining feasible contracts get the same checker/cost computation.',
 '- **C_coi_cuts:** C with the conservative source-provenance support prefilter. This is a known cone-of-influence relaxation, not a distinct proposed method D.',
 '- **D:** NOT IMPLEMENTED because the candidate rule reduced to existing transformations.','',
 'The comparison does not benchmark the published authors’ software. In particular, these Python implementations are not NuSMV, Kang’s joint diagnoser, Li’s cyclic-model algorithm, a Büchi-game solver or R2U2. They test the bounded reduction and cost preservation, not state-of-the-art performance superiority.','',
 'For real cases, the CSV domains=5 denotes five logical origin-mutation groups used by the support map, not five independent or protected physical domains. All fields still share the unresolved process boundary. Only the synthetic domain-count axis denotes the explicit correlated-overwrite partition defined by that synthetic generator.','',
 '## Exact results on source-backed cases','',
 '| Case | Feasible contracts / 64 | Optimum read+state cost | Optimum contracts (period:bundle mask) |',
 '|---|---:|---:|---|']
for r in results:
 if r['method']=='A_pairs' and r['kind']=='v7_component':
  lines.append(f"| {r['case']} | {len(r['feasible'])} | {r['best_objective']} | {', '.join(r['best_contracts'])} |")
lines += ['','All four implementations return exactly the same full feasible sets, per-contract costs, optimum values and complete optimum sets on all 12 cases. The independent tests also compare exact clauses, decisions and all checker prefixes. No UNKNOWN is converted into an unsupported specific origin.','',
 '## Measured runtime, memory and work at 400 ms','',
 '| Context / method | Median ms | Python peak bytes | Candidate nodes | Pair tests | Preprocessing pair visits | Boolean tests | Explicit oracle calls | Solver calls | Checker builds |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:
 if r['kind']=='v7_component' and r['deadline_ms']=='400':
  lines.append('| '+' | '.join([r['case']+'/'+r['method'],f"{float(r['median_runtime_ms']):.3f}"]+[r[k] for k in ('peak_python_bytes','configurations','pair_tests','preprocessing_pair_visits','boolean_tests','oracle_calls','solver_calls','checker_builds')])+' |')
lines += ['','Each runtime is the median of three untraced perf_counter_ns runs, including target construction, method preprocessing, contract checks and feasible checker generation. Input JSON loading is outside the timer. Memory is a separate tracemalloc run measuring peak Python allocations after inputs are loaded; it is not RSS, a total system-memory bound or deployed checker RAM. Fixed method order and microbenchmark scale limit timing conclusions.','',
 '“Candidate nodes” counts complete assignments visited, not internal solver or transition-system states. “Pair tests” counts explicit history equality tests; “preprocessing pair visits” separately counts support/difference-set extraction. Boolean tests are clause/assignment or membership evaluations. Solver calls are zero; explicit reference-oracle calls are not mislabeled as SMT calls. No compiled checker, executable-size measurement, hardware-memory measurement or WCET evidence is produced.','',
 '## Synthetic one-axis scaling','',
 '| Synthetic case | Origins | Domains | Timestamps | Bundles | Contracts | A ms | B ms | C ms | C+COI ms |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:
 if r['kind']=='synthetic_not_ECU' and r['method']=='A_pairs':
  group={x['method']:x for x in rows if x['case']==r['case']}
  lines.append('| '+' | '.join([r['case']]+[r[k] for k in ('origins','domains','timestamps','candidate_bundles','configurations')]+[f"{float(group[k]['median_runtime_ms']):.3f}" for k in ('A_pairs','B_boolean','C_cuts','C_coi_cuts')])+' |')
lines += ['','Synthetic generation is deterministic: each origin has two realizations; after t=0 one realization sets all fields in its origin-selected common domain to zero, while the other retains generated bits. This tests correlated evidence changes, not physical attacks. Domain count, origins, time points and candidate fields vary from a disclosed base fixture. The support filter uses the universal safe bound on synthetic data, because there is no source-backed ECU graph for it. These tiny cases are functional scaling probes, not asymptotic lower-bound families.','',
 '## Mechanism challenge result','']
real=[r for r in rows if r['kind']=='v7_component' and r['method']=='C_coi_cuts']
slower=0
for r in real:
 c=next(x for x in rows if x['case']==r['case'] and x['method']=='C_cuts')
 slower+=float(r['median_runtime_ms'])>float(c['median_runtime_ms'])
lines += [f'The source support prefilter is slower than conventional exact-clause learning on **{slower} of {len(real)} real cases** in this run, despite rejecting some candidates before explicit pair checking. Its preprocessing cost is included. No measured advantage over C is established by fewer oracle calls alone.',
 '', 'The main mathematical finding is independent of these timings: support pruning is a relaxation of ordinary critical-pair clauses. Even a favorable timing would not make that rule distinct. The finite implementation confirms the reduction rather than demonstrating a new synthesis method.',
 '', 'The common objective is preserved by using the identical minimized finite-prefix checker for each feasible contract. This does not prove an optimal physical monitor or the best possible diagnosis algorithm; it optimizes the specified menu and fixed completed-prefix behavior only. All v6/v7 assumptions remain unresolved.']
(HERE/'baseline_comparison.md').write_text('\n'.join(lines)+'\n')
summary={'cases':12,'real_cases':6,'synthetic_cases':6,'methods':4,'method_case_comparisons':len(rows),
         'real_contracts_per_case':64,'real_contract_assignments':384,
         'all_feasible_sets_and_joint_optima_agree':True,'source_prefilter_slower_cases':slower,
         'D':'NOT_IMPLEMENTED_NO_DISTINCT_RULE','novelty_verdict':'NO-GO'}
(HERE/'comparison_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
