# 7 — Explanation

This chapter is a distinct formalism from Chapters 1–5. It concerns an inference artefact and the
reasons it exposes for one decision, not the denotation of a property over a trace or input space.
Its perturbations are the deletions admitted by `artifacts.InferenceArtifact`; its oracle is the
system's own engine, and its exact side is the artefact's exact inference.

## 7.1 Setting and perturbations

Fix one decision and an artefact with fact set `F`, base interpretation `β`, query `q`, reason
family `\mathcal{R}`, and tolerance `tol` (the default is `1e-9`). Write

$$
\mathcal{R}=\{u_1,\dots,u_n\},\qquad u_i\subseteq F,\qquad
F_q=\bigcup_i u_i,
$$

and let `φ_q` be the disjunction of conjunctions whose supports are the `u_i`. The artefact's
exact inference is `V(β)`; the audited engine's answer is `E(β)`. Both are evaluated on the same
program and interpretation. The engine is a black box here, except for the monotonicity
 declaration required by Definition 7.7.

**Definition 7.1 (deletion lattice).** For `S\subseteq F_q`, let `β[S↦0]` be `β` with every fact in
`S` assigned probability zero. The deletion lattice is

$$
\mathbb{L}(\beta)=\{\beta[S\mapsto0]:S\subseteq F_q\},
$$

ordered by inclusion of deletion subsets, with `β` at its top. This is the whole perturbation
space used by this chapter. The optional `at(fact, probability)` surface is not read by any
statement below.

The exact side obeys

$$
V(\beta[S\mapsto0])=\Pr_\beta[\varphi_q\wedge\bigwedge_{a\in S}\neg a],
$$

because assigning a fact probability zero removes exactly the worlds in which that fact holds.

**Definition 7.2 (moved).** A deletion subset `S` is moved when

$$
\mathrm{MOVED}(S)\Longleftrightarrow
|E(\beta)-E(\beta[S\mapsto0])|>tol.
$$

One evaluation of `MOVED` is one engine probe and is the unit counted by the budget.

## 7.2 Sufficiency and the two explanation families

**Definition 7.3 (deletion-sufficient set).** A set `S\subseteq F_q` is sufficient for the engine's
answer at `β` when every deletion subset contained in `F_q\setminus S` is not moved. Holding `S`
on, nothing outside `S` can be deleted without changing the answer.

**Definition 7.4 (AXp).** An abductive explanation (AXp) is a sufficient set with no proper
sufficient subset.

**Definition 7.5 (CXp).** A set `C\subseteq F_q` is contrastive when `MOVED(C)` holds. A CXp is a
contrastive set with no proper contrastive subset. A singleton CXp is exactly what a per-fact probe
can see; a larger CXp is a joint necessity that such a probe can miss.

**Definition 7.6 (relevance).** A fact `a\in F_q` is relevant when it belongs to some AXp, and is
irrelevant otherwise.

These definitions specialise the abductive/contrastive explanation vocabulary to the deletion
lattice and replace preservation of a classifier label with preservation of the engine's answer
within `tol` (`[@ignatiev-2019]`, `[@darwiche-2020]`, `[@shih-2018]`). They are weaker than a
feature-space definition: this chapter quantifies only over `\mathbb{L}(\beta)`.

## 7.3 Monotonicity and duality

The artefact declares whether its inference is monotone in its facts. This is one premise, not two:
without it, a retracted reason and a deleted reason are indistinguishable to the one-directional
probe.

**Lemma 7.7 (upward closure).** If `MOVED(S)` and `S\subseteq T`, then `MOVED(T)`.

Under the declaration, deletion cannot increase the engine's answer:
`E(β[T↦0])\le E(β[S↦0])\le E(β)`. The definition of `MOVED(S)` therefore gives `MOVED(T)`.

**Lemma 7.8 (hitting-set condition).** A set `S` is sufficient if and only if `F_q\setminus S` is
not moved, if and only if it contains no CXp, if and only if `S` intersects every CXp.

The first equivalence is Definition 7.3 at `F_q\setminus S`; the remaining equivalence uses
Lemma 7.7.

**Theorem 7.9 (minimal-hitting-set duality).** The AXps are exactly the minimal hitting sets of the
CXps, and the CXps are exactly the minimal hitting sets of the AXps.

This is Reiter's minimal-hitting-set duality between conflicts and diagnoses, specialised here by
Lemma 7.8 to `\mathbb{L}(\beta)` (`[@reiter-1987]`, `[@ignatiev-2020]`).

**Corollary 7.10 (union).**

$$
\bigcup \mathrm{AXp}=\bigcup \mathrm{CXp}.
$$

A fact is relevant exactly when it belongs to some CXp.

**Corollary 7.11 (singleton pruning).** If `MOVED(\{a\})`, then `a` belongs to no CXp of size greater
than one, because a minimal contrastive set cannot properly contain that singleton.

**Corollary 7.12 (short circuit).** If `MOVED(F_q)` does not hold, there is no CXp, every fact is
irrelevant, and the empty set is the unique AXp. One probe settles the decision.

## 7.4 Reasons rather than facts

**Definition 7.13 (live reason).** A reason `u_i\in\mathcal{R}` is live when some fact of `u_i` that
no other member of `\mathcal{R}` uses is relevant. A shared relevant fact establishes dependence on
the fact but cannot attribute that dependence to one of the reasons that carries it.

**Definition 7.14 (deleted reason).** A reason `u_i\in\mathcal{R}` is deleted when no fact of `u_i`,
private or shared, is relevant. In that case no CXp meets `u_i`, so Lemma 7.8 makes
`F_q\setminus u_i` sufficient throughout `\mathbb{L}(\beta)` (`test_the_reason_the_engine_really_ignores_is_still_reported_deleted`).

