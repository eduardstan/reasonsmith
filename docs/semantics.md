# What a reasonsmith verdict means

This document states what follows from a reasonsmith verdict, and under which assumptions. It is
written for a reader who wants to check the claims rather than accept them: every soundness claim
below names a test that fails if the claim becomes false, and §6 collects that mapping in one
table. `tests/test_docs_semantics.py` holds this document to it — a test named here that does not
exist in the suite fails the build.

Where this document and the code disagree, the code is right and this document has a defect.

---

## 1. The objects

**Requirement** — `spec.py`, `Requirement`. A frozen record of one duty, carrying exactly the ten
fields of `REQUIREMENT_FIELDS` and no others: `id`, `source_document`, `article_clause`,
`verbatim_text`, `stakeholder`, `formalism`, `spec`, `requires`, `binding`, `scope`. `formalism` is
one of `record`, `temporal`, `logical`, and decides which engine answers it. `requires` is the
non-empty set of signal names a system must be able to emit for the duty to be checkable at all.
`binding` separates a statutory obligation from an interpretive recital. `scope` is a regulatory
class from `REGULATORY_CLASSES`, or empty for a duty that is not class-limited. A pack that omits a
field, adds one, or leaves one blank is refused at load time rather than loaded with a guess
(`test_loader_rejects_missing_field`, `test_loader_rejects_an_unknown_field`,
`test_loader_rejects_blank_and_duplicate_fields`, `test_requirement_needs_at_least_one_signal`).

**Pack** — `spec.py`, `Pack`. A named collection of requirements with source metadata. Duplicate
requirement ids are refused, because `get_requirement` returns the first match and the second would
be unreachable.

**System under test** — `sut.py`, `SystemUnderTest`. A protocol with three methods —
`capabilities()`, `decisions()`, `logic()` — and one optional method, `decide(case)`, deliberately
outside the protocol because replay is optional. reasonsmith never introspects a system beyond
these.

**Capability declaration** — the return of `capabilities()`: a collection of the signal names the
system can emit, and nothing else. A bare string and a mapping are both refused at every site a
capability set crosses into reasonsmith, because `set("reasons")` would declare seven
single-character signals and a `{name: bool}` map would declare the signals it marks `False`
(`test_base_sut_rejects_a_bare_capability_string`, `test_base_sut_rejects_a_capability_map`,
`test_unattainable_analysis_rejects_a_capability_map`). A declaration is authoritative only when the
system made it; an adapter that derived it from a trace instead marks itself
`capability_basis = "trace"` and its findings are worded as being about that trace rather than about
the system (`test_unattainable_from_a_trace_does_not_speak_for_the_system`,
`test_declared_capabilities_word_the_finding_as_about_the_system`).

**Trace** — the return of `decisions()`: an iterable of decision records, each a mapping from signal
name to value. A record of any other shape is refused naming the system that produced it
(`test_a_trace_of_the_wrong_shape_names_the_system`). A signal *present* in a record is one whose
value is not `None`, not a blank string, and not an empty list/dict/set/tuple — `_is_present` in
`report.py`. An empty reason list is not a reason given
(`test_a_present_but_empty_signal_does_not_count_as_evidence`), and `0` or `False` is
(`test_a_falsy_but_real_signal_value_counts`).

A trace is a sample of behaviour chosen by whoever produced it. Nothing in reasonsmith establishes
that it is representative, complete, or unfiltered.

**Verdict and strength** — `verdict.py`. A `Verdict` is one of `satisfied`, `violated`,
`inconclusive`, `not_applicable`. A `Strength` is one of `unattainable`, `observed`, `probed`,
`proved`, ordered strictly in that order (§4). `strength=None` is not a rung: it means no engine
here evaluated this requirement.

