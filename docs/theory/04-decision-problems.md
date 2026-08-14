# 4 — Decision problems

This chapter names the questions the implementation actually asks. Each problem is stated as
**INPUT** and **QUESTION**; the procedure and its limits are part of the statement. The denotation
and structures are Definitions 3.1–3.11, while the objects `O(σ)`, `D(L)`, `L`, `P`, and `R` are
Definitions 1.1–1.6.

## 4.1 Log model checking

**INPUT.** An observed log structure $O(\sigma)$ and a well-formed formula $\varphi$.

**QUESTION.** Does $\sigma \models \varphi$?

**OBJECT.** The one trace supplied by `sut.decisions()`, not an inferred population of traces.

**PROCEDURE.** The reference interpreter evaluates the formula on the finite trace, using the
Kleene layer of Definition 3.11 and the temporal clauses of Definition 3.8. The record engine is
the specialised presence check; the observed engine handles the other trace properties.

**COMPLETENESS.** Complete for the formula and the supplied finite log wherever the denotation is
defined; an answer is a claim about that log only.

**KNOWN INCOMPLETENESS.** An empty log is undefined (Definition 3.10), missing or ill-typed values
can leave a formula undefined, and the trace is not representative, complete, or unfiltered. The
counterfactual atom is refused on $O(\sigma)$ (Definition 3.9), and temporal monitor renderings
have the divergences recorded in Remark 3.1 and Remark 3.3.

## 4.2 Validity over a constrained input space

**INPUT.** A declaration $L$ and a formula $\varphi$ in the state fragment, with the admissible
execution structure $D(L)$.

**QUESTION.** Does every admissible execution satisfy $\varphi$?

**OBJECT.** The constrained input space described by `L`: the rules, declared constraints, and
declared sorts, not merely the records in an observed log.

**PROCEDURE.** The proved engine encodes the rules and constraints in Z3, checks that the premises
are satisfiable, and checks `premises ∧ ¬spec` for unsatisfiability. It verifies the solver witness
against the reference interpreter before accepting a proof. `always(state property)` reaches the
same question through the temporal reduction in Definition 3.8.

**COMPLETENESS.** For the supported encoding and declared domain, an accepted unsatisfiability
result is a universal result over that domain; a reproduced witness establishes a counterexample.

**KNOWN INCOMPLETENESS.** This is a statement about the exposed declaration, not necessarily the
deployed implementation. Unsatisfiable premises, an encoding disagreement, unsupported fragments,
undeclared directions, and real-arithmetic differences are refused or not evaluated. Replay is not
this problem: it ranges over only a bounded subset and cannot establish validity.

## 4.3 Bounded refutation

**INPUT.** A replayable `decide()` procedure, a formula $\varphi$, and a finite search budget.

**QUESTION.** Is there a counterexample within the budget?

**OBJECT.** The planned inputs and their replayed decision records, a bounded subset of the cases
the implementation might answer.

**PROCEDURE.** The probed engine generates candidates, calls `decide()`, converts the returned record,
and evaluates $\varphi$ with the reference interpreter. A failing input is replayed to confirm it.
The budget records its cap, seed, strategy, candidate counts, and errors.

**COMPLETENESS.** A confirmed counterexample is sufficient for a violated result at `probed`.

**KNOWN INCOMPLETENESS.** Finding no counterexample refutes nothing outside the plan and never
establishes the universal question. Any planned input that errors makes the result not evaluated;
`probed` cannot round up to `proved` (Definition 8.1 and the strength chain).

## 4.4 2-safety

**INPUT.** A declaration $L$, an outcome $o$, and a protected input $p$.

**QUESTION.** Do all admissible pairs agreeing off $p$ agree on $o$?

**OBJECT.** The pair set $P$ of executions admitted by $D(L)$ that agree on every input except $p$;
the replay set $R$ is the bounded implementation-side analogue.

**PROCEDURE.** The counterfactual proved engine self-composes the rule encoding twice, holds all free
inputs equal except $p$, and checks that unequal outcomes are unsatisfiable. The probed engine
enumerates paired replays. The protected value comes from declaration constraints, never from a
trace.

**COMPLETENESS.** The proved procedure is universal over the declared pair space when its premises,
sorts, directions, and interpreter checks are accepted. A replay witness is a valid refutation of
the replayed implementation.

**KNOWN INCOMPLETENESS.** No trace rung can answer this property; unawareness is `unattainable`, not
invariance. The proof concerns declared rules while replay concerns the implementation, and the
sets need not coincide: the documented relation is $R \subseteq P$ only under its stated hypotheses.
This is not group-statistical fairness, proxy analysis, or a population property.

## 4.5 Abductive explanation

**INPUT.** An inference artefact, a tolerance, and its facts, reasons, deletion operation, and
engine answer.

**QUESTION.** Which reasons are subset-minimally sufficient, and which were unused?

**OBJECT.** The deletion lattice $\mathbb{L}(\beta)$ of interpretations obtained by switching
facts off, and the artefact's reason family $\mathcal{R}$. The exact definitions of sufficient,
AXp, CXp, live, deleted, and undetermined are defined in [`07-explanation.md`](07-explanation.md).

**PROCEDURE.** `explanations.contrastive_sets` uses MARCO seed/shrink/grow, Z3 as a subset-lattice
oracle, and the system engine as the membership oracle. Certificates then lift fact-level results
to reasons under the declared monotonicity premise.

**COMPLETENESS.** A completed enumeration supports the universal `deleted` claim and enumerated
minimal sets; one contrastive witness is enough for `live`.

**KNOWN INCOMPLETENESS.** The search is budgeted: incomplete enumeration yields `undetermined`, not
more deleted reasons. It probes only the deletion lattice and therefore does not answer questions
about arbitrary interpretations. This is a different formalism—weighted model counting and
abductive explanation—and its full definitions are defined in [`07-explanation.md`](07-explanation.md).

## 4.6 Requirement-level questions

**INPUT.** A requirement pack, rather than a system's evidence.

**QUESTION.** Are the requirements jointly satisfiable; what is an unsatisfiable core; does one
requirement entail another; are two requirements equivalent; and which subformulas are vacuous?

**OBJECT.** The set of requirement formulas and their shared pack-level atom abstraction. Mutation
coverage additionally quantifies over mutants of an exposed `logic()` rule block.

**PROCEDURE.** `analysis.py` reuses the proved Z3 encoding and `_PackScope` for joint satisfiability,
cores, entailment, equivalence, and vacuity. For temporal requirements, `ltlf.py` asks BLACK finite-
trace satisfiability and entailment where installed; mutation analysis reruns `check_conformance`
against generated mutants.

**COMPLETENESS.** A reported core, entailment, equivalence, or vacuity finding is witnessed by the
corresponding decision procedure and abstraction. The vacuity two-point check is exact for its
replaceable monotone or antitone occurrence.

**KNOWN INCOMPLETENESS.** Counterfactual, graded, and unsupported temporal shapes are skipped by
name. Pack-level atoms are uninterpreted apart from `contains` implying `present`, so unreported
relations are not disproved. BLACK reports only affirmative satisfiability; mutation scores cover
only generated mutants and are not coverage claims. The optional BLACK procedure may be absent.