**Definition 7.15 (undetermined reason).** A reason is undetermined when it is neither live nor shown
deleted: the CXp enumeration did not terminate within budget, or its only relevant facts are shared.

Live is existential: one CXp witness establishes it. Deleted is universal: it requires a complete
enumeration. A partial search therefore never reports more deleted reasons; it can only leave reasons
undetermined. `unseparable`, `inconclusive`, and `undetermined` remain separately reported states,
while `Certificate.uncertified` is their union. The implementation deliberately never promotes an
`unseparable` or `inconclusive` reason into `deleted` (`test_a_reason_the_probe_cannot_separate_is_never_promoted_to_deleted`).

## 7.5 Certificate and value gap

A certificate is the measured result of the deletion search together with the exact and engine
values at the unperturbed interpretation. It certifies neither legal adequacy nor correctness of a
reason's wording. Its deleted-count claim is about the decisions whose artefacts enumerated at least
one reason; a zero enumerated reason is no measurement of a zero deleted count.

**Definition 7.16 (value gap).** The value gap is

$$
V(\beta)-E(\beta),
$$

with both values computed at the same `β`, before any deletion. For a top-`k` engine that retains a
set of proofs, it is the probability of worlds satisfying `φ_q` only through a discarded proof.

For the exact side, write

$$
\mathrm{Gap}(S)=V(\beta)-V(\beta[S\mapsto0])
=\Pr_\beta[\varphi_q\wedge\bigvee_{a\in S}a].
$$

`Gap` is monotone and submodular as a measure of a union. `MOVED` is only upward-closed by Lemma
7.7; it is not submodular. In particular, joint necessity is
`MOVED({a,b})` together with neither singleton moved. The value gap therefore licenses a claim about
the engine's value, not about any particular reason, and sums of per-reason deletion changes are not
the value gap.

## 7.6 Enumeration, budget, and partial claims

`explanations.contrastive_sets` uses the MARCO seed/shrink/grow loop, Z3 as the subset-lattice
oracle, and the engine as the membership oracle (`[@liffiton-2016]`). Singleton-moving facts are
pruned by Corollary 7.11. A moved seed is shrunk to a CXp and its supersets are blocked; an unmoved
seed is grown to a maximal unmoved set, whose complement is an AXp by Lemma 7.8, and its subsets are
blocked. Unsatisfiability of the map solver means every subset is covered and every CXp has been
found.

The searchable space is exponential in `|F_q|` in the worst case. The corresponding classifier
sufficiency problem is `NP^PP`-complete, a warning about the cost of the probabilistic setting and
not a claim that this black-box implementation decides every instance (`[@waldchen-2021]`).

**Definition 7.17 (probe budget record).** A bounded run carries its cap, probes spent, and whether
the enumeration terminated in `details[PROBE_BUDGET_KEY]`, as required by
`PROBE_BUDGET_FIELDS` (`test_the_certificate_verdict_carries_its_probe_budget`). A bound that the reader cannot see cannot qualify a universal claim.

If the budget is exhausted before the map solver is unsatisfiable, every CXp already found remains a
CXp and every live reason retains its existential witness. No reason may be called deleted, because
that requires the universal conclusion supplied by termination; unresolved reasons are
undetermined. Thus a partial enumeration reports fewer missing reasons, never more.

## 7.7 Claimed semantics and measured refutation

The explanation certificate and the semantic-law measurement are distinct. `semantic_laws` returns
no `RequirementResult`, occupies no rung, and is read by no requirement.

**Definition 7.18 (claimed semantics).** Let `S` be a member of the closed vocabulary
`spec.CLAIMED_SEMANTICS`. The claim made by an artefact is

$$
(C)\qquad E(\beta')=\llbracket\Pi,\beta',q\rrbracket_S
$$

for every interpretation `β'` in the product of fact probabilities. The vocabulary admits the
claim; this tool does not establish it.

For the one semantics with laws, the right side is the distribution-semantics exact probability.
For each `a\in F_q`, the measured laws are

$$
\mathrm{L2}\qquad E(\beta)=\beta(a)E(\beta[a\mapsto1])+(1-\beta(a))E(\beta[a\mapsto0]),
$$

$$
\mathrm{L3}\qquad E(\beta[a\mapsto0])\le E(\beta)\le E(\beta[a\mapsto1]).
$$

**Proposition 7.19 (law refutation).** If (C) holds, L2 and L3 hold at every fact `a\in F_q`.
Therefore a measured violation of either law refutes (C). L2 follows from the affine decomposition of
an independent fact probability; L3 follows from the positive-literal formula `φ_q`.

Non-refutation is not agreement. The laws move one fact at a time, so they do not find a disagreement
requiring two facts to move together. A vocabulary member for which this tool has no law is not
evaluated, naming the claim; a name outside the vocabulary is refused at the artefact boundary
(`test_a_claim_outside_the_vocabulary_never_reaches_this_module`, `test_the_law_sets_name_a_subset_of_the_shipped_vocabulary`,
`test_neither_one_directional_variant_refutes_a_top_k_engine`,
`test_the_battery_refutes_every_deviating_provenance_and_never_the_exact_one`,
`test_the_deletion_probe_never_reaches_the_widened_perturbation`).
The vertex law is absent because an artefact bounded by its own exact depth cannot establish that
`F_q` covers every fact mentioned by `φ_q`; without that premise, the law would create a false
accusation.

## 7.8 Limits

The perturbation space is downward-only even though a family may optionally expose `at`: every
explanation definition and every certificate probe calls `without` and nothing else. The formalism
does not detect a defeater with no fact in an enumerated reason, does not attribute a shared fact to a
single reason, does not make reasons correct, and does not measure a group of reasons collectively.
These are limits of the object defined here, not claims supplied by a verdict.
