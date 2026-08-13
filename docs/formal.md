# The mathematics of reasonsmith — migration stub

The gathered mathematics is now organized as numbered theory chapters. Read:

- [00-notation](theory/00-notation.md) for the global symbol table;
- [01-models](theory/01-models.md), [02-syntax](theory/02-syntax.md), and
  [03-semantics](theory/03-semantics.md) for the objects, grammar, and denotation;
- [04-decision-problems](theory/04-decision-problems.md) for the six questions this tool asks;
- [05-decision-procedures](theory/05-decision-procedures.md) for their procedures and soundness;
- [06-formalisation](theory/06-formalisation.md) and [07-explanation](theory/07-explanation.md) for
  refinement and explanation mathematics; and
- [08-evidence](theory/08-evidence.md), forthcoming, for the remaining evidence mathematics;
- [bibliography](theory/bibliography.md) for the repository-wide citation registry.

Chapters 04–05 replace the migrated language and engine material formerly in this file. This file
remains as a redirect while the evidence and graded-reading material below awaits its migration.

---

## Pending migration: evidence and graded readings

## 3. Reasons

The explanation formalism formerly kept in this section now lives in
[`theory/07-explanation.md`](theory/07-explanation.md), Definitions 7.1–7.19 and their
lemmas, theorem, corollaries, remarks, and propositions. That chapter is the authoritative
location for the deletion lattice, AXp/CXp duality, certificates, value gap, budget, and claimed
semantics. This stub keeps the evidence and graded-reading material below for the next migration.

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
(theory/07-explanation.md, Definition 7.1), and `observed ∉ rungs(artifact)` because no trace holds the artefact. `assessment` admits no
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