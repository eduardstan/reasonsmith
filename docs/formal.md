# The mathematics of reasonsmith

This document states, once and in one notation, the mathematics the rest of this repository
implements: the objects a conformance run is about, the denotation of the property language, the
definition of a sufficient reason and of the deletion certificate, the two coordinates a verdict
carries, the graded readings, and one soundness statement per engine. The repository's
**bibliography** is maintained separately as a registry the build enforces rather than a list.

**Nothing here is new.** Every definition below already exists somewhere in the tree — in
[`theory/02-syntax.md`](theory/02-syntax.md), [`semantics.md`](semantics.md),
[`sufficient-reasons.md`](sufficient-reasons.md), or in the module that implements it. This
document gathers them into one notation and one place; it derives nothing further, extends nothing,
and introduces no construct, engine, rung or basis. A reader who finds a definition here that is
nowhere else has found a defect in this document.

**What this document owns, and what the others keep.** The bibliography registry lives in
[`theory/bibliography.md`](theory/bibliography.md): every citation anywhere in this repository
resolves to an entry there, and the mechanism that enforces that is stated there. This document
owns the gathered notation and formal claims; it does not own the operational documents. [`semantics.md`](semantics.md) states
what a verdict means to a reader of a report; [`theory/02-syntax.md`](theory/02-syntax.md) states the grammar and
the refusals a pack author meets; [`sufficient-reasons.md`](sufficient-reasons.md) states the
argument that led to the reason definitions and the cost of each choice. Those documents keep their
own phrasing on purpose, and drift between them and this one is prevented mechanically rather than
by care: **every definition the code also defines is generated from the code in each document that
states it**, so three documents agreeing with `Strength`, `BASIS_RUNGS`, `rulelang.FRAGMENTS` and
`manyvalued.ALGEBRAS` cannot disagree with each other. `tests/test_docs_formal.py` is this
document's half of that, and it also checks that every `test_*` named below resolves to a test that
exists.

**Where this document and the code disagree, the code is right and this document has a defect.**

**Every claim names the test that falsifies it**, inline rather than in a table at the end — a
second list of the same pairs would be a second place to drift. A definitional clause with no
executable consequence is either wrong or not worth stating; the three places one is stated anyway
say so in the clause, and each is a clause about what is *deliberately absent*, which no test can
witness by running.

**One notation collision is resolved here, and it is the only renaming.**
[`sufficient-reasons.md`](sufficient-reasons.md) writes `A` for an artefact's fact set and
[`theory/02-syntax.md`](theory/02-syntax.md) writes `A` for the algebra a formula is read over. In one document
they cannot both be `A`. The algebra keeps `A` and the fact set becomes `F`; §3 is written in `F`
throughout and is otherwise word-for-word the same mathematics.

---

## 1. Objects

### 1.1 Signals, records, traces

Fix a countable set `Σ` of **signal names** and a set `Val` of values.

- A **decision record** is a finite partial map `r : Σ ⇀ Val`. `sut.decisions()` yields these.
- A signal `x` is **present** in `r` when `r(x)` is defined and is not `None`, not the blank
  string, and not an empty list, dict, set or tuple (`report._is_present`). `0` and `False` are
  present; an empty reason list is not (`test_a_present_but_empty_signal_does_not_count_as_evidence`,
  `test_a_falsy_but_real_signal_value_counts`).
- A **trace** is a finite sequence `σ = r₀ … r_{n−1}` of records. `|σ| = n`. The empty trace is `ε`.

A trace is a sample chosen by whoever produced it. Nothing in this repository establishes that it
is representative, complete or unfiltered, and every soundness statement in §6 is relative to the
trace it was given.

### 1.2 The system under test

A **system** exposes up to five things (`sut.SystemUnderTest`, plus two methods deliberately
outside the protocol because neither is a capability a system must have):

| | Reads | Kind |
|---|---|---|
| `capabilities()` | a set `C ⊆ Σ` of signal names the system can emit | declaration |
| `decisions()` | a trace σ | evidence |
| `logic()` | a **declaration** `L`, or nothing | declaration |
| `decide(case)` | a record, for a replayed input | procedure |
| `artifact(d)` | the inference behind decision `d` | procedure |

A **declaration** is `L = (Var, sorts, rules, constraints, computes)`: a set of variable names, a
sort per name, a rule block, a constraint set over the free inputs, and the subset
`computes ⊆ Var` of names the rules produce. `Var \ computes` are the names the system's situation
supplies; a name in neither is a name the system has **no notion of**, and the three states are
distinguishable only because `computes` is declared (§6.6). `RulesAdapter` derives `computes` from
its rules' assignment targets, and a `computes` name outside `Var` is refused at construction.

A capability declaration is authoritative only when the system made it. An adapter that derived one
from a trace marks itself `capability_basis = "trace"`, and findings resting on it are worded as
being about that trace (`test_unattainable_from_a_trace_does_not_speak_for_the_system`).

### 1.3 The inference artefact

An **inference artefact** for one decision (`artifacts.InferenceArtifact`) is

```
𝒜 = (F, β, q, R, without, exact_depth, monotone, reasons_are_exact)   [ , at ]
```

- `F` — the **facts**, whatever the artefact treats as switchable. For the one shipped ground-program
  family these are the EDB atoms of a nesyarena ground program.
- `β : F → [0,1]` — the **base interpretation**, one independent probability per fact.
- `q` — the decision, as a query atom.
- `R = {r₁, …, r_n}` with each `rᵢ ⊆ F` — the **reasons**: every support bounded proof enumeration
  finds for `q` at the artefact's own `exact_depth`. Write `F_q = ⋃ᵢ rᵢ`.
- `without : F → 𝒜` — the **deletion** perturbation, `without(a) = 𝒜[β ↦ β[a↦0]]`. It is the only
  perturbation §3 quantifies over and the only one the certificate calls; §3.1 is the whole
  consequence.
- `at : F × [0,1] → 𝒜` — **optional**, and present on the ground-program family only:
  `at(a, v) = 𝒜[β ↦ β[a↦v]]`, with `without(a) = at(a, 0)`. Read together with `probability : F →
  [0,1]`, which returns `β(a)`; a family offering both admits an arbitrary interpretation over one
  fact and a family offering neither is reached by every shipped verdict all the same, because
  nothing in §3 and no engine in §6 calls it (`test_the_deletion_probe_never_reaches_the_widened_perturbation`).
  §3.6 records what admitting it reversed and §3.7 is the one measurement that uses it.
