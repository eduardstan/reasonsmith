# What a reasonsmith verdict means

This document states what follows from a reasonsmith verdict, and under which assumptions. It is
written for a reader who wants to check the claims rather than accept them: every soundness claim
below names a test that fails if the claim becomes false, and §6 collects that mapping in one
table. `tests/test_docs_semantics.py` holds this document to it — a test named here that does not
exist in the suite fails the build.

Where this document and the code disagree, the code is right and this document has a defect.

---

## 1. The objects

**Requirement** — `spec.py`, `Requirement`. A frozen record of one duty, carrying exactly the eleven
fields of `REQUIREMENT_FIELDS` and no others: `id`, `source_document`, `article_clause`,
`verbatim_text`, `stakeholder`, `formalism`, `spec`, `rationale`, `requires`, `binding`, `scope`.

`spec` is the property, written in the one language of §2. `rationale` is the English explanation of
the duty; it is carried on the requirement and in `to_dict()`, and **no verdict is derived from its
wording** — it is the field prose belongs in, which is why `spec` no longer has to hold any.
`formalism` names which *fragment* of that one language the property belongs to, and the pack loader
parses `spec`, classifies it and refuses a declared fragment that is not the one it found
(`test_the_loader_refuses_a_spec_that_is_not_in_the_declared_fragment`). It does **not**, by itself,
decide which engine answers the duty — see §3.5. `requires` is the non-empty set of signal names a
system must be able to emit for the duty to be checkable at all, and every signal the property reads
*unconditionally* must appear in it (`test_the_loader_refuses_a_spec_reading_an_ungated_signal`). A
signal read only inside a disjunction is exempt, and the exemption is not a convenience: `requires`
is a conjunction, so gating one branch of an either/or clause reports a system that lawfully took
the other branch `unattainable` without running it — which is a wrong answer arrived at by a
different route than a wrong verdict
(`test_the_loader_lets_a_disjunct_go_ungated_but_not_the_rest_of_the_property`,
`test_neither_branch_signal_gates_the_content_duty`). The exemption reaches an either/or and
nothing wider: every branch of the disjunction must be settled by `present()` atoms alone, and a
name occurring in every branch is needed whichever one settles the formula, so it stays gated
(`test_a_disjunction_of_magnitudes_gates_its_signals`,
`test_a_name_every_disjunct_reads_is_still_gated`). The cost is that an ungated branch signal is
never asked for by the unattainable analysis, so a system declaring neither branch is judged on its
trace and can be reported `violated` there
(`test_a_creditor_giving_neither_branch_is_violated`).
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
outside the protocol because replay is optional. Three plain instance attributes outside that
protocol are also semantic inputs. `evaluate_requirement` and `check_conformance` in `report.py`
select `system_scope`, falling back to `declared_scope`, to decide applicability
(`test_declared_scope_attribute_is_the_applicability_fallback`,
`test_system_scope_precedes_a_conflicting_declared_scope`,
`test_the_two_scope_gates_never_disagree`). `_unattainable_result` reads `capability_basis` to
decide whether a missing signal describes the system as built or only the supplied trace
(`test_unattainable_from_a_trace_does_not_speak_for_the_system`,
`test_declared_capabilities_word_the_finding_as_about_the_system`).

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

There is **one** property language, in `rulelang.py`, and `formalism` names which fragment of it a
requirement's `spec` belongs to. The three fragments are decided by the shape of the formula, not by
the word a pack author typed: `classify_fragment` returns `temporal` when the formula uses a
temporal operator, `record` when it is a conjunction of `present(signal)` atoms and nothing else,
and `logical` for every other well-formed property of a single decision record. The loader demands
an **exact** match against the declared `formalism` — a presence conjunction is also a well-formed
`logical` property, and a lenient check would let one be declared `logical` and silently lose the
record engine's per-signal diagnostics (`test_the_loader_refuses_a_spec_that_is_not_in_the_declared_fragment`).

Text that is not in the language at all — prose such as `"Record check"`, or `"not a property !@#$"`
— is a load error naming what was found, not a spec that quietly goes unread
(`test_the_loader_refuses_prose_where_a_property_belongs`). A well-formed expression that is
definitely not Boolean is also refused at load time: that includes a quoted prose value and a bare
arithmetic expression (`test_the_loader_refuses_quoted_prose_as_a_non_boolean_property`,
`test_the_loader_refuses_arithmetic_as_a_non_boolean_property`). A bare signal remains valid
because its kind is unknown until a system supplies a value and it may be Boolean.

**What this replaced, and why it mattered.** `spec` used to mean two unrelated things. For
`temporal` and `logical` it was a formula the engine evaluated; for `record` it was English prose
that no engine read, so a reader met prose and an STL formula in the same field three lines apart,
and `formalism` was doing two jobs under one name — saying what the property *is*, and deciding
which engine was allowed to discharge it. Fifteen of the eighteen duties shipping then were
labelled `record` and could therefore never exceed `observed`, whatever the system under test
exposed. The English
moved to `rationale`, the property became executable, and engine selection became the search in
§3.5.

