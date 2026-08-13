# The mathematics of reasonsmith — migration stub

The gathered mathematics is now organized as numbered theory chapters. Read:

- [00-notation](theory/00-notation.md) for the global symbol table;
- [01-models](theory/01-models.md), [02-syntax](theory/02-syntax.md), and
  [03-semantics](theory/03-semantics.md) for the objects, grammar, and denotation;
- [04-decision-problems](theory/04-decision-problems.md) for the six questions this tool asks;
- [05-decision-procedures](theory/05-decision-procedures.md) for their procedures and soundness;
- [07-explanation](theory/07-explanation.md) and [08-evidence](theory/08-evidence.md), forthcoming,
  for the remaining explanation, certificate, and evidence mathematics; and
- [bibliography](theory/bibliography.md) for the repository-wide citation registry.

Chapters 04–05 replace the migrated language and engine material formerly in this file. This file
remains present until the later migration PRs land. The pending material below is intentionally
retained verbatim so its source claims and executable bindings remain reachable.

---

## Pending migration: reasons, evidence, and graded readings

## 3. Reasons

Fix one decision and its artefact `𝒜 = (F, β, q, R, without, …)` as in §1.3, and a tolerance `tol`
(`1e-9` by default). This section is [`sufficient-reasons.md`](sufficient-reasons.md) in the
notation of §1.3, with that document's `A` written `F`.

### 3.1 The deletion lattice

> **Definition 1 (deletion lattice).** For `D ⊆ F_q`, write `β[D↦0]` for `β` with every fact in `D`
> set to probability zero. The **deletion lattice** is `L(β) = { β[D↦0] : D ⊆ F_q }`, ordered by `⊆`
> on `D`, with `β` as its top element.

`L(β)` is the whole of what **this section** quantifies over, because `without` is the only
perturbation the certificate and the CXp enumeration call. It is no longer all the protocol can
reach — §3.6 records that reversal — and nothing below reads the wider surface. Giving a fact
probability zero deletes exactly the worlds in which it holds:

```
V(β[D↦0])  =  Pr_β[ φ_q ∧ ⋀_{a∈D} ¬a ]
```

> **Definition 2 (moved).** `MOVED(D) ⟺ |E(β) − E(β[D↦0])| > tol`.
>
> One evaluation of `MOVED` is one **engine probe**, which is the cost unit the budget counts.

This is not a classifier over a feature space, which is the setting the published definitions are
stated in. Two things differ and both matter: the decision is a **probability, not a label**, so
what is preserved is the engine's answer up to `tol` rather than an `f(v) = c`; and the perturbation
space these definitions range over is **not a product of feature domains**, so the interpretations
they reach are exactly those below `β` in the deletion order. Both differences make the definitions
below **weaker** than their counterparts, never stronger.

### 3.2 Sufficiency, AXp, CXp, relevance

The shape is the abductive explanation of `[@ignatiev-2019]` and its contrastive dual, with the
feature space replaced by `L(β)` and "same prediction" by "same answer within `tol`"; the
vocabulary of sufficient reasons is `[@darwiche-2020]` and its prime-implicant reading
`[@shih-2018]`.

> **Definition 3 (deletion-sufficient set).** `S ⊆ F_q` is **sufficient** for the engine's answer at
> `β` iff for every `D ⊆ F_q \ S`, `¬MOVED(D)`.

> **Definition 4 (AXp).** `S ⊆ F_q` is an **abductive explanation** iff it is sufficient and no
> proper subset of it is.

> **Definition 5 (CXp).** `C ⊆ F_q` is **contrastive** iff `MOVED(C)`, and a **CXp** iff it is
> contrastive and no proper subset of it is.

> **Definition 6 (relevance).** `a ∈ F_q` is **relevant** iff it belongs to some AXp, and
> **irrelevant** otherwise.

A CXp of size 1 is exactly what a per-fact probe can see. Every CXp of size ≥ 2 is a joint necessity
such a probe is blind to, and reading its absence as irrelevance was this instrument's sharpest
defect: two reasons jointly necessary and individually removable were both reported `deleted`, so
the tool accused a system of omitting two reasons its inference demonstrably used
(`test_two_jointly_necessary_reasons_are_no_longer_reported_deleted`).

### 3.3 Duality, and the declaration it rests on

Everything below needs `monotone = True`, and nothing below holds without it. That declaration was
added for a *soundness* reason — so that a lawfully retracted reason is not read as a dropped one —
and turns out to be exactly the precondition this theory needs. It is one premise, not two.

> **Lemma 1 (upward closure).** If `MOVED(D)` and `D ⊆ D'` then `MOVED(D')`.
>
> Under the declaration `E` is non-decreasing in `β`, so
> `E(β[D'↦0]) ≤ E(β[D↦0]) ≤ E(β)`, and `MOVED(D)` puts the middle term more than `tol` below the
> right one.

> **Lemma 2 (sufficiency is a hitting-set condition).** `S` is sufficient ⟺ `F_q \ S` is not moved
> ⟺ `F_q \ S` contains no CXp ⟺ `S` intersects every CXp.

> **Theorem (minimal-hitting-set duality).** The AXps are exactly the minimal hitting sets of the
> CXps, and the CXps exactly the minimal hitting sets of the AXps.
>
> This is the conflict/diagnosis duality of `[@reiter-1987]`, related to abductive and contrastive
> explanations by `[@ignatiev-2020]`. Lemma 2 is the only thing specialising it to `L(β)`.

> **Corollary 1.** `⋃ AXps = ⋃ CXps`; a fact is relevant iff it belongs to some CXp.

> **Corollary 2 (pruning).** A fact `a` with `MOVED({a})` belongs to no CXp of size > 1.

> **Corollary 3 (short circuit).** If `¬MOVED(F_q)` there is no CXp at all, every fact is
> irrelevant, and `∅` is the unique AXp — one probe settles the decision.

### 3.4 Reasons, not facts

The duty is about reasons, so the fact-level notion is lifted, and the lift is where a reason all of
whose facts are shared with another is answered as well as it can be.

> **Definition 7 (live).** `r ∈ R` is **live** iff some fact of `r` that no other reason in `R` uses
> is relevant.
>
> The privacy condition is what makes the conclusion *about `r`*: a shared relevant fact establishes
> that the engine depends on **that fact** and cannot say through which of the reasons carrying it.

> **Definition 8 (deleted).** `r ∈ R` is **deleted** iff **no** fact of `r` — private or shared — is
> relevant.
>
> No attribution problem arises, which is why the quantifier is over all facts. If no fact of `r` is
> relevant then by Corollary 1 no CXp meets `r`, so by Lemma 2 `F_q \ r` is sufficient: the answer
> survives the removal of the whole of `r` in every context `L(β)` reaches
> (`test_the_reason_the_engine_really_ignores_is_still_reported_deleted`).

> **Definition 9 (undetermined).** `r ∈ R` is **undetermined** iff it is neither live nor shown
> deleted: the CXp enumeration did not terminate within budget, or the only relevant facts of `r`
> are shared.

**The two claims have different quantifiers, and only one of them survives a partial search.** Live
is existential over CXps and one witness establishes it. Deleted is universal and is established
only by an enumeration that **terminated**. So a shorter search reports **fewer** missing reasons,
never more, and there is no setting of the budget at which this instrument accuses a system it would
otherwise have cleared. The cap, the probes spent and whether the enumeration terminated travel in
`details[PROBE_BUDGET_KEY]` exactly as `PROBE_BUDGET_FIELDS` forces, because how far it got is the
bound on every `deleted` (`test_the_certificate_verdict_carries_its_probe_budget`).