- `monotone ∈ {True, False, None}` — whether the artefact's inference is monotone in its facts.
  It is **required**, not defaulted, and `None` is refused rather than read as `True` (§6.7).
- `reasons_are_exact ∈ {True, False}` — whether `R` was enumerated from a model encoding or
  **recounted** by the system about its own inference. Silence claims the weaker reading, which is
  the opposite default from `monotone`, because guessing monotone accuses a compliant system while
  guessing recounted only understates one (`test_a_family_that_does_not_say_claims_the_weaker_rung`).

Two further maps are the artefact's own arithmetic: `V(β) = Pr_β[φ_q]`, the exact weighted model
count of the decision's DNF `φ_q = ⋁ᵢ ⋀_{a ∈ rᵢ} a`; and `E(β)`, the **engine's** answer to `q` on
the same program and the same `β`. `E` is a black box and the only thing assumed of it is the
monotonicity `monotone` declares.

`artifacts/ground_program.py` is one adapter over a nesyarena `GroundProgram` and
`artifacts/reason_trace.py` is the second family. The protocol names no representation
(`test_the_protocol_is_satisfiable_without_a_ground_program`,
`test_the_ground_program_family_is_one_adapter_and_the_protocol_names_no_representation`).

### 1.4 Requirements, and the two gates

A **requirement** (`spec.Requirement`) carries exactly fifteen fields. Five are mathematical and the
rest are provenance:

- `spec` — the property, a formula of the language of §2;
- `formalism` — which **fragment** it belongs to, refused at load if it is not the one
  `classify_fragment` finds;
- `requires ⊆ Σ` — the non-empty **capability gate**: the signals a system must be able to emit for
  the duty to be checkable at all;
- `scope`, `domains` — the two **reach gates**, a regulatory class and a set of decision domains.

The gates compose as follows, and the order is the definition (`report._inapplicability`, then
`report._evaluate_requirement`). For a system with declared class `c`, declared domains `D` and
capabilities `C`:

```
   scope ≠ ∅ and c ∉ scope            ⟹  not_applicable          (no strength)
   domains ≠ ∅ and D ∩ domains = ∅    ⟹  not_applicable          (no strength)
   requires ⊄ C                        ⟹  unattainable, inconclusive
   otherwise                           ⟹  the ladder of §6.8
```

`requires` is a **conjunction**, which is why a signal read only inside a disjunction is exempt from
it: gating one branch of an either/or clause reports a system that lawfully took the other branch
`unattainable` without running it
(`test_the_loader_lets_a_disjunct_go_ungated_but_not_the_rest_of_the_property`,
`test_a_disjunction_of_magnitudes_gates_its_signals`).

An undeclared class or domain gives `not_applicable`, never `satisfied`
(`test_an_undeclared_system_cannot_reach_satisfied_on_a_domain_limited_duty`). Neither gate models
the **trigger inside a decision** — 12 CFR 1002.9 fires on adverse action, not on being a creditor —
and §6.9 is the one rule that reaches part of that.

### 1.5 Verdicts and results

A **verdict** is one of `satisfied`, `violated`, `inconclusive`, `not_applicable`
(`verdict.Verdict`). Combination is worst-case, and the empty combination is `inconclusive` and
deliberately **not** the vacuously true `satisfied` of an empty conjunction: a conformance verdict
is a claim about evidence, and having checked nothing is not evidence
(`test_verdict_combination`, `test_combining_no_verdicts_is_not_satisfied`).

A **result** (`report.RequirementResult`) is a verdict together with a strength, a basis and its
measurements. Its `__post_init__` is the enforcement point, and the whole of §4 is what it enforces:
a result claiming more than it has cannot be constructed
(`test_result_cannot_claim_more_than_its_evidence`,
`test_a_string_verdict_or_strength_is_parsed_not_trusted`).

---

## 2. The language

[`theory/02-syntax.md`](theory/02-syntax.md) Definition 2.2 defines the **grammar**, the kind discipline, the side conditions
and the twenty-eight named refusals; that is syntax and is not restated here. This section is the
**denotation**, in the notation of that document's §2, which it is a compression of and not a second
statement.

### 2.1 The signature

```
⟦·⟧_{M,A} : Spec → (𝒫(Trace_M) ⇀ A)
```

A formula denotes a **partial** map from *sets of traces* to a value in an algebra `A`, relative to
a structure `M`. Three parameters, each taken in its uniform reading:

- **`M`, the structure** — a finite trace or an input space (§2.2). The rungs of §4's chain are
  different instantiations of this one denotation, not two denotations joined by a bridge theorem.
- **`𝒫(Trace_M)`, sets of traces** — uniformly, in the sense of `[@clarkson-2010]`. This is how the
  relational atom is typed: it is a 2-safety property `[@terauchi-2005]` and so not a property of any
  single execution. Three quarters of the language pays nothing for this, by the factoring theorem
  of §2.6.
- **`A`, the algebra** — a complete residuated lattice (§5). `𝔹` is a degenerate instance of that
  and not a separate system.

`⇀` is a partial map, and the partiality is the point of half this package: a formula with no value
on the evidence supplied is *not evaluated*, never satisfied and never violated.

### 2.2 Structures

- **`O(σ)`, an observation structure** — a finite trace σ; `Trace_{O(σ)} = {σ}`. Names are read out
  of a record, and a name a record does not carry is not an error but the question `present()` asks.
  This is `sut.decisions()`.
- **`D(L)`, a declaration structure** — a declaration `L` as in §1.2. `Trace_{D(L)}` is every finite
  sequence of records each of which is an execution of `rules` on an input satisfying `constraints`.
  This is `sut.logic()`.

Replay is not a third structure. It yields `T ⊆ Trace_{D(L)}` for the `L` the system implements but
does not expose, and that containment *is* the content of the `probed` rung: the same denotation on
a subset, which can refute a universal claim and cannot establish one
(`test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach`,
`test_probed_never_rounds_up_to_proved`).

### 2.3 Partiality, and when it resolves

Write `↑` for *undefined*. Four things make a formula undefined at a point, and each is *not
evaluated* rather than a verdict: a name the structure does not interpret; a value of the wrong sort
for the operation asked of it; an atom no supplied evidence scores; and `undetermined(...)`, which
is `↑` by construction at every structure and every algebra (§2.8).

Undefinedness does not simply propagate. The rule is **insensitivity**:

> `⟦φ⟧` is defined at a point when its value is the same for every value in `A` its undefined
> subformulas could take, and `↑` otherwise.

That is what makes the reference interpreter's short-circuit correct rather than a shortcut:
`0 ⊗ a = 0` for every `a` in every algebra here. The Z3 encoding is strict instead, so it reports
`↑` where the definition resolves — an incompleteness of one implementation and never an
unsoundness, since it refuses where the definition answers
(`test_the_encoder_and_the_interpreter_answer_the_same`).

### 2.4 State formulas

`⟦φ⟧^rec_{M,A}(r) ∈ A` for a formula of the `record`, `logical` or `graded` fragment at a record `r`.
Four of the six rows are **crisp** — value `0` or `1` even when `A` is not `𝔹` — and that is a claim
about the language and not about the algebra:

| Atom | `⟦·⟧^rec(r)` |
|---|---|
| `present(x)` | `1` if `x` is present in `r` (§1.1), else `0` |
| `contains(x, "p")` | `1` if `r(x)` is a statement containing `p` under the ASCII fold, else `0`; `↑` if `r(x)` is present and is not a statement |
| `e₁ ⋈ e₂` | `1` if the comparison holds of the two values, else `0`; `↑` if either is `↑` |
| `x` (bare Boolean atom) | `1` if `r(x)` is `True`, `0` if `False`, `↑` otherwise |
| `degree(x, "q")` | `G(q(x)) ∈ A`, the degree the supplied `Grading` assessed; `↑` if it assessed none |
| `undetermined(x, "q", "a")` | `↑`, always |

`contains()` is `0` and not `↑` where the record carries nothing, which is what lets an implication
guarded by `present()` decide a duty biting only where a statement was made; it is `↑` and not `0`
where the record carries something that is not a statement, because `0` would report a system
satisfied on a field nothing read. The fold is ASCII-only and one-to-one so that the interpreter,
the synthetic per-record flag and the Z3 regular language agree
(`test_the_solvers_fold_is_the_interpreters_fold`).

The value layer beneath the comparisons is ordinary arithmetic with two choices that had to be made
to agree across two implementations: `/` is true division, `↑` at a zero divisor, and `%` follows
Python's floor-based remainder rather than Z3's non-negative `mod`
(`test_division_is_true_division_on_both_sides`,
`test_modulo_follows_python_semantics_for_any_divisor`).

### 2.5 Connectives

| Formula | `⟦·⟧` |
|---|---|
| `not φ` | `¬⟦φ⟧` |
| `φ and ψ` | `⟦φ⟧ ⊗ ⟦ψ⟧`, the strong conjunction |
| `φ or ψ` | `⟦φ⟧ ⊕ ⟦ψ⟧`, the dual t-conorm |
| `φ -> ψ`, `φ => ψ`, `φ implies ψ`, `Implies(φ, ψ)` | `⟦φ⟧ → ⟦ψ⟧`, the residuum |
| `φ <=> ψ`, `φ <-> ψ`, `Iff(φ, ψ)` | `(⟦φ⟧ → ⟦ψ⟧) ⊗ (⟦ψ⟧ → ⟦φ⟧)`, the biresiduum |

Over `𝔹` every row is the classical connective, so nothing two-valued moves
(`test_the_interpreter_reads_equivalence_as_the_truth_table`,
`test_the_solver_reads_equivalence_as_the_truth_table`). Over a residuated lattice `<=>` and `==`
are different formulas: the first is the biresiduum, the second a crisp comparison of two degrees —
a threshold — which §5.4 refuses
(`test_a_graded_comparison_the_author_wrote_is_still_refused`).

**`⊗` and `⊓` are two different conjunctions and the code uses both.** `and` is `⊗`; quantification
over positions and over traces is the lattice infimum `⊓`. Over `𝔹` they coincide, which is why
nothing two-valued ever had to notice
(`test_the_degree_of_a_trace_is_the_infimum_of_its_records`).

### 2.6 Traces, sets of traces, and the factoring theorem

For every fragment but `counterfactual`:

```
⟦φ⟧^tr(σ)   =  ⨅_{i < |σ|}  ⟦φ⟧^rec(σᵢ)        for a state formula φ
⟦φ⟧^set(T)  =  ⨅_{σ ∈ T}    ⟦φ⟧^tr(σ)
```

with `⨅` the lattice infimum. A temporal formula's trace value is `⟦φ⟧^pos(σ, 0)`.

> **Factoring.** For every fragment but `counterfactual`, `⟦φ⟧^set` factors through the traces
> individually. So an implementation reading one trace at a time is a correct implementation of the
> set-valued denotation, and the reports this tool emits carry `⟦φ⟧^tr(σ)` for the single supplied σ.

That is the cost the uniform typing buys back. The uniformity was still taken, and the reason is
`counterfactually_invariant` (§2.7), the one atom for which the factoring fails.

**The empty set and the empty trace are deliberately not the top of the lattice.** Mathematically
`⨅ ∅ = 1`. This package narrows the denotation at exactly that point:

```
⟦φ⟧^set(∅) = ↑          ⟦φ⟧^tr(ε) = ↑
```

An empty trace is *not evaluated* rather than satisfied, combining zero verdicts is `inconclusive`,
and `manyvalued.degree_over_trace` raises rather than returning `1.0`. Having observed nothing is
not evidence, and it is not evidence graded any higher than it is evidence Boolean
(`test_an_empty_trace_is_not_evidence`,
`test_a_graded_duty_with_no_grading_or_no_trace_is_not_evaluated`,
`test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable`). This is the
one place the code departs from the mathematics on purpose, and it is stated for that reason even
though it changes no formula.

### 2.7 The relational atom

`counterfactually_invariant(o, p)` is the whole of the `counterfactual` fragment and the one place
`⟦·⟧^set` does not factor. Over a declaration structure `D(L)`:

```
⟦counterfactually_invariant(o, p)⟧^set_{D(L)}(T) = 1
  iff  for every pair of records r, r′ occurring in traces of T that arise from admissible inputs
       agreeing on every input variable except p,   r(o) = r′(o).
```

This is counterfactual fairness `[@kusner-2017]` read as a 2-safety property `[@terauchi-2005]`,
hence a hyperproperty and not a trace property `[@clarkson-2010]`; self-composition `[@barthe-2004]`
is the proof method §6.6 uses.

Over an observation structure `O(σ)` it is **`↑`, and no engine may compute it**. The reason is not
that a hyperproperty cannot be evaluated on a subset — this one is subset-closed. It is that
refuting it needs a pair differing in `p` *and in nothing else*, and a log supplies no such pair
except by coincidence and no way to certify that a pair is one. The refusal lives in
`rulelang.eval_expression`, which every trace-reading engine evaluates through, so it is a fact
about the code and not a convention (`test_no_engine_can_evaluate_the_atom_against_a_decision_record`,
`test_the_ladder_for_this_fragment_carries_no_trace_rung`).

Two consequences, both enforced. **The atom does not compose**: a conjunction, negation or
implication over it is a strictly larger claim and nothing here discharges one
(`test_the_atom_is_the_whole_spec_or_no_part_of_one`). **Unawareness is not invariance**: if `L` has
no notion of `p` there are no admissible pairs, the condition is vacuously `1`, and reporting that
as `satisfied` would certify an unaware system as provably fair — so the engine reports
`unattainable` (`test_a_system_with_no_notion_of_the_protected_variable_is_unattainable`).

### 2.8 Where there is no reading in a general `A`

Three, stated rather than invented. Each is a clause about a deliberate absence, which is why each
names the refusal that enforces it rather than a test that could exhibit a value.

1. **`undetermined(x, "q", "a")` has no value in any `A`** — not `0`, not `1`, not a degree. The
   construct says a predicate the law states without a sharp boundary is settled by a named
   authority outside this tool, and any value at all would be this tool guessing. The *authority* is
   what the result reports instead
   (`test_an_undetermined_atom_is_reported_undetermined_and_names_its_authority`).
2. **The temporal operators have no reading in a general `A`.** Over `𝔹` they are the finite-trace
   semantics of `[@degiacomo-2013]`, owned by two published implementations — rtamt at the `observed`
   rung and BLACK `[@geatti-2019]` in the pack analysis. Over a residuated lattice they would be a
   many-valued temporal logic this package has not implemented and must not improvise, so a graded
   atom under a temporal operator is a **load error** and that refusal is a consequence of this gap
   rather than a policy (`test_a_graded_atom_under_a_temporal_operator_is_refused_at_load`).
3. **`⟦φ⟧(∅)` has no value**, though `A` supplies one (§2.6).

One clause of the temporal semantics this package does own, because `engines/temporal.py`
implements it:

```
⟦always(φ)⟧^tr(σ)  =  ⨅_{i < |σ|} ⟦φ⟧^rec(σᵢ)        for φ free of temporal operators
```

exact over a finite trace, and the whole of why a temporal duty can reach the proof rung
(`test_only_always_reaches_the_temporal_proof_rung`, `test_a_nested_temporal_operator_does_not_reduce`).

### 2.9 Fragments, and the four implementations

`rulelang.classify_fragment` assigns each `spec` the **narrowest** fragment, asked in this order,
which is the definition and not an optimisation:

```
counterfactual  ▸  undetermined  ▸  graded  ▸  temporal  ▸  record  ▸  logical
```

(`test_the_fragment_order_is_the_documented_order`). Four implementations of §2 ship, each at a
particular `M` and `A`, and each already had a differential test written as a hygiene check between
two components; named as what they are, those tests are this document's conformance evidence.

| Implementation | `M` | `A` | Conformance evidence |
|---|---|---|---|
| `rulelang.eval_expression` | `O(σ)`, one record | the Kleene chain `F < U < T` ([`theory/03-semantics.md`](theory/03-semantics.md) Definition 3.11) | it *is* the reference |
| `engines/proved._ast_to_z3` | `D(L)` | `𝔹` | `test_the_encoder_and_the_interpreter_answer_the_same` |
| `engines/observed.to_stl` + rtamt | `O(σ)` | `𝔹` via robustness sign — the margin the rung reports, not its verdict (§6.2) | `test_the_monitor_agrees_with_the_reference_reading` |
| `ltlf.to_ltlf` + BLACK `[@geatti-2019]` | a propositional abstraction of `O(σ)` | `𝔹` | `test_the_ltlf_backend_agrees_with_the_monitor` |

`manyvalued.degree_of` is not a fifth implementation but the reference interpreter at a different
`A` (§5.3). [`theory/03-semantics.md`](theory/03-semantics.md) Remark 3.1 reports four shapes on which the rtamt rendering and
this denotation part company; three are refused in the rendering and the fourth is a boundary
convention.

---

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

`report._evaluate_requirement` dispatches `undetermined` and `graded` **after** the capability gate
and **before** the engine ladder. That ordering is the whole of the guarantee that a system showing
nothing is still `unattainable` and never a low degree
(`test_a_system_that_can_show_nothing_is_unattainable_and_never_graded`,
`test_an_assessment_duty_reaches_no_engine_at_all`). No shipped duty uses either construct
(`test_no_shipped_pack_uses_either_open_texture_construct`).

---

## 6. Soundness, one engine at a time

Each statement below has the form *if this engine reports this verdict at this strength, then this
holds*. [`semantics.md`](semantics.md) §3 is the operational statement of each, with the full list
of what the engine reports *not evaluated* for; this section is the antecedent and the consequent.

Seven engines ship under `engines/`, and `test_the_formal_doc_states_one_soundness_paragraph_per_engine`
holds this section to that directory.

### 6.1 `record`

> **satisfied at `observed`:** for every record in the trace it was given, every signal named by a
> `present()` atom of `spec` carried a present value in the sense of §1.1. The domain is exactly
> those records (`test_the_record_engine_evaluates_its_spec`).
>
> **violated at `observed`:** at least one record carried no present value for at least one such
> signal, and the result names which signals and which record indices
> (`test_record_engine_violated_on_blank_field`).

