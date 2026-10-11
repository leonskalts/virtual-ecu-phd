# CLOVER-CERT v8 novelty verdict

**NO-GO**

The proposed deadline-restricted provenance support rule is mathematically sound under its stated fixed-model assumptions, but it is not distinct from known methods. It computes a conservative cone of influence and uses the result as a necessary critical-pair hitting-set clause. Using exact trace differences recovers the conventional observation-selection clause. Adding a lower bound on read/checker cost gives ordinary branch-and-bound; merging equivalent residual checker behavior gives ordinary automata minimization.

Closest competitor: [Bittner et al. (AAAI 2012)](https://ojs.aaai.org/index.php/AAAI/article/download/8225/8083), Figure 3 / Equation (1). The correspondence concerns feasibility refinement; no equivalence of the complete joint cost problem is claimed.

What was proved in writing: exact equivalence between bounded pair separation and observation clauses; sound rejection from an upper bound on possible differing coordinates; preservation of UNKNOWN and sound singleton decisions for the declared executions; correctness of the finite checker quotient; and cost-optimum preservation when the feasible sets and objective coincide. Completeness is established for exact finite clauses, not arbitrary source-provenance upper bounds. These are reductions and elementary correctness results, not a new complexity theorem or a machine-checked proof.

What was experimentally tested: identical requirements and cost objective across direct exhaustive pairs, generic finite Boolean clauses, conventional learned clauses and learned clauses with a source-support prefilter. Six source-backed component cases and six separately labeled synthetic cases compare full feasible sets, all feasible costs and complete optimum sets. Independent tests cover oracle equivalence, every generated checker prefix, support soundness, UNKNOWN preservation and invalid bounds. Actual timings, allocation peaks and operation counts are in `baseline_comparison.md`; small-instance speed is not a novelty criterion.

No separate proposed method D was implemented, because no genuinely distinct pruning rule survived the collision check. The limited executable prototype tests the falsifiable reduction and its known-method ablation. It is not relabeled as a novel synthesis algorithm.

Two requested journal full texts (Li et al. 2026 and the 2026 symbolic-RV journal version) remain bibliographic limitations. Their algorithms are not inferred from abstracts. This does not weaken the demonstrated collision with the accessible closest paper, and it cannot support a novelty claim.

The source-backed ECU evidence remains scientifically useful: it defines concrete fields, temporal ordering and counterexamples that an eventual method must respect. All 41 v6 findings remain, including missing physical timestamp integrity, common-cause containment and independent actuator feedback. Real-model arbitrary evidence corruption is not added merely to make the research problem richer.

**Maturity:** the work is ready to serve as a bounded reference benchmark and a specification for further research. It is **not sufficiently mature to implement a full algorithm as a claimed novel journal contribution**. A next candidate would need a computational mechanism not equivalent to these known reductions, a theorem exploiting a proved structural property of the admissible model, fair comparisons to actual strong implementations, and completion of the bibliographic checks. A richer application vocabulary, a joint cost expression or an empirical speedup alone would not meet that gate.