**The measurement.** Deciding relevance is hard, and the honest statement of how hard is the
`NP^PP`-completeness of `[@waldchen-2021]`, whose probabilistic setting is this one's shape. Here the
engine is a black box, so the only oracle is a probe. `explanations.contrastive_sets` enumerates
CXps with the seed/shrink/grow MARCO loop of `[@liffiton-2016]`, Z3 as the oracle over the subset
lattice — one Boolean per searchable fact, blocking clauses recording what is covered — and the
system's own engine as the membership oracle. Corollary 2 prunes the space and Corollary 3 is the
common case for a truncating engine.

### 3.5 The certificate, and the value gap

`Certificate.uncertified` is the union of three separately reported states — `unseparable` (no
private fact to attribute a movement to), `inconclusive` (the probe carried no exact signal at all)
and `undetermined` (Definition 9) — because each means the same thing to a verdict (*not counted
deleted, not counted live*) and different things to a reader.

The certificate runs a **second, independent** check on a different axis, and neither implies the
other. The **value gap** is `V(β) − E(β)`: both terms at the same `β`, nothing switched off. For a
top-`k` engine reporting `Pr_β[φ_kept]` it is `Pr_β[φ_q ∧ ¬φ_kept]` — the probability of exactly
those worlds in which the decision holds only by way of a proof the engine discarded. Write
`Δ(D) = V(β) − V(β[D↦0])`; then

```
Δ(D) = Pr_β[ φ_q ∧ ⋁_{a∈D} a ]
```

which is the measure of a union of events, hence **monotone and submodular** in `D`. `MOVED` is
merely **upward-closed** (Lemma 1) and is submodular in no sense — joint necessity *is* the
statement `MOVED({a,b}) ∧ ¬MOVED({a}) ∧ ¬MOVED({b})`, which no submodular indicator admits.

That asymmetry is the old defect in two lines: the old rule read the exact side one fact at a time,
where submodularity means single probes **over**-state what a fact exclusively carries, and read the
engine side one fact at a time, where mere upward-closure means single probes **under**-state what
the engine depends on. Both errors push toward `deleted` and they compose. A mass therefore licenses
a claim that the engine's *value* is wrong and **not** a claim that any particular reason is
irrelevant, and `Σ_r Δ(private facts of r)` is not the gap in either direction. No rendering adds
per-reason drops up, and none may start.

### 3.6 What is out of reach — and one reversal, recorded

- **The perturbation space *of §3* is not widened, and the protocol's is.** An AXp here is an AXp
  *relative to `L(β)`*, which is a weaker object than an AXp over a full feature space, and that
  has not changed. What has changed is the sentence this bullet used to carry, which said the
  protocol admits no perturbation but deletion. **That is a reversal and this is the record of it**,
  in the shape [`ROADMAP.md`](../ROADMAP.md) §2 records the `since` reversal, because a document
  that quietly drops a refusal it published is worse than one that never published it.

  **What was refused.** `artifacts.InferenceArtifact` stated that there is a `without(fact)` and
  deliberately no `with_(fact)`, and that adding one was work no verdict here is authorised to rest
  on. The ground for the refusal was the soundness of `deleted`: §3.1–§3.4 are stated over `L(β)`,
  Lemma 1 needs the deletion order, and a reason measured over a wider space would be a different
  object wearing the same name.

  **What changed.** A measurement was designed that never touches `deleted` and needs the width:
  §3.7. Its discrimination was measured to live in the *width* of the perturbation and in nothing
  cheaper — over the 16 generated instances of `docs/build_nesyarena_report.py`, a triple that only
  lowers a fact's probability and a triple that only raises it each refute a top-`k` engine on
  **none** of them, while the triple spanning `[0,1]` refutes `top-1-proofs` on 8 and `top-3-proofs`
  on 4 (`test_neither_one_directional_variant_refutes_a_top_k_engine`). A top-`k` engine's
  kept-proof set is locally constant, so `E` is locally multilinear and the kink appears only where
  the ranking changes. So `at : F × [0,1] → 𝒜` is admitted, **optionally**, by the captain's
  explicit decision of 2026-08-11.

  **What is still refused, and it is the whole of what the old refusal was protecting.** No
  definition in §3 quantifies over anything but `L(β)`; `certificate.py` and `explanations.py` call
  `without` and nothing else, which is checked rather than asserted
  (`test_the_deletion_probe_never_reaches_the_widened_perturbation`); every one of Lemma 1,
  Lemma 2, the duality theorem and Definitions 3–9 is unchanged and rests on the same one premise;
  and a family offering no `at` loses no verdict, because no requirement in this repository reads
  the wider surface at all. `reason_trace` deliberately offers none: a rationale the system
  recounted has no interpretation to move.
- **Defeat is not detected.** A defeater holding no fact of any enumerated reason is never switched
  off, leaves no fingerprint, and is refused at the declaration instead (§6.7).
- **A shared fact is not attributed.** Splitting a reason from its sharers is a question about the
  *program*, not about the probe.
- **The pass only ever moves a reason out of `deleted`.** Definition 8 would license promoting an
  `unseparable` or `inconclusive` reason into it, and the implementation deliberately does not:
  minting accusations out of a search whose completeness rests on a declaration nothing here
  confirms is a decision to make on purpose, not a corollary to fall into.

### 3.7 The claimed semantics, refuted over the wider surface

This is the one thing `at` is for, and it is not a verdict: `semantic_laws` returns no
`RequirementResult`, occupies no rung and is read by no requirement, the standing `ltlf.py` has.

An artefact carries a `claimed_semantics`, and §1.3 says what it is worth today — printed on the
certificate, checked by nothing. Write `S` for the semantics it names and `⟦·⟧_S` for its
denotation. The claim is

```
    (C)     ∀ β' ∈ [0,1]^F .  E(β') = ⟦P, β', q⟧_S
```

— about the black box `E` at *every* interpretation and not only at the `β` the decision was taken
at. Nothing on this evidence model establishes (C). Its **refutation** needs one witness, and that
is all this measures.

`claimed_semantics` is a name from `spec.CLAIMED_SEMANTICS`, closed and refused outside itself at
the artefact and certificate boundaries ([`semantics.md`](semantics.md) §3, *The semantics claim is
a closed vocabulary*). `semantic_laws.SEMANTICS_WITH_LAWS` is the subset of that vocabulary this
tool has laws for, and it has one member today. For it, `S` = distribution semantics and
`⟦P, β', q⟧_S = Pr_{β'}[φ_q]`.
Two laws are checked at each `a ∈ F_q`, over the three interpretations `β`, `β[a↦0]`, `β[a↦1]`:

```
    L2 (multilinearity)   E(β) = β(a)·E(β[a↦1]) + (1−β(a))·E(β[a↦0])
    L3 (monotonicity)     E(β[a↦0]) ≤ E(β) ≤ E(β[a↦1])
```

> **Proposition (refutation is sound).** If (C) holds then L2 and L3 hold at every `a ∈ F_q`.
> Hence a measured violation of either refutes (C).
>
> L2: `Pr_{β'}[ψ]` is affine in `β'(a)` for **every** propositional `ψ` — Shannon expansion,
> `Pr[ψ] = Pr[a]·Pr[ψ | a] + (1−Pr[a])·Pr[ψ | ¬a]`, with the two conditionals independent of
> `β'(a)` under the artefact's independent-facts reading of `β`. The step needs no premise about
> which facts `ψ` mentions, so it needs none about the artefact's enumeration being complete for
> `q`.
> L3: `φ_q` is a disjunction of conjunctions of **positive** literals (§1.3), so it is monotone,
> so `Pr_{β'}[φ_q]` is non-decreasing in each `β'(a)`. This is the same positivity §3.1 already
> uses and the one premise beyond L2's.

