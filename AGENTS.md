# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.

## The authority

`src/reasonsmith/table7.toml` is a verbatim transcription of Table 7 of *Symbols and Neurons: A
Review of Symbolic XAI in Deep Learning* (Stan, Sciavicco & Napoletano, JAIR 2026, p. 36:22), whose
first author owns this repository. The conformance checks come from Table 19 of the same paper. The
paper is the authority: where a design and the table disagree, the table wins, or the disagreement
is reported as a finding. Do not improve, extend or modernise the wording — the transcription's
value is that a lawyer can check it against the print.

## Dependency

nesyarena supplies the ground-program IR, bounded proof enumeration, the exact WMC oracle and the
adapter protocol. Depend on it; do not reimplement any of those. `pyproject.toml` pins
`nesyarena==0.1.0` from PyPI — `pip install reasonsmith` is the user install, and
`pip install -e ".[dev]"` in a venv is the contributor install, the one CI
(`.github/workflows/ci.yml`) runs. Never point it at a sibling checkout, tag, or a
branch: the measured numbers must stay reconstructible. `torch` is
deliberately not a declared dependency of *this* package but
has been installed and measured in a separate environment — see [RESULTS.md](RESULTS.md),
"What Changed From Prior Torch Caveats" and "Build and Reproduction Commands", for the
exact commands and counts, and do not re-litigate that caveat from stale memory of "torch was never
installed here". `tests/conftest.py` puts `src` on the path so this package itself needs no
install, but nesyarena does. `pip install`ing nesyarena only gets the built package, not its
`tests/`/`experiments/` directories — to run nesyarena's *own* suite (as opposed to depending on
it), clone `github.com/eduardstan/nesyarena` separately and check out
`22b539bad6c3510fe457aa751141c5c4aa1483ea`, the commit 0.1.0 was built from (RESULTS.md, "PyPI
Release Note", records how that was verified; the repo publishes no tag).

## Two rules that shaped the code

- No emitted record, certificate or measurement may present itself as complete when it is not, and
  every one carries its own limits. See the module docstrings in `evidence.py` and `certificate.py`
  for why each check exists before changing one.
- No check asserts branding or presentation. Limits tests pin semantic boundary clauses, not full
  prose.

What a `deleted` reason **is** is written down in `docs/theory/07-explanation.md` — read it before
touching `certificate.py` or `explanations.py`. The probe used to switch each reason off *alone*,
which answers a question about single facts and reports about reasons: two reasons jointly necessary
and individually removable each leave the engine's answer where it was, so both were reported
`deleted` and the tool accused a system of omitting reasons its inference demonstrably used. The
definition is Ignatiev/Narodytska/Marques-Silva's abductive explanation and its contrastive dual,
specialised to the deletions `artifacts.InferenceArtifact` admits, resting on Reiter's minimal-
hitting-set duality; published sources only, registered in `docs/theory/bibliography.md`.
`explanations.contrastive_sets` measures it with the MARCO seed/shrink/grow loop, Z3 as the oracle over the subset lattice and the system's
own engine as the membership oracle. Four things must not be undone: the monotonicity declaration is
what every lemma rests on, so this is one premise with the artefact protocol and not two; `live` is
existential and one contrastive set establishes it while `deleted` is universal and needs the
enumeration to have **finished**, so a partial search reports `undetermined` and there is no budget
at which this instrument names more missing reasons than a complete search; the pass only ever moves
a reason *out* of `deleted` and never promotes an `unseparable` one into it, which `docs/theory/07-explanation.md` §7.4 states as a decision rather than an omission; and the search's probes and whether it terminated travel in
`details[PROBE_BUDGET_KEY]` exactly as `PROBE_BUDGET_FIELDS` forces, because how far it got is the
bound on every `deleted`. `Certificate.uncertified` is now the union of three separately reported
states — `unseparable`, `inconclusive`, `undetermined` — and `tests/test_sufficient_reasons.py`
holds all of it.

The reason-deletion probe is **one-directional** — it switches a fact off, never on — so `deleted`
means *the answer did not depend on this reason under this interpretation*, and on an engine that is
not monotone in its inputs a lawfully retracted reason is indistinguishable from a dropped one. That
premise is now **declared rather than assumed**. `artifacts/` is reasonsmith's own abstraction of an
inference artefact — what a reason-bearing artefact is, what it must expose for the probe to measure
reasons from it, and whether its inference is monotone — and `artifacts/ground_program.py` is one
adapter over a nesyarena `GroundProgram`, which is why neither `artifacts/__init__.py` nor
`certificate.py` imports nesyarena any more. `artifacts/reason_trace.py` is the second
family — the reasons a system *recounts* for one decision, each tested by suppressing its facts and
re-running the system through a caller-supplied `answer` — and a knowledge graph, an extracted rule
set or a decision tree after it is an adapter and not a branch in the core. A recounted reason set
does not reach the ground program's rung: `Strength.RECOUNTED` sits between `observed` and `probed`,
the `artifact` basis row admits it, a family declares `reasons_are_exact` and **silence claims the
weaker rung** (the opposite default from `monotone`, because guessing monotone accuses a compliant
system while guessing recounted only understates one), one recounted decision caps the run, and
`RequirementResult._validate_reason_set` refuses a result claiming above
`report.EXACT_REASON_SET_KEY`. It is a *rung* and not a fifth basis by the test `docs/theory/08-evidence.md` §8.2 now states:
different object, different basis; same object less deeply, different rung. It reaches no log-only
system — the re-run is what makes the measurement independent of the rationale it measures — so the
auditors blocker of `docs/what-this-does-not-do.md` §4 is narrowed, not closed. `docs/theory/07-explanation.md` §§7.1–7.6 (*The inference artefact*)
is the contract and `tests/test_artifact_protocol.py` holds it.

The **probe** is one-directional; the **protocol** is not, since 2026-08-11. `at(fact, probability)`
and `probability(fact)` are optional members (read through `artifacts.admits_interpretation`,
implemented by the ground-program family and deliberately not by `reason_trace`), and admitting them
reversed a refusal this repository had published in `artifacts/__init__.py` and `docs/theory/07-explanation.md`
§7.1. Both now **record** the reversal in the shape `ROADMAP.md` §2 records the `since` one, and the
record is not a postscript: what was refused, what changed, what is *still* refused. Four things must
not be undone. Nothing in `docs/theory/07-explanation.md` §7.1 quantifies over anything but the deletion
lattice `L(β)`, and `certificate.py`/`explanations.py` call `without` and nothing else — checked by
`test_the_deletion_probe_never_reaches_the_widened_perturbation`, not asserted in prose. `deleted`,
its lemmas and its one premise did not move, and `without(fact)` is now literally `at(fact, 0.0)`.
No requirement reads the wider surface, so a family offering no `at` loses no verdict and no shipped
verdict moved. And the widening is paid for by a measurement, not by a possibility:
`semantic_laws.py` refutes a false `claimed_semantics` from the system's own answers with no
reference implementation in the loop, and `test_neither_one_directional_variant_refutes_a_top_k_engine`
is the measured fact that nothing narrower buys the discrimination — delete that test and the
reversal is unearned. `semantic_laws.py` is a **measurement and not a verdict**: no
`RequirementResult`, no rung, no requirement reading it, and deliberately not under `engines/`, the
standing `ltlf.py` has. It keeps two vocabularies apart and must go on doing so:
`spec.CLAIMED_SEMANTICS` is what an artefact may *claim* (closed, refused outside itself by
`normalize_claimed_semantics` at the artefact and certificate boundaries) and
`SEMANTICS_WITH_LAWS` is the one member of it this tool can *refute*, derived by intersection so a
rename there cannot leave a dangling member here. An admitted claim with no law is *not evaluated*
naming it; an unadmitted one never arrives. `docs/theory/07-explanation.md` §7.1 (the reversal) and §7.7 (the soundness proposition,
and why the design's vertex law is absent) are the contract; `tests/test_semantic_laws.py` holds it.

`engines/certificate.py` asks the declaration before it certifies and again of the
measurement afterwards, and reports **not evaluated** — never violated, never satisfied, never
downgraded to the presence check sharing the clause — for an artefact declaring non-monotone,
declaring nothing, or declaring monotone where a deletion raised the system's answer. One refused
artefact refuses the run. It is *not evaluated* and deliberately not *unattainable*: the gap is in
this tool, and telling a creditor to stop having lawful policy exceptions is the wrong instruction.
Four things must not be undone: the declaration is **required**, not defaulted to True, for the
reason `engines/counterfactual.py` refuses undeclared `computes` — a defeasible artefact and a
monotone one produce the same probe and the same count; the sign of `engine_drop` is kept, so a
deletion that raises the engine's answer is flagged `non_monotone` on the verdict and the
certificate, and that flag is now what *refutes* a false declaration rather than decorating a
verdict — it can refute and never confirm, since a defeater holding no fact of any enumerated reason
is never switched off at all; a defeated reason is still counted `deleted` wherever a certificate is
produced and must never be moved into the `unseparable`/inconclusive bucket, which would lose the
flag; and **every** private fact of a reason is switched off, not the first in `repr` order, because
coverage decided by a field's name gave two otherwise identical systems different probes. The budget
therefore counts facts switched off, not reasons. `tests/test_artifact_protocol.py` holds all of it
and `docs/theory/07-explanation.md` §§7.1–7.6 (*The inference artefact*) is the contract.

In v0.2 the first rule becomes structural. A verdict carries the strength of the evidence behind it
(`verdict.py`), and `RequirementResult.__post_init__` refuses to construct a result that claims more
than it has — including `strength=None` for "no engine here evaluated this", which is deliberately
not a strength on the lattice. Three consequences worth knowing before editing `report.py`: combining
zero verdicts is `inconclusive`, never vacuously `satisfied`; `SUPPORTED_FORMALISMS` is the list
of formalisms this build can actually evaluate — every member either has an engine or is
deliberately refused without one (`undetermined` and `graded`), so widening it means adding an
engine or an explicit no-engine dispatch, never a name this build cannot act on; and a
`probed` result cannot be constructed without the search budget that produced it
(`PROBE_BUDGET_KEY` / `PROBE_BUDGET_FIELDS`), so the bound travels with the verdict into every
rendering instead of being a rendering convention.

The lattice is a chain and it has a **second coordinate beside it**, not more links: `strength` says
how far a claim was pushed and `verdict.EvidenceBasis` says what the claim is *about*. Five members
— `behavioural` (a trace property), `relational` (a 2-safety property), `artifact` (an abductive
explanation over a model encoding), `assessment` (a truth degree over a residuated lattice), and
`statistical` (a declared sample measurement with uncertainty) — each named after the evidence
contract cited in `docs/theory/08-evidence.md` §8.2. It exists
because three duty shapes were off the chain and every one of them was prose in a module docstring:
the counterfactual fragment's missing trace rung, the certificate duty's ladder of one, and a graded
duty that counted as one an engine failed to settle. Five things must not be undone. A basis is a
**kind and never a rank**, so the members carry no order and `<` between two of them, or one and a
`Strength`, raises rather than answering — this is the whole reason it is a dimension and not five
more rungs. `BASIS_RUNGS` is the rungs each basis admits and `RequirementResult.__post_init__`
**refuses** a result outside its row, which is three docstring sentences turned into one refusal;
widen a row only when an engine for that rung exists, and
`test_the_basis_admits_exactly_the_rungs_the_ladder_can_reach` is the drift check against
`_engine_ladder`. `report.evidence_basis` derives it from the **requirement alone** and
`evaluate_requirement` stamps it once beside `domains`, so no pack field and no adapter can widen
what a duty claims. `render.basis_sentence` is the one place any rendering words a basis — the
discipline `render.degree_sentence` carries for a degree — and the HTML track draws only the rungs
the basis admits, so a ceiling reads as the duty's rather than as an exposure the system withheld.
And the lay projection is shown **no basis**, on the flag that already withholds the strength. The
`on_an_assessment` count is split out of `not evaluated` for the same reason: those two look
identical on a result and instruct a reader to do opposite things.
`tests/test_evidence_basis.py` holds all of it, including the pin that no shipped verdict moved.

Which engine a requirement reaches is decided by what the system exposes — for *every* fragment,
not just `logical`, since the property-language unification. `rulelang.py` is the one property
language: every `spec` is a formula in it (presence atoms `present(signal)`, the phrase atom
`contains(signal, "literal")`, comparisons, connectives, temporal operators), `formalism` names
which fragment the formula belongs to, `load_pack` classifies the spec and refuses a mismatch or
prose, and the English lives in the required `rationale` field. `report._engine_ladder` then
collects every engine the fragment *and* the exposed surface allow and takes the strongest evidence
produced: `logic()` gets Z3, `decide()` gets the replay search, and a trace gets the record engine
for a presence conjunction and the observed engine for **every other fragment, `logical`
included** — a state property is a property of one decision record, so a trace of them is evidence
about it, and declining to read one was a defect the label caused rather than the evidence. A
temporal duty reaches Z3 in exactly one shape: `engines/temporal.py` reduces `always(f)` — with `f`
free of temporal operators — to `f` and hands it to the proved engine, which is exact because over a
finite trace `always(f)` holds iff `f` holds at every position and every position is a decision the
exposed logic admits. `until(l, r)` and `since(l, r)` are the two binary temporal operators, and they are a **syntax
mapping and nothing else**: rtamt has parsed both infix all along, this language writes prefix calls
because it parses through Python's `ast`, and `engines/observed.to_stl` renders one into the other.
Never implement their semantics here. `until` shipped on the evidence of
`ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out`; `since` shipped without a qualifying duty by
an explicit decision recorded as a reversal in `ROADMAP.md` §2, and `docs/theory/03-semantics.md` §3.8 states
both, along with the discipline that still governs the next operator.
`eventually(f)` and every nested shape stay at `observed`, deliberately, and
the asymmetry between a universal satisfied verdict and an existential violated one travels on the
result as `TRACE_SEMANTICS` (`docs/theory/05-decision-procedures.md` §5.1, *reference interpreter*). Two limits of the trace
rung are stated rather than silent: rtamt cannot render a comparison against a Boolean constant, and
it reads the `spec` as written, so implication in a pack must be spelled `->` and never
`Implies(...)`. What the rung's **verdict** is has moved and the rest of it has not: it is
`rulelang.eval_temporal_trace` over the finite-trace clauses, and rtamt's robustness is the *margin*
reported beside it — `ρ = 0` decides nothing and `ρ(x > c) = ρ(x >= c)`, so any Boolean question
answered by comparing a score is a defect. The interpreter evaluates in the Kleene chain `F < U < T`
and `U` is ignorance about a record, never truncation of a trace; `docs/theory/03-semantics.md` Definition 3.11 is the
definition and the only place the tables belong.
Read `docs/theory/02-syntax.md` and `docs/theory/05-decision-procedures.md` §5.2 before editing any of it — they state the rule,
the atom encodings, and the one case the ladder does not resolve (exposed logic disagreeing with the
trace).

One rule cuts across every rung and is deliberately written **outside** all of them: an implication
whose antecedent nothing in an engine's evidence domain satisfies is *not evaluated*, `strength=None`,
naming the antecedent and the domain. It is a fact about the **formula**, which is why seven local
domain guards never found it and why the fix is not an eighth: `rulelang.implication_antecedent`
names the subtree (stripping a top-level `always`, never an `eventually`) and
`report.not_evaluated_for_unreachable_trigger` words the refusal once against the result model. Each
rung then answers it with what it already holds — `proved` checks premises ∧ antecedent satisfiable
(the premise check one quantifier deeper), `temporal` inherits it through the reduction, `observed`
evaluates the antecedent per position, `probed` counts the replays that reached it, and
`certificate` counts the certified decisions that reached it in the walk that already decides the
property against the measured count — and `probed` is
in that list because the ladder falls to it, so guarding the proof rung alone only moves a vacuous
`satisfied` down a rung, while `certificate` is in it for the opposite reason: the ladder gives
`ecoa_reg_b_1002_9_b_2_principal_reasons_complete` that rung and no other, so nothing beneath it
could catch the same empty claim. Every rung asks it on the *satisfied* path alone: a violation names a
witness whose antecedent fired. What this cost is stated in `docs/semantics.md` §1 and must not be
quietly undone: a creditor lawfully on the 12 CFR 1002.9(a)(2)(ii) disclosure branch is now neither
accused nor cleared, because `not applicable` per decision is the honest verdict and the result model
has no per-record applicability. Whether a trigger *fired* is a truth value and never an identity: a
rung testing `eval_expression(...) is True` reads the record's raw object, so a flag logged as `1`
counted as never fired and the duty left the audit on the Python type of a logged value. Read it
through `rulelang.kleene_value` first. `tests/test_trigger_counting_is_differential.py` holds every
trigger-counting rung to one trace, in the shape `test_the_solvers_fold_is_the_interpreters_fold`
gives `contains()` — a test pinning one engine would not have caught it, because the sibling site was
already right and what was wrong was that the two disagreed.

`counterfactual` is the fourth fragment and the only **relational** one — a property of a *pair* of
executions. `counterfactually_invariant(outcome, protected)` is its single atom, it is the whole of
a `spec` or no part of one, and `engines/counterfactual.py` is the whole of its ladder: Z3
self-composition at `proved` (the rules encoded twice under `_Scope` namespaces, every free input
held equal but the protected one), paired replay at `probed`, and **no trace rung, ever**. The
refusal lives in `rulelang.eval_expression`, not in `_engine_ladder`, because every trace-reading
engine evaluates through that interpreter — move it and the guarantee becomes a convention. Two
cases must never merge, and telling them apart is the only reason `computes` is consulted here: a
system that accepts the protected variable and provably ignores it is `satisfied`; a system with no
notion of it is `unattainable`. Without the declaration both encode identically and both come back
`unsat`, which would certify an unaware system as provably fair. Two further `unsat`s mean *no pair
exists* rather than *no pair disagrees*, and the proof rung refuses both before it reads the
negation: a declaration that pins the protected variable (the replay rung already refused that
system, so the ladder was publishing the engine that asked less), and rules that assign the
protected name while `computes` omits it — checked on the encoding (`is_definitely_assigned`,
`scope.inputs`), because that route is invisible to the declaration. A third refusal is about the
**sort**: a protected variable the declaration does not type as an integer is *not evaluated* at both
rungs, naming the variable and its declared sort, because a prohibited basis is a category and over a
dense sort the replay search samples fractions between the categories (0, 0.125, 0.25, 0.5 over a band
running to 8) while the proof rung's witness may be a pair the system can never be given. It lives in
`_direction_refusal`, so both rungs inherit it. `TREATMENT_LIMIT` rides on every
result because the duty cannot see a proxy or a disparate impact, and neither rung ever takes the
protected value from the trace — a decision record holding a fact about a natural person is a
collection cost this repository does not create, which is also why no shipped example system
declares one. For the same reason the protected argument is the one name
`report.analyze_unattainable` does not subtract from `capabilities()`: that set is what a system can
*emit* into a record, this duty needs what its procedure *accepts*, and gating on it would report a
creditor whose log carries a prohibited basis for nobody unattainable and tell it to start logging
one per decision. The name stays in `requires` because it is what the engine names as missing when a
system's declared logic has no notion of it.
The two rungs do not range over the same object — the proof quantifies over the *declared rules* on
the *declared input space*, the replay runs the *implementation* on the *logged* cases — so the
lower rung is run whenever the higher one reached a verdict and `cross_rung_signal` reports what
their disagreement **eliminates**, never that they disagree: `proved` violated with `probed`
satisfied is the relation holding and names the log, while the other direction discharges `R ⊆ P`
first, by evaluating the declared constraints on the replayed pair, so a pair the declared space
does not admit is named as such and only a pair inside it leaves the residual finding that
`decide()` does not implement the declared `logic()`. It moves no verdict, no strength and no
witness; `docs/theory/04-decision-problems.md` §4.4 is the claim and its contrapositive, and
`tests/test_counterfactual_invariance.py` carries a witness per direction.
`applicant_prohibited_basis` is the first shipped signal outside the paper's four Section 6.3
categories; `test_exactly_one_shipped_signal_is_outside_the_paper_s_taxonomy` keeps it the only one.
Read `docs/theory/04-decision-problems.md` §4.4 (*counterfactual*) and the `docs/refinement.md` row before touching any
of it. Group-statistical fairness — parity, equalised odds, calibration — is unreachable on this
evidence model and is documented as a hazard in `docs/authoring-packs.md`; do not build one.

The proof rung refuses a property built out of names the declared rules never assign, on the ground
that such a name is a free constant of the encoding — for `present()`, for `contains()`, and (since
the temporal reduction made it reachable) for a comparison of magnitudes. The third refusal is the
one that needed a **direction**, so `sut.logic()` may declare `computes` beside `variables`: the
names the system produces, as against the ones its situation supplies. The two together give three
states — computed, input, *no notion of* — and `_check_declared_directions` refuses a property
reading a name in the third state, or a declared output the rules do not settle on every path.
A declared **input** is quantified over where the property also reads a name the rules settle, or
reads its free names as flags rather than magnitudes — which is what keeps
`income >= 30000 implies approved` and `gdpr_art22_1_no_prohibited_decision_for_any_input` provable.
`RulesAdapter` derives `computes` from its rules' assignment targets — the premise of that adapter
is that the rules *are* the decision procedure — so no adapter here is undeclared, and a `computes`
name outside `variables` is refused at construction. Nothing second-guesses the declaration: an
adapter calling an output an input is answered about the system it described, the same trust
`system_domains` gets. What a declaration may **not** do is widen what reaches the solver, so
`_check_magnitudes_are_computed` runs beside `_check_declared_directions` and never instead of it:
`variables` is a type table, a caller may list a name the system merely logs, and reading such a
name as an input made both `proved` verdicts a function of the caller's type table — `violated` over
numbers nobody computes, and `satisfied` where a constraint of the system's own restates the duty.
`docs/theory/05-decision-procedures.md` §5.2, *When the magnitudes are not the system's own*, states all of it, names
every test, and states the cost: a duty comparing declared-input magnitudes alone cannot be
`proved`.

`contains(signal, "phrase")` is the one atom that reads *what a statement says* rather than whether a
field is blank, and it exists because a duty settled by `present()` alone accepts a reason of
`"n/a"`. It must keep agreeing across all three encodings — the rulelang interpreter, the synthetic
per-record flag fed to rtamt, and the Z3 regular language — which is why the case fold is ASCII-only
and one-to-one and a non-ASCII phrase is refused; `test_the_solvers_fold_is_the_interpreters_fold`
is the differential check, the counterpart of the blank-string one for `present()`. Only a clause
that states its own negative constraint may use it: the shipped example,
`ecoa_reg_b_1002_9_b_2_specific_reasons`, checks the two statements 12 CFR 1002.9(b)(2) itself calls
insufficient and decides nothing about whether any other statement is specific. Do not add a phrase
the regulation does not supply, and never push the judgement into the adapter as a self-declared
`reason_is_specific` flag — `docs/theory/03-semantics.md` Definition 3.5 is why. That duty also carries the clause's
trigger as an implication, which removed a false violation against a creditor lawfully on the
(a)(2)(ii) disclosure branch; where that antecedent fires nowhere the duty is *not evaluated*, under
the cross-cutting rule stated above and in `docs/semantics.md` §1.
`docs/findings-nesyarena.md` shows those ECOA duties landing on a real system.

Two fragments exist for **open-textured predicates** — the words a clause states without a sharp
boundary, which the fourth column of `docs/refinement.md` names over and over (*meaningful*,
*sufficiently detailed*, *adequate*) — and **no shipped duty uses either**, which
`test_no_shipped_pack_uses_either_open_texture_construct` keeps true. `undetermined(signal,
"predicate", "authority")` is a predicate no engine settles, reported *not evaluated* naming who
does; `degree(signal, "predicate")` is a truth degree read over a residuated lattice in
`manyvalued.py` (Łukasiewicz, Gödel, product, each checked against the residuation law). Neither
reaches an engine: `report._evaluate_requirement` dispatches both **after** the capability gate and
before `_engine_ladder`, which is the whole of the guarantee that a system showing nothing is still
`unattainable` and never a low degree. Six things must not be undone: the algebra is a **pack**
parameter (`[grading] algebra`) refused at load when missing and handed to graded requirements only,
so a two-valued duty cannot acquire one; the degree comes from a `manyvalued.Grading` a caller
passes to `check_conformance` and never from the audited system, with authority/scale/method forced
onto the result the way `PROBE_BUDGET_FIELDS` forces the search budget; `render.degree_sentence` is
the only place any rendering formats a degree and a result carrying one carries **no strength**, so
`0.7` can never read as a fraction of a rung — the strength lattice did not move and `graded` is not
one; a graded atom under a comparison (a compliance threshold) or a temporal operator is a **load
error**; an ungraded atom and an empty trace are *not evaluated*, never `0.0` and never `1.0`; and
nothing turns a degree into a verdict, because that needs a threshold no statute states. Read
`docs/theory/08-evidence.md` §8.4 — which carries the presentation rule — before touching any of it, and
`ROADMAP.md` objective 6 for what a first shipped duty would owe.

The arrow rewriter is textual and runs **before** the parse, so what it emits decides what every
later check can tell apart. `<=>` and `<->` emit `Iff(φ, ψ)`, a distinct node on the footing
`Implies(φ, ψ)` has, and never `==`: over the Booleans the two are the same function, but over a
residuated lattice `==` is a crisp comparison of two degrees — a threshold — so collapsing the
connective made the graded fragment refuse an equivalence naming a construct the author never
typed, while `implies` was spared only by being spelled as a call rather than as an arrow.
`manyvalued.Algebra.biresiduum` is the graded reading, `(φ → ψ) ⊗ (ψ → φ)`, **derived** from the
stored residuum for the reason `negation` is derived rather than added as a fourth operation. Three
things must not be undone: the two-valued reading is equality of truth values and is pinned against
the truth table in both the interpreter and the Z3 encoding, so no existing spec moved; an
author-written `==` under a graded atom is still refused, naming `==`; and no shipped pack uses
either spelling, so nothing generated moved. `tests/test_equivalence_connective.py` holds all of it
and `docs/theory/02-syntax.md` and `docs/theory/08-evidence.md` §8.4 are the contract.

`requires` is a conjunctive gate, so a branch of an either/or clause must not be listed in it: the
loader (`spec._check_spec`, via `rulelang.unconditional_signal_names`) exempts a signal read only
inside a disjunction, because gating one branch reports a system that lawfully took the other
`unattainable` without running it. The exemption is narrow on purpose — every branch must be
settled by `present()` atoms, and a name every branch reads stays gated — so a disjunction over
magnitudes does not quietly widen the gate. `ecoa_reg_b_1002_9_a_2_written_statement` is the worked
example and `docs/authoring-packs.md`, *An either/or clause*, is the rule, including the three costs
it buys: a system declaring neither branch is judged on its trace rather than reported unattainable,
a typo inside a disjunct is not caught at load time, and the duty leaves the `record` fragment, so
a log holding a single decision is reported not evaluated on it.

A duty reaches a system through **two** gates, on two axes that are not the same question, and both
are required fields with no default (`spec.REQUIREMENT_FIELDS`). `scope` is a regulatory class from
`REGULATORY_CLASSES` — the EU AI Act's own five-member vocabulary. `domains` is the *kind of
decision* the duty is about, from `DECISION_DOMAINS`, matched by intersection against what a system
declares (`--system-domain`, or a `system_domains` attribute on an adapter), with `[]` meaning "not
domain-limited" and reaching every system. `report._inapplicability` is the one place both are
decided, so `check_conformance`'s plan and `evaluate_requirement` cannot drift apart, and
`evaluate_requirement` stamps `domains` onto the result once rather than threading it through four
engines. An undeclared system is `not_applicable`, never `satisfied` — the argument for that over
`inconclusive` is in `docs/semantics.md` §1, and `tests/test_domain_gate.py` holds all of it.
The one thing to keep straight before touching any of it: **`DECISION_DOMAINS` is this repository's
list and no regulation's**, because no statute defines one. A pack limiting a duty to a domain owes
its description a sentence saying so — `test_every_shipped_pack_classifies_every_requirement`
enforces it — the same discipline `docs/authoring-packs.md` applies to an invented threshold. What
the gate buys is exactly one guarantee, and not a taxonomy: a system that has not declared its
domain is never reported satisfied on a domain-limited duty. It does not model the *trigger* inside
a decision (12 CFR 1002.9 fires on adverse action, not on being a creditor), and it does not check
that a system declaring `consumer-credit` issues credit.

Two further required fields, `deontic_type` and `defeasibility`, classify the **clause** and are
read by **no engine at all**. They exist because "the general rule is formalised, the exception is
not" was said of the fourth column of `docs/refinement.md` often enough to look like one missing
construct, and a classification carried by the loader makes it countable. The count is
`docs/refinement.md`, *The defeasibility census*, derived from the packs by
`tests/test_docs_refinement.py` — a requirement added without the fields is refused by `load_pack`,
and one added with them fails the build until the census is re-counted. Three things must not be
undone: a **defeater** (an exception overriding an otherwise-applicable duty) is not a **trigger**
(a condition of application, already expressible as an implication's antecedent and missing only a
signal), and collapsing them is what made the gap look like 28 omissions when it measures 3; a
defeater counts only where the clause states it in `verbatim_text` or in a source
`docs/legal-sources.md` retrieved, so raising the number means retrieving a clause, never
classifying from memory; and neither field may grow an engine, a fragment or a rung without the
census saying so — the answer it gives today is that **rebuilding the property language on
prioritized defaults is not justified**, with 1 defeater already modelled in ordinary propositional
structure. `docs/authoring-packs.md`, *The two classifications no engine reads*, is the rule for an
author.

An engine and a pack can be **installed rather than vendored**. `plugins.py` is the whole of it —
`importlib.metadata.entry_points` over `reasonsmith.engines` and `reasonsmith.packs` — and it is
deliberately not a plug-in framework: no registry, no lifecycle, no manifest. A discovered engine
joins `_engine_ladder` at the rung its `max_strength` declares and cannot report above it
(`RequirementResult.__post_init__`, `ENGINE_PLUGIN_KEY`); one that raises, times out, returns the
wrong type or will not import reports *not evaluated*, never satisfied and never violated; one
taking a built-in's name is refused rather than namespaced; and every plug-in result names its
plug-in. `load_pack` resolves an installed pack through the same lookup and the same checks, with
built-ins winning a name collision. There is no wall clock — a plug-in that hangs hangs the run, and
that limit is stated in `docs/authoring-engines.md` rather than papered over. Read that document and
`docs/authoring-engines.md` (*An engine that was installed rather than vendored*) before widening any
of it; nothing here audits a plug-in, so its declared ceiling is the only bound on what it claims.

`src/reasonsmith/packs/*.toml` are derived, not authored. The EU AI Act, GDPR and ECOA packs quote
`docs/legal-sources.md`, which is the retrieval record for the official statutory text and the one
place a quote is checked against the law. The Table 7 pack restates the rows of
`src/reasonsmith/table7.toml`, and `test_pack_matches_table7_transcription` holds it to the print:
quoted text character-for-character, both halves of the legal source, and the paper's own
evidence-field keys as the signal names. Do not rename a signal to something tidier — that test is
the only thing keeping the pack attached to the paper.

`docs/refinement.md` is the refinement record: one row per shipped requirement giving the clause,
the informal duty, the formal property, and what the formalisation deliberately left out. A new
requirement means a new row in the same commit — `tests/test_docs_refinement.py` reads the packs and
fails if one gains a requirement the record does not name. It also carries, once rather than
eighteen times, what the two applicability gates still do not reach — *Two axes of reach are
modelled, and the trigger is still not one*, whose largest remaining item is the trigger inside a
decision that no system-level gate can close.

`gdpr_recital71_error_risk_minimised` is the duty whose approximation error reasonsmith
**measures** rather than reads. It compares `engines.certificate.SEMANTICS_VALUE_GAP` — the absolute
distance between the system's own engine's answer and exact inference's answer to the same query on
the same interpretation, both computed from the artefact `artifact()` returns — against
`artifact_logs_decision_margin`, so an error larger than the decision's own margin fails. It was a
self-declaration (`scope_statements_declared_deviation`) until ROADMAP objective 5 repaired it, and
the repair is one overwrite in `engines/certificate._env`, the same move that duty's sibling already
made for `artifact_logs_deleted_reason_count`. Five things must not be undone. `MEASURED_SIGNALS` is
what `report._engine_ladder` and `report.evidence_basis` key on, so a duty naming either signal gets
one rung and the `artifact` basis and can never be answered off a log. The reference is refused
before it is used: `artifacts.reference_semantics` names what a family's own `exact_value()`
computes (`distribution semantics` for the ground program, None for a reason trace) — canonicalising
an accepted spelling and **carrying** a name outside `spec.CLAIMED_SEMANTICS` rather than raising,
because that name is not the audited system's claim and it is read mid-audit, where the outcome owed
is the refusal below and never an exception a reader meets as a failed decision — and
`artifacts.semantics_reference_refusal` splits the two outcomes —
no reference at all is **unattainable** (the gap is in the system, expose a model encoding), a claim
the reference does not match is **not evaluated** naming the claim (the gap is in this tool). That
second refusal is what stops the duty accusing a system that documents its own approximation, since
the closed vocabulary has no member for an approximation *of* a member; it is the reason the
vocabulary closed first and `test_an_honestly_declared_approximation_is_not_accused` is what holds
it. The monotonicity refusals are asked only of the deleted-count duty, because the declaration is
the premise `deleted` rests on and the gap is read at the unperturbed interpretation. And the reach
is one artefact family, stated in the pack description, `docs/theory/07-explanation.md` §7.1 and column four of
`docs/refinement.md` — every other system is `unattainable`, including all five nesyarena
provenances, which is why two violations left `docs/nesyarena-conformance-report.md` in the same
change. The bound is still the system's own margin, so no number in the duty is invented, and exact
equality is a checked limit because the clause's comparison is non-strict.
`tests/test_deviation_duty.py` holds all of it; why it exists is finding 1 of
`docs/findings-nesyarena.md`.

`docs/example-output.md` is derived too. `tests/test_docs_example_output.py` re-runs every command
block in it and compares stdout byte-for-byte, and cross-checks the header's line count and
`md5sum` against RESULTS.md. So anything that changes what the demo or the CLI prints — a wording
tweak included — means regenerating the transcripts and updating both files' headers together.
Both `docs/example-output.md` and `docs/three-systems.md` also state, near the top, the
`reasonsmith` version they were generated with, and each document's pin holds that note to
`reasonsmith.__version__`: the tree runs ahead of the last release, so a reader who installed
from PyPI and sees different output must be able to tell a stale page from a broken install. The
number is only worth anything while it is the version the tree actually is, so a version bump
means regenerating the note in the same change, or the pin fails.
The README's own CLI block is derived too, and `tests/test_docs_readme_transcripts.py` holds it
byte-for-byte to `python docs/build_readme_transcripts.py` the way the other pins hold their
documents: anything a wording change moves fails there. The builder raises rather than writing
when a command it names matches no block, because the ad-hoc helper it replaced reported success
having substituted nothing and left the front page showing a verdict the tool no longer prints.
`docs/report.html` is generated as well, but not by the CLI: `docs/build_example.py` composes it — the
Table 7 run declared into the high-risk class, beside the demonstration's key finding, which no
report the CLI writes may carry — and `test_docs_index_html_matches_the_renderer` holds the
committed page byte-for-byte to that script. Touching the renderer means regenerating the page with
`python docs/build_example.py`, the command the page names as its own provenance. That page names
no commit and cannot be made to: the commit carrying it does not exist while it is rendered, so a
hash written there would name another commit and break the byte pin the moment the page was
committed. It names the check that reproduces it instead (`PROVENANCE_NOTE` in the builder), the
same shape of claim `docs/nesyarena-conformance-report.md` carries — do not add a hash back to
either. The renderer
itself lives in `render.py` — module-level `render_text`/`render_html`, with the presentation
constants and `_source_checkout` — and `ConformanceReport`'s methods of the same names are thin
delegates to it, so a rendering edit is a `render.py` edit and nothing in `report.py`. One such
convention bears stating: the text renderer names the offending decision record of a violated
finding by the record's own `decision_id` — the same identifier the JSON
(`details.offending_trace_segment`) and HTML (witness table) renderings already use — and falls
back to the step index only when a record carries no identifier, so a reader is never handed an
empty name. That line lives on the text surface (`render_text`) and was deliberately not moved
into an engine summary, because `evidence_summary` travels into the JSON; editing an engine to
fix a redaction therefore changes a second rendering. The website
(landing, vendored libraries, fonts, assets) lives in the separate private `reasonsmith-site`
repo and deploys to Vercel — see [#35](https://github.com/eduardstan/reasonsmith/pull/35); this
repo only generates the dossier that gets published there as `report.html`, and the audience
gallery published there as `audiences.html`. Both files travel through the same hourly
`sync-dossier.yml` in the site repo.

`docs/audiences.html` is the second generated page and the only one that publishes more than one
rendering of a run: `docs/build_audiences.py` runs the shipped `symbolic_rules` system against the
`ecoa` pack — the run that mixes verdicts and strengths most, two duties `proved`, one `observed`
and two `unattainable` (no `probed` rung), so each projection has something to withhold — and
embeds all five `--audience` renderings verbatim as `srcdoc` frames inside a sixth, full
`render_html` page. That shell is not decoration:
the design tokens live inside `render_html`'s stylesheet and are not exported, so being a report
page is the only way the gallery can style itself without a second palette.
`tests/test_docs_audiences.py` holds the page byte-for-byte to the builder and fails if the
gallery grows a `<style>` block, a colour literal, a font stack, a `var(--token)` the renderer
does not define or a class it does not style. Regenerate with `python docs/build_audiences.py`.
Each frame is scrolled on load to `render_html`'s own `id="findings"` and is 24rem tall
(`FRAME_ANCHOR` / `FRAME_HEIGHT`), because opened at the top four of the five renderings are
identical for a whole screen — masthead, headline and dashboard are chrome no projection touches —
and the page demonstrated nothing. Renaming or dropping that `id` in `render.py` returns every
frame to the top while the byte-for-byte pin still passes, so
`test_every_frame_opens_where_the_documents_differ` asserts the anchor exists in all five
renderings.

The page's stylesheet is two token blocks, and three rules keep them from drifting. The dark block
is `@media screen and (prefers-color-scheme: dark)` — the `screen` is load-bearing, because the
`@media print` block below it overrides a handful of declarations and otherwise assumes the light
values, so a dark override reaching print media prints white on white
(`test_the_dark_scheme_is_screen_only_so_print_stays_light`). A solid chip pairs its fill
(`--ink`, `--ok`, `--warn`, `--accent`) with `var(--paper)`, never `var(--surface)`: that pairing
inverts with the scheme, and `--surface` puts near-white text on a light green fill in the dark
block. The report header is not an inversion of the page — it is a dark band in both schemes, so
it and the key-finding banner read `--band`/`--band-ink`/`--band-faint`/`--band-line`/
`--band-accent` rather than swapping `--ink` and `--surface`. Satisfied-green and violated-red
carry meaning here, so `test_both_schemes_keep_the_verdict_colours_apart` pins the hue channel of
`--ok` and `--accent-deep` in both blocks: a scheme that desaturates them toward a common grey
passes every contrast check and still destroys the distinction. `demo.py` carries its own
stylesheet for the key-finding section that `docs/build_example.py` composes in, and it is subject
to all three rules.

`docs/build_showcase.py` is the third generated page and the only builder writing **three** files
from one run: `docs/assets/showcase-figure.svg`, `docs/assets/showcase-cast.svg` and
`docs/showcase.html`. It exists because the other two generated pages are *outputs* — they render a
conformance run to someone who already knows what one is — and nothing introduced the tool
visually, so the project's own result arrived as a paragraph above a forty-line transcript. The run
is `demo.key_finding_report()`, the same one `docs/build_example.py` composes its key finding from,
so the figure, the cast, the showcase page and the dossier cannot disagree about how many reasons
the decision used. Four things must not be undone. **Nothing on either figure is a literal** —
`test_the_figure_states_only_the_run_s_own_numbers` asserts every reason label is in the SVG *and*
absent from the builder's source, because a typed label looks identical and outlives the
measurement. **The cast is real stdout**: `_terminal_lines` runs the CLI in-process, wraps at
`COLUMNS` the way a terminal does and never rewraps at word boundaries, elides only whole lines and
counts what it elided, and `_select` raises for a rule matching nothing —
`docs/build_readme_transcripts.py`'s defect in the shape it takes here. Every timing is synthesised
from the row index, which is the whole reason the cast can be byte-pinned at all; a hand-recorded
one cannot. **The cast is a deliberate placeholder** for the TUI proposed in
[#120](https://github.com/eduardstan/reasonsmith/pull/120) and is built to be swapped: one function
and one constant. And the two SVGs carry their **own** palette, which is not a second design system
— they are embedded in `README.md` on GitHub, outside any stylesheet this repository controls, so
they must state their values; every class in them is prefixed `rs-fig-`/`rs-cast-` because an
inline SVG `<style>` is document-scoped once the page inlines it, and
`test_the_figures_style_nothing_but_themselves` is what stops a figure restyling the report beneath
it. Regenerate with `python docs/build_showcase.py`; `tests/test_docs_showcase.py` holds all three
files byte-for-byte.

After the badges, README opens with the two generated preview SVGs and the measured sentence they
summarise. It then gives the organising question and diagram, the five reading paths, and *Install
and run* with `pip install`, the trusted-code warning and one generated `check` transcript; *Limits*
states six boundaries before the licence. The full unprojected transcript is
`docs/example-output.md` **§3** — the one committed transcript whose run exits 2 — and
`REPORTING_EXIT_CODES` in `tests/test_docs_example_output.py` is what admits it. The theory lives in
the documents the reading paths link rather than being embedded on the front page.

`ConformanceReport.to_dict()` leads with `schema_version` (`report.JSON_SCHEMA_VERSION`), the
`--json` envelope's shape version. It is not the package version, it increments only when a key is
removed, renamed or changes type or meaning, and `tests/test_json_schema_version.py` writes out the
key set at both levels beside the number so a shape change without a bump fails. Adding a key fails
it too, deliberately: the convention says that is not a bump, and the test exists to make the
decision be made rather than skipped.

`AudienceProjection` has one field that emits rather than suppresses: `plain_account`, on for
`affected-individual` alone, turning on `render._lay_sections`. Everything it prints is quoted —
the decision and the reason out of `ConformanceReport.decisions` (the trace `check_conformance`
already read, carried on the report and deliberately absent from `to_dict`, which is the findings
record), and a reason left unstated out of the certificate engine's own measurement. It paraphrases
no statute and explains no decision; `docs/semantics.md` §3 is the rule and the four tests in
`tests/test_audience_view.py` are the enforcement, including the one that fails if the view ever
becomes a subset of an expert view again. The `--audience` transcripts in `README.md` are derived
and held by the same `tests/test_docs_readme_transcripts.py`, so a wording change there means
`python docs/build_readme_transcripts.py`.

`docs/assets/og.png` is generated from `brand/og.html` in the site repository, is served live as the
site's social card, and must never be edited here — regenerate there, copy here, update the pinned
digest in `tests/test_social_card.py`.

`docs/three-systems.md` and the three files in `src/reasonsmith/examples/` are the answer to "how
does any model get into this tool?": a neural black box (`JSONLAdapter`, log only), a probabilistic
scorer (`CallableAdapter`, replayable) and a rule set (`RulesAdapter`, logic exposed), all checked against
the one binding duty `ecoa_reg_b_1002_9_b_2_specific_reasons` and reaching `observed`, `probed` and
`proved` respectively. `tests/test_docs_three_systems.py` holds each transcript byte-for-byte the
way `test_docs_example_output.py` does, asserts the three rungs are still three, and pins the
neural system's ceiling. That ceiling is the point of the artefact: raising it means changing the
*system*, never the adapter, and `docs/three-systems.md` is the one home of that table since the
README reorganisation routed the front page at the document instead of restating it.

A fifth example, `truncating_credit_system.py`, is the only one that comes back **violated**, and
that is its whole job: the other four pass, so before it a reader who ran every shipped example
never saw the tool report a breach. It imports `reasonsmith.demo`'s `TruncatingCreditSystem` rather
than reimplementing it — that system's output is also the README transcript, `docs/example-output.md`
and the committed dossier, so a second copy would be a fourth thing to keep in step. It checks the
clause's *content* duty (`..._principal_reasons_complete`), never the *form* duty its siblings
check, which this same system satisfies. `reasonsmith check --help`'s epilogue names it first;
`test_a_shipped_example_reports_a_violation_and_help_names_it` in `tests/test_adoption_surface.py`
pins both halves. README uses that run for the worked transcript in *Install and run*, after the two
generated previews, organising diagram and five reading paths. It routes the deeper limits to
[`docs/what-this-does-not-do.md`](docs/what-this-does-not-do.md) instead of embedding the theory.

They live under `src/` and not under `docs/` for one reason: **a documented command must run for
someone who only ran `pip install reasonsmith`**, and no wheel carries `docs/`. So a command a
document prints names either a shipped module (`python -m reasonsmith.examples.<name>`,
`--system-module reasonsmith.examples.<name>:system_under_test`) or a file inside the installed
package, whose directory `python -m reasonsmith.examples` prints — which is why the README's
sample-log command carries a `$(…)` substitution and why `docs/build_readme_transcripts.py`
expands that one substitution before running the command in-process. A new data file the
documentation names needs a pattern in `pyproject.toml`'s `package-data`; a `.py` module ships by
being a module. `tests/test_packaged_examples.py` builds the wheel and reads what is in it,
because this defect once shipped invisibly: from a checkout every missing file was right there.

`docs/language-model.md` and the fourth adapter
`src/reasonsmith/examples/language_model_notices.py` are a
different axis, and the filename `three-systems.md` was left alone rather than made false. A
language model you can call adds **no rung** — it sits at `probed` beside the probabilistic
scorer — so do not write "four systems, four rungs". What it demonstrates is which duties a system
can be answered on at all: run against the whole `ecoa` pack it is `observed`, `probed` and
`unattainable` in one report, the last on `ecoa_reg_b_1002_9_b_2_principal_reasons_complete`,
whose `artifact_logs_deleted_reason_count` is measured from an inference artefact a decoder has
none of. The adapter takes one `complete(prompt: str) -> str` — never a vendor SDK, never a
network call — behind a deterministic stub, because `tests/test_docs_language_model.py` pins the
transcript byte-for-byte and asserts the ceiling on the mechanism: `logic()` is `None`, and the
adequacy duty is never downgraded to the presence check sharing its clause.

`docs/nesyarena-conformance-report.md` is the third generated document, and the only run against a
real system rather than a demonstration fixture: `docs/build_nesyarena_report.py` drives the five
`nesyarena.suts.registry()` provenances over generated ground programs against the GDPR, EU AI Act
and ECOA packs, and `test_nesyarena_report_matches_the_builder` holds the committed file to it
byte-for-byte. Anything that moves `render_text`'s wording, the nesyarena version or the builder's
own constants means regenerating with `python docs/build_nesyarena_report.py`. Like
`docs/report.html`, it names its build command and deliberately carries no commit hash; reproducibility
is owned by the byte-for-byte builder test, so do not add a hash back. Its adapter declares only
signals a provenance genuinely emits, so a set of pack signals is deliberately undeclared — the
census and the count live in `docs/findings-nesyarena.md`, which pins them — and
neither a regulatory class nor a decision domain is declared — these systems decide graph
reachability and Sudoku validity, so there is nothing to declare; the resulting unattainable and
not-applicable verdicts are the finding, not a gap to close, and naming a domain to make the ECOA
rows evaluate again would put finding 3's false positive back by hand.
`docs/findings-nesyarena.md` is the written account of that report, held to it by
`tests/test_findings_nesyarena.py`: every figure the prose quotes is derived from the run the
builder drives — the report, the declared/undeclared signal census, the per-formalism requirement
census — and a failure names the figure and what to regenerate, so a pack change that moves a
count fails the build until the prose is re-derived. Two sharp edges: the pack loader refuses a
`formalism` that does not match a requirement's spec, so pin breaks must come from the builder's
census or the document, never from a duty reclassification; and historical claims (the first
run's 11 requirements and 8 signals, the pre-domain-gate ECOA column of 8 satisfied / 2 violated
/ 5 unattainable) are not derivable and are verified against git history instead.

The numbered theory chapters state the mathematics **once, in one notation**, with
`docs/theory/00-notation.md` as the symbol table and `docs/theory/bibliography.md` as the citation
registry. Two things to know before editing them or adding a citation anywhere. A citation is a backticked pandoc key — `` `[@hajek-1998]` `` — and
`tests/test_docs_formal.py` enforces it as a *registry*: every key used in `docs/*.md` or
`src/reasonsmith/**/*.py` resolves to an entry, every entry is cited by a claim, and a paragraph
naming a publication venue (`VENUE_MARKERS`) with no key **fails the build**, which is what stops
references drifting back into docstrings the way twelve of them had into `verdict.py`. And the
document does not replace `semantics.md`: it keeps its own operational phrasing, while the numbered
theory chapters own the mathematics. The anti-drift mechanism is that **every definition the code
also defines is generated from the code in each document that states it** — the chain from
`Strength`, the rung table from `BASIS_RUNGS`, the fragments from `rulelang.FRAGMENTS`, the
algebras from `manyvalued.ALGEBRAS` — so documents held to the code cannot disagree with each
other. `theory/07-explanation.md` no longer carries its own reference list; it points at the
registry. Widening the scanned corpus is a one-line change to `SCANNED_EXCLUSIONS`; the venue-marker
check is a heuristic and the document says so rather than being trusted further than it is.

`docs/semantics.md` states what each verdict means and what it does not, and every claim in it names
the test that fails if the claim becomes false. `tests/test_docs_semantics.py` checks that mapping,
so **renaming or deleting a test breaks the build if that test is named there** — update the
document in the same commit. It is also where a claim the code cannot support belongs: report the
gap in the document rather than describing a tool that does not exist.

`docs/theory/02-syntax.md` is the **definition of the property language** — the grammar;
`docs/theory/03-semantics.md` defines its denotation `⟦·⟧_{M,A} : Spec → (𝒫(Trace_M) ⇀ A)`
over a structure (a finite trace, or an input space) and a declared algebra (`𝔹` as a degenerate
residuated lattice, not a separate system), typed over sets of traces uniformly so the counterfactual
atom is the 2-safety property it is. It is a *description* of `rulelang.py` and never a second front
`tests/test_language_definition.py` generates from the grammar, refuses each refusal the document
keys by id, and holds the claim-to-test map the way `test_docs_semantics.py` holds `semantics.md`'s.
The four encodings are recast there as implementations of one denotation, with the existing
differential tests — `test_the_encoder_and_the_interpreter_answer_the_same`,
`test_the_solvers_fold_is_the_interpreters_fold`,
`test_the_ltlf_backend_agrees_with_the_monitor` — named as their conformance evidence. Three
refusals in the code are stated there as **consequences of the definition** rather than as policy,
and must not be re-explained as policy: no many-valued reading of a temporal operator (hence no
graded atom under one), no value at the empty trace (the lattice top is the vacuous `satisfied`
rewritten as a number), and unawareness as `unattainable` (the relational atom quantifies over pairs
of admissible inputs, and an unaware system admits none). `docs/theory/03-semantics.md` Remark 3.3 reports **four shapes where the rtamt
rendering and the definition disagree** — `%` (ANTLR error-recovers by dropping the token; `_monitor`
now installs rtamt's raising error listener, so this one raises rather than being read differently),
a chained comparison (rtamt left-associates over robustness where
the language conjoins), `<->` (rtamt's `iff` robustness is negative whenever the two margins
differ), and the known exact tie. The first three are **refused in the rendering** —
`engines/observed._refuse_shapes_the_monitor_misreads`, asked of the parsed formula so that `<->`
and `<=>` reach one refusal — so a duty writing one is *not evaluated* naming the construct rather
than answered off a misread formula; the tie is a divergence of the *margin* alone, since the
verdict no longer reads the score.
All four stay latent, `MONITOR_DIVERGENCES` is the exclusion list, and it is pinned twice: every row
must still diverge (or raise) *behind* its refusal and no shipped spec may use one, so a refusal
whose reason has gone loses a duty a rung for nothing.
Three things must not be undone: the refusal list is three
constructs long only because rtamt **raises** for every other construct this language admits and it
does not support (`!=`, `min`, `max`, `Implies(...)`, `<=>`), which is why
`test_rtamt_still_behaves_the_way_the_refusals_assume` probes each one and asserts which of
*raises*/*agrees*/*misreads* rtamt does — delete it and the `%` hole can reopen under another
construct as invisibly as it did the first time; the rendering stays **textual** (`req.spec` reaches
rtamt as written, arrows included, because an AST round-trip would spell `->` as `Implies(...)`), so
a refusal goes beside the existing ones and never into a rewritten pipeline; and no construct leaves
the *language* to suit this backend.

## The web home and the install surface

The live home is `https://reasonsmith.dev` (landing) with the conformance dossier at
`https://reasonsmith.dev/report.html`; the old `eduardstan.github.io/reasonsmith` Pages URL is
superseded and nothing should reintroduce it. `reasonsmith` is published on PyPI — the
README's *Install and run* section owns that claim and the install commands,
[RESULTS.md](RESULTS.md) owns the `torch` caveat, and this file names no version, because one
written here goes stale at the next release. The forbidden string appears here deliberately:
this paragraph is the statement of the rule, and a rule that cannot name what it forbids
is not a rule — any repository-wide check for it must exclude this file.

The release discipline lives in `CONTRIBUTING.md`, *Versioning and Releases*, and is enforced by
`tests/test_release_discipline.py` (the version lives in **four** places — the pyproject
`version`, the topmost released `CHANGELOG.md` heading, `__version__` in
`src/reasonsmith/__init__.py` and `version` in `CITATION.cff`, the one the guard originally
missed — and they must agree; no tracked markdown may carry a bare `#NN` outside code and
anchors) and by the tag check in `.github/workflows/publish.yml`
(a release whose tag is not `v` plus the pyproject version never builds). Bumping the version
means closing `[Unreleased]` and opening a fresh one in the same change. The same module pins
prose counts against the shipped tree — the README's pack and engine counts, `ROADMAP.md`'s
"Current state, for scale" line, and the same claims where the prose restates them spelled out —
derived at test time from `spec.list_packs()` and the modules under `engines/` (never
`BUILTIN_ENGINE_NAMES` alone, which once missed an entry). A new pack, engine or requirement
means updating those sentences in the same change, or the pin fails. It also pins the CI coverage
floor, which for a long time never failed: `--cov-fail-under=N` compares `round(total, precision)`
against N and pytest-cov defaults `precision` to 0, so a real 92.79% rounded to 93 and the job
exited 0 while its own summary printed `FAIL`. `[tool.coverage.report] precision = 2` in
`pyproject.toml` is what makes the floor real — for both workflows and a local run — and
`test_the_coverage_floor_fails_a_total_below_it` asks `should_fail_under` itself rather than a
literal. The canonical Linux floor is **95%**, a measured credibility gate rather than a rendering
convention. Windows has runner-specific measured floors (`95.10%`, `95.10%`, and `95.0%` for
Python 3.11, 3.12, and 3.13) because platform-only optional paths are skipped there; the 3.13
floor was explicitly rounded down from its measured 95.07% after the Seoul pack landed. Do not
lower any other floor or weaken the measurement without an explicit decision, and do not "fix" a
shortfall by moving it.

`analysis.py` is the only module that reads a **pack** rather than a system's evidence, reached
through `validate-pack --analyse`: joint satisfiability with an unsatisfiable core, entailment and
equivalence between requirements, vacuity, and — with `--system-module` — a mutation score per duty.
It has no encoding of its own. `_ast_to_z3` and `_Scope` are `engines/proved.py`'s, `_PackScope`
overrides only `present`/`contains` (the two atoms that have no meaning when there is no rule block
to assign anything, so each becomes one uninterpreted Boolean plus the `contains implies present`
axiom `rulelang.contains_literal` implements), and the system-relative domain is
`proved.encode_logic_domain`, the same one the proof rung quantifies over. Four things must not be
undone: the vacuity definition is the one in `docs/theory/04-decision-problems.md` §4.6 and **must keep coinciding with
`report.not_evaluated_for_unreachable_trigger`** on the case that rule already handles — that
agreement is `test_vacuity_coincides_with_the_unreachable_trigger_rule` and a disagreement is a
finding to report, never a definition to widen on either side; only the *satisfied* side and only
the *outermost* replaceable occurrence is reported, because a looser rule prints false alarms and
an analysis nobody reads is worth nothing; a question the encoding cannot reach is skipped **by
name** into `PackAnalysis.skipped` (the counterfactual fragment, a non-`always` temporal spec, a
property naming what the system has no notion of — that last through `_check_declared_directions`,
the proof rung's own refusal, asked here because the vacuity question inherits it); and a mutation
score reaches only a system exposing its rules through `logic()`, which is not most audited systems,
so `MUTATION_LIMIT` travels on every analysis carrying one and **no number here may be rendered as a
coverage claim**. Findings do not change `validate-pack`'s exit code. The measured figures live in
RESULTS.md, *Pack Analysis Note*, never in a test.

The `temporal` fragment is not a property of one record, so Z3 reached it only through the
`always(state property)` reduction and every other shape — including the shipped `until` duty —
was skipped by every question above. `ltlf.py` decides the whole fragment instead, and it is **a
syntax mapping and an emptiness question and nothing else**, on the terms `engines/observed.to_stl`
sets for rtamt: BLACK is asked whether the formula is satisfiable over a finite trace,
entailment is `left & !right` unsatisfiable, equivalence is both ways. **Never implement a temporal
semantics, monitor, automaton construction or tableau here** — the previous attempt at this hand-
wrote a monitor for operators rtamt had parsed all along. It is deliberately not under `engines/`:
it returns no `RequirementResult`, occupies no rung, and the engine count `test_release_discipline`
pins reads that directory. Six things must not be undone: it is an **optional extra** whose
procedure is the BLACK binary from a system package manager (the `ltlf` extra declares no Python
dependency, so installing it adds nothing) and its absence is `UNAVAILABLE_NOTE` with `PackAnalysis.temporal`
left `None`, never a weaker answer in the same words; the reading is propositional, so satisfiability
is reported **only in the affirmative** and `LTLF_ABSTRACTION_LIMIT` rides on every answer — rtamt
keeps every magnitude, this keeps every position, and neither replaces the other; every question
is asked over a non-empty trace, on which an `always` duty cannot hold vacuously — a clause BLACK's
own finite-trace semantics supplies rather than a guard formula conjoined here; a past operator (`once`, `historically`, `prev`, `since`, `rise`, `fall`) is
LTLf-inexpressible and is skipped **by name**; `ATOM_BUDGET` is checked before the solver is called
because there is no wall clock anywhere in this package, and "no pair entails another" must never
render for "no pair was decided"; and **no LTL₃ verdict is computed** — the
tool exposes no monitor construction, so the Bauer/Leucker/Schallhart distinction is reported
unavailable rather than synthesised, and the strength lattice did not move. That is not the `U` of
the Kleene chain `rulelang` evaluates in (`docs/theory/03-semantics.md` Definition 3.11): ignorance about a record is a
different question from truncation of a trace, and the two must not be conflated in prose or in a
value. The acceptance test is
`test_the_ltlf_backend_agrees_with_the_monitor`: the two backends may not disagree about any shipped
temporal duty, in the shape `test_the_solvers_fold_is_the_interpreters_fold` gives `contains()`.
`docs/theory/05-decision-procedures.md` §5.4 (*The temporal fragment, decided as a finite-trace formula*) is the contract.

## The front door

Before editing the CLI, read the maintenance contracts in `src/reasonsmith/cli.py`'s module
docstring. README, "Install and run", owns the install and the one worked `check` invocation;
`docs/adopting.md` owns the rest of the user-facing usage — `explain`, the surfaces a system comes
in through, and `published-counts`, which is a site-build command rather than an audit one — and
`docs/authoring-packs.md` owns `validate-pack` and the pack-authoring rules.

`ROADMAP.md` is the public backlog and the one document that may state what is *missing*: six
numbered objectives, each citing the committed document that names the gap, with a measurable
outcome and its dependencies: open outcomes fail today, while closed objectives record why the same
check now passes. Nothing goes on it that no document already states — find the gap in
`docs/refinement.md`, `docs/semantics.md` or `docs/findings-nesyarena.md` first, or write it there
first. Closing an objective means deleting the sentence it quotes from that source document in the
same commit; `docs/what-this-does-not-do.md` and the README's *Limits* section cite the same gaps and
go stale with it. `CONTRIBUTING.md` defers its roadmap table here rather than keeping a second list.

## Autoformalisation corpus

`src/reasonsmith/challenges/manifest.toml` is schema version 2 and covers every shipped requirement.
Record/logical cases carry `signals`, temporal cases carry finite `trace` records, and the
counterfactual case carries `pairs` of left/right executions; `autoformalize.check_challenges` is the
model-free checker and `proposer._challenge_prompt` presents each shape. Update the manifest,\`docs/autoformalization.md`, and the measured corpus note in `RESULTS.md` when coverage changes.

## Neural verifier boundary

The optional Marabou bridge is `src/reasonsmith/neural_verifiers/marabou.py`, documented in `docs/neural-verifiers.md`: it is an out-of-process oracle pinned to Marabou 2.0.0/VNN-LIB 1.0, bounded-search only, and never a verdict engine. SAT must pass the existing `neural_queries.verify_query` witness replay; bounded UNSAT is provenance only. Keep this boundary intact until the design’s slice-4 soundness gate. The alpha-beta-CROWN bridge is the independent slice-6 adapter in `src/reasonsmith/neural_verifiers/alpha_beta_crown.py`; its upstream source commit, status mapping, and failed Python 3.12 install gate are recorded in `docs/neural-soundness-corpus.md`. Preserve the native-status distinction, SAT replay requirement, and differential disagreement block.

## Seoul Frontier AI Safety Commitments pack

`src/reasonsmith/packs/seoul_frontier_ai_safety_2024.toml` is the frozen GOV.UK edition updated
2025-02-07. Its `frontier_trigger` requires the adapter's self-asserted `frontier_ai_status =
"frontier"`; missing or `not-frontier` is `not_applicable`, and the declaration is never inferred.
Commitment IV is the four-signal logical depth anchor; the replayable and rules examples are
`src/reasonsmith/examples/frontier_risk_{scorer,rules}.py`. GOV.UK drift extraction and the edition
sentinel live in `drift.py`; the fixture is `tests/fixtures/drift/ai_seoul_frontier_commitments.html`.
Later editions must use `__updated_YYYY-MM-DD` rather than mutating this pack. Regenerate generated
outputs with the builders named in their tests after changing report wording or pack inventory.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