The signals looked for are the property's, not the `requires` list's — different questions, and a
verdict answers only the second. *Presence is not correctness*: a reason field containing `"n/a"` is
present, and a duty wanting more than presence has to say so with `contains()`.

### 6.2 `observed`

> **satisfied at `observed`:** `⟦spec⟧^tr(σ)` is `T` over the trace it was given — the finite-trace
> clauses of [`theory/03-semantics.md`](theory/03-semantics.md) Definition 3.8, evaluated in the Kleene chain that document's Definition 3.11
> defines — where position *t* is the record at index *t* (`test_temporal_satisfied`).
>
> **violated at `observed`:** `⟦spec⟧` is `F` at at least one position, and the result names
> those indices and carries the offending records
> (`test_temporal_violated_returns_offending_segment`).

The verdict is that denotation and not the sign of the rtamt robustness signal, which is reported
beside it as a margin. `ρ > 0` implies satisfaction and `ρ < 0` implies violation, but `ρ = 0`
implies neither and `ρ` does not represent strictness — `ρ(x > c) = ρ(x ≥ c)` — so a Boolean
question answered from `ρ` is unsound at exactly the boundary
(`test_strict_comparison_boundary_table`). The monitor's time axis is the record index, so a bound
reads as a count of decisions and never as wall-clock time. A trace shorter than two records is
*not evaluated*: a discrete-time monitor cannot read a sampling period off one sample.

### 6.3 `probed`

> **satisfied at `probed`:** the engine replayed *N* planned inputs through the system's own
> `decide()`, and every input for which `decide()`, record conversion and property evaluation all
> completed satisfied `spec` under the reference interpreter. The budget records *N*, the seed, the
> strategy, per-field candidate counts and how many inputs errored
> (`test_no_counterexample_in_budget_is_probed_and_every_rendering_carries_the_budget`).
>
> **violated at `probed`:** one replayed input produced a decision failing `spec`, and that input,
> replayed a second time, failed again
> (`test_a_genuine_counterexample_is_reported_violated_with_the_input`).

Nothing about any input outside that plan, which is the entire distance between this rung and
`proved` (`test_probed_never_rounds_up_to_proved`). A search in which *any* planned input raised is
*not evaluated* rather than satisfied over the part that answered: the inputs a system raises on are
not a random sample of the space but the band its author put outside what it answers for
(`test_a_satisfaction_over_a_partly_unmeasurable_domain_is_not_a_satisfaction`).

### 6.4 `certificate`

> **satisfied at `probed`:** for **every** decision the system exposed an artefact for, bounded proof
> enumeration to that artefact's own `exact_depth` found **at least one** reason; every reason
> holding a private fact was switched off alone and the system's own engine re-run; every reason no
> such single deletion moved was put to the §3 search and came back not-deleted; so no reason was
> shown `deleted` in the sense of Definition 8, and the property held on that decision's record with
> the measured count in place (`test_the_certificate_verdict_carries_its_probe_budget`).
>
> **violated at `probed`:** on at least one certified decision the measured `deleted` count breached
> the property.

The antecedent says *at least one* because a zero from an empty enumeration is the **absence** of a
measurement and not a measurement of zero: with nothing enumerated, nothing is switched off, and a
property reading the deleted count comes out clean without exact inference having evaluated anything
(`test_a_decision_whose_reasons_were_never_enumerated_cannot_buy_satisfied`). A violation needs one
witness and a satisfaction needs complete evidence, so the two verdicts treat an unmeasured decision
differently.

**Every** private fact of a reason is switched off, not the first in `repr` order, because coverage
decided by a field's name gave two otherwise identical systems different probes. The budget
therefore counts **facts switched off**, not reasons.

A family whose reasons are **recounted** reports at `recounted` and never at `probed`
(`test_a_recounted_reason_set_cannot_be_reported_at_the_enumerated_rung`). One recounted decision
caps the run. What separates the rungs is the reference set: a probe over a recounted set can show
that the answer does not depend on a reason the system recounted; it can never show that the set is
all of them, which is what an enumeration establishes.

### 6.5 `proved`, and `proved` over a trace

> **satisfied at `proved`:** Z3 found the conjunction of the encoded rules, the declared constraints
> and the **negation** of `spec` unsatisfiable — and before that verdict was read, the premises alone
> were checked satisfiable and the encoding was checked against the reference interpreter on the
> model the solver produced for them (`test_property_holds_for_all_inputs_proved`).
>
> **violated at `proved`:** Z3 produced a counterexample input, and executing that input reproduced
> the violation — against the system's own `decide()` where one exists, otherwise against the
> declared logic, and the summary names which
> (`test_property_fails_with_verified_counterexample`).

The quantifier is over **all** valuations of the free inputs the declared constraints admit, at the
declared sorts. That is the strongest thing this tool says, and it rests on three assumptions worth
stating: it is a claim about the logic the system exposed and not about the deployed artifact, and
nothing here can check that the two are the same; `real` is exact rational arithmetic to the solver
and IEEE-754 float64 to the system, so a proof touching one carries `REAL_ARITHMETIC_LIMIT`; and a
declared sort is a description of the system and not a licence to narrow the inputs
(`test_declared_sorts_never_become_hidden_input_constraints`). `unsat` from premises no input can
satisfy proves every property and its negation alike, and is *not evaluated*
(`test_unsatisfiable_premises_are_not_a_proof`); so is an encoding that disagrees with the
interpreter on the solver's own witness
(`test_encoding_disagreeing_with_the_interpreter_is_not_a_proof`).

`engines/temporal.py` is the same statement about `f`, reached through the reduction of §2.8. The two
verdicts are **not** mirror images and the summary says so: `satisfied` is universal and covers every
trace the system can emit, while `violated` is existential — some admissible input breaches `f`, so
some trace the system admits breaches the duty, and a run whose log contains no such decision is
still reported violated. That asymmetry travels on the result as `TRACE_SEMANTICS`
(`test_a_temporal_violation_names_the_trace_it_is_and_is_not_about`).

### 6.6 `counterfactual`