**Three things this deliberately does not claim.** Non-refutation is not agreement: refutation is a
lower bound on deviation, and on the shipped battery one provenance deviates on 16 instances and is
refuted on 12 (`test_the_battery_refutes_every_deviating_provenance_and_never_the_exact_one`). The
laws move one fact at a time, so a disagreement needing two facts moved together is not looked for —
the same blindness `MOVED` had before §3.2 lifted it, and it is not lifted here. And a claim the
vocabulary admits but no law here characterises — `weighted sum`, `free-text rationale` — is **not
evaluated** naming the claim, in the sense [`semantics.md`](semantics.md) §4 gives it: the gap is in
this tool, and running the laws of one semantics against a claim of another would refute a system
for implementing exactly what it said. A claim *outside* the vocabulary reaches no law at all,
because the artefact boundary refuses it first
(`test_a_claim_outside_the_vocabulary_never_reaches_this_module`); the two must not be collapsed,
since one says *this tool cannot answer* and the other says *this declaration is not admitted*
(`test_the_law_sets_name_a_subset_of_the_shipped_vocabulary`).

**Why the third law of the design is absent.** A vertex law — `β'` 0/1-valued ⟹ `E(β') ∈ {0,1}` —
needs a premise L2 and L3 do not: that `F_q` covers every fact `φ_q` mentions, so that fixing `F_q`
to a vertex fixes `φ_q`'s truth value. An artefact bounded by its own `exact_depth` cannot establish
that, and a law whose premise the instrument cannot check is a false-accusation machine. It is left
out rather than shipped with a caveat.

---

## 4. Evidence: two coordinates

A claim carries **how far it was pushed** and **what it is about**. These are different questions
and the answer is a product, not a longer chain.

### 4.1 The strength chain

`verdict.Strength` is a strict total order:

```
unattainable < observed < recounted < probed < proved
```

(`test_strength_lattice_ordering`; `test_the_formal_doc_states_the_chain_the_code_defines` generates
this sentence from the code rather than trusting it). Comparison against a non-`Strength` is refused
rather than coerced (`test_strength_comparison_rejects_foreign_types`).

| Rung | The method the result records |
|---|---|
| `unattainable` | the capability gate stopped evaluation before an engine ran |
| `observed` | a conclusion from the supplied trace |
| `recounted` | the deletion probe of §3, over a reason set the *system recounted* |
| `probed` | a conclusion by bounded replay through `decide()`, or the deletion probe over an enumerated reason set |
| `proved` | a conclusion by solver reasoning over the valuations the declared constraints admit |

The chain is the operational form of the *approximates or guarantees* question of `[@stan-2026]`
§6.3, with `probed` between the two and `unattainable` as the case that paper does not name: a
system that cannot produce the required record at all.

**What a comparison does not mean.** It is not a confidence score. A `proved` verdict over logic
that has nothing to do with the deployed system is worth less than an `observed` verdict over a year
of production decisions; the chain cannot see that, because it ranks *how* a conclusion was reached
and not *what about*. Strength is not comparable across requirements either: a duty discharged only
by a record check is not a weaker duty.

`strength = None` is **not a rung**. It means no engine here evaluated this requirement, and a result
carrying it cannot be `satisfied` or `violated` (`test_result_cannot_claim_more_than_its_evidence`).

### 4.2 The basis dimension

`verdict.EvidenceBasis` says what the claim is about. Four members, each named after a published
class of specification:

| Basis | What the evidence is about | Named after |
|---|---|---|
| `behavioural` | the system's executions, one at a time | a **trace property** `[@alpern-1985]` |
| `relational` | a *pair* of executions | a **2-safety property** `[@terauchi-2005]`, a hyperproperty `[@clarkson-2010]`, proved by self-composition `[@barthe-2004]`; the duty itself `[@kusner-2017]` |
| `artifact` | the inference *behind* a decision | the **abductive explanation** `[@ignatiev-2019]`, the model-precise side of formal XAI `[@marques-silva-2022]`; for `recounted`, **faithfulness** `[@jacovi-2020]`, measured by erasure `[@deyoung-2020]`, on evidence a self-report can fail to be `[@turpin-2023]` |
| `assessment` | how an open-textured predicate applies, per a named authority | a **truth degree over a residuated lattice** `[@hajek-1998]`; a degree of truth is not a degree of belief `[@dubois-2001]` |