**Result** — `report.py`, `RequirementResult`. One requirement's outcome. Its `__post_init__` is the
enforcement point: a result that claims more than it has cannot be constructed. Strings are parsed
into enum members before any guard runs, so `strength="unattainable"` cannot slip past a comparison
against `Strength.UNATTAINABLE` (`test_a_string_verdict_or_strength_is_parsed_not_trusted`). An
unattainable result cannot be `satisfied`; `signals_missing` is populated exactly when the result is
unattainable and may only name signals the requirement asked for; a result with no strength cannot
carry `satisfied` or `violated`; a `not_applicable` result may carry neither a strength nor a
missing-signal list (`test_result_cannot_claim_more_than_its_evidence`). A `probed` result cannot be
constructed at all without the search budget that produced it
(`test_a_probed_result_cannot_be_constructed_without_its_budget`).

---

## 2. The property language

There are three formalisms and they do **not** share one language.

### `record` — the `spec` string is not evaluated

`RecordEngine` reads `requires` and nothing else. The `spec` field of a record requirement is
documentation: the shipped packs carry free prose there (`"Record check"`), which no parser would
accept. Two record requirements identical but for their `spec` — one prose, one a property false on
every record, one unparseable — produce the identical verdict, strength and summary
(`test_the_record_engine_reads_requires_not_spec`). A reader who takes a record verdict as a claim
about the `spec` text is reading something the tool never checked.

### `temporal` — Signal Temporal Logic, parsed by rtamt

`ObservedEngine` hands `req.spec` to `rtamt.StlDiscreteTimeSpecification`. The accepted syntax is
rtamt's, not this project's; a formula rtamt cannot parse is reported not evaluated rather than
guessed at (`test_unexpressible_formula_reports_not_evaluated`).

Two things about the encoding are this project's own and are load-bearing:

- **Time is the record index.** The monitor is fed `time = 0..n-1`, one step per record, in the order
  the trace supplied them. A temporal bound counts decisions, not seconds. A violation at step *t*
  is the record at position *t* (`test_temporal_violated_returns_offending_segment`).
- **Flags and magnitudes are read off the formula, never off the trace.** `var >= 0.5` (or
  `0.5 <= var`) is the one way a pack asks whether a signal is *present*: that variable keeps the
  1.0/0.0 encoding. Every other comparison — any other constant, 0.5 under any other operator, or a
  variable against a variable — makes both sides magnitudes, and a record that carries no finite
  real number for a magnitude makes the whole requirement not evaluated rather than scored 0.0
  (`test_quantitative_bound_needs_a_measurement`, `test_non_finite_flag_counts_as_absent`).

### `logical` — the rulelang mini-language

`rulelang.py` is the one place rule and specification text is parsed, rewritten and executed. It
never calls `eval`, `exec` or `compile`; the whitelist is the interpreter itself. Pack text is data
(`test_pack_text_is_never_executed_as_python`).

**Expressions** (`parse_expression` → `eval_expression`) accept exactly:

| Construct | Accepted |
|---|---|
| Constants | `None`, `bool`, `int`, `float`, `str` |
| Names | resolved against the decision record; an unbound name raises rather than defaulting |
| Unary | `not`, `-`, `+` |
| Binary | `+`, `-`, `*`, `/`, `%` |
| Boolean | `and`, `or` |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=`, including chained |
| Calls | `implies(a, b)` / `Implies(a, b)`, `abs(x)`, `min(a, b)`, `max(a, b)` — no keyword arguments |
| Arrows | `<=>` and `<->` rewrite to `==`; `=>`, `->` and ` implies ` rewrite to `Implies(...)` |

Arrow rewriting is textual and happens before parsing. It respects parentheses and string literals,
so an arrow inside a quoted string is left alone (`test_arrow_rewriting_leaves_string_literals_alone`)
and a parenthesised implication binds tighter than a surrounding `and`
(`test_arrow_rewriting_respects_parentheses_and_precedence`). Chained equivalence is refused as
ambiguous rather than associated silently. Everything not in the table raises
`UnsupportedConstructError`; nothing is skipped.

**Statements** (`execute_statements`, used for `sut.logic()` rule blocks) accept assignment to a
single name, and `if`/`else`. A bare expression statement is refused explicitly — it asserts nothing
to the interpreter and would look like an assertion to a solver
(`test_bare_expression_rules_are_refused_by_both_sides`). Everything else is refused.

### The agreement obligation

`engines/proved.py` encodes the same constructs into Z3. That is a second implementation of one
language, and their agreement is a soundness obligation, not an implementation detail: if the
encoder models a statement the interpreter drops, or the two disagree on an operator, the solver
proves a property about a program nobody wrote and it is reported `proved`.

Three things hold the two sides together:

1. **Both sides refuse the same constructs.** A construct one side cannot model is refused by both,
   not skipped by either (`test_bare_expression_rules_are_refused_by_both_sides`,
   `test_nested_and_augmented_statements_are_modelled_or_refused_by_both_sides`).
2. **Both sides give the same answer on operators where Python and Z3 differ by default.** `/` is
   true division on both (`test_division_is_true_division_on_both_sides`); `%` follows Python's
   floor semantics for a negative divisor, where Z3's `mod` is non-negative
   (`test_modulo_follows_python_semantics_for_any_divisor`).
3. **Every proof is cross-checked at runtime.** Before any verdict is read off the solver, the Z3
   encoding is run against the rulelang interpreter on the witness the solver chose for the
   premises. A disagreement is reported not evaluated
   (`test_encoding_disagreeing_with_the_interpreter_is_not_a_proof`).

**The gap, stated plainly:** point 3 checks *one* witness, and points 1–2 check named constructs. No
test establishes that the two implementations agree on every input, and none establishes that their
accepted construct sets are equal as sets. The runtime cross-check is what catches a divergence
before it is reported as a proof; it is not a proof of equivalence, and `engines/proved.py` says so
in its own module docstring.

---

## 3. Soundness, one engine at a time

### `record` — `engines/record.py`

> **If the record engine reports `satisfied` at strength `observed`, then:** for every record in the
> trace it was given, every signal named in `requires` carried a present value, in the `_is_present`
> sense of §1. The domain is exactly those records.

*What it does not tell you.* Nothing about the correctness, truthfulness or usefulness of those
values — presence is not correctness. A reason field containing `"n/a"` is present. Nothing about
decisions outside the supplied trace; the evidence summary says so in the result itself
(`test_observed_verdict_states_what_it_does_not_cover`). Nothing about `req.spec`, which this engine
does not read (§2). And the trace is a sample chosen by whoever produced it.

> **If it reports `violated` at strength `observed`, then:** at least one record in the trace carried
> no present value for at least one required signal, and the result names which signals and which
> record indices (`test_record_engine_violated_on_blank_field`,
> `test_a_declared_signal_absent_from_the_trace_is_a_violation`).

An empty trace is `inconclusive` with `strength=None` — not evaluated, never satisfied. Having
observed zero decisions is not evidence that a requirement holds
(`test_an_empty_trace_is_not_evidence`).

### `observed` — `engines/observed.py`

> **If the observed engine reports `satisfied` at strength `observed`, then:** the rtamt discrete-time
> STL monitor for `req.spec` returned non-negative robustness at every time step of the trace it was
> given, where step *t* is the record at position *t* (`test_temporal_satisfied`).

*What it does not tell you.* Nothing about any execution of the system that is not in that trace.
"Held for every step we monitored" is a statement about a finite, supplied sequence. Nothing about
wall-clock time: the monitor's time axis is the record index, so a bound reads as a count of
decisions. And the flag/magnitude reading of §2 is a modelling choice — a pack author who writes
`x >= 0.5` meaning a threshold on a measured quantity gets a presence test.

> **If it reports `violated` at strength `observed`, then:** robustness went negative at at least one
> step, and the result names those step indices and carries the offending records
> (`test_temporal_violated_returns_offending_segment`).

Not evaluated, never satisfied, when: the trace is shorter than two records, because a discrete-time
monitor cannot read a sampling period off one sample
(`test_trace_too_short_names_the_trace_not_the_formula`); rtamt cannot parse the formula
(`test_unexpressible_formula_reports_not_evaluated`); or any record carries no finite real number for
a variable the formula treats as a magnitude (`test_quantitative_bound_needs_a_measurement`).

### `probed` — `engines/probed.py`

This is the rung for a system that exposes `decide()` but no `logic()`: there is nothing to reason
over, so the engine searches.

> **If the probed engine reports `satisfied` at strength `probed`, then:** the engine replayed the
> *N* inputs its budget names through the system's own `decide()`, and every one of them that
> produced a decision satisfied `req.spec` under the rulelang interpreter. The budget states *N*, the
> seed, the strategy, the per-field input space it varied, and how many inputs produced no decision
> at all (`test_no_counterexample_in_budget_is_probed_and_every_rendering_carries_the_budget`).

*The domain, exactly.* `plan_inputs` replays the recorded decisions first, unmodified, then perturbs
a randomly chosen recorded decision by replacing one or two fields with values drawn from that
field's candidate pool: the values the trace shows for that field, the numeric literals of the
property, and their immediate neighbours. A field whose values are of a kind the engine cannot vary
is left out of the space entirely, and the budget's `input_space` names the fields that were in it,
so what was held fixed is readable. The plan is a deterministic function of `(req.spec, records,
trials, seed)` and nothing else, so a reported budget can be re-derived
(`test_the_same_seed_searches_the_same_space`), and the inputs the budget counts are the inputs the
system was actually run on (`test_the_engine_replays_exactly_the_planned_inputs`).

*What it does not tell you.* Nothing about any input outside that plan — which is the entire
distance between this rung and `proved`. `proved` says *for every input admitted by the constraints*;
`probed` says *for every input we replayed, and here is the list*. A property can hold across 200
replayed inputs and fail on the 201st, and no rendering of a probed verdict may present it otherwise
(`test_probed_never_rounds_up_to_proved`). It also tells you nothing about inputs the system refused
to decide: those are counted in the budget, not read as passes
(`test_an_input_the_system_cannot_decide_is_counted_not_read_as_a_pass`).

> **If it reports `violated` at strength `probed`, then:** one replayed input produced a decision
> failing `req.spec`, and that same input, replayed a second time through `decide()`, failed again.
> The result carries the input and the decision (`test_a_genuine_counterexample_is_reported_violated_with_the_input`).

A candidate that does not reproduce is a defect in the search, not a finding about the system, and is
reported not evaluated (`test_a_counterexample_that_does_not_reproduce_is_not_evaluated`). So are: a
system exposing no `decide()` (`test_a_system_without_decide_is_not_evaluated_never_satisfied`), a
trace with nothing to perturb around (`test_an_empty_trace_gives_the_search_nothing_to_probe_around`),
a non-positive trial budget (`test_nonpositive_trial_budget_is_not_confused_with_an_empty_trace`), and
a property this engine cannot express (`test_the_complete_property_must_be_expressible_and_boolean`).

### `proved` — `engines/proved.py`

> **If the proved engine reports `satisfied` at strength `proved`, then:** Z3 found the conjunction of
> the encoded rules, the declared constraints and the *negation* of `req.spec` unsatisfiable — and
> before that verdict was read, the premises alone were checked satisfiable, and the encoding was
> checked against the rulelang interpreter on the model the solver produced for them
> (`test_property_holds_for_all_inputs_proved`).

The quantifier is over **all** valuations of the free inputs admitted by the declared constraints, at
the declared sorts. That is the strongest thing this tool says.

*What it does not tell you — the assumptions, including the uncomfortable ones.*

- **It is a claim about the logic the system exposed through `logic()`, not about the deployed
  artifact**, unless the two are the same thing. reasonsmith cannot check that they are. When a
  counterexample is found and the system exposes no `decide()`, the verification is run against the
  declared logic through the reference interpreter, and the evidence summary says exactly that rather
  than implying the system itself was run
  (`test_counterexample_replayed_on_declared_logic_says_so`).
- **`real` is exact rational arithmetic to the solver and IEEE-754 float64 to the system.** A proof
  touching a real carries `REAL_ARITHMETIC_LIMIT` on the result that makes the claim. This is not
  decoration: `t = a + b; d = t - b` proves `d == a` and the system returns `0.10000000000000003` for
  `a=0.1, b=0.2` (`test_a_proof_over_reals_says_it_is_a_proof_over_the_rationals`).
- **The encoding-versus-interpreter agreement is checked on one witness**, per §2.
- **A declared sort is a description of the system, not a licence to narrow the inputs.** An encoding
  that could only be satisfied by restricting the input domain is refused
  (`test_declared_sorts_never_become_hidden_input_constraints`).

Reported not evaluated, never `proved` or `satisfied`: a solver result of `unknown` or a timeout
(`test_solver_timeout_reported_not_evaluated`); premises no input can satisfy, since `unsat` from a
vacuous model proves every property and its negation alike
(`test_unsatisfiable_premises_are_not_a_proof`); logic or a property using a construct the encoding
does not model (`test_unsupported_construct_reported_not_evaluated`); rules undefined on the witness
the solver chose (`test_rules_undefined_on_the_witness_are_named_as_such`); a disagreement between
encoding and interpreter (`test_encoding_disagreeing_with_the_interpreter_is_not_a_proof`); a system
exposing no logic at all (`test_system_without_logic_reported_not_evaluated`); and a counterexample
that does not reproduce (`test_counterexample_verification_failure_reported_not_evaluated`,
`test_unverified_counterexample_is_not_rendered_as_a_violation`).

> **If it reports `violated` at strength `proved`, then:** Z3 produced a counterexample input, and
> executing that input reproduced the violation — against the system's own `decide()` where one
> exists, otherwise against the declared logic, and the summary names which
> (`test_property_fails_with_verified_counterexample`).

### The assumption all four share

None of these engines defends against a system that is adversarial toward its own audit. The probed
engine states the boundary and this document does not invent a second version of it — from
`engines/probed.py`:

> Replay inputs are isolated against accidental mutation by the system under test. This does not
> defend against a system that deliberately subverts copying: a system that lies to its auditor
> cannot be audited by that auditor, and reasonsmith does not claim otherwise.

The isolation against *accidental* mutation is real and tested
(`test_nested_mutation_cannot_change_the_verification_input_or_witness`,
`test_uncloneable_probe_input_is_not_evaluated`). The defence against a deliberate one is not claimed.

Read across all four engines, the same shape holds: a declared capability set is taken at its word, a
trace is taken as given, and exposed logic is taken as describing the system. reasonsmith checks
what a system says against what a specification asks. It does not check whether the system was
honest.

---

## 4. The lattice

`unattainable < observed < probed < proved`, a strict total order
(`test_strength_lattice_ordering`, and `test_semantics_doc_states_the_lattice_the_code_defines`
holds this sentence to the order the code defines). Comparison against anything that is not a
`Strength` is refused rather than coerced (`test_strength_comparison_rejects_foreign_types`).

**What a comparison means.** `a < b` says the evidence at *b* was reached by a method that quantifies
over strictly more than the method at *a*:

- `unattainable` — the system cannot produce the required signals at all, so no method reaches it.
- `observed` — the property held over a trace the system supplied.
- `probed` — the property held over inputs the auditor generated and the system was run on.
- `proved` — the property holds over every input the constraints admit.

**What a comparison does not mean.** It is not a confidence score, and it does not rank how much a
reader should believe anything. A `proved` verdict over logic that has nothing to do with the
deployed system is worth less than an `observed` verdict over a year of production decisions; the
lattice cannot see that, because it ranks *how the conclusion was reached* and not *what it was
reached about*. Strength is also not comparable across requirements as a quality measure: a duty that
can only be discharged by a record check is not a weaker duty, and it can never rise above
`observed`.

The weakest-link direction is what the code composes on: `min_strength` exists, and combining
verdicts propagates the worst case, with an empty collection giving `inconclusive` rather than a
vacuous `satisfied` (`test_verdict_combination`, `test_combining_no_verdicts_is_not_satisfied`).

### Four outcomes that must never collapse

`not applicable`, `unattainable`, `not evaluated` and `violated` are four distinct report categories
(`test_the_four_unresolved_outcomes_are_four_distinct_report_categories`), every result lands in
exactly one, and the counts reconcile against the total rather than merely summing to something
plausible (`test_counts_reconcile_against_both_totals`). They differ in what a reader should do next:

| Outcome | What happened | What to do next |
|---|---|---|
| **not applicable** | The duty is limited to a regulatory class, and the system was not declared to be in it — either no class was declared at all, or a different one was. Nothing about the system was checked. reasonsmith never infers the class. | Declare the class and re-run, or establish that the duty genuinely does not reach the system. Read the declared-scope line first: an undeclared system is neither placed in scope nor cleared. |
| **unattainable** | The signals the duty needs are outside the system's capability set. Computed as a set difference, *without executing the system*. | Change the system. No amount of testing discharges this one — that is what "as built" means. |
| **not evaluated** | The duty reaches the system, the system can emit the signals, and no engine here established anything: an empty trace, an unparseable formula, a solver timeout, an unmodelled construct. `strength=None`, which is deliberately not a rung on the lattice. | Fix the evidence or the specification and re-run. This is a gap in the audit, not a finding about the system. |
| **violated** | An engine produced a witness: a record, a trace step, or an input that fails the property. | Fix the system. This is the only outcome that fails a `check` run. |

Collapsing any two of them loses that instruction. "Unattainable" read as "violated" sends someone to
fix a system that is behaving as designed; "not evaluated" read as "satisfied" is the single overclaim
this tool exists to prevent; "not applicable" read as "satisfied" clears a duty nobody checked.

The operational consequence is in the exit code: only a violation exits non-zero. Unattainable
(`test_cli_exits_zero_when_findings_are_unattainable`), not applicable
(`test_cli_exits_zero_when_every_requirement_is_not_applicable`) and not evaluated are findings to
read in the report, not breaches; a violation exits 2 (`test_cli_exits_nonzero_on_a_violation`).

The unattainable analysis is computed without running the system, and a whole-pack run over an
all-unattainable pack reads no decisions at all (`test_unattainable_analysis_no_execution`,
`test_check_conformance_never_executes_a_system_it_cannot_check`).

---

## 5. The limits, in one place

`reasonsmith.report.LIMITS` is the authoritative statement and it travels on every emitted report, in
every rendering. This document does not restate it — read it there, and note in particular that it
covers both ways a requirement becomes not applicable
(`test_limits_cover_both_ways_a_requirement_becomes_not_applicable`).

Three things it says that bear repeating as the boundary of this whole document:

- reasonsmith does not determine whether a legal duty is discharged. It assesses capability
  information and trace evidence against formal specifications.
- reasonsmith does not infer a system's regulatory class. An undeclared system is neither placed in
  scope nor cleared of a class-limited duty (`test_the_two_scope_gates_never_disagree`, and a
  misspelled class is refused rather than read as out-of-scope,
  `test_a_scope_outside_the_vocabulary_is_refused`).
- reasonsmith certifies nothing. A report is a record of what was checked and how, carrying its own
  limits, and it carries no narrative it did not measure
  (`test_report_for_an_arbitrary_system_carries_no_narrative_it_did_not_measure`).

---

## 6. Claim-to-test map

| Claim | Test |
|---|---|
| `record satisfied` ⇒ every required signal present in every record of the supplied trace | `test_record_engine_satisfied` |
| A record verdict is a claim about the trace and says so | `test_observed_verdict_states_what_it_does_not_cover` |
| A record duty's `spec` string is never evaluated | `test_the_record_engine_reads_requires_not_spec` |
| An absent or blank signal in an observed record is a violation, naming it | `test_record_engine_violated_on_blank_field`, `test_a_declared_signal_absent_from_the_trace_is_a_violation` |
| Presence means non-empty, not merely keyed | `test_a_present_but_empty_signal_does_not_count_as_evidence`, `test_a_falsy_but_real_signal_value_counts` |
| An empty trace is not evaluated, never satisfied | `test_an_empty_trace_is_not_evidence` |
| `observed satisfied` ⇒ non-negative STL robustness at every step of the supplied trace | `test_temporal_satisfied` |
| A temporal violation names the record positions that breached | `test_temporal_violated_returns_offending_segment` |
| A trace too short to monitor is not evaluated, and the trace is blamed, not the formula | `test_trace_too_short_names_the_trace_not_the_formula` |
| A formula rtamt cannot parse is not evaluated | `test_unexpressible_formula_reports_not_evaluated` |
| A magnitude bound over an unmeasured signal is not evaluated, never scored | `test_quantitative_bound_needs_a_measurement`, `test_non_finite_flag_counts_as_absent` |
| `probed satisfied` ⇒ no counterexample among the replayed inputs, and every rendering carries the budget | `test_no_counterexample_in_budget_is_probed_and_every_rendering_carries_the_budget` |
| A probed result cannot exist without its budget | `test_a_probed_result_cannot_be_constructed_without_its_budget` |
| The probe plan is re-derivable from its seed | `test_the_same_seed_searches_the_same_space` |
| The budget counts the inputs the system was actually run on | `test_the_engine_replays_exactly_the_planned_inputs` |
| Probed never rounds up to proved, in any count, headline or rendering | `test_probed_never_rounds_up_to_proved` |
| An input the system refuses to decide is counted, not read as a pass | `test_an_input_the_system_cannot_decide_is_counted_not_read_as_a_pass` |
| `probed violated` ⇒ the counterexample reproduced on a second replay | `test_a_genuine_counterexample_is_reported_violated_with_the_input` |
| A counterexample that does not reproduce is not evaluated, never violated | `test_a_counterexample_that_does_not_reproduce_is_not_evaluated` |
| No `decide()`, no trace, no budget, or an inexpressible property ⇒ not evaluated | `test_a_system_without_decide_is_not_evaluated_never_satisfied`, `test_an_empty_trace_gives_the_search_nothing_to_probe_around`, `test_nonpositive_trial_budget_is_not_confused_with_an_empty_trace`, `test_the_complete_property_must_be_expressible_and_boolean` |
| Replay inputs are isolated against accidental mutation | `test_nested_mutation_cannot_change_the_verification_input_or_witness`, `test_uncloneable_probe_input_is_not_evaluated` |
| `proved satisfied` ⇒ negated property unsat, over all inputs the constraints admit | `test_property_holds_for_all_inputs_proved` |
| Vacuous premises are not a proof | `test_unsatisfiable_premises_are_not_a_proof` |
| Solver `unknown` or timeout is not evaluated | `test_solver_timeout_reported_not_evaluated` |
| An unmodelled construct is not evaluated, and pack text is never executed | `test_unsupported_construct_reported_not_evaluated`, `test_pack_text_is_never_executed_as_python` |
| A proof is cross-checked against the reference interpreter before it is read | `test_encoding_disagreeing_with_the_interpreter_is_not_a_proof`, `test_rules_undefined_on_the_witness_are_named_as_such` |
| Encoder and interpreter refuse the same constructs and agree on `/` and `%` | `test_bare_expression_rules_are_refused_by_both_sides`, `test_nested_and_augmented_statements_are_modelled_or_refused_by_both_sides`, `test_division_is_true_division_on_both_sides`, `test_modulo_follows_python_semantics_for_any_divisor` |
| Arrow rewriting preserves the property | `test_arrow_rewriting_respects_parentheses_and_precedence`, `test_arrow_rewriting_leaves_string_literals_alone` |
| A proof over reals names the rational/float64 gap | `test_a_proof_over_reals_says_it_is_a_proof_over_the_rationals` |
| A declared sort never becomes a hidden input constraint | `test_declared_sorts_never_become_hidden_input_constraints` |
| A system exposing no logic is not evaluated | `test_system_without_logic_reported_not_evaluated` |
| `proved violated` ⇒ the counterexample reproduced, and the summary names what against | `test_property_fails_with_verified_counterexample`, `test_counterexample_replayed_on_declared_logic_says_so` |
| An unverified counterexample is not rendered as a violation | `test_counterexample_verification_failure_reported_not_evaluated`, `test_unverified_counterexample_is_not_rendered_as_a_violation` |
| The lattice is a strict total order, and this document states the order the code defines | `test_strength_lattice_ordering`, `test_semantics_doc_states_the_lattice_the_code_defines` |
| A strength does not compare against foreign types | `test_strength_comparison_rejects_foreign_types` |
| Combining zero verdicts is inconclusive, and combination propagates the worst case | `test_combining_no_verdicts_is_not_satisfied`, `test_verdict_combination` |
| The four unresolved outcomes are four distinct categories, and every result lands in exactly one | `test_the_four_unresolved_outcomes_are_four_distinct_report_categories`, `test_counts_reconcile_against_both_totals` |
| Unattainable and violated are visually distinct in the report | `test_html_distinguishes_unattainable_from_violated` |
| Only a violation exits non-zero | `test_cli_exits_nonzero_on_a_violation`, `test_cli_exits_zero_when_findings_are_unattainable`, `test_cli_exits_zero_when_every_requirement_is_not_applicable` |
| The unattainable analysis never executes the system | `test_unattainable_analysis_no_execution`, `test_check_conformance_never_executes_a_system_it_cannot_check` |
| A result cannot claim more than its evidence, and a raw string cannot slip past the guards | `test_result_cannot_claim_more_than_its_evidence`, `test_a_string_verdict_or_strength_is_parsed_not_trusted` |
| A capability set is signal names and nothing else | `test_base_sut_rejects_a_bare_capability_string`, `test_base_sut_rejects_a_capability_map`, `test_unattainable_analysis_rejects_a_capability_map` |
| A trace-derived capability set does not speak for the system | `test_unattainable_from_a_trace_does_not_speak_for_the_system`, `test_declared_capabilities_word_the_finding_as_about_the_system` |
| A malformed trace names the system that produced it | `test_a_trace_of_the_wrong_shape_names_the_system` |
| A pack's requirement fields are exact and non-blank | `test_loader_rejects_missing_field`, `test_loader_rejects_an_unknown_field`, `test_loader_rejects_blank_and_duplicate_fields`, `test_requirement_needs_at_least_one_signal` |
| The regulatory class is never inferred, and a misspelling is refused rather than read as out-of-scope | `test_the_two_scope_gates_never_disagree`, `test_a_scope_outside_the_vocabulary_is_refused`, `test_limits_cover_both_ways_a_requirement_becomes_not_applicable` |
| A report carries no narrative it did not measure | `test_report_for_an_arbitrary_system_carries_no_narrative_it_did_not_measure` |
| This document is linked, and every test it names exists | `test_semantics_doc_is_linked_from_the_readmes`, `test_every_test_named_in_the_semantics_doc_exists` |