> **satisfied at `proved`:** the duty was `counterfactually_invariant(o, p)`; the declaration named
> `p` an input it accepts and `o` a value it computes; the rules were encoded **twice** under two
> namespaces; every free input of the two copies was held equal except `p`; the pair was checked to
> admit at least one input at all; **each** copy was checked to agree with the reference interpreter
> on that witness; and Z3 found `o@0 ≠ o@1` unsatisfiable — so no pair of valuations the constraints
> admit, differing in `p` alone, produces two different values of `o`
> (`test_a_system_accepting_the_protected_variable_and_ignoring_it_is_satisfied`,
> `test_two_copies_of_one_rule_block_do_not_collide`).
>
> **satisfied at `probed`:** the same, over the pairs the budget named and nothing outside them
> (`test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach`).

Three `unsat`s must never be read as this verdict, and each is refused before the negation is read.
A declaration that **pins** `p`, or rules that **assign** `p` while `computes` omits it — checked on
the encoding, because that route is invisible to the declaration — mean *no pair exists* rather than
*no pair disagrees* (`test_constraints_pinning_the_protected_variable_are_not_a_proof`,
`test_rules_assigning_the_protected_variable_are_not_a_proof`). And a system with **no notion** of
`p` is `unattainable`, never `satisfied` (§2.7): without the `computes` declaration an unaware system
and a provably-fair one encode identically and both come back `unsat`
(`test_the_two_cases_reach_different_verdicts_on_the_same_rules`).

A `p` the declaration does not type as an **integer** is *not evaluated* at both rungs, naming the
variable and its sort: a prohibited basis is a category, and over a dense sort the replay search
samples fractions between the categories while the proof rung's witness may be a pair the system can
never be given (`test_a_protected_variable_not_typed_as_an_integer_is_not_evaluated`).

Neither rung ever takes `p`'s value from the trace
(`test_paired_replay_takes_no_protected_value_from_the_trace`). `TREATMENT_LIMIT` rides on every
result: this is a property of a *pair* and says nothing about a proxy or about effects across a
population. Group-statistical fairness is unreachable on this evidence model.

**The two rungs do not range over the same object**, so a disagreement between them is evidence in
its own right rather than a contradiction to be resolved by trusting the higher one. Write
`D = { x : x ⊨ constraints }` for the declared input space and
`P = { (x, x′) ∈ D × D : x and x′ agree off p }` for the pairs the proof rung quantifies over; write
`R` for the pairs the replay rung actually ran, each built from a logged decision by setting `p` to
two values enumerated from `constraints`. The proof rung decides `∀ (x, x′) ∈ P . o_L(x) = o_L(x′)`
over the *declared rules*; the replay rung decides `∀ (y, y′) ∈ R . decide_S(y) = decide_S(y′)` over
the *implementation*.

> **Claim.** If (a) `R ⊆ P` and (b) `decide_S` agrees with `o_L` on `D`, then
> `probed = violated` implies `proved = violated`.
>
> **Contrapositive.** `proved = satisfied` together with `probed = violated` implies `¬(a)` or
> `¬(b)`.

Neither hypothesis is free here. (a) fails whenever a logged decision lies outside `D`: `p`'s two
values are enumerated from `constraints`, but every other field of a replayed case comes from the
trace and no rung tests it against them. (b) fails when the system's `decide()` does not implement
the `logic()` it declared — which the proof rung cannot see, because a `satisfied` verdict there is
an `unsat` and an `unsat` replays nothing.

So the lower rung is run whenever the higher one reached a verdict, and a disagreement is reported
as the **disjunct it eliminates** rather than as the bare fact that two rungs differ
(`engines.counterfactual.cross_rung_signal`). Direction 1 — `proved = violated` with
`probed = satisfied` — is the relation holding rather than a defect in either rung, and what it
names is the log: it does not exercise what the rules permit
(`test_a_proof_the_log_does_not_reach_names_the_log`). Direction 2 discharges (a) first, which is
decidable by evaluating `constraints` on the replayed pair: a pair outside `D` is reported as such
and nothing is said about the declaration
(`test_a_replay_outside_the_declared_input_space_is_named_before_the_declaration_is`), a pair inside
it leaves `¬(b)` as the residual and the finding is that the declaration is unfaithful to the
implementation (`test_a_declaration_its_own_decide_does_not_implement_is_the_residual`), and a
record leaving a declared constraint unsettled eliminates neither
(`test_a_record_that_leaves_a_declared_constraint_unsettled_eliminates_neither`). The signal moves
no verdict, no strength and no witness
(`test_the_signal_moves_no_verdict_no_strength_and_no_witness`).

### 6.7 The premise every artefact rung declares

The reason-deletion probe is **one-directional** — it switches a fact off, never on — so `deleted`
means *the answer did not depend on this reason under this interpretation*. On an engine that is not
monotone in its inputs, a lawfully retracted reason is indistinguishable from a dropped one. That
premise is **declared rather than assumed** (§1.3), and it is the same premise §3.3 needs.

`engines/certificate.py` asks the declaration before it certifies and asks the measurement again
afterwards, and reports **not evaluated** — never violated, never satisfied, and never downgraded to
the presence check sharing the clause — for an artefact declaring non-monotone, declaring nothing, or
declaring monotone where a deletion **raised** the system's answer
(`test_an_artefact_declaring_non_monotone_inference_is_not_evaluated_and_names_why`,
`test_an_artefact_that_declares_nothing_is_not_evaluated_rather_than_assumed_monotone`,
`test_a_declaration_the_probe_contradicts_is_refused_rather_than_trusted`). One refused artefact
refuses the run (`test_the_refusal_survives_a_whole_conformance_run_and_reaches_no_weaker_duty`).

The sign of the drop is kept, so the `non_monotone` flag can **refute** a false declaration and can
never confirm a true one: a defeater holding no fact of any enumerated reason is never switched off
at all (`test_the_absence_of_the_fingerprint_is_not_evidence_of_monotonicity`).

It is *not evaluated* and deliberately not *unattainable*: the gap is in this tool, and telling a
creditor to stop having lawful policy exceptions is the wrong instruction.

### 6.8 Which engine answers a duty