**A basis is a kind and never a rank.** The members carry no order: `<`, `<=`, `>`, `>=` raise
between two bases and between a basis and a strength, so nothing can sort them into a ladder and no
basis has a `rank` (`test_the_evidence_bases_are_not_ordered`,
`test_a_basis_is_never_compared_against_a_strength`). This is the whole reason the answer is a
dimension and not four more rungs.

### 4.3 Which rungs each basis admits

`verdict.BASIS_RUNGS` is a relation `⊑ ⊆ Basis × Strength`, and it is read off what an engine can
actually reach rather than asserted:

| Basis | Admits |
|---|---|
| `behavioural` | `unattainable`, `observed`, `probed`, `proved` |
| `relational` | `unattainable`, `probed`, `proved` |
| `artifact` | `unattainable`, `recounted`, `probed` |
| `assessment` | `unattainable` |

(`test_the_formal_doc_states_the_basis_rungs_the_code_defines`.) Three of the absences are theorems
of the preceding sections rather than policy. `observed ∉ rungs(relational)` because a decision
record holds one execution and a 2-safety property needs two (§2.7). `proved ∉ rungs(artifact)`
because the enumeration is exact only on the one ground program and base interpretation it ran over
(§3.1), and `observed ∉ rungs(artifact)` because no trace holds the artefact. `assessment` admits no
rung at all because the chain ranks methods of interrogating a system and no system was interrogated
(§5.5). `unattainable` is in every row because it is not an engine's answer: the capability gate is
a set difference over declared signal names, identical for every duty, run before any basis is
consulted (`test_every_basis_admits_unattainable_so_the_capability_gate_is_never_bypassed`).

Three structural consequences:

1. **A result may not carry a rung its basis does not admit** — `RequirementResult.__post_init__`
   refuses one (`test_a_result_cannot_carry_a_rung_its_basis_does_not_admit`).
2. **The basis is derived from the requirement alone** — the certificate signal, then the fragment —
   so no pack field and no adapter can widen what a duty claims
   (`test_the_basis_is_derived_from_the_duty_and_never_declared`).
3. **The table and the ladders are held together in both directions**: no ladder may offer a rung
   its duty's basis refuses, and no basis may advertise a rung above the strongest any shipped
   ladder offers (`test_the_basis_admits_exactly_the_rungs_the_ladder_can_reach`).

### 4.4 The test for a new member

Evidence about a **different object** is a basis; evidence about the **same object, less deeply**,
is a rung. That test has been applied once: `recounted` is evidence about the inference behind a
decision — what `artifact` is already about — reached less deeply, so it is a rung on that row and
not a fifth basis (`test_a_recounted_reason_set_reports_one_rung_below_an_enumerated_one`,
`test_a_recounted_reason_set_cannot_be_reported_at_the_enumerated_rung`).

---

## 5. Graded readings

### 5.1 The algebra

`A = (A, ⊓, ⊔, ⊗, →, ¬, 0, 1)` is a **complete residuated lattice**: `⊓` and `⊔` are the lattice
meet and join, `⊗` is a commutative monoid operation with unit `1`, monotone in each argument, and
`→` is its residuum:

```
x ⊗ z ≤ y   ⟺   z ≤ x → y                    (residuation)
¬x = x → 0                                     (negation, derived)
x ↔ y = (x → y) ⊗ (y → x)                      (biresiduum, derived)
```

`𝔹 = {0, 1}` with `⊓ = ⊗ = ∧`, `⊔ = ∨` and `→` material implication is a degenerate instance, not a
separate system. Every fragment but `graded` is read there.

Negation and the biresiduum are **derived and not stored**, so a member of the table below is
internally consistent by construction rather than by three or four independent choices
(`test_each_algebra_is_a_residuated_lattice_on_the_grid`).

### 5.2 The three shipped algebras