### `present(signal)` — the presence atom

`present(x)` asks whether a decision record carries a value for `x`, in the `_is_present` sense of
§1: not missing, not `None`, not a blank string, not an empty collection. It is the one atom every
engine answers, and they answer it the same way because there is one definition
(`rulelang.is_present`) rather than one per engine. Its argument is a signal name, never an
expression: there is no such question about a computed value.

### `temporal` — Signal Temporal Logic, monitored by rtamt

`ObservedEngine` renders the property in rtamt's syntax with `to_stl` and hands that to
`rtamt.StlDiscreteTimeSpecification`. Each `present(x)` becomes a comparison over its own synthetic
flag, whose time series is 1.0 exactly where `rulelang.is_present` says the record carries `x` and
0.0 otherwise. The synthetic flag is never a magnitude. An explicit `x >= 0.5` remains the separate
flag predicate described below; it is not rewritten into presence. This makes `0` and `False`
present to both the temporal and record engines
(`test_temporal_presence_agrees_with_record_presence_for_falsy_values`). A formula rtamt cannot
parse is reported not evaluated rather than guessed at
(`test_unexpressible_formula_reports_not_evaluated`).

The temporal fragment is narrower than rtamt's own syntax on purpose: `TEMPORAL_OPERATORS` holds the
prefix call forms a Python parser accepts, so rtamt's infix `until` and `since` are not in this
language. A pack needing one is a finding to record here, not a reason to widen the language until
it fits — widening it to accommodate one stubborn duty is how a property language becomes an untyped
string again. No shipped duty needs one.

Two other degenerate shapes are refused at this same shared parse boundary. A Boolean literal may
be a comparison operand in a non-temporal property (`approved == True`) but may not stand alone as a
Boolean atom, including under `always`, `not`, `and`, `or` or implication
(`test_the_loader_refuses_boolean_constants_as_atoms`,
`test_a_boolean_constant_remains_valid_as_a_comparison_operand`). The temporal fragment also
refuses `==` and `!=` comparisons against Boolean constants in either operand order, because rtamt
cannot render their Boolean role without misreading them as measured magnitudes. The load error
names the bare atom spelling to use instead, such as `always(approved)` or
`always(not approved)`; a requirement constructed directly is not evaluated
(`test_the_loader_refuses_temporal_boolean_constant_comparisons`,
`test_a_direct_temporal_boolean_comparison_is_not_evaluated`,
`test_a_bare_boolean_atom_is_monitored_for_true_and_false_traces`). A signal may not occupy both a
bare Boolean role and a measured-magnitude role in one property; that contradictory role assignment
is a load error, and a directly constructed requirement is not evaluated
(`test_the_loader_refuses_conflicting_boolean_and_magnitude_roles`,
`test_conflicting_boolean_and_magnitude_roles_are_not_evaluated`).

Two things about the encoding are this project's own and are load-bearing:

- **Time is the record index.** The monitor is fed `time = 0..n-1`, one step per record, in the order
  the trace supplied them. A temporal bound counts decisions, not seconds. A violation at step *t*
  is the record at position *t* (`test_temporal_violated_returns_offending_segment`).
- **Flags and magnitudes are read off the formula, never off the trace.** `var >= 0.5` (or
  `0.5 <= var`) is the one comparison pattern treated as a flag instead of requiring a measured
  magnitude. For such a variable, Boolean values become 1.0/0.0, any other present non-numeric
  value becomes 1.0, an absent or non-finite value becomes 0.0, and a finite numeric value remains
  that number. A signal used directly as a bare Boolean atom must carry `True` or `False` in every
  record; true becomes 1.0 and false becomes -1.0 so false has negative robustness and is a breach
  (`test_a_false_bare_boolean_atom_is_violated`). If the trace does not establish that Boolean
  kind, the property is not evaluated (`test_a_bare_boolean_atom_without_an_established_kind_is_not_evaluated`).
  This truth reading is distinct from presence: `present(x)` is true when a record carries `False`,
  while the bare atom `x` is false
  (`test_presence_and_bare_boolean_atoms_keep_distinct_false_semantics`). Every other comparison —
  any other constant, 0.5 under any other operator, or a variable against a variable — makes both
  sides magnitudes, and a record that carries no finite real number for a magnitude makes the whole
  requirement not evaluated rather than scored 0.0
  (`test_quantitative_bound_needs_a_measurement`, `test_non_finite_flag_counts_as_absent`,
  `test_temporal_satisfied`,
  `test_ecoa_thirty_day_notice_violated_by_a_late_notification`,
  `test_ecoa_unaccepted_counteroffer_gets_the_ninety_day_deadline`).

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
| Calls | `implies(a, b)` / `Implies(a, b)`, `abs(x)`, `min(a, b)`, `max(a, b)`, `present(signal)` — no keyword arguments |
| Temporal | `always`, `eventually`, `once`, `historically`, `next`, `prev`, `rise`, `fall`, each over one operand |
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

Three tested checks hold the two sides together:

1. **Named statement cases are checked on both sides.** Bare expression statements are refused by
   both; nested `if` statements are modelled by both; augmented assignment is refused by the
   interpreter and produces no solver verdict
   (`test_bare_expression_rules_are_refused_by_both_sides`,
   `test_nested_and_augmented_statements_are_modelled_or_refused_by_both_sides`).
2. **Named operator differences are checked to agree.** `/` is true division on both
   (`test_division_is_true_division_on_both_sides`); `%` follows Python's floor semantics for a
   negative divisor, where Z3's `mod` is non-negative
   (`test_modulo_follows_python_semantics_for_any_divisor`).
3. **Every proof is cross-checked at runtime on one witness.** Before any verdict is read off the
   solver, the Z3 encoding is run against the rulelang interpreter on the witness the solver chose
   for the premises. A disagreement on that witness is reported not evaluated
   (`test_encoding_disagreeing_with_the_interpreter_is_not_a_proof`).

**The gap, stated plainly:** point 3 checks *one* witness, and points 1–2 check named constructs. No
test establishes that the two implementations agree on every input, and none establishes that their
accepted construct sets are equal as sets. The runtime cross-check is what catches a divergence
on that witness before it is reported as a proof. Agreement there does not establish agreement on
another admitted valuation and is not a proof of equivalence; `engines/proved.py` says so in its own
module docstring.

---

## 3. Soundness, one engine at a time

### `record` — `engines/record.py`

> **If the record engine reports `satisfied` at strength `observed`, then:** for every record in the
> trace it was given, every signal named by a `present()` atom of `req.spec` carried a present
> value, in the `_is_present` sense of §1. The domain is exactly those records.

The signals looked for are the property's, not the `requires` list's. `requires` is the capability
gate that decides whether the duty is attainable at all; the formula is what is checked
(`test_the_record_engine_evaluates_its_spec`). The two agree on every conjunct in the shipped packs
because the loader refuses a property reading an unconditional signal `requires` does not name, and
they deliberately part company on a disjunction — `ecoa_reg_b_1002_9_a_2_written_statement` reads
two branch signals its `requires` does not gate (§2, `requires`). They are different questions and a
verdict answers only the second.

The conjunction is walked directly rather than scored by the rtamt monitor, and that is a soundness
choice about *diagnostics* rather than about the verdict: robustness is one number for the whole
formula and cannot say which conjunct failed, so routing presence through it to make two engines
look alike would cost exactly the naming this engine exists for.

A `spec` this engine cannot walk as a conjunction of presence atoms is reported not evaluated, never
answered from `requires` as though the property were absent
(`test_the_record_engine_evaluates_its_spec`).

*What it does not tell you.* Nothing about the correctness, truthfulness or usefulness of those
values — presence is not correctness. A reason field containing `"n/a"` is present. Nothing about
decisions outside the supplied trace; the evidence summary says so in the result itself
(`test_observed_verdict_states_what_it_does_not_cover`). And the trace is a sample chosen by whoever
produced it.

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

The two-record floor is what holding an either/or costs `ecoa_reg_b_1002_9_a_2_written_statement`.
A disjunction is not a conjunction of `present()` atoms, so the duty is quantified over the trace
rather than checked record by record, and a log holding exactly one decision is reported not
evaluated on it — not satisfied, not violated — and leaves the binding headline counts
(`test_a_single_decision_trace_is_not_evaluated_never_satisfied`). A one-record log was enough
while it was a `record` duty; the pack description and `docs/refinement.md` carry the same limit.

### The first shipped duty that reads a declared approximation error — `gdpr_recital71_error_risk_minimised`

This is the first shipped duty whose verdict comes from a value a system declares about its own
approximation error. It is interpretive (`binding = false`): GDPR Recital 71 asks that "the risk of
errors is minimised", and a recital creates no obligation of its own. It runs on the observed
engine, so everything said about `observed` above applies unchanged; what follows is what this duty
adds.

> **If it reports `satisfied` at strength `observed`, then:** in every record of the supplied trace,
> the deviation the system declared for that decision (`scope_statements_declared_deviation`) was no
> larger than the margin it declared between that decision and its own threshold
> (`artifact_logs_decision_margin`)
> (`test_a_declared_deviation_below_the_decision_margin_is_satisfied`,
> `test_a_declared_deviation_exactly_equal_to_the_margin_is_reported_satisfied`).

*What it does not tell you.* Nothing about whether the system computes what it claims to compute.
The deviation is a self-declaration and no engine here verifies it: a system that under-reports its
own error is not detected, and a system honest enough to report a large one is the only kind this
duty can flag. Nothing about decisions outside the trace. And nothing about the law — the bound is
the system's own decision margin, not a figure Recital 71 states, and no number in this duty comes
from the regulation (`test_the_deviation_duty_is_interpretive_and_not_class_limited`).

Nor does `satisfied` exclude a decision that turns on an exact boundary tie. Where deviation and
margin are equal, robustness is zero: rtamt's quantitative semantics score `<` and `<=` alike at
that boundary, and the observed engine treats only negative robustness as a breach. In the
threshold-facing case the claimed oracle value sits exactly on the decision threshold, but whether
the decision would have differed depends on the system's own tie-break, which this record does not
carry. This duty therefore reports an exact tie satisfied and does not detect a decision that turns
on one. Closing that gap would require signed evidence and a strict-boundary reading the shared
observed engine does not have; no engine was changed here
(`test_a_declared_deviation_exactly_equal_to_the_margin_is_reported_satisfied`).

> **If it reports `violated` at strength `observed`, then:** at least one record declared a deviation
> larger than that decision's own margin, and the result names the step. On the system's own numbers
> that decision could have gone the other way had the system computed what it claims
> (`test_a_declared_deviation_that_could_have_moved_a_decision_is_violated`).

Silence is not compliance. A system that declares no deviation is `unattainable` on that signal, and
one whose record carries anything but a finite number where the deviation belongs is not evaluated
(§2, magnitudes). Neither is ever satisfied
(`test_an_undeclared_deviation_is_unattainable_never_satisfied`,
`test_an_unparseable_deviation_is_not_evaluated_never_satisfied`).

### `probed` — `engines/probed.py`

This is the rung for a system that exposes `decide()` but no `logic()`: there is nothing to reason
over, so the engine searches.

> **If the probed engine reports `satisfied` at strength `probed`, then:** the engine replayed *N*
> planned inputs through the system's own `decide()`. Every input for which `decide()`,
> conversion to a decision record, and property evaluation all completed satisfied `req.spec` under
> the rulelang interpreter. The budget records *N*, the seed, the strategy, per-field candidate-value
> counts, and how many inputs errored during one of those operations
> (`test_no_counterexample_in_budget_is_probed_and_every_rendering_carries_the_budget`,
> `test_an_input_the_system_cannot_decide_is_counted_not_read_as_a_pass`,
> `test_an_input_whose_property_cannot_be_evaluated_is_counted_not_read_as_a_pass`).

*The domain, exactly.* `plan_inputs` offers recorded decisions in supplied order and unmodified,
deduplicates identical records, and stops when the plan reaches `trials`; later recorded decisions
are therefore omitted when the cap is reached
(`test_probe_plan_deduplicates_seed_records_and_obeys_trial_cap`). If capacity remains, it chooses a
recorded decision and replaces one or two fields with values from per-field candidate pools. A field
with any Boolean observation gets `{True, False}`. A field whose observations are all numeric gets,
for every observed value *v*, `{v, v+1, v-1, -v, 0, v*2}`, and for every numeric literal *L* in the
property, `{L, L+1, L-1}`. A field whose observations are all strings gets the observed strings plus
`""`. Every other field is excluded from the varied space and remains as it was in the selected
record (`test_probe_candidate_pools_and_budget_counts_are_exact`). The budget's `input_space` maps
each field eligible for variation to its candidate count; it does not enumerate inputs. Given the
same `req.spec`, records, trials, and recorded seed, the plan is re-derived
(`test_the_same_seed_searches_the_same_space`), and the inputs the budget counts are the inputs the
system was actually run on (`test_the_engine_replays_exactly_the_planned_inputs`).

*What it does not tell you.* Nothing about any input outside that plan — which is the entire
distance between this rung and `proved`. `proved` says *for every input admitted by the constraints*;
`probed` says *for every planned input whose decision record and property evaluation completed*.
A property can hold across 200 replayed inputs and fail on the 201st, and no rendering of a probed
verdict may present it otherwise (`test_probed_never_rounds_up_to_proved`). It also tells you nothing
about inputs for which `decide()` or property evaluation raised: both are aggregated into the
budget's `inputs_errored` count and skipped, not read as passes
(`test_an_input_the_system_cannot_decide_is_counted_not_read_as_a_pass`,
`test_an_input_whose_property_cannot_be_evaluated_is_counted_not_read_as_a_pass`).

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

## 3.5. Which engine answers a duty

`report._engine_ladder` collects every engine that could discharge the requirement and
`evaluate_requirement` takes the strongest evidence any of them produced. Two things decide the
list, and the requirement supplies only one of them:

- **The fragment** says what kind of property this is. `record` and `logical` are `STATE_FRAGMENTS`
  — properties of a single decision record — so an engine that reasons about one decision at a time
  can discharge them. `temporal` is not.
- **The system's exposed surface** says what can be reasoned over. A non-`None` `logic()` admits
  `ProvedEngine`; a callable `decide()` admits `ProbedEngine`; a trace admits `RecordEngine` for a
  presence property and `ObservedEngine` for a temporal one.

So the same presence property is `observed` against a trace and `proved` against exposed `logic()`
(`test_a_record_duty_reaches_proved_when_the_system_exposes_its_logic`), and `probed` against a
system that can only be re-run (`test_a_record_duty_reaches_probed_when_the_system_can_only_be_re_run`).
Which rung a duty reaches is a fact about the system under test, not about which word a pack author
typed. It was the second of those before this section existed, which is substantially why
`docs/findings-nesyarena.md` reports zero results at `probed` and zero at `proved`.

**The ladder searches for evidence, not for an engine.** An engine that came back with
`strength=None` established nothing, so the search continues to the next rung down and the duty
lands on the strongest rung that actually produced evidence
(`test_a_record_duty_the_solver_cannot_reach_falls_to_the_engine_that_can`). When no engine produced
any, the strongest engine's not-evaluated result is what is reported, so the reader is told which
interface was missing (`test_system_without_logic_reported_not_evaluated`) — except for a proof
rung that never had any logic to reason over, which says nothing about the evaluation and yields
to a lower rung's account of the evidence the system did supply
(`test_an_empty_trace_is_not_evidence`). An engine whose
interface *raises* is treated the same way as one that returns no evidence: a `logic()` that
throws establishes nothing, so the failure is named in a `strength=None` result and the duty
still lands on the strongest rung that did produce evidence
(`test_a_record_duty_survives_a_system_whose_logic_raises`,
`test_a_logical_duty_names_the_logic_failure_rather_than_propagating_it`). Selecting the rungs
never executes the system: both optional rungs are read off the callable surface
(`test_building_the_ladder_never_executes_the_system`). A malformed *trace* is deliberately not
absorbed this way — that is the system's own decision log coming back the wrong shape, and it
still raises and names the system (`test_a_trace_of_the_wrong_shape_names_the_system`).

**A temporal duty never rises above `observed`** (`test_a_temporal_duty_never_rises_above_observed`).
The solver and the replay search both reason about one decision at a time and have nothing to say
about a formula quantified over a trace. There is no temporal engine above `observed` in this build,
and a rung for a claim no engine established would be the overclaim this package exists to refuse.

**What selection does not change.** Nothing here alters the lattice or what any verdict means; §3 is
unchanged by it. A `proved` verdict is still a claim about the logic the system exposed, and an
`observed` one still a claim about the trace it supplied. **The consequence worth stating plainly:**
where a system's exposed logic and its trace disagree — the rules prove a reason is always written,
and a logged decision carries none — the ladder reports the `proved` verdict and the trace is never
read for that duty. That is not a contradiction the tool resolves; it is a system misdescribing
itself to its auditor, which §3 already says reasonsmith does not detect.

### When the presence atom cannot be proved

`ProvedEngine` refuses `present(x)` unless the declared rules definitely assign `x`: every path
through the rules must write it. Each refusal drops the duty to the strongest engine that *can*
answer rather than losing its verdict:

- **`x` is a free input of the rules** — read, never written. Proving a property about the solver's
  free constant would say the record carries `x` because this encoding declared a constant called
  `x`, which is a fact about the encoding
  (`test_a_record_duty_the_solver_cannot_reach_falls_to_the_engine_that_can`).
- **Only some branches assign `x`.** An assignment in an `if` without an assignment on the other
  path does not establish that every decision carries it
  (`test_presence_is_not_proved_when_only_one_branch_assigns_the_signal`).

The signal's sort is not itself a reason for refusal. In particular, **a string is not refused**:
`present()` over a string encodes as
  "not in the language of blanks" over `BLANK_CHARACTERS`, which is exactly the set `str.strip()`
  removes, so the solver and `is_present` agree on every string rather than approximately
  (`test_the_solvers_blank_string_is_pythons_blank_string`). A system whose rules can write a blank
  reason is therefore proved to *violate* the duty, not proved to satisfy it
  (`test_a_presence_proof_refuses_the_blank_string_the_solver_could_choose`).

---

## 4. The lattice

`unattainable < observed < probed < proved`, a strict total order
(`test_strength_lattice_ordering`, and `test_semantics_doc_states_the_lattice_the_code_defines`
holds this sentence to the order the code defines). Comparison against anything that is not a
`Strength` is refused rather than coerced (`test_strength_comparison_rejects_foreign_types`).

**What a comparison means.** `a < b` orders the evidence-gathering method recorded on the result:

- `unattainable` — capability analysis stopped evaluation before an engine ran.
- `observed` — a record or temporal conclusion was reached from the supplied trace.
- `probed` — a logical conclusion was reached by bounded replay through `decide()`.
- `proved` — a logical conclusion was reached by solver reasoning over the valuations admitted by
  the declared constraints.

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
| **unattainable — declared basis** | The signals the duty needs are outside the system's declared capability set. Computed as a set difference, *without executing the system*. | Change the system. |
| **unattainable — trace basis** | No record in the supplied trace carries the required signals; the adapter derived its capability set from that trace. This does not establish that the system cannot emit them. | Supply a longer trace or an explicit capability declaration. Change the system only if further evidence confirms the signals are absent. |
| **not evaluated** | The duty reaches the system, the system can emit the signals, and no engine here established anything: an empty trace, an unparseable formula, a solver timeout, an unmodelled construct. `strength=None`, which is deliberately not a rung on the lattice. | Fix the evidence or the specification and re-run. This is a gap in the audit, not a finding about the system. |
| **violated** | An engine produced a witness: a record, a trace step, or an input that fails the property. | Fix the system. Of these four report outcomes, this is the only one that fails a `check` run. |

Collapsing any two of them loses that instruction. "Unattainable" read as "violated" sends someone to
fix a system that is behaving as designed; "not evaluated" read as "satisfied" is the single overclaim
this tool exists to prevent; "not applicable" read as "satisfied" clears a duty nobody checked.

The operational consequence is in the exit code: among completed reports, only a violation exits
non-zero. Unattainable
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

Two consequences of that report text, followed by a separate package-level terminology distinction:

- reasonsmith does not determine whether a legal duty is discharged. It assesses capability
  information and trace evidence against formal specifications
  (`test_report_limits_exclude_legal_determination_and_scope_inference`).
- reasonsmith does not infer a system's regulatory class. An undeclared system is neither placed in
  scope nor cleared of a class-limited duty
  (`test_report_limits_exclude_legal_determination_and_scope_inference`,
  `test_the_two_scope_gates_never_disagree`). A misspelled class is refused rather than read as
  out-of-scope (`test_a_scope_outside_the_vocabulary_is_refused`).
- Separately, the package emits a **reason-deletion certificate**, a measured artifact about which
  reasons an approximate engine dropped. It does not issue a **compliance certification**. The
  artifact detects a dropped reason and carries its separate limits
  (`test_a_perturbed_engine_that_drops_a_reason_fails`,
  `test_certificate_limits_exclude_compliance_certification`,
  `test_certificate_carries_its_limits`); a conformance report carries no narrative it did not
  measure (`test_report_for_an_arbitrary_system_carries_no_narrative_it_did_not_measure`).

---

## 6. Claim-to-test map

| Claim | Test |
|---|---|
| `record satisfied` ⇒ every required signal present in every record of the supplied trace | `test_record_engine_satisfied` |
| A record verdict is a claim about the trace and says so | `test_observed_verdict_states_what_it_does_not_cover` |
| A record duty is discharged by the property in its `spec`, not by its `requires` | `test_the_record_engine_evaluates_its_spec` |
| `record` and `temporal` route to their respective engine families | `test_record_and_temporal_formalisms_route_through_report` |
| `logical` routes to proved with exposed logic, probed with only `decide()`, and no evidence with neither | `test_property_holds_for_all_inputs_proved`, `test_an_opaque_system_reaches_probed_through_the_report`, `test_system_without_logic_reported_not_evaluated` |
| One property language: the loader classifies the fragment and refuses a mismatch, prose and definitely non-Boolean roots included | `test_the_loader_refuses_a_spec_that_is_not_in_the_declared_fragment`, `test_the_loader_refuses_prose_where_a_property_belongs`, `test_the_loader_refuses_quoted_prose_as_a_non_boolean_property`, `test_the_loader_refuses_arithmetic_as_a_non_boolean_property` |
| A signal the property reads unconditionally must be gated by `requires` | `test_the_loader_refuses_a_spec_reading_an_ungated_signal` |
| A branch of an either/or is not gated, so neither branch alone makes the duty unattainable | `test_the_loader_lets_a_disjunct_go_ungated_but_not_the_rest_of_the_property`, `test_neither_branch_signal_gates_the_content_duty` |
| The exemption reaches an either/or only: a disjunction over magnitudes gates its names, and a name every branch reads stays gated | `test_a_disjunction_of_magnitudes_gates_its_signals`, `test_a_name_every_disjunct_reads_is_still_gated` |
| Either lawful branch of 12 CFR 1002.9(a)(2) satisfies the content duty, and neither branch violates it | `test_a_creditor_giving_the_specific_reasons_is_satisfied`, `test_a_creditor_disclosing_the_right_to_request_reasons_is_satisfied`, `test_a_creditor_giving_neither_branch_is_violated` |
| Quantified over the trace, the 12 CFR 1002.9(a)(2) content duty is not evaluated on a single-decision log rather than satisfied | `test_a_single_decision_trace_is_not_evaluated_never_satisfied` |
| The same presence property is observed off a trace, probed against `decide()`, and proved against `logic()` | `test_a_record_duty_reaches_proved_when_the_system_exposes_its_logic`, `test_a_record_duty_reaches_probed_when_the_system_can_only_be_re_run` |
| The ladder takes the strongest evidence produced, not the strongest engine available | `test_a_record_duty_the_solver_cannot_reach_falls_to_the_engine_that_can` |
| An engine whose interface raises establishes nothing, and the duty still lands on the rung that answered | `test_a_record_duty_survives_a_system_whose_logic_raises`, `test_a_logical_duty_names_the_logic_failure_rather_than_propagating_it`, `test_a_raising_logic_is_attempted_once_per_evaluation` |
| Building the ladder reads the callable surface and never executes the system | `test_building_the_ladder_never_executes_the_system` |
| A malformed trace still raises and names the system | `test_a_trace_of_the_wrong_shape_names_the_system` |
| A presence proof requires the rules to assign the signal on every path | `test_a_record_duty_the_solver_cannot_reach_falls_to_the_engine_that_can`, `test_presence_is_not_proved_when_only_one_branch_assigns_the_signal` |
| A temporal duty never rises above observed | `test_a_temporal_duty_never_rises_above_observed` |
| The solver's blank string is Python's blank string, so a provable blank reason is a violation | `test_the_solvers_blank_string_is_pythons_blank_string`, `test_a_presence_proof_refuses_the_blank_string_the_solver_could_choose` |
| An absent or blank signal in an observed record is a violation, naming it | `test_record_engine_violated_on_blank_field`, `test_a_declared_signal_absent_from_the_trace_is_a_violation` |
| Presence means non-empty, not merely keyed, in every engine | `test_a_present_but_empty_signal_does_not_count_as_evidence`, `test_a_falsy_but_real_signal_value_counts`, `test_temporal_presence_agrees_with_record_presence_for_falsy_values` |
| An empty trace is not evaluated, never satisfied | `test_an_empty_trace_is_not_evidence` |
| `observed satisfied` ⇒ non-negative STL robustness at every step of the supplied trace | `test_temporal_satisfied` |
| A temporal violation names the record positions that breached | `test_temporal_violated_returns_offending_segment` |
| A trace too short to monitor is not evaluated, and the trace is blamed, not the formula | `test_trace_too_short_names_the_trace_not_the_formula` |
| A formula rtamt cannot parse is not evaluated | `test_unexpressible_formula_reports_not_evaluated` |
| Bare Boolean atoms use Boolean trace values, false has negative robustness, and unknown kinds are not evaluated | `test_a_false_bare_boolean_atom_is_violated`, `test_a_bare_boolean_atom_without_an_established_kind_is_not_evaluated` |
| Presence and Boolean truth remain distinct for a recorded `False` value | `test_presence_and_bare_boolean_atoms_keep_distinct_false_semantics`, `test_temporal_presence_agrees_with_record_presence_for_falsy_values` |
| Boolean literals are refused as atoms but remain valid comparison operands in state properties | `test_the_loader_refuses_boolean_constants_as_atoms`, `test_a_boolean_constant_remains_valid_as_a_comparison_operand`, `test_a_logical_boolean_constant_comparison_still_reaches_proved` |
| Temporal Boolean-constant comparisons are refused in favour of sound bare Boolean atoms | `test_the_loader_refuses_temporal_boolean_constant_comparisons`, `test_a_direct_temporal_boolean_comparison_is_not_evaluated`, `test_a_bare_boolean_atom_is_monitored_for_true_and_false_traces` |
| A signal cannot occupy bare-Boolean and measured-magnitude roles in one property | `test_the_loader_refuses_conflicting_boolean_and_magnitude_roles`, `test_conflicting_boolean_and_magnitude_roles_are_not_evaluated` |
| The formula selects flag versus magnitude treatment, and flag values follow the stated conversion | `test_non_finite_flag_counts_as_absent`, `test_temporal_satisfied`, `test_ecoa_thirty_day_notice_violated_by_a_late_notification`, `test_ecoa_unaccepted_counteroffer_gets_the_ninety_day_deadline`, `test_ecoa_accepted_counteroffer_keeps_the_thirty_day_deadline` |
| A magnitude bound over an unmeasured signal is not evaluated, never scored | `test_quantitative_bound_needs_a_measurement`, `test_non_finite_flag_counts_as_absent` |
| The Recital 71 error duty is satisfied only when every declared deviation is no larger than that decision's own margin, including the known exact-tie boundary | `test_a_declared_deviation_below_the_decision_margin_is_satisfied`, `test_a_declared_deviation_exactly_equal_to_the_margin_is_reported_satisfied` |
| A declared deviation larger than that margin violates it, naming the decision | `test_a_declared_deviation_that_could_have_moved_a_decision_is_violated` |
| An undeclared or unmeasured deviation is unattainable or not evaluated, never satisfied | `test_an_undeclared_deviation_is_unattainable_never_satisfied`, `test_an_unparseable_deviation_is_not_evaluated_never_satisfied` |
| The duty that reads a deviation is interpretive and not class-limited | `test_the_deviation_duty_is_interpretive_and_not_class_limited` |
| `probed satisfied` ⇒ no counterexample among the replayed inputs, and every rendering carries the budget | `test_no_counterexample_in_budget_is_probed_and_every_rendering_carries_the_budget` |
| A probed result cannot exist without its budget | `test_a_probed_result_cannot_be_constructed_without_its_budget` |
| The probe plan is re-derivable from its seed | `test_the_same_seed_searches_the_same_space` |
| Seed records are deduplicated in order and capped by `trials` | `test_probe_plan_deduplicates_seed_records_and_obeys_trial_cap` |
| Boolean, numeric and string candidate pools, excluded fields and budget counts follow the stated rules | `test_probe_candidate_pools_and_budget_counts_are_exact` |
| The budget counts the inputs the system was actually run on | `test_the_engine_replays_exactly_the_planned_inputs` |
| Probed never rounds up to proved, in any count, headline or rendering | `test_probed_never_rounds_up_to_proved` |
| An input whose `decide()` or property evaluation raises is counted, not read as a pass | `test_an_input_the_system_cannot_decide_is_counted_not_read_as_a_pass`, `test_an_input_whose_property_cannot_be_evaluated_is_counted_not_read_as_a_pass` |
| `probed violated` ⇒ the counterexample reproduced on a second replay | `test_a_genuine_counterexample_is_reported_violated_with_the_input` |
| A counterexample that does not reproduce is not evaluated, never violated | `test_a_counterexample_that_does_not_reproduce_is_not_evaluated` |
| No `decide()`, no trace, no budget, or an inexpressible property ⇒ not evaluated | `test_a_system_without_decide_is_not_evaluated_never_satisfied`, `test_an_empty_trace_gives_the_search_nothing_to_probe_around`, `test_nonpositive_trial_budget_is_not_confused_with_an_empty_trace`, `test_the_complete_property_must_be_expressible_and_boolean` |
| Replay inputs are isolated against accidental mutation | `test_nested_mutation_cannot_change_the_verification_input_or_witness`, `test_uncloneable_probe_input_is_not_evaluated` |
| `proved satisfied` ⇒ negated property unsat, over all inputs the constraints admit | `test_property_holds_for_all_inputs_proved` |
| Vacuous premises are not a proof | `test_unsatisfiable_premises_are_not_a_proof` |
| Solver `unknown` or timeout is not evaluated | `test_solver_timeout_reported_not_evaluated` |
| An unmodelled construct is not evaluated, and pack text is never executed | `test_unsupported_construct_reported_not_evaluated`, `test_pack_text_is_never_executed_as_python` |
| A proof is cross-checked against the reference interpreter on one premise witness before it is read | `test_encoding_disagreeing_with_the_interpreter_is_not_a_proof`, `test_rules_undefined_on_the_witness_are_named_as_such` |
| Named statement cases are modelled or refused on both sides, and `/` and `%` agree in the named cases | `test_bare_expression_rules_are_refused_by_both_sides`, `test_nested_and_augmented_statements_are_modelled_or_refused_by_both_sides`, `test_division_is_true_division_on_both_sides`, `test_modulo_follows_python_semantics_for_any_divisor` |
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
| Applicability prefers `system_scope`, falling back to `declared_scope` only when absent | `test_system_scope_precedes_a_conflicting_declared_scope`, `test_declared_scope_attribute_is_the_applicability_fallback`, `test_the_two_scope_gates_never_disagree` |
| Capability basis decides whether unattainability speaks about the system or its trace | `test_unattainable_from_a_trace_does_not_speak_for_the_system`, `test_declared_capabilities_word_the_finding_as_about_the_system` |
| A malformed trace names the system that produced it | `test_a_trace_of_the_wrong_shape_names_the_system` |
| A pack's requirement fields are exact and non-blank | `test_loader_rejects_missing_field`, `test_loader_rejects_an_unknown_field`, `test_loader_rejects_blank_and_duplicate_fields`, `test_requirement_needs_at_least_one_signal` |
| Report limits exclude legal-duty determination and regulatory-class inference | `test_report_limits_exclude_legal_determination_and_scope_inference`, `test_limits_cover_both_ways_a_requirement_becomes_not_applicable` |
| A misspelled regulatory class is refused rather than read as out-of-scope | `test_a_scope_outside_the_vocabulary_is_refused` |
| A reason-deletion certificate detects a dropped reason and excludes compliance certification beyond its measured input | `test_a_perturbed_engine_that_drops_a_reason_fails`, `test_certificate_limits_exclude_compliance_certification`, `test_certificate_carries_its_limits` |
| A report carries no narrative it did not measure | `test_report_for_an_arbitrary_system_carries_no_narrative_it_did_not_measure` |
| This document is linked, and every test it names exists | `test_semantics_doc_is_linked_from_the_readmes`, `test_every_test_named_in_the_semantics_doc_exists` |