Which engine a requirement reaches is decided by the fragment **and** by what the system exposes,
not by the fragment alone (`report._engine_ladder`). The ladder collects every engine the pair
allows and takes the strongest evidence produced: `logic()` gets Z3, `decide()` gets the replay
search, and a trace gets the record engine for a presence conjunction and the observed engine for
every other fragment, `logical` included — a state property is a property of one decision record, so
a trace of them is evidence about it. A duty on the `counterfactual` fragment gets the two rungs of
§6.6 and **no trace rung, ever**.

An engine may be **installed rather than vendored**, through the `reasonsmith.engines` entry-point
group. A discovered engine joins the ladder at the rung its `max_strength` declares and cannot report
above it; one that raises, times out, returns the wrong type or will not import reports *not
evaluated*; one taking a built-in's name is refused rather than namespaced. Nothing here audits a
plug-in, so its declared ceiling is the only bound on what it claims.

### 6.9 One rule outside every rung

An implication whose antecedent **nothing in an engine's evidence domain satisfies** is *not
evaluated*, `strength=None`, naming the antecedent and the domain.

This is a fact about the **formula** and not about any rung, which is why seven local domain guards
never found it and why the fix was not an eighth: `rulelang.implication_antecedent` names the
subtree — stripping a top-level `always`, never an `eventually` — and
`report.not_evaluated_for_unreachable_trigger` words the refusal once against the result model. Each
rung then answers it with what it already holds:

| Rung | The domain the antecedent is asked over |
|---|---|
| `proved` | the valuations the premises admit — the premise check one quantifier deeper |
| `temporal` | inherited through the reduction of §2.8 |
| `observed` | the positions of the supplied trace |
| `probed` | the replays that reached it |
| `certificate` | the certified decisions that reached it |

`probed` is in that list because the ladder falls to it, so guarding the proof rung alone would only
move a vacuous `satisfied` down a rung; `certificate` is in it for the opposite reason, because the
ladder gives one shipped duty that rung and no other, so nothing beneath it could catch the same
empty claim. Every rung asks it on the **satisfied** path alone: a violation names a witness whose
antecedent fired (`test_a_creditor_who_took_the_disclosure_branch_is_not_violated`,
`test_an_antecedent_no_admissible_input_reaches_is_not_evaluated_at_proved`).

**What it costs is stated rather than quietly undone.** A creditor lawfully on the 12 CFR
1002.9(a)(2)(ii) disclosure branch is now neither accused nor cleared, because *not applicable per
decision* is the honest verdict and the result model has no per-record applicability.

### 6.10 The same question asked of a pack

`analysis.py` asks four questions about the **duties** rather than about a system's evidence: joint
satisfiability with an unsatisfiable core, entailment and equivalence between requirements, vacuity,
and — where a system exposes `logic()` — a mutation score per duty. It has no encoding of its own;
`_ast_to_z3` and `_Scope` are the proof rung's.

**Vacuity** is the question of `[@kupferman-2003]` in the subformula-replacement formulation of
`[@beer-2001]`, restricted to the fragments this repository ships:

> A requirement is **vacuously discharged** on a given evidence domain when some subformula of its
> `spec` can be replaced by *any* well-formed formula of the same fragment without changing the
> verdict.

The check is the two-point one and is exact rather than heuristic here: the target is one AST
*occurrence*, so the property is monotone or antitone in it, and a verdict equal at both constants is
equal throughout. Only the *satisfied* side and only the outermost replaceable occurrence is
reported, because a looser rule prints false alarms and an analysis nobody reads is worth nothing.
This definition **must keep coinciding** with §6.9 on the case that rule already handles
(`test_vacuity_coincides_with_the_unreachable_trigger_rule`); a disagreement is a finding to report,
never a definition to widen on either side.

The **temporal** fragment is decided by `ltlf.py`, which is a syntax mapping and an emptiness
question and nothing else: BLACK `[@geatti-2019]` is asked whether the formula is satisfiable over
a finite trace, entailment is `left & !right` unsatisfiable, and equivalence is both ways. The reading
is propositional — every comparison of magnitudes becomes one opaque atom — so satisfiability is
reported **only in the affirmative** and `LTLF_ABSTRACTION_LIMIT` rides on every answer. Every
question is asked over a non-empty trace, which is §2.6's refusal of `⨅ ∅` restated in the object
logic — a clause inherited from BLACK's own finite-trace semantics rather than conjoined as a guard
formula. Past
operators are LTLf-inexpressible and are skipped by name. **No LTL₃ verdict is computed**: the
installed procedure answers a satisfiability question and exposes no monitor construction, so the
distinction `[@bauer-2011]` draws between *satisfied on this prefix* and *satisfied on every
extension* is reported unavailable rather than synthesised. That is a different third value from the
`U` of the Kleene chain the reference interpreter evaluates in — ignorance about a *record*, not
truncation of a *trace* — and [`theory/03-semantics.md`](theory/03-semantics.md) Definition 3.11 states why the two must not be read
as one. BLACK was priced
against `flloat` `[@flloat]`, the previous backend, which is pure Python on PyPI but has no past
operators and an exponential powerset DFA construction; BLACK publishes no wheel, so the extra is a
binary a user installs by hand and its absence is reported rather than worked around.

The framing in which any of these questions is worth asking of a legal text is isomorphism
`[@benchcapon-1992]`: a legal knowledge base should stay structurally faithful to its source, one
rule per provision, so that a change in the law is a local change in the model and a lawyer can
check one against the other. That is what `verbatim_text` and `drift.py` are for, and it is why
`src/reasonsmith/table7.toml` is a verbatim transcription of Table 7 of `[@stan-2026]` rather than an
improvement on it (`test_pack_matches_table7_transcription`).

### 6.11 A trace, pinned into a satisfiability question

Satisfiability is the only question the installed procedure is ever asked. `ltlf.accepts(φ, σ)` —
whether **one concrete trace** satisfies a formula — is therefore not asked of it directly: it is
re-encoded as satisfiability over a formula built from σ that admits σ and no other trace. That
re-encoding is the whole of the argument that an `accepts` answer is an answer about the trace it
was handed, and it is the one proposition the finite-trace decision procedure rests on, which is
why it is stated here rather than left in the module.

The move itself is the bounded-model-checking one of `[@biere-1999]`: a bounded run is written as a
propositional constraint and given to a satisfiability procedure, rather than the property being
walked over the run by a monitor. What is bounded here is not a search depth but the trace, which
was already finite.

**Setting.** LTLf over finite non-empty traces `σ = σ₀ … σ_{n−1}`, `n ≥ 1`, with `σᵢ ⊆ AP` — the
semantics of `[@degiacomo-2013]`, which BLACK implements in the finite-trace mode `[@geatti-2021]`
adds to the tableau of `[@geatti-2019]`. `X` is the **strong** next, so `σ, i ⊨ X φ` requires
`i + 1 < n`, and `Last := ¬X⊤` holds at exactly one position, `n − 1`. `AP` is not a global
vocabulary: `accepts` derives it per question, as the atoms occurring in the rendered formula
together with every key any position of the given trace carries, and reads a key a position omits
as false. This is the propositional abstraction of §6.10 — every comparison of magnitudes is one
opaque letter — so a *position* here is a decision record of §1.1 seen through that abstraction.

**Definition (complete literal).** For a position `σᵢ ⊆ AP`:

```
λᵢ  :=  ⋀_{a ∈ σᵢ} a  ∧  ⋀_{a ∈ AP \ σᵢ} ¬a
```

The conjunction ranges over **all** of `AP`, and the completeness is load-bearing rather than tidy.
A `λᵢ` naming only the atoms a valuation happens to carry leaves every other atom free at that
position; the conjunction below is then satisfied by traces other than σ, and `accepts` answers
about a set of traces while reporting an answer about the one it was given. That is a property of
the formula the code builds and is decided before any solver reads it, so it is checked without one
(`test_the_pinning_formula_states_every_atom_at_every_position`).

**Definition (characteristic formula).**

```
pin(σ)  :=  ⋀_{i=0}^{n−1} Xⁱ λᵢ  ∧  X^{n−1} Last
```

> **Proposition.** `L(pin(σ)) = {σ}` over the alphabet `2^AP`.

*Proof.* (⊇) Position `i` exists in σ for every `i < n` and `λᵢ` holds there by construction, so
`σ ⊨ Xⁱ λᵢ`; position `n − 1` exists and has no successor, so `σ ⊨ X^{n−1} Last`. (⊆) Let
`τ ⊨ pin(σ)` with `|τ| = m`. `X^{n−1} Last` requires position `n − 1` to exist, so `m ≥ n`; `Last`
there requires that position to have no successor, so `m = n`. Each `Xⁱ λᵢ` then forces `τᵢ = σᵢ`,
because `λᵢ` decides every atom of `AP` at that position. Hence `τ = σ`. ∎

> **Corollary.** For `σ ≠ ε`, `accepts(φ, σ) ⟺ SAT(φ ∧ pin(σ))`.

> **Corollary.** `entails(l, r) ⟺ ¬SAT(l ∧ ¬r)`, over the same non-empty finite traces; the
> equivalence `analysis.Relation` reports is that asked in both directions.

Neither corollary is a claim about the *pack* in the negative direction: the abstraction is sound
for the entailments it reports and incomplete for the ones it does not, which is why §6.10 reports
satisfiability only in the affirmative and `LTLF_ABSTRACTION_LIMIT` rides on every answer.

**The non-emptiness the proposition assumes is the semantics', not a guard's.** The previous backend
conjoined a `NON_EMPTY` formula and 0.8.0 deleted it; nothing replaced it and nothing had to,
because BLACK's finite-trace mode interprets a formula over traces of length at least one, so the
empty trace is not among the traces quantified over at all
(`test_black_non_empty_semantics_g_false_is_unsat`, which asks the procedure whether `G(⊥)` is
satisfiable and requires the answer to be no; and
`test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable` at the mapping's
own surface). The assumption is load-bearing in exactly one shape, and it is a reachable one rather
than a corner: where `AP = ∅` every `λᵢ` is the empty conjunction and `pin(σ)` reduces to
`X^{n−1} Last`, which at `n = 1` is `¬X⊤` — a formula the empty trace satisfies under any semantics
admitting it. `accepts` builds that shape whenever the rendered formula carries no atom. The trace
σ = ε is refused one step earlier still, without the procedure being asked anything
(`test_an_empty_trace_is_refused_before_the_solver_is_asked`), which is §2.6's `⟦φ⟧^tr(ε) = ↑`
restated at this boundary.

**What the encoding costs, and what `ATOM_BUDGET` therefore bounds.** `pin(σ)` introduces **no new
atom**: `AP` is exactly the atoms of the rendered formula together with the trace's own keys, so a
question's distinct-atom count — which is what `ATOM_BUDGET` counts and `_decide` refuses on — does
not grow with `n` at all. What grows is the formula: `n·|AP|` literal occurrences, and a rendered
string quadratic in `n` because `Xⁱ` is written as nested prefixes. Neither is exponential in
`|AP|`, which the replaced powerset-DFA construction was and which the flloat-era budget of six was
set around. The budget remains an **unmeasured** bound and is stated as one: LTLf satisfiability is
PSPACE-complete `[@degiacomo-2013]` and the tableau is worst-case exponential in the formula, so no
atom count is a runtime guarantee, and it is the only bound `_decide` has because there is no wall
clock anywhere in this package (`test_a_question_over_the_atom_budget_is_refused_by_name`). It
bounds the questions that route through `_decide` — `satisfiable` and `entails`, which are the
questions `analysis.py` asks — and not `accepts`, which calls the procedure directly and which no
analysis path reaches.

The proposition is pinned behaviourally as well as structurally, because a proof about a formula the
code does not build is worth nothing: `test_pin_characteristic_formula_accepts_sigma_and_rejects_neighbors`
constructs `pin(σ)`, asks the procedure for σ itself, for **every** trace one Hamming step from σ —
one flipped atom at one position, `n·|AP|` of them — and for both length neighbours `n − 1` and
`n + 1`, and requires σ to be the only acceptance. Like every question for the solver it is skipped
where the optional extra is absent, so on a machine without the binary the encoding is held by the
structural check alone.

---

## Bibliography

The bibliography registry is maintained in [`theory/bibliography.md`](theory/bibliography.md); citations in this document retain the repository-wide citation-key convention.