`manyvalued.ALGEBRAS` carries the three fundamental continuous t-norms, from which every continuous
t-norm is an ordinal sum `[@hajek-1998]`:

| Name | `x ⊗ y` | `x → y` | `¬x` |
|---|---|---|---|
| `lukasiewicz` | `max(0, x + y − 1)` | `min(1, 1 − x + y)` | `1 − x` |
| `godel` | `min(x, y)` | `1` if `x ≤ y`, else `y` | `1` if `x = 0`, else `0` |
| `product` | `x · y` | `1` if `x ≤ y`, else `y / x` | `1` if `x = 0`, else `0` |

(`test_the_formal_doc_names_the_algebras_the_code_defines`.) Under Łukasiewicz the biresiduum works
out to `1 − |x − y|`, and in every algebra it is `1` exactly when the two degrees agree
(`test_lukasiewicz_equivalence_is_one_minus_the_distance`,
`test_the_biresiduum_is_one_exactly_when_the_degrees_agree`).

**Which algebra is a declared parameter of the pack** (`[grading] algebra`), refused at load when a
graded duty ships without one, and never a default: a conjunction of two halves is `0` under
Łukasiewicz, `0.5` under Gödel and `0.25` under product, so a default nobody read would be a
semantics this tool picked on a pack author's behalf
(`test_the_three_algebras_disagree_about_a_conjunction_of_two_halves`,
`test_a_two_valued_duty_cannot_acquire_a_degree`).

### 5.3 The degree of a formula

A **grading** `G` (`manyvalued.Grading`) is third-party evidence supplied to `check_conformance`
beside the pack: one degree per `predicate(signal)` for the whole run, together with the
**authority** that fixed the scale, what the scale is, and how the degrees were obtained. All three
are required, in the shape `PROBE_BUDGET_FIELDS` forces on a bounded search
(`test_a_grading_must_state_who_fixed_the_scale`). A degree is never read off the system under test
or off its trace: a degree a system asserts about itself is a self-declaration wearing a lattice's
clothes.

`degree_of` reads §2.5's connectives over the declared algebra **above** a graded atom, and hands
every subtree containing none to the two-valued reference interpreter, mapping the result to
`1.0`/`0.0`. That is not an optimisation: it is what keeps the crisp parts of a graded formula
meaning exactly what they mean everywhere else, `present()`'s blank string and `contains()`' fold
included (`test_the_crisp_parts_of_a_graded_formula_mean_what_they_mean_everywhere_else`).

Over a trace, `degree_over_trace` is the infimum of the per-record degrees — §2.6's `⨅`, and not
`⊗` — and it raises on the empty trace rather than returning the lattice top
(`test_the_degree_of_a_trace_is_the_infimum_of_its_records`).

### 5.4 What a degree is not

- **A degree is never a verdict.** Nothing turns one into `satisfied`, because that needs a
  threshold no statute states. A graded result is `inconclusive` at `strength=None` and carries the
  degree as a measurement; `render.degree_sentence` is the one place any rendering formats one.
- **A threshold may not be written into a pack.** A graded atom under a comparison or under
  arithmetic is a load error — the first asks for a number on an undefined scale, the second states
  the pack author's cut-off as the regulation's
  (`test_a_graded_atom_under_arithmetic_or_a_comparison_is_refused`).
- **An unscored atom is not a degree of zero**, and an empty trace is not a degree of one. Both are
  *not evaluated* (`test_an_ungraded_atom_is_not_evaluated_and_never_a_degree_of_zero`).
- **A degree is not a probability and not a fraction of a proof** `[@dubois-2001]`. Vagueness is not
  missing information: *sufficiently detailed* has no sharp boundary even when every fact is known,
  which is the case two-valued logic mishandles and many-valued logic exists for.

### 5.5 Neither open-texture fragment reaches an engine

---

## Bibliography

The bibliography registry is maintained in [`theory/bibliography.md`](theory/bibliography.md); citations in this document retain the repository-wide citation-key convention.