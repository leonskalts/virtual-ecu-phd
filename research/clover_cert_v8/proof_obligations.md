# Proofs, completeness conditions and failure cases

These are hand-written finite-model proofs, not machine-checked theorems. Tests check the implementation against the stated finite definitions; they are not the proof.

## P1. Exact critical-pair reduction

**Input:** fixed admissible executions E, passive observation coordinates Q, required pairs R_d, and a menu of contracts S⊆Q. Define D(e,f,d)={q∈Q: publication(q)≤d and v(e,q)≠v(f,q)}.

**Output/rule:** keep precisely the menu assignments satisfying

    Φ(S) = ∧_(e,f)∈R_d  ∨_q∈D(e,f,d) selected(q).

Bundled coordinates replace selected(q) by the corresponding bundle/schedule expression. An empty clause makes the requirement infeasible.

**Proof:** equality of two ordered, fixed-schedule observation histories means equality at every selected coordinate. Hence h_S(e,d)≠h_S(f,d) iff at least one selected coordinate belongs to D(e,f,d). Conjoin this equivalence over all required pairs. Therefore Φ holds exactly for the feasible contracts. This proves soundness and completeness for the specified E, R_d, menu and deadline. It proves neither completeness of E as a physical model nor independence of coordinates.

**Collision:** Φ is a monotone critical-pair hitting-set formula. The bounded trace-refinement correspondence to Bittner et al.'s Figure 3/Equation (1) is direct: observables become time-indexed coordinates, and a failed requirement adds their separating disjunction. See the [primary paper](https://ojs.aaai.org/index.php/AAAI/article/download/8225/8083). Origin/time/domain annotations change D, not the Boolean mechanism. This comparison concerns the feasibility/refinement mechanism; it does not assert that that paper solves our exact checker-state cost objective.

## P2. Sound temporal support pruning

**Input:** for every e, an upper bound I(e) on coordinates that may differ from a common baseline b under its mutations, including transitive control/data dependencies, held state, restoration and delayed publication. Assume v(e,q)=v(b,q) whenever q∉I(e). Set U(e,f,d)=(I(e)∪I(f)) restricted to publication by d.

**Rule:** reject S if for some required pair S∩U(e,f,d)=∅. For a partial assignment with allowed remaining coordinates T, reject the whole branch if (S∪T)∩U=∅.

**Proof:** if q∉I(e)∪I(f), both values equal the same baseline value, so v(e,q)=v(f,q). Therefore D(e,f,d)⊆U(e,f,d). If S misses U, it misses D and fails P1. The same holds for every completion of the partial assignment if S∪T misses U. No complete transition-product construction is needed for this negative conclusion when sound per-origin bounds are already available. Computing bounds and checking pair obligations still has a cost; v8 does not call it product-free synthesis.

**Completeness:** the rule completely recognizes infeasibility only when the upper-bound clauses describe exactly the same menu assignments as Φ. U=D for every pair is sufficient, not necessary. General dependency reachability is too coarse to ensure this. A matching-polarity stuck bit and a zero-command degraded pump have nonempty structural influence but equal values. A contract may hit U and still have no evidence. Passing the filter is never a positive certificate.

**Why not distinct:** I is a cone-of-influence/noninterference upper bound, time restriction is bounded unrolling, and the resulting clause is a relaxation of P1. Keeping only inclusion-minimal clauses is ordinary subsumption. Neither common-cause annotations nor a deadline alters those transformations. There is no separate novel theorem here.

**Invalid cases:** different baseline/environment values not included in I; underestimated persistence after a fault ends; treating acquisition time as publication time; ignoring control dependencies or timestamp writes; deleting correlations from shared corruption; replacing possible distinguishing effects by guaranteed effects in the wrong direction; or using bounds computed under A after withdrawing A. Active measurements that alter execution/protection also violate the fixed-E assumption.

## P3. UNKNOWN and origin soundness

For every modeled e, o(e)∈K_S(h_S(e,d),d). Thus a singleton answer equals o(e). If the full-view set contains two distinct origins, any projection still contains those origins; UNKNOWN remains UNKNOWN. For a full-view singleton a, P1 with pairs to all other origins makes the projected set contain no origin other than a. Therefore the comparison's R_d preserves all full-view verdicts exactly at d. It need not preserve all compatible-origin sets for UNKNOWN histories.

Every admissible corruption realization must be included before applying this argument. In particular, a separate field called shadow, timestamp or protected record does not justify excluding a coherent write world. Otherwise the apparent certificate is sound for a smaller model only. No physical all-assumptions-verified theorem is claimed.

## P4. Compact checker correctness and objective preservation

Build a prefix trie of selected histories. At each node, output the singleton origin of all executions sharing that prefix, otherwise UNKNOWN. Every unlisted observation leads to an absorbing UNKNOWN state. Two nodes may be merged when their current output and every labeled successor's equivalence class agree; default UNKNOWN transitions are shared.

**Proof:** by backward induction over the finite suffix length, merged nodes produce identical outputs for every continuation. The base cases are leaves and the UNKNOWN sink. Matching outputs/successor classes give identical next output and, inductively, all later outputs. Removing an explicit edge to the default sink changes no behavior. Distinct residual behaviors cannot be merged by a deterministic Moore checker without changing some continuation output. The resulting state count is the minimum for this fixed completed prefix behavior, not for all possible diagnostic algorithms or alternative permissible UNKNOWN extensions.

All methods use this same construction for feasible contracts and enumerate all candidates. By P1–P3 and independent equivalence checks, their feasible sets coincide; identical cost construction then gives identical optimum value and complete optimum set. A faster implementation of the same search/quotient is not an algorithmic novelty proof.

## P5. Resource bounds and dominance

If selected scalar-read cost is c(S), every completion costs at least c(S)+L, provided L is a proved lower bound on its checker-state cost and added acquisition costs are nonnegative. Thus c(S)+L>B soundly prunes against incumbent B. L=1 is always valid for our checker; a stronger L needs its own proof. For equality, pruning is safe only if one optimum suffices; retaining all optima requires strict inequality.

This is standard branch-and-bound. The number of already visited trie nodes is not a valid lower bound on the *minimized* checker. Acquisition-cost-only dominance is not enough for a joint objective: a cheaper acquisition choice could require a more expensive checker. A safe dominance test must also prove behavioral adequacy and the full cost inequality. Such a test may cost as much as evaluating the candidate, and no cheaper distinct dominance criterion was established here.

## Limits of the result

No general completeness proof is offered for source support pruning, no asymptotic advantage is proved, no extension to arbitrary attacks or active contracts is proved, and no hardware trust obligation is discharged. The demonstrated formal result is an exact reduction plus a conservative relaxation with explicit invalidity conditions. These results support **NO-GO** for the proposed novelty claim.
