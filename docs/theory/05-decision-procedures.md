# 5 — Decision procedures

There is **no proof system here**. The package has four implementations of one denotation and two
external decision procedures. Soundness is therefore a proposition about each procedure's reported
answer under its stated assumptions, not a theorem of a calculus. The denotation is Definition 3.1;
the structures $O(\sigma)$ and $D(L)$ are Definitions 1.5–1.6.

## 5.1 Reference interpreter

`rulelang.eval_expression` and `rulelang.eval_temporal_trace` are the reference implementation of
the denotation. The `record` engine specialises the presence conjunction; the `observed` engine
uses the interpreter for the other trace fragments, including `logical`. The `counterfactual` atom
is refused by the interpreter on an observation model, as Definition 3.9 requires.

> **Proposition 5.1 (reference interpretation).** Whenever the interpreter returns a defined value
> for a formula on the supplied record or finite trace, that value is the denotation specified by
> Definitions 3.5–3.11 for that structure and the Kleene value layer of Definition 3.11.

This procedure is complete only for the supplied evidence and the defined fragment. An empty trace,
missing or ill-typed values, and the relational atom on $O(\sigma)$ remain undefined. Its conformance
status is by definition the reference, rather than a differential comparison. The record and observed
behaviour are held by `test_temporal_satisfied`, `test_temporal_violated_returns_offending_segment`,
and `test_a_present_but_empty_signal_does_not_count_as_evidence`.

## 5.2 Z3 over $D(L)$

`engines/proved.py` is a decision procedure, not a calculus. It encodes the declared constraints and
rules, checks the premises, and checks `premises ∧ ¬spec` for unsatisfiability. A solver witness is
run through the reference interpreter before it is accepted. The `proved` engine reaches this
procedure; `engines/temporal.py` reaches it only after reducing `always(state property)`.

> **Proposition 5.2 (proof procedure).** If the premises are satisfiable, the encoding agrees with
> the reference interpreter on its checked witness, and Z3 reports `premises ∧ ¬spec` unsatisfiable,
> then every valuation admitted by the declared constraints satisfies `spec` in the encoded
> declaration model $D(L)$. If Z3 supplies a witness and replay reproduces the violation, that
> witness refutes the universal claim.

The proposition is about the exposed declaration, not automatically the deployed implementation.
It is incomplete where the encoding is unsupported, premises are unsatisfiable, directions are
undeclared, the encoding disagrees with the interpreter, or exact solver reals meet system float64.
The differential evidence is `test_the_encoder_and_the_interpreter_answer_the_same` (and its numeric
counterpart `test_the_encoder_and_the_interpreter_compute_the_same_number`).

## 5.3 rtamt over $O(\sigma)$

`engines/observed.to_stl` renders the supported temporal formula for rtamt over the supplied
observation structure. rtamt's robustness is a reported margin, not a verdict: the verdict comes
from the reference finite-trace denotation. A zero margin decides neither side, and strict and
non-strict comparisons can have the same margin.

> **Proposition 5.3 (monitor rendering).** For every formula shape accepted by the renderer and not
> on its documented divergence list, the Boolean result obtained from the rendered finite trace
> agrees with the reference interpreter's finite-trace result; the reported robustness is only an
> additional margin.

This is incomplete for the deliberately refused or divergent shapes recorded in Definition 3.8
and Remark 3.3, for traces too short to supply a sampling period, and wherever the renderer cannot
represent a construct. The conformance evidence is `test_the_monitor_agrees_with_the_reference_reading`
and `test_strict_comparison_boundary_table`. The runtime `next` and `prev` boundary readings remain
those of Remark 3.1.

## 5.4 BLACK over the propositional abstraction

`ltlf.py` invokes BLACK `[@geatti-2021]` only for pack analysis, not as a conformance rung. It maps a finite temporal
formula to a propositional abstraction: each magnitude comparison is an opaque atom, and the
procedure is asked satisfiability or entailment over non-empty finite traces. It trusts only an
affirmative satisfiability answer. Its absence, refusal, or a non-affirmative solver response is not
silently changed into a negative finding.

> **Proposition 5.4 (affirmative abstraction).** If BLACK affirms satisfiability of the rendered
> propositional abstraction, then the abstraction has a non-empty finite-trace model under the
> procedure's finite-trace semantics. If it affirms an entailment query, the corresponding
> unsatisfiability question has the stated meaning over that same abstraction.

The abstraction is incomplete for the original magnitudes and for questions it does not affirm;
relations skipped by the mapping are not answered. The optional binary may be absent. Runtime
`next` is weak at the final position, whereas BLACK's rendered `X` is strong, so that known
boundary divergence is documented in Definition 3.8's Remark 3.1 and is not resolved here. The
procedure's evidence includes `test_the_ltlf_backend_agrees_with_the_monitor`,
`test_black_non_empty_semantics_g_false_is_unsat`, and
`test_a_question_over_the_atom_budget_is_refused_by_name`.

## 5.5 MARCO for abductive explanation

`explanations.contrastive_sets` runs MARCO's seed/shrink/grow loop. Z3 is the oracle over the subset
lattice, and the system's engine is the membership oracle. This is the deletion-lattice formalism,
not a proof rung; its definitions and certificate consequences are retained in the theory/07-explanation.md
of `theory/07-explanation.md`.

> **Proposition 5.5 (MARCO enumeration).** Under the declared monotonicity premise, every contrastive
> set reported by the completed seed/shrink/grow search is minimal, and a completed enumeration
> supports the universal `deleted` conclusion; one contrastive witness suffices for the existential
> `live` conclusion.

The procedure is incomplete while budgeted enumeration has not terminated: it reports
`undetermined`, never additional `deleted` reasons. It probes only interpretations in the deletion
lattice and cannot establish claims about arbitrary perturbations. The certificate differential
warrant is `test_the_certificate_verdict_carries_its_probe_budget`; the joint-necessity boundary is
`test_two_jointly_necessary_reasons_are_no_longer_reported_deleted`.

## 5.6 The LTLf `pin(σ)` construction

The LTLf procedure asks BLACK satisfiability `[@biere-1999]` rather than directly asking whether one concrete trace
satisfies a formula. `ltlf.accepts(φ, σ)` constructs a characteristic formula `pin(σ)` that admits
only the supplied non-empty finite trace, then asks satisfiability of `φ ∧ pin(σ)`. Every atom at
every position is stated, including atoms absent from a record; the final-position formula makes the
length exact.

> **Proposition 5.6 (characteristic trace).** Over the procedure's non-empty finite-trace semantics,
> $L(pin(\sigma)) = \{\sigma\}$.

Consequently, for non-empty $\sigma$, `accepts(φ, σ)` agrees with satisfiability of
`φ ∧ pin(σ)`, and entailment is reduced to unsatisfiability of `left ∧ ¬right` over the same
traces. The construction is incomplete as a procedure for the full language: it uses the
propositional abstraction, past operators are skipped, the atom budget can refuse a question, and
runtime weak `next` differs from BLACK's strong `X` at the boundary. The structural and behavioural
conformance evidence is `test_the_pinning_formula_states_every_atom_at_every_position` and
`test_pin_characteristic_formula_accepts_sigma_and_rejects_neighbors`.

The proposition concerns the formula built by `ltlf.py`, not a monitor. BLACK uses non-empty traces;
the empty trace is refused before the solver is asked, so the construction does not restore the
empty-trace top value excluded by Definition 3.10.

The optional finite-trace analysis keeps the three-valued runtime-verification distinction unavailable rather than synthesising it `[@bauer-2011]`.
