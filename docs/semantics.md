# What a reasonsmith verdict means

This document states what follows from a reasonsmith verdict, and under which assumptions. It is
written for a reader who wants to check the claims rather than accept them: every soundness claim
below names a test that fails if the claim becomes false, and §6 collects that mapping in one
table. `tests/test_docs_semantics.py` holds this document to it — a test named here that does not
exist in the suite fails the build.

Where this document and the code disagree, the code is right and this document has a defect.

---

## 1. The objects

**Requirement** — `spec.py`, `Requirement`. A frozen record of one duty, carrying exactly the twelve
fields of `REQUIREMENT_FIELDS` and no others: `id`, `source_document`, `article_clause`,
`verbatim_text`, `stakeholder`, `formalism`, `spec`, `rationale`, `requires`, `binding`, `scope`,
`domains`.

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
class from `REGULATORY_CLASSES`, or empty for a duty that is not class-limited. `domains` is the set
of decision domains the duty is about, from `DECISION_DOMAINS`, or empty for a duty about no
particular kind of decision; the two are separate axes and are gated separately (§4). Neither
vocabulary is guessed at, and only one of them belongs to a regulation: `REGULATORY_CLASSES` is the
EU AI Act's own, `DECISION_DOMAINS` is this repository's, which is a claim a pack using one has to
carry (`docs/authoring-packs.md`). A pack that omits a
field, adds one, or leaves one blank is refused at load time rather than loaded with a guess
(`test_loader_rejects_missing_field`, `test_loader_rejects_an_unknown_field`,
`test_loader_rejects_blank_and_duplicate_fields`, `test_requirement_needs_at_least_one_signal`).

**Pack** — `spec.py`, `Pack`. A named collection of requirements with source metadata. Duplicate
requirement ids are refused, because `get_requirement` returns the first match and the second would
be unreachable.

**System under test** — `sut.py`, `SystemUnderTest`. A protocol with three methods —
`capabilities()`, `decisions()`, `logic()` — and two optional methods deliberately outside it,
because neither capability is one a system must have: `decide(case)` for replay, and
`artifact(decision)` returning the inference a decision came from as an
`artifacts.InferenceArtifact` — or as the keyword arguments of `certificate.certify` for the one
family this package ships an adapter for — never a verdict, which would be the system grading its
own homework (§3, *certificate*). That artefact declares whether its inference is monotone, and an
artefact that declares nothing, declares no, or is contradicted by the probe is not measured at all
(§3, *The inference artefact*). Four plain instance attributes outside that
protocol are also semantic inputs. `evaluate_requirement` and `check_conformance` in `report.py`
select `system_scope`, falling back to `declared_scope`, to decide applicability
(`test_declared_scope_attribute_is_the_applicability_fallback`,
`test_system_scope_precedes_a_conflicting_declared_scope`,
`test_the_two_scope_gates_never_disagree`). They read `system_domains` the same way, with no second
spelling honoured, for the domain gate; an adapter that sets nothing is a system whose domain is
undeclared, which is a lawful state and not a broken adapter
(`test_an_undeclared_system_cannot_reach_satisfied_on_a_domain_limited_duty`,
`test_the_two_domain_gates_never_disagree`). `_unattainable_result` reads `capability_basis` to
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

**The definition lives in [`docs/language.md`](language.md)** — the grammar, checked against the
parser; the denotation `⟦·⟧_{M,A}`, a partial map from sets of traces to a declared algebra, of
which every engine below is an implementation; and the four implementations named as such, with
their differential tests as the conformance evidence. That document also reports four shapes on
which the trace-rung implementation and the definition disagree (`docs/language.md` §4). This
section says what the language *is* for a reader of a verdict; go there for what a formula *means*.

There is **one** property language, in `rulelang.py`, and `formalism` names which fragment of it a
requirement's `spec` belongs to. The four fragments are decided by the shape of the formula, not by
the word a pack author typed: `classify_fragment` returns `counterfactual` when the formula is the
one relational atom, `temporal` when it uses a temporal operator, `record` when it is a conjunction
of `present(signal)` atoms and nothing else, and `logical` for every other well-formed property of a
single decision record. `counterfactual` is asked first and is exclusive — the atom is the whole of
a spec or no part of one — because that fragment is the one thing on this page that no engine
reading a decision log may be handed, and classifying it into `logical` would hand it to one
(§3, *counterfactual*). The loader demands
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

### `contains(signal, "phrase")` — the phrase atom

`contains(x, "p")` asks whether the text a record carries for `x` carries `p`. Like `present()`,
its first argument is a signal name and never an expression, for the same reason: every engine has
to bind it to one field of one decision record. Its second argument is a **string literal and never
a name**, so the wording a duty forbids is fixed by the pack rather than supplied by the system
being audited. Anything else — an arity other than two, a computed haystack, a name where the
phrase belongs, an empty phrase, a non-ASCII phrase — is refused where it is written
(`test_a_malformed_contains_atom_is_refused_rather_than_guessed_at`).

**Why it exists.** Fifteen of the eighteen duties shipping before it were conjunctions of
`present()`, so the strongest claim available about an explanation duty was *"for every admitted
input the reason field is non-blank"* — which a reason string of `"n/a"` satisfies and
12 CFR 1002.9(b)(2) does not accept. The clause supplies its own negative constraint, naming two
statements that are insufficient, and this is the narrowest atom that expresses one.

**What it means, exactly.**

- **Comparison folds ASCII case and nothing else.** `fold_ascii_case` lowercases the twenty-six
  ASCII capitals and leaves every other character alone. `str.lower()` is not length-preserving over
  the whole of Unicode — `"İ".lower()` is two characters — and the Z3 encoding renders each phrase
  character as a regular language matching *exactly one* character, so a fold that is not
  one-to-one would make the solver and the interpreter disagree about the same string. A non-ASCII
  phrase is therefore refused at load time rather than compared under a fold only one side can
  perform (`test_the_fold_is_ascii_case_and_reaches_no_further`).
- **A record carrying nothing carries no phrase.** Where `_is_present` says the signal is absent,
  `contains()` is false. That is what lets an implication guarded by `present()` decide a duty that
  only bites where a statement was made (`test_a_record_carrying_no_statement_carries_no_phrase`).
- **A statement given in parts is read part by part.** A log recording reasons as a list of
  strings is recording a statement of reasons, and refusing to read it would report *not evaluated*
  because of how the log is shaped rather than because of what it says. The parts are searched
  separately and never joined, so a phrase cannot match across the seam between two reasons that
  never appeared together (`test_a_statement_given_in_parts_is_read_part_by_part`,
  `test_the_parts_of_a_statement_are_never_joined`).
- **Any other present value is refused, not read as carrying nothing.** A number or a mapping is
  not a statement, and answering `False` there would report a system satisfied on a field nothing
  read. The interpreter raises, and every engine that reads the atom — the trace monitor and the
  replay search alike — reports the whole requirement not evaluated, naming the signal, so the
  stronger rung is never the easier one to satisfy. That is the same discipline an unmeasured
  magnitude gets (`test_a_present_value_that_is_not_a_statement_is_refused`,
  `test_a_non_text_value_makes_the_duty_not_evaluated_never_satisfied`,
  `test_a_non_text_value_is_not_evaluated_on_every_rung`).
- **It is a substring test and claims to be nothing more.** It answers whether a phrase occurs. It
  does not model whether a statement is *specific*, does not paraphrase, and catches no wording but
  the one the pack names. A duty built on it can establish that a statement the clause itself calls
  insufficient was made; it cannot establish that any other statement is sufficient.

**The three encodings, and how they are held together.** `contains()` is evaluated in three places,
and a predicate meaning one thing to the monitor and another to the solver would report `proved`
about a property nobody wrote. The rulelang interpreter compares folded strings. rtamt cannot reason
about text at all, so — exactly as `present()` already does — the atom is evaluated in Python per
record and reaches the monitor as a synthetic flag, which is what keeps its meaning the one meaning
(`test_a_forbidden_phrase_in_the_trace_is_an_observed_violation`). That rewriting is textual, and a
call head a phrase merely quotes is skipped rather than rewritten
(`test_a_call_head_a_phrase_merely_quotes_is_not_rewritten`). Z3 encodes it as a bracketed regular
language, character by character, conjoined with the blankness language `present()` already uses —
a substring search alone would find a phrase of blanks in a string of blanks, where the interpreter
says the record carries nothing
(`test_the_solver_finds_no_phrase_in_a_string_the_record_does_not_carry`). A generated corpus,
blank haystacks included, checks that the solver's answer is the interpreter's
(`test_the_solvers_fold_is_the_interpreters_fold`) — the counterpart of what
`test_the_solvers_blank_string_is_pythons_blank_string` does for `present()`.

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

The temporal fragment is written in prefix call form, because this language parses through Python's
`ast`; rtamt writes its operators infix. For the one-operand operators of
`UNARY_TEMPORAL_OPERATORS` the two spellings coincide. For `until` and `since` they do not, and the
difference was for a long time the whole of why this language did not have them: rtamt has parsed
both all along. They are now `BINARY_TEMPORAL_OPERATORS`, written `until(left, right)` and
`since(left, right)`, held to the same arity check the one-operand operators get, classified into
the `temporal` fragment, and rendered back to rtamt's infix form by `engines/observed.to_stl`
(`test_the_binary_operators_are_temporal_operators_of_the_language`,
`test_a_binary_temporal_spec_classifies_as_temporal`,
`test_the_arity_check_reaches_the_binary_operators`,
`test_the_rendered_form_is_rtamt_infix_and_rtamt_monitors_it`). **That mapping is the whole of what
this package adds. No temporal semantics is implemented here**, and a second implementation of one
is the thing to refuse if it is ever proposed: the monitor this package already depends on owns
them, which is why the rendered text is handed to rtamt in a test rather than merely compared
against a string.

`until` was added on the evidence of a clause that needs it —
`ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out`, 12 CFR 1002.9(c)(2), whose obligation runs
from a notice of incompleteness and ends either when the applicant supplies the information or when
the designated period lapses (`test_the_shipped_incompleteness_duty_uses_until`). `since` was added
as its dual **without such a clause**: the retrieved corpus holds none, and the decision to add it
anyway was taken deliberately and is recorded as a reversal in `ROADMAP.md` §2. It is exercised by
`test_the_rendered_form_is_rtamt_infix_and_rtamt_monitors_it` for that reason — nothing else stands
between an operator no shipped duty uses and its rotting unrendered. The discipline the roadmap
states is unchanged for any operator after these two: a pack needing one is a finding to record
here first, not a reason to widen the language until it fits, because widening a property language
to accommodate one stubborn duty is how it becomes an untyped string again.

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

  That is now a **stated domain rather than a convention**. `sut.TimeDomain` names the clock a run
  counts on, `ObservedEngine.evaluate` takes it as a parameter defaulting to `sut.ORDINAL_DOMAIN`,
  and `TimeDomain.ticks` is the only place the `time` series comes from
  (`test_a_timeless_log_still_gets_the_record_index`,
  `test_passing_the_ordinal_domain_is_the_same_run_as_passing_nothing`). A decision record may
  carry its own clock under the reserved key `sut.TIME_DOMAIN_KEY` — a mapping of event kind to
  the timestamp that event happened at, which is how the three events 12 CFR 1002.9(a)(1) counts
  from are told apart (`test_a_record_may_carry_event_timestamps_and_event_kinds`,
  `test_the_three_events_the_clause_counts_from_are_distinguishable`).

  Three things about it are deliberate. A log carrying no such key states **no** clock and
  acquires none by being read (`test_a_log_without_event_times_states_no_time_domain`,
  `test_an_unread_or_empty_trace_states_no_time_domain`). A log that does carry one is still
  answered on the record index, so recording when things happened never costs a system a verdict
  it already had (`test_a_clocked_log_keeps_the_verdict_a_timeless_one_would_have_had`). And a
  duty asked for on any other domain is **not evaluated, never satisfied** — on a timeless log
  because there is no clock to count on, and on a clocked one because no metric or interval
  semantics reads those timestamps yet
  (`test_a_duty_needing_a_clock_is_not_evaluated_and_never_satisfied`,
  `test_the_refusal_says_which_of_the_two_gaps_it_hit`,
  `test_only_the_ordinal_domain_has_a_time_axis`). No shipped duty asks for one, and none can: the property language has no way to state
  a domain, so requiring one is a caller's act until an interval semantics gives a pack the words.
  What that leaves open is the gap `docs/refinement.md` records against
  `ecoa_reg_b_1002_9_a_1_timing_of_notice` — a deadline is still checked against a latency number
  the system computes about itself, and the recorded events are evidence nothing yet reads.

  The `--json` envelope carries `time_domain`: the clock the trace this run read *stated*,
  `"ordinal"` for every shipped example, and never a claim that a verdict was counted on
  timestamps (`test_the_report_states_the_clock_the_trace_stated`).
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
| Calls | `implies(a, b)` / `Implies(a, b)`, `Iff(a, b)`, `abs(x)`, `min(a, b)`, `max(a, b)`, `present(signal)`, `contains(signal, "phrase")` — no keyword arguments |
| Temporal | `always`, `eventually`, `once`, `historically`, `next`, `prev`, `rise`, `fall`, each over one operand |
| Arrows | `<=>` and `<->` rewrite to `Iff(...)`; `=>`, `->` and ` implies ` rewrite to `Implies(...)` |

Arrow rewriting is textual and happens before parsing. It respects parentheses and string literals,
so an arrow inside a quoted string is left alone (`test_arrow_rewriting_leaves_string_literals_alone`)
and a parenthesised implication binds tighter than a surrounding `and`
(`test_arrow_rewriting_respects_parentheses_and_precedence`). Chained equivalence is refused as
ambiguous rather than associated silently, while an implication chain is admitted
right-associatively, because `a -> b -> c` has a settled reading in every logic this package
touches and `a <=> b <=> c` does not
(`test_a_chained_equivalence_is_refused_as_ambiguous`,
`test_an_implication_chain_stays_admitted_right_associatively`).

Equivalence rewrites to a **call and never to `==`**. Over the Booleans the two are the same
function — `eval_expression` reads `Iff` as equality of truth values and
`test_the_interpreter_reads_equivalence_as_the_truth_table` holds it to the table, with
`test_the_solver_reads_equivalence_as_the_truth_table` holding the Z3 encoding to the same — so no
two-valued spec moved. Over a residuated lattice they are not: `==` is a crisp comparison of two
degrees, which is a threshold §9 refuses, and collapsing the connective textually before the parse
meant the graded fragment refused an equivalence naming a construct the author never wrote.
`implies` was spared only by being spelled as a call rather than as an arrow, which was an accident
of text substitution and not a decision. `test_the_rewriter_never_collapses_equivalence_to_a_comparison`
fails if the rewriter ever collapses it again. Everything not in the table raises
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
values — presence is not correctness. A reason field containing `"n/a"` is present, and a duty that
wants more than presence has to say so: `contains()` (§2) is how a clause's own words about what a
statement may not say get into a property, and 12 CFR 1002.9(b)(2) is the shipped duty that does it
(`test_the_property_does_not_decide_whether_any_other_statement_is_specific`). Nothing about
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
(`test_unexpressible_formula_reports_not_evaluated`); any record carries no finite real number for
a variable the formula treats as a magnitude (`test_quantitative_bound_needs_a_measurement`); or the
property is an implication whose antecedent scored below zero at every position, because a trace
that never reaches the trigger scores non-negative for every system alike
(`test_an_antecedent_false_at_every_position_is_not_evaluated_at_observed`, and §4 for the rule).

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
budget's `inputs_errored` count, and neither is ever read as a pass
(`test_an_input_the_system_cannot_decide_is_counted_not_read_as_a_pass`,
`test_an_input_whose_property_cannot_be_evaluated_is_counted_not_read_as_a_pass`). Since a
satisfaction needs complete evidence, a search in which *any* planned input raised is reported not
evaluated rather than satisfied over the part that answered
(`test_a_satisfaction_over_a_partly_unmeasurable_domain_is_not_a_satisfaction`). The inputs a system
raises on are not a random sample of the space — they are the band its author put outside what it
answers for — so satisfaction over the remainder is a claim about a domain the search chose after
seeing which parts refused it. This is asked on the satisfied path alone, and it costs an unaffected
system nothing: a system that errors on nothing earns the same verdict, strength and counts as
before (`test_a_system_that_errors_on_nothing_still_earns_its_satisfaction`). It is asked *before*
the unreachable-antecedent guard of §4, because where inputs raised, "the antecedent fired nowhere"
would be a claim about the measured part alone while the unmeasured part is exactly what might have
reached it. No summary, budget or rendering states a replay count larger than the number of inputs
the property was read over, and `inputs_errored` is surfaced wherever the budget is rendered, so the
counts a reader sees reconcile
(`test_no_summary_or_budget_line_states_more_replays_than_were_measured`). One refusal is
not an errored input: where a replayed decision records something that is not a statement for a
signal a `contains()` atom reads, the whole run is reported not evaluated rather than counted and
passed over — the same answer the observed engine gives for that shape off a trace, so the stronger
rung is never the easier one to satisfy (`test_a_non_text_value_is_not_evaluated_on_every_rung`).

> **If it reports `violated` at strength `probed`, then:** one replayed input produced a decision
> failing `req.spec`, and that same input, replayed a second time through `decide()`, failed again.
> The result carries the input and the decision (`test_a_genuine_counterexample_is_reported_violated_with_the_input`).

A candidate that does not reproduce is a defect in the search, not a finding about the system, and is
reported not evaluated (`test_a_counterexample_that_does_not_reproduce_is_not_evaluated`). So are: a
system exposing no `decide()` (`test_a_system_without_decide_is_not_evaluated_never_satisfied`), a
trace with nothing to perturb around (`test_an_empty_trace_gives_the_search_nothing_to_probe_around`),
a non-positive trial budget (`test_nonpositive_trial_budget_is_not_confused_with_an_empty_trace`), and
a property this engine cannot express (`test_the_complete_property_must_be_expressible_and_boolean`).
So is a search in which no replayed decision reached the property's antecedent: "no counterexample"
is worth what the search was, and a search whose trigger fired nowhere found none the way an empty
search does (`test_a_search_that_never_reached_the_antecedent_is_not_evaluated_at_probed`, §4).

### `certificate` — `engines/certificate.py`

The second engine at `probed`, and the only one whose evidence comes from *exact* inference. It
answers one duty — `ecoa_reg_b_1002_9_b_2_principal_reasons_complete`, whether the reasons a notice
states are all the reasons the decision's inference used — by running the reason-deletion
certificate of `certificate.py` over the artefact the system exposes through the optional
`artifact(decision)` hook, and grounding the one signal
`engines.certificate.DELETED_REASON_COUNT` with what the probes measured.

Its reason for existing is a defect, and the defect is worth stating plainly. `certificate.py`,
`conformance.py` and `drift.py` were reachable from no duty and no CLI verb. The two halves of this
package met in exactly one place — `demo.render_key_finding_html`, on decision `APP-1042` — and
there they disagreed: the Table 7 evidence record reports COMPLETE while the certificate reports
FAIL. So `reasonsmith check` reported the reason-giving duty **satisfied** on a decision this same
package proves has four of five legally owed reasons deleted. This engine is what closes that
(`test_the_demonstrations_own_decision_is_reported_violated`,
`test_form_completeness_and_reason_fidelity_are_now_separate_verdicts`).

> **If the certificate engine reports `satisfied` at strength `probed`, then:** for **every**
> decision the system exposed an artefact for, bounded proof enumeration to that artefact's own
> `exact_depth` found **at least one** reason — not one of them was left unmeasured — and every
> reason holding a fact no other reason uses was switched off alone
> and the system's own engine re-run on the perturbed interpretation. Every reason no such single
> deletion moved was then put to the joint search below, and no reason came back deleted from it
> either, so no reason was shown deleted, and the property held on that decision's record
> with the measured count in place. The budget records how many inferences were replayed, over how
> many decisions and how many switched-off reasons
> (`test_the_certificate_verdict_carries_its_probe_budget`,
> `test_an_engine_that_deletes_nothing_is_probed_and_never_proved`).

**A decision whose enumeration found no reason at all is covered by no verdict here.** The
antecedent above says *at least one* because the zero it would otherwise report is the absence of a
measurement, not a measurement of zero: with nothing enumerated, nothing is switched off,
`len(cert.deleted)` is zero, and a property reading
`engines.certificate.DELETED_REASON_COUNT` comes out clean without exact inference having
evaluated anything. The engine asks `conformance.measured(cert)` — this package's single predicate
for whether a certificate measured anything at all — rather than reading the count. That predicate
is the no-enumerated-reason clause of `Certificate.verdict`'s refusal to report `PASS`, and the
refusal exists because *a zero value gap on an un-enumerated query is not agreement*. The other
clause of that property, that `uncertified` also blocks `PASS`, is deliberately **not** acted on
here: an unseparable reason stays in the certified set and is reported as a caveat rather than
turning the verdict, which is the rule *the domain, exactly* below already states. Such a decision
is dropped from the certified set, counted in `decisions_without_an_enumerated_reason`, and named
in the summary. The artefact's own `exact_depth` is the usual cause, and lowering it needs no
intent — a misconfiguration, a program that grew a rule layer or a wrong query identifier produce
the same artefact. Weaker evidence must not buy a stronger verdict
(`test_a_decision_whose_reasons_were_never_enumerated_cannot_buy_satisfied`).

**A violation needs one witness; a satisfaction needs complete evidence.** So the two verdicts
treat such a decision differently, and the asymmetry is the one *`proved`, over a trace* below
already states for a trace: a satisfied verdict is universal over it, a violated one existential.
A breach measured on a decision that *was* enumerated is a witness and is still reported
**violated** at `probed`, naming the unmeasured decisions in its summary. A run that would
otherwise be satisfied is **not evaluated** the moment one certified decision went unmeasured,
naming the count and `engines.certificate.DELETED_REASON_COUNT` as unmeasured for them. The
lenient rule — satisfied over whatever remained — is defeated by the same move the refusal was
written to stop: declare `exact_depth=0` on every decision but one genuinely clean one. This is
not the `decisions_without_an_artifact` case and that precedent is not equivalent: a decision
without an artefact was never certified, while a decision whose artefact declared depth 0 was
certified and produced nothing, which is a stronger signal rather than a weaker one
(`test_a_decision_whose_reasons_were_never_enumerated_cannot_buy_satisfied`).

**A trace whose decisions never triggered the duty is not evaluated here either.** This duty is an
implication — 12 CFR 1002.9(b)(2) governs the statement of reasons a creditor gave, so a decision
that states none does not reach it — and a run where the antecedent held on no certified decision
is reported **not evaluated**, naming the antecedent and the certified decisions it was looked for
in, exactly as the other rungs of §4 (*A duty whose trigger never fired is not evaluated, at every
rung*) do — this engine's own row is the last one in that section's table. It is the same rule and
the same two functions, asked of this engine's domain
(`test_a_certified_trace_that_never_reached_the_antecedent_is_not_evaluated`), and a trace that does
reach the trigger is unaffected
(`test_a_certified_trace_that_does_reach_the_antecedent_still_reaches_probed`). The refusal is
placed after the unmeasured-subset one above, so a run that is both incomplete and untriggered is
reported as incomplete.

**A trace where only *some* decisions triggered the duty is satisfied about those, and the summary
says which.** This is the mixed trace, and it is the shape a real creditor's log has: one notice
states its reasons and another lawfully takes the 12 CFR 1002.9(a)(2)(ii) disclosure branch. The
verdict is `satisfied` and the duty is right to be silent about the second decision — (b)(2)
governs the statement of reasons a creditor gave, and there was none. What was not right was the
sentence: "Probed over 2 certified decision(s): … so no reason was shown deleted" describes a
measurement that found two decisions clean, on a run where the deletion probe measured four reasons
deleted behind one of them and the duty set it aside. So the satisfied summary now names how many
certified decisions the trigger reached, how many it did not, and how many reasons were measured
deleted behind those, and says in as many words that this verdict speaks to none of them. The
counts also travel in `details` as `decisions_whose_trigger_never_fired` and
`deleted_reasons_behind_an_untriggered_decision`
(`test_a_certified_decision_the_trigger_never_reached_is_named_in_the_satisfied_summary`). The
verdict itself is unchanged — what 12 CFR 1002.9(b)(2) reaches is a question about the duty and not
about the measurement, and no engine answers it by rewording a summary.

*The domain, exactly.* The decisions the system's trace holds **and** for which `artifact()`
returned an artefact rather than None. The enumeration is exact on *one* ground program and one
base interpretation — `certificate.LIMITS` says so in its own words — so this rung is `probed` and
never `proved`: nothing here establishes the property for a decision the system did not expose, or
for a reason lying past the `exact_depth` the artefact itself supplied. A reason whose every fact
is shared with another reason cannot be switched off alone, so its dependency is neither shown nor
assumed; it is counted as deleted by nothing and as live by nothing, and the result reports how
many there were.

*What it does not tell you.* Nothing about whether the reasons are *correct*, only that the system
used all of the ones exact inference found. Nothing about whether they are what a person would call
principal. And nothing about a system that lies about its own artefact — a system that returns a
program it did not run is a system misdescribing itself to its auditor, which *the assumption all
six share* below already covers.

**And — the sharpest of them — nothing about a system whose reasons can be *retracted*.** The probe
is one-directional: it only ever sets a fact's probability to zero, never raises one and never adds
a fact. So `deleted` means *the engine's answer did not depend on this reason under this
interpretation*, and on an engine that is not monotone in its inputs — a policy exception evaluated
after the underwriting rules fire, the ordinary shape of one — a reason the engine lawfully
*withdrew* is reported deleted exactly as a reason it dropped by defect is. That is a false
accusation against a system whose notice stated its reasons correctly, and this rung once drove a
`violated` verdict on it. **So the artefact declares whether its inference is monotone, and where
the definition does not apply the reasons are not measured at all.** That is the contract of the
next section, and it is what turned a disclosed limit into a refusal. **The retracted reason is
still counted deleted** wherever a certificate is produced at all — it was probed cleanly and the
measurement is right about the question it asked; the question is what is wrong, and moving it into
an inconclusive bucket would lose the signal that catches a false declaration
(`test_a_retracted_reason_is_reported_deleted_and_the_engine_is_flagged_non_monotone`).

*The reach of the probe, exactly.* **Every** fact of a reason that no other reason uses is switched
off, one at a time, and one whose deletion moves the engine settles the reason live. The budget
counts facts rather than reasons for that reason. Probing one such fact per reason — the first in
`repr` order — made coverage a function of what a system's fields are *called*: two systems alike
but for a field name got materially different probes, and whether a defeater was ever exercised was
decided alphabetically (`test_every_private_fact_of_a_reason_is_switched_off`). A fact shared with
another reason is still switched off by nobody in that pass, which is the `unseparable` case above.

**A reason no single deletion moves is not thereby deleted, and reading it so was this rung's
sharpest defect.** Two reasons that are *jointly* necessary and *individually* removable each leave
the engine's answer exactly where it was — the engine falls back from one to the other — so a probe
that only ever switches one fact off at a time reported both `deleted`, and this rung accused a
system of omitting two reasons its inference demonstrably used. That is unsoundness in the direction
that matters: a false accusation, from an instrument whose purpose is to make one only on measured
evidence. So the definition of a reason the answer depends on is now written down —
[`sufficient-reasons.md`](sufficient-reasons.md), which specialises Ignatiev, Narodytska and
Marques-Silva's abductive explanation and its contrastive dual to the deletions the artefact admits
— and measured. A **contrastive set** is a subset-minimal set of facts whose *joint* deletion moves
the engine; a fact is **relevant** iff it lies in one; a reason is `live` where a fact private to it
is relevant, and `deleted` only where **no** fact of it is
(`test_two_jointly_necessary_reasons_are_no_longer_reported_deleted`,
`test_the_reason_the_engine_really_ignores_is_still_reported_deleted`,
`test_the_duty_no_longer_reports_this_system_violated_on_the_two_it_uses`).

The declaration the section below turns on is what makes this available at all: upward closure of
"the engine moved" is what makes a subset-minimal moving set a contrastive set, what makes the
whole-space probe settle the lattice in one, and what lets the search skip the facts a single
deletion already answered. It is one premise and not two.

**`deleted` is universal over the contrastive sets, so it is claimed only where the enumeration
finished.** `live` is existential and one contrastive set establishes it. The enumeration is
exponential where the single-fact pass was linear, so it is bounded, and the bound travels: its
probes are counted into `trials` and whether it *finished* rides in `input_space`, under the
discipline `PROBE_BUDGET_FIELDS` already forces
(`test_the_joint_search_budget_travels_into_the_verdict`). A search that ran out of budget reports
its unresolved reasons `undetermined` — never `deleted` — so a shorter search names **fewer**
missing reasons than a complete one and never more. There is no setting of the budget at which this
rung accuses a system it would otherwise have cleared
(`test_a_partial_enumeration_degrades_to_undetermined_and_never_to_deleted`,
`test_no_budget_makes_this_instrument_name_more_missing_reasons_than_a_complete_search`).

**The three not-certified states are reported apart, because they are three different facts about
the evidence.** `unseparable` is a reason with no fact of its own to attribute a movement to;
`inconclusive` is a probe that moved exact inference not at all, so there was no signal to read;
`undetermined` is a reason the joint search did not resolve — its budget ran out, or the only
relevant fact it holds is shared with another reason and the dependence cannot be attributed to one
rather than the other. `uncertified` remains their union, because all three mean the same thing to a
verdict: counted deleted by nothing and live by nothing
(`test_the_three_not_certified_states_are_reported_apart`). What one bucket had been hiding is worth
naming: a reason called `deleted` off one private fact while a *shared* fact of it moves the engine
was an assertion that the answer did not depend on that reason, made where a deletion of one of its
facts moved the answer. `docs/example-output.md`'s drift window is the shipped instance and it now
reads `not certifiable`.

**A reason the probe cannot separate is never promoted to `deleted`, and the licence that says it
could is deliberately unused.** The definition in
[`sufficient-reasons.md`](sufficient-reasons.md) would, on its face, license the promotion: on a
*complete* enumeration, a reason that shares all of its facts with another reason was not needed —
and so can be reported as having failed to state it. The licence rests on completeness, and
completeness rests on the artefact's declaration that its inference is monotone — the declaration
*The inference artefact* below can refute and never confirm. An accusation minted from that
licence would therefore rest on an unverifiable self-report by the very system under audit, the one
premise this rung refuses everywhere else. So a reason the probe cannot separate — `unseparable`,
and with it `inconclusive` and `undetermined` — always stays uncertified, counted deleted by
nothing and live by nothing, and the pass only ever moves a reason *out* of `deleted`
(`test_a_reason_the_probe_cannot_separate_is_never_promoted_to_deleted`).

The refusal is a gate, not a wall, and the gate is named: an **independent** check that an
artefact's inference is monotone — independent meaning not derived from the artefact's own
declaration, however strongly that declaration were worded — would make the promotion available,
and only a check does. A stronger declaration is not the condition. No such check exists in this
tree, and the one fingerprint the probe can leave is a deletion that moves the answer *up*, whose
absence proves nothing (*The inference artefact* below; `test_the_absence_of_the_fingerprint_is_not_evidence_of_monotonicity`).
Until one exists, the licence in [`sufficient-reasons.md`](sufficient-reasons.md) stays deliberately
unused, and the reader who reaches for it is pointed back here from its §8.

> **If it reports `violated` at strength `probed`, then:** on at least one certified decision, the
> deletion probe showed the system's answer does not depend on a reason exact inference found. The
> result names the decision, the reasons, and the certificate's own attribution — which inference
> setting the loss is consistent with (`test_the_demonstrations_own_decision_is_reported_violated`).

**The count is measured, never read.** The engine builds the property's environment from the
decision record and then writes the measured count over whatever that record claimed for it, so a
system that logs its own zero is still judged on the measurement
(`test_a_logged_completeness_count_never_settles_the_duty`). A `reasons_are_complete` flag the
adapter sets about itself is the self-declaration this section refuses everywhere else, and this is
the one duty where it would have been easy.

**A system that cannot supply the oracle is `unattainable`, and is never returned to the presence
check.** `report._engine_ladder` gives this duty a ladder of exactly one rung, so no trace, no
replay and no proof over exposed rules can answer it in the weaker sibling duty's place — the
substitution is the whole defect, and it is the kind that comes back as a convenience. The result
names the signal that could not be measured and says why nothing weaker stands in for it
(`test_a_system_exposing_no_oracle_is_unattainable_and_names_the_signal`,
`test_the_adequacy_duty_is_never_downgraded_to_the_presence_check`).

One consequence of that gate is worth stating rather than discovering: an adapter whose
capabilities are derived from a trace can never declare `artifact_logs_deleted_reason_count`,
because no record carries it, so a plain decision log is reported unattainable by the capability
analysis with its generic wording — *a longer trace could show the system emitting these signals* —
which is true of the mechanism and unhelpful about this signal. A log that does carry the key
reaches this engine and gets the accurate message. Both end at `unattainable`; only the wording
differs.

Reported not evaluated, never satisfied: an empty trace, and a trace no decision of which the
system could open up (`test_a_trace_with_no_artifact_is_not_evaluated_never_satisfied`); an
`artifact()` that raises, returns something that is neither an `artifacts.InferenceArtifact` nor a
mapping, or returns arguments `certify`
refuses (`test_an_artifact_that_raises_or_is_the_wrong_shape_is_not_evaluated`); a property
that never reads the one signal this engine measures
(`test_the_engine_refuses_a_property_it_cannot_ground`); and a property this engine cannot decide
on a certified decision — a construct it does not interpret, or a second signal the record does not
carry — where the measurement was made and the verdict is still withheld
(`test_a_property_that_cannot_be_decided_on_a_record_is_not_evaluated`).

### The inference artefact, and the one premise it declares — `artifacts/`

`artifacts.InferenceArtifact` is this package's own answer to *what a reason can be measured from*:
what a reason-bearing artefact is, what it must expose for the deletion probe to measure reasons
from it, and whether its inference is **monotone in its facts**. A nesyarena ground program is one
family satisfying it (`artifacts/ground_program.py`) and a reason trace is the second
(`artifacts/reason_trace.py`); neither `artifacts/__init__.py` nor `certificate.py` imports a
representation, which is what makes each of them — and a knowledge graph, an extracted rule set or a
decision tree after them — an adapter rather than a second branch in the core
(`test_the_ground_program_family_is_one_adapter_and_the_protocol_names_no_representation`,
`test_the_protocol_is_satisfiable_without_a_ground_program`). The two shipped families do not report
at the same strength, and the paragraph below on `recounted` is why.

**Three states, and only the first is measured.** `engines/certificate.py` asks the declaration
before it certifies anything, and asks it again of the measurement afterwards; every refusal is
*not evaluated*, naming the reason, and none is ever `violated`, `satisfied`, or handed down to the
presence check that shares the clause.

| The artefact says | What happens |
|---|---|
| `monotone = True`, and no probe contradicts it | Measured, exactly as before (`test_a_declared_monotone_system_reaches_the_verdict_it_always_did`) |
| `monotone = False` | Not evaluated, naming defeat: a reason this system withdrew is not a reason its notice owed (`test_an_artefact_declaring_non_monotone_inference_is_not_evaluated_and_names_why`) |
| nothing at all | Not evaluated, naming the missing declaration (`test_an_artefact_that_declares_nothing_is_not_evaluated_rather_than_assumed_monotone`) |
| `monotone = True`, and a deletion moved the engine's answer *up* | Not evaluated, naming the measurement that refuted it (`test_a_declaration_the_probe_contradicts_is_refused_rather_than_trusted`) |

**What the declaration is worth, and what it is not.** It is a claim the system makes about itself,
of exactly the kind `capabilities()` and `logic()` already are, and *The assumption all seven share*
below is the standing answer for all of them: reasonsmith checks what a system says against what a
specification asks, and does not check whether the system was honest. One direction of check is new.
The declaration can be **refuted** by the measurement and never confirmed by it — a deletion that
moves the answer up is a fingerprint only a non-monotone inference leaves, so `monotone = True`
beside one is a declaration the run itself contradicts. Its *absence* proves nothing: a defeater
holding no fact of any enumerated reason is never switched off at all, which is the ordinary shape
of a policy exception, and both halves of that are measured
(`test_the_absence_of_the_fingerprint_is_not_evidence_of_monotonicity`). That is why the flag is
kept and why it is not enough on its own — the precedent is `counterfactual` below, which consults
`computes` and then cross-checks the encoding for the route the declaration cannot see.

**Undeclared is refused rather than read as monotone**, for the same reason that engine reports a
system declaring no directions *not evaluated*: a defeasible artefact and a monotone one produce the
same probe and the same count, so answering either would be answering both. Reading silence as
monotone would leave the declaration worth nothing for every system built before it existed, which
is every system this finding is about.

**Refusing is *not evaluated* and deliberately not *unattainable*.** §4's table is what decides it:
`unattainable` instructs a reader to change the system, and a creditor whose policy exceptions
retract reasons is behaving as designed and lawfully. The gap is in this tool — it has one
definition of a reason and that definition assumes monotonicity — so the honest category is the one
that says *fix the evidence or the specification*. A representation that can express defeat, and a
definition of a reason that survives it, is the work this refusal is standing in front of and is not
in this tree.

**One refused artefact refuses the run.** A verdict assembled from the decisions that happened to be
monotone is a verdict over a subset, which the completeness rule above already refuses for
`satisfied`; reporting `violated` off the remainder would also hide from the reader that the trace
held a decision this instrument cannot read
(`test_the_refusal_survives_a_whole_conformance_run_and_reaches_no_weaker_duty`).

**A family whose reasons are recounted rather than enumerated reports one rung lower, and the rung
is refused rather than trusted.** An LLM reason trace is not a proof object: a certificate over one
claims strictly less than a certificate over a ground program and must not report at the same
strength. This paragraph used to end there, saying the lattice could not express the difference and
that admitting a second family therefore needed a decision about the lattice before it needed an
adapter. That decision was made, and `Strength.RECOUNTED` is it.

*What the rung is.* `recounted` is the rung a verdict reaches when the reason set the deletion probe
ran over is one the **system recounted about its own inference**, rather than one enumerated from a
model encoding. The probe is the same probe: every reason's private facts are switched off in turn
and the system's own answer re-run. What differs is the reference set, and the difference is exactly
the one the literature calls **faithfulness**: a self-explanation may be plausible and yet not
describe the computation that produced the decision (A. Jacovi, Y. Goldberg, *Towards Faithfully
Interpretable NLP Systems: How Should We Define and Evaluate Faithfulness?*, ACL 2020, 4198–4205;
measured, as here, by erasure — J. DeYoung, S. Jain, N. F. Rajani, E. Lehman, C. Xiong, R. Socher,
B. C. Wallace, *ERASER: A Benchmark to Evaluate Rationalized NLP Models*, ACL 2020, 4443–4458; and
demonstrably failing on decoders — M. Turpin, J. Michael, E. Perez, S. R. Bowman, *Language Models
Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting*, NeurIPS
2023). A probe over a recounted set can show that the answer does not depend on a reason the system
recounted; it can never show that the set is all of them, which is what the `probed` rung's
enumeration establishes and is why that rung is above this one.

*Why a rung and not a basis.* §10's distinction decides it: evidence about a **different object** is
a different basis, evidence about the **same object, less deeply** is a different rung. A reason
trace makes a claim about the inference behind a decision, which is what the `artifact` basis is
already about. It is merely a claim nothing here can check as hard. So the `artifact` row gains a
member and no fifth basis exists
(`test_a_recounted_reason_set_reports_one_rung_below_an_enumerated_one`).

*Where the difference is enforced.* A family says which it is with `reasons_are_exact`, and
**silence claims the weaker rung** — the opposite default from `monotone` above, because here the
two answers are not both dangerous: guessing monotone accuses a compliant system, while guessing
recounted only understates one (`test_a_family_that_does_not_say_claims_the_weaker_rung`). One
certified decision whose set was recounted caps the whole run, the flag rides on the result
(`report.EXACT_REASON_SET_KEY`), and `RequirementResult.__post_init__` **refuses** a result that
claims above it — the same shape of structural refusal the probe budget and the plug-in ceiling
already carry (`test_a_recounted_reason_set_cannot_be_reported_at_the_enumerated_rung`). Nothing
here audits a family's claim that its enumeration is exact; what is new is that the claim has to be
made, and that not making it costs a rung.

**The second family, and what it does not reach.** `artifacts/reason_trace.py` is that adapter: a
set of reasons the system recounts for one decision, each tested by suppressing its facts and
re-running the system. It widens what can be certified from *systems that expose a ground program*
to *systems that recount their reasons and can be re-run with a fact withheld* — a language model
behind a `complete()` stub is one, and the whole of the coupling is one module, as
`test_the_protocol_is_satisfiable_without_a_ground_program` said it would be. It does **not** reach
a system that is only a log. The re-run is what makes the measurement independent of the rationale
it is measuring; without it, `exact_value` and `engine_value` are the same self-report and every
reason comes back live by construction. The auditors' blocker in the README — reach into systems
that are only logs — is therefore narrowed and not closed. No shipped example system uses this
family, so no shipped verdict moved.

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
(`test_unsatisfiable_premises_are_not_a_proof`); an implication whose antecedent no admissible input
satisfies, which is that same check one quantifier deeper — `unsat` on the negation is then a fact
about the trigger and not about the system
(`test_an_antecedent_no_admissible_input_reaches_is_not_evaluated_at_proved`, and §4 for the rule
and its cost); logic or a property using a construct the encoding
does not model (`test_unsupported_construct_reported_not_evaluated`); rules undefined on the witness
the solver chose (`test_rules_undefined_on_the_witness_are_named_as_such`); a disagreement between
encoding and interpreter (`test_encoding_disagreeing_with_the_interpreter_is_not_a_proof`); a system
exposing no logic at all (`test_the_proof_rung_still_names_the_missing_logic_when_it_is_asked_directly`); and a counterexample
that does not reproduce (`test_counterexample_verification_failure_reported_not_evaluated`,
`test_unverified_counterexample_is_not_rendered_as_a_violation`).

> **If it reports `violated` at strength `proved`, then:** Z3 produced a counterexample input, and
> executing that input reproduced the violation — against the system's own `decide()` where one
> exists, otherwise against the declared logic, and the summary names which
> (`test_property_fails_with_verified_counterexample`).

### `proved`, over a trace — `engines/temporal.py`

> **If the temporal proof engine reports `satisfied` at strength `proved`, then:** the duty was
> `always(f)` for some `f` free of temporal operators, and Z3 proved `f` over every valuation of the
> free inputs the declared constraints admit — the whole `proved` paragraph above, unchanged, about
> `f` (`test_only_always_reaches_the_temporal_proof_rung`).

This is the rung this document said did not exist. The argument is one reduction and no new
machinery. A conformance run reads a **finite** decision trace, which is why the semantics claimed
here is LTLf and not LTL: over a finite trace, `always(f)` holds exactly when `f` holds at every
position. Every position of every trace this system can emit is a decision its exposed `logic()`
produces from an input its own `constraints` admit. So a proof of `f` over that whole input space is
a proof of `always(f)` for every trace the system can emit — a strictly larger set than the one trace
this run read, which is what makes the rung `proved` rather than `observed`. `TRACE_SEMANTICS`
travels on every result the engine returns, so the set of traces a verdict is about is on the page
and not left to be inferred, the same discipline the probe budget is held to.

*What it does not tell you.*

- **The two verdicts are not mirror images, and the summary says so.** `satisfied` is universal and
  covers every trace the system can emit, this run's included. `violated` is existential: the solver
  found one admissible input whose decision breaches `f`, verified to reproduce, so *some* trace the
  system admits breaches the duty. That is a finding about the system as built and **not** a finding
  about the trace supplied here — a run whose log happens to contain no such decision is still
  reported violated (`test_a_temporal_violation_names_the_trace_it_is_and_is_not_about`).
- **`always` is the only operator that reduces**, and the operand must itself be a state property.
  `eventually(f)` asserts that some position *exists*, which is a fact about the trace a system
  emitted rather than about the decisions its logic admits, and no reasoning about one decision at a
  time establishes it; `always(eventually(f))` fails the same test one level down. Both stop at
  `observed` exactly as every temporal duty did before this engine existed
  (`test_only_always_reaches_the_temporal_proof_rung`,
  `test_a_nested_temporal_operator_does_not_reduce`).
- **Everything the `proved` engine cannot claim, this cannot claim**, because the verdict *is* that
  engine's verdict: `unknown`, a timeout, vacuous premises, an antecedent no admissible input
  reaches (`test_the_temporal_reduction_inherits_the_refusal`), an encoding that disagrees with the
  interpreter, or a counterexample that does not reproduce all yield not evaluated, and the duty
  falls back to the trace.
- **The empty trace is covered vacuously**, since `always(f)` is true of it. A satisfied verdict here
  is therefore not evidence that the system ever decided anything — the same caveat the
  `unattainable` and empty-trace rules carry elsewhere in this document.

### `counterfactual` — `engines/counterfactual.py`

> **If the counterfactual engine reports `satisfied` at strength `proved`, then:** the duty was
> `counterfactually_invariant(outcome, protected)`; the system's `logic()` declared `protected` an
> input it accepts and `outcome` a value it computes; the declared rules were encoded **twice**
> into one solver under two namespaces; every free input of the two copies was constrained equal
> except `protected`; the encoded pair was checked to admit at least one input at all; **each** copy
> of the encoding was checked to agree with the reference interpreter on that witness; and Z3 found
> `outcome@0 != outcome@1` unsatisfiable — so **no** pair of valuations the system's own
> `constraints` admit, differing in `protected` alone, produces two different values of `outcome`
> (`test_a_system_accepting_the_protected_variable_and_ignoring_it_is_satisfied`,
> `test_two_copies_of_one_rule_block_do_not_collide`).

This is the first relational property in this repository, and the first paragraph on this page
written over a *pair* of executions rather than over one. The six above say "the trace it was given"
or "the valuations the constraints admit"; this one says "the pairs". `PAIR_SEMANTICS` and
`TREATMENT_LIMIT` travel on every result the engine returns, so which set of pairs a verdict is
about, and what a fairness verdict from this tool is not, are on the page rather than left to be
inferred.

*What it does not tell you.*

- **It is a property of treatment and it says nothing about effects.** A proxy is invisible to it: a
  rule set that never reads the protected variable and decides by postcode is `satisfied` here, and
  correctly so under the property as written. Disparate impact — a fact about outcomes across a
  population — is not a property of any pair of decisions and is formalised nowhere in this
  repository. `TREATMENT_LIMIT` says this on every result, satisfied ones included, because that is
  where it matters.
- **A system with no notion of the variable is `unattainable` and never `satisfied`.** This is the
  distinction the whole duty turns on, and it is not available from the encoding alone: a system
  that accepts the protected variable and provably ignores it, and a system that has never heard of
  it, produce the *identical* encoding — in both the name is a free constant the outcome does not
  depend on, so the negation is `unsat` in both. What tells them apart is the `computes` direction
  declaration of §3.5, *When the magnitudes are not the system's own*: a name in neither `variables`
  nor `computes` is one the system has no notion of, and the duty is reported unattainable naming
  it. A system declaring no directions at all is reported *not evaluated*, because guessing would
  certify an unaware system as provably fair
  (`test_a_system_with_no_notion_of_the_protected_variable_is_unattainable`,
  `test_a_system_declaring_no_directions_is_not_evaluated`).
- **The claim is bounded by the constraints the system declared**, exactly as the `proved` paragraph
  above is. A system declaring a narrow input band is proved invariant over that band and over
  nothing else, and no engine here checks that the declared band is the deployed one.
- **Where the declaration admits no pair at all, the verdict is *not evaluated*.** This is the
  degenerate case of the bound above, and an `unsat` meaning "no pair exists" is not evidence of "no
  pair disagrees". Two roads reach it and the engine closes both before it reads the negation: a
  declaration that *pins* the protected variable — directly, or through a variable the encoding
  holds equal across the copies — so that no admissible pair differs in it at all
  (`test_constraints_pinning_the_protected_variable_are_not_a_proof`, where the replay rung refuses
  the same system); and declared *rules* that assign the protected name while `computes` omits it,
  so the encoding overwrites the input the intervention turns and the decision is reached from a
  value neither copy was free to differ in
  (`test_rules_assigning_the_protected_variable_are_not_a_proof`). The second is not a case the
  direction declaration can close, because it is a name the rules assign and the declaration does
  not claim; the check is on the encoding rather than on what was declared.
- **The two verdicts are not mirror images**, for the reason the temporal paragraph gives.
  `satisfied` is universal over every admitted pair. `violated` is existential: the solver named one
  admissible pair whose outcomes differ, and **both halves** of it were replayed against the system
  and seen to differ again, so *some* pair the system admits breaches the duty — a finding about the
  system as built, not about any decision it has taken
  (`test_the_witness_pair_is_replayed_on_both_halves`).
- **A protected variable the declaration does not type as an integer is *not evaluated*.** A
  prohibited basis is a category, and a category declared over a sort that is not the integers
  admits the values between the categories too. Over `real`, the replay rung's enumeration of a
  band running `0 <= basis <= 8` returned 0, 0.125, 0.25 and 0.5 — four points in the bottom
  sixteenth of it, none of them a category — and reported `satisfied` on a system that
  discriminates at category 2; the proof rung's witness pair, on the same declaration, may be a
  pair the system can never be given. Both rungs refuse it before they encode or enumerate
  anything, naming the variable and the sort it was declared as
  (`test_a_protected_variable_not_typed_as_an_integer_is_not_evaluated`), and the same system typed
  `int` reaches its verdict unchanged
  (`test_the_same_system_typed_int_still_reaches_its_earned_violation`). This is an authoring
  mistake refused rather than sampled, and it costs a duty answerable only where the variable table
  says what the codes are.
- **It reaches one variable and does not compose.** Moving two protected variables together is a
  different property; the atom is the whole of a spec or no part of one, so a conjunction, a
  negation or a temporal quantification over it is refused at load time rather than answered
  (`test_the_atom_is_the_whole_spec_or_no_part_of_one`).
- **Everything the `proved` engine cannot claim, this cannot claim**, because the rung is that
  encoding twice: `unknown`, a timeout, premises admitting no pair, a copy that disagrees with the
  interpreter, or a witness pair that does not reproduce all yield not evaluated.

> **If the paired-replay engine reports `satisfied` at strength `probed`, then:** for every decision
> in the trace and every admissible value of `protected` beyond the first, `decide()` was run on the
> recorded input with `protected` set to the first admissible value and again with it set to that
> other value, **nothing else changed**, and the two runs produced the same `outcome`; the values
> came from the system's declared `constraints` and its declared sort, never from the trace; and the
> budget on the result names the pairs replayed, the values used and the pairs that raised
> (`test_paired_replay_reaches_probed_when_the_proof_rung_cannot`,
> `test_paired_replay_takes_no_protected_value_from_the_trace`).

*What it does not tell you.* Everything above, and the bound of a search — including a bound on the
protected values themselves. `DEFAULT_MAX_VALUES` stops the enumeration at four, so over a band
admitting nine the search moves the variable across four of them, and the summary says which of the
two it did: every value the constraints admit, or that many of them with the declaration admitting
more. It used to name the values it searched as "the values the declared constraints admit", which
is the one sentence a reader would check a declared band against
(`test_the_replay_summary_does_not_call_the_values_it_searched_the_admitted_set`,
`test_a_replay_that_did_exhaust_the_admitted_values_says_so`). The claim covers the pairs
the budget names and no others, so a system whose logged decisions all sit far from the threshold
the protected variable would move is reported `satisfied` here while the solver rung reports the
same system `violated` (`test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach`). The
trace supplies the *base inputs* this search varies around and nothing else; a value the trace shows
for the protected variable is never one it replays.

**No rung reads a trace, and that is a fact about the code rather than about the ladder.** A trace
holds what a system decided; a counterfactual asks what it would have decided. So
`rulelang.eval_expression` refuses the atom outright — every engine that reads a decision record
goes through that interpreter, so none of them can answer this duty even if a ladder handed it to
one (`test_no_engine_can_evaluate_the_atom_against_a_decision_record`,
`test_the_ladder_for_this_fragment_carries_no_trace_rung`). A system that exposes neither `decide()`
nor `logic()` is reported *not evaluated*, however long its log
(`test_a_log_only_system_is_never_answered_from_its_trace`).

**The protected variable is an input, not a logged field.** Neither rung ever takes its value from a
decision record, which is what lets a system answer this duty while its audit log carries a
prohibited basis for nobody. The capability gate says the same thing: `capabilities()` is what a
system can *emit* into a record, so the protected argument of the atom is the one name
`report.analyze_unattainable` does not subtract from it, and a system that accepts the variable and
never logs it is answered rather than reported unattainable
(`test_a_system_that_never_logs_the_protected_variable_is_still_answered`). The name stays in the
duty's `requires` because it is the one the engine names as missing when a system's declared logic
has no notion of it. A duty that instructed every checkable system to log race per decision
would have made reasonsmith the reason it was collected — under the GDPR, an Article 9 processing
purpose invented to check a fairness duty. `docs/refinement.md` records the cost of the other
direction: nothing here can compare across groups, because nothing here reads a group.

### The assumption all seven share

None of these engines defends against a system that is adversarial toward its own audit. The probed
engine states the boundary and this document does not invent a second version of it — from
`engines/probed.py`:

> Replay inputs are isolated against accidental mutation by the system under test. This does not
> defend against a system that deliberately subverts copying: a system that lies to its auditor
> cannot be audited by that auditor, and reasonsmith does not claim otherwise.

The isolation against *accidental* mutation is real and tested
(`test_nested_mutation_cannot_change_the_verification_input_or_witness`,
`test_uncloneable_probe_input_is_not_evaluated`). The defence against a deliberate one is not claimed.

Read across all seven engines, the same shape holds: a declared capability set is taken at its word, a
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
  can discharge them. `temporal` is not, and `counterfactual` is not a property of any decision
  record at all.
- **The system's exposed surface** says what can be reasoned over. A non-`None` `logic()` admits
  `ProvedEngine`; a callable `decide()` admits `ProbedEngine`; **a trace admits a rung for every
  fragment but one** (`test_every_valid_formalism_has_an_engine_that_reads_a_trace`). Which engine
  reads it depends on the shape: `RecordEngine` for a presence conjunction, `ObservedEngine` for
  everything else, temporal and `logical` alike.

**The `counterfactual` fragment is the one exception, and it has no trace rung.** Its ladder is
built and returned before every other rung is considered: `CounterfactualProofEngine` where the
system exposes `logic()`, `PairedReplayEngine` where it exposes `decide()`, and nothing else — not
the record engine, not the rtamt monitor, and not an installed plug-in. `counterfactually_invariant`
is a property of a *pair* of executions, a trace holds what a system decided rather than what it
would have decided, and no length of decision log establishes one. The refusal is enforced one layer
below the ladder as well: `rulelang.eval_expression` raises on the atom, and every trace-reading
engine evaluates through that interpreter, so this is a fact about the code rather than a convention
this function is trusted to keep (`test_the_ladder_for_this_fragment_carries_no_trace_rung`,
`test_no_engine_can_evaluate_the_atom_against_a_decision_record`). A system exposing neither
surface is reported *not evaluated*, and a system whose declared logic has no notion of the
protected variable is reported *unattainable* — never `satisfied`, because unawareness is not a
discharge (§3, *counterfactual*).

**One duty has a ladder of exactly one rung, and for the opposite reason to everything above.** A
duty gating on `engines.certificate.DELETED_REASON_COUNT` asks whether the reasons a decision
states are *all* the reasons its inference had. Every other rung would answer a weaker question off
the system's own log — that the reason field is non-blank, or that the number the system wrote in
it is small — so a system exposing no inference artefact is reported `unattainable` by the
certificate engine rather than falling through to a presence check
(`test_the_adequacy_duty_is_never_downgraded_to_the_presence_check`). Everywhere else on this page
a weaker rung answers the *same* property with weaker evidence; here it would answer a *different*
property under the same duty's name, which is the substitution §3 (*certificate*) exists to remove.

The second bullet used to give `logical` nothing, and that contradicted the first. A `logical`
property is a property of one decision record — that is what puts it in `STATE_FRAGMENTS` — so a
trace of decision records is evidence about it, and a build that refused to read one reported *not
evaluated* while the evidence sat in front of it. The label on the fragment was deciding what could
be checked, which is the defect fragment classification exists to prevent. A `logical` duty is now
answered from a trace exactly as a `record` one always was
(`test_a_logical_duty_is_answered_from_a_trace_when_there_is_nothing_to_reason_over`).

**A presence conjunction keeps the record engine, and that is not an ordering detail.** The record
engine walks the conjunction conjunct by conjunct and names *which* signal was missing from *which*
record; the rtamt monitor cannot, because robustness is one number for the whole formula. Routing
presence through the monitor to make the two branches look alike would trade that diagnostic away
for nothing (§3, `record`).

**Two limits of the trace rung, both stated rather than silent.** rtamt scores real-valued signals,
so the shapes it cannot render soundly are reported *not evaluated*, never satisfied — a comparison
against a Boolean constant, which the `logical` fragment otherwise permits (§2), is one
(`test_the_trace_rung_does_not_reach_every_logical_shape_and_says_so`). And the monitor renders the
`spec` **as the pack wrote it**, so implication must be spelled `->` rather than `Implies(...)`:
the two are the same property to every other engine, and only the arrow reaches rtamt
(`test_the_monitor_reads_the_spec_as_written_so_implication_is_spelled_with_an_arrow`). That is
arbitrary, which is why the shipped Article 22 duty is spelled with the arrow and the test says so;
teaching the renderer to lower the prefix form is a change to the renderer, not to this ladder.

**A temporal duty rises above `observed` in one shape only, and that ceiling is untouched by the
above.** It is in the next-but-one paragraph and it is a different claim: the solver and the replay
search reason about one decision at a time, so they have nothing to say about a formula quantified
over a trace *unless the quantification reduces to a property of one decision*. Giving the state
fragments a rung *downward* to the trace does not give the temporal fragment one upward.

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
interface was missing (`test_the_proof_rung_still_names_the_missing_logic_when_it_is_asked_directly`) — except for a proof
rung that never had any logic to reason over, which says nothing about the evaluation and yields
to a lower rung's account of the evidence the system did supply
(`test_an_empty_trace_is_not_evidence`). An engine whose
interface *raises* is treated the same way as one that returns no evidence: a `logic()` that
throws establishes nothing, so the failure is named in a `strength=None` result and the duty
still lands on the strongest rung that did produce evidence
(`test_a_record_duty_survives_a_system_whose_logic_raises`,
`test_a_logical_duty_survives_a_system_whose_logic_raises`,
`test_a_logic_failure_is_named_when_no_rung_produced_evidence`). Selecting the rungs
never executes the system: both optional rungs are read off the callable surface
(`test_building_the_ladder_never_executes_the_system`). A malformed *trace* is deliberately not
absorbed this way — that is the system's own decision log coming back the wrong shape, and it
still raises and names the system (`test_a_trace_of_the_wrong_shape_names_the_system`).

**A temporal duty reaches `proved` only when it is `always(f)` over a state property**
(`test_only_always_reaches_the_temporal_proof_rung`, `test_a_nested_temporal_operator_does_not_reduce`).
That one shape reduces to a property of a single decision — see §3, *`proved`, over a trace* — so the
solver can answer it, and `engines/temporal.py` puts the rung on the ladder for a system that exposes
`logic()`. Every other temporal shape stops at `observed` where it always did: the solver and the
replay search both reason about one decision at a time and still have nothing to say about a formula
that quantifies existentially over a trace, and a rung for a claim no engine established would be the
overclaim this package exists to refuse.

**What selection does not change.** Nothing here alters the lattice or what any verdict means; §3 is
unchanged by it. A `proved` verdict is still a claim about the logic the system exposed, and an
`observed` one still a claim about the trace it supplied. **The consequence worth stating plainly:**
where a system's exposed logic and its trace disagree — the rules prove a reason is always written,
and a logged decision carries none — the ladder reports the `proved` verdict and the trace is never
read for that duty. That is not a contradiction the tool resolves; it is a system misdescribing
itself to its auditor, which §3 already says reasonsmith does not detect.

### An engine that was installed rather than vendored

The ladder collects engines from the system's exposed surface rather than from the pack, so a new
engine is reached the moment it *exists* — and "exists" means installed, not in this tree. An engine
shipped as its own pip package, declared in the `importlib.metadata` entry-point group
`reasonsmith.engines`, joins the ladder at the rung it declares in `max_strength` and can discharge
a duty like any built-in (`test_an_installed_engine_joins_the_ladder_and_discharges_a_duty`). The
property language is untouched by this; only the set of engines that may discharge a duty is open.

What such a verdict means is bounded by four claims, and by nothing else, because **reasonsmith does
not audit the plug-in**:

- **A plug-in cannot report above the ceiling it declared.** The refusal is in
  `RequirementResult.__post_init__`, beside the probe budget and the not-applicable invariants, so a
  result claiming more than the plug-in declared cannot be constructed at all
  (`test_a_result_claiming_above_the_declared_ceiling_is_refused`,
  `test_an_overclaiming_plugin_reports_not_evaluated_rather_than_proved`).
- **A plug-in that raises, exhausts its own time bound, returns the wrong type, or cannot be
  imported reports *not evaluated*** — never satisfied, and never violated either, because a false
  violation from an unaudited package is as bad as a false pass
  (`test_a_broken_plugin_establishes_nothing`,
  `test_a_broken_plugin_cannot_fail_a_duty_the_builtin_satisfies`,
  `test_a_plugin_that_cannot_be_imported_is_skipped`). reasonsmith imposes no wall clock of its own:
  a plug-in that hangs hangs the run, and bounding its own search is the plug-in's job.
- **A plug-in cannot take a built-in engine's name.** It is refused with a warning and the built-in
  stands, rather than being namespaced into a decorated name that would leave the shadowing engine
  answering the same duty (`test_a_plugin_shadowing_a_builtin_engine_is_refused`). The same rule
  holds for a pack name (`test_a_pack_shadowing_a_builtin_pack_name_is_refused`).
- **Every plug-in result names the plug-in**, in `details["engine_plugin"]` and in the evidence
  summary, failures included (`test_an_installed_engine_joins_the_ladder_and_discharges_a_duty`,
  `test_a_broken_plugin_establishes_nothing`).

That is the whole guarantee, and it is deliberately a guarantee about *form*. A `proved` from
`engines/proved.py` is a claim this repository's suite is about; a `proved` from an unfamiliar
plug-in is worth exactly what the installer's trust in that package is worth. The provenance in
every plug-in result is what lets a reader tell the two apart, and reading it is the installer's
job — see [`authoring-engines.md`](authoring-engines.md). With nothing installed, both groups are
empty and the ladder is the built-in ladder, unchanged
(`test_with_no_plugin_installed_the_ladder_is_the_builtin_ladder`).

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

### When the phrase atom cannot be proved

`contains()` refuses the same free-input case, for the same reason, and one of its own: a signal the
declared rules give a sort other than string is not one this predicate reads, and coercing a sort
would prove a property about a program nobody wrote
(`test_the_solver_refuses_a_signal_it_cannot_read_as_text`). Both refusals drop the duty to the
strongest engine that *can* answer it. Where the rules do write text, the duty is genuinely proved
over every admitted input — a system whose rules can write a statement the clause calls
insufficient is proved to violate it rather than watched until one turns up in a log
(`test_a_forbidden_phrase_the_rules_can_write_is_proved_to_violate`,
`test_rules_that_never_write_a_forbidden_phrase_are_proved_to_satisfy`).

The signal's sort is not itself a reason for refusal. In particular, **a string is not refused**:
`present()` over a string encodes as
  "not in the language of blanks" over `BLANK_CHARACTERS`, which is exactly the set `str.strip()`
  removes, so the solver and `is_present` agree on every string rather than approximately
  (`test_the_solvers_blank_string_is_pythons_blank_string`). A system whose rules can write a blank
  reason is therefore proved to *violate* the duty, not proved to satisfy it
  (`test_a_presence_proof_refuses_the_blank_string_the_solver_could_choose`).

### When the magnitudes are not the system's own

The same free-constant argument reaches a third atom, and answering it needs something the sorts
alone cannot say: whether a name is an **input the decision situation supplies** or an **output the
system computes**. `sut.logic()` may now say so. Alongside `variables`, `rules` and `constraints` it
may carry **`computes`**, the names the system produces, and the two together split every name into
three states:

| declaration | reading | the solver's free constant is |
| --- | --- | --- |
| in `computes` | an output the system produces | wrong unless the rules settle it |
| in `variables`, not in `computes` | *at most* an input the situation supplies | right unless the property reads only free names and compares them as magnitudes |
| in neither list | a name the system has no notion of | an invention |

The middle row says **at most**, and the qualification is the whole of what `variables` can carry.
It is a type table: its job is sorts, and a caller listing a name there is naming a signal the system
deals with — which may be one it merely *logs*. That is neither an input nor an output, the three
states have no seat for it, and no declaration distinguishes it from a genuine input. So the middle
row is a permission and not a licence: `_check_magnitudes_are_computed` below runs over declared
logic too, and a property that reads no name the rules assign and compares free **magnitudes** is
refused whatever `variables` says.

The outer boundary is **both** lists and not `variables` alone. `RulesAdapter` keeps `computes`
inside `variables` and refuses to construct otherwise, but the protocol asks an adapter only for the
names its system produces, so a computed name the type table does not repeat is an output at the
default sort and never a name the system has no notion of
(`test_a_computed_name_outside_the_type_table_is_an_output_not_an_unknown`). A `computes` given as a
bare string is a misdeclaration and reported not evaluated, because reading it as the iterable it
technically is yields its own characters and quietly makes every declared variable an input
(`test_computes_declared_as_a_string_is_refused_rather_than_read_as_characters`).

`_check_declared_directions` reads that and refuses two things, neither of which is a judgement
about the property:

- **A name the system has no notion of.** `_Scope.read` declares a constant for any name it meets,
  so without this the encoding invents the very value the verdict is then about. Left unguarded,
  `always(scope_statements_declared_deviation <= artifact_logs_decision_margin)` against a system
  whose rules decide on a score alone was reported `violated` at `proved` — the one verdict that
  exits non-zero — on the solver's own choice of `deviation = 1, margin = 0`. The counterexample
  verification does not catch that: the reference interpreter is handed the same free inputs, so
  the "violation" reproduces. Refused, the duty falls to the engine that reads the trace, which
  measures the magnitudes where the decisions carry them and reports them unmeasured where they do
  not (`test_a_magnitude_the_rules_never_compute_is_not_proved_violated`).
- **A declared output the exposed rules do not settle on every path.** The system says it computes
  the name and the logic it handed over does not show how, so the constant standing in for it is
  free after all (`test_a_declared_output_the_rules_never_settle_is_refused_a_proof`). `present()`
  and `contains()` refuse the same thing for their own atoms and with their own wording, which is
  why this guard runs after the property is encoded rather than before.

**A declared input is quantified over, and that is the point.** `income >= 30000 and age >= 18
implies approved == True` reads three free magnitudes and one computed `approved`
(`test_property_holds_for_all_inputs_proved`), and
`gdpr_art22_1_no_prohibited_decision_for_any_input` asks whether *any* admissible input yields a
prohibited decision, ranging over Article 22 flags no rule assigns
(`test_article_22_still_quantifies_over_flags_the_rules_never_assign`). Both are claims about what
the system decides over its own input space, and proving them is this engine's whole purpose, and
both pass the heuristic below on its own terms: the first reads `approved`, a name the rules do
settle, and the second reads free **flags** rather than free magnitudes. What the declaration may
not do is admit what that heuristic refuses — a property reading no name the rules assign and
comparing free magnitudes — however many of those magnitudes the type table lists. So a system whose
rules decide on a score alone is refused a proof of the Recital 71 comparison in **both**
directions: `violated`, on numbers it never computes
(`test_a_logged_magnitude_is_not_an_input_because_the_type_table_names_it`), and
`satisfied`, where a constraint of its own restates the duty
(`test_a_constraint_restating_the_duty_cannot_prove_the_system_satisfies_it`). The second is the
self-declaration §3 refuses everywhere else, and a constraint must not carry it to the top rung.

**What this engine does not do is second-guess the declaration.** An adapter calling an output an
input is claiming its situation supplies a value it in fact produces, and it will be answered about
the system it described — the same trust `system_domains` is given, and the same false positive
available from the adapter side. `RulesAdapter` derives `computes` from its own rules' assignment
targets, so no adapter in this repository declares nothing and none can drift from the rules it
exposes; a caller may override it, and a declared name outside `variables` is refused at
construction (`test_computes_is_derived_from_the_rules_and_must_name_declared_variables`).

**The heuristic stays, and it stays for every logic — an additional filter, never an alternative.**
`_check_magnitudes_are_computed` refuses a property that reads **no** name the declared rules assign
and reads at least one free name as a **magnitude** — an arithmetic sort. Sort and reachability are
proxies for direction and cut along the wrong joint: a system that genuinely computes a margin but
exposes it only as an input to a downstream rule set is refused a proof it could have had, and a
duty comparing a free magnitude with a computed one is admitted. It is kept rather than removed
because every alternative is worse. Reading `variables` as "every variable is an input" hands back
exactly the `violated`-at-`proved` verdict above; refusing every proof to logic that predates the
declaration would withdraw verdicts for a reason having nothing to do with the system; and running
the heuristic only where no declaration exists lets a declaration *widen* what reaches the solver,
which is the one thing a declaration must never do. So both guards run wherever `computes` is
declared, logic carrying none gets the answer it has today and never a wider one
(`test_logic_that_declares_no_directions_keeps_the_sort_heuristic`), and a refusal on either path
still reads as "this engine could not tell whether the system computes these numbers", not as "it
does not". The cost is stated rather than hidden: a duty comparing declared-input **magnitudes**
alone, reading no name the rules assign, cannot be `proved` even where the declaration is exact.

---

## 4. The lattice

`unattainable < observed < recounted < probed < proved`, a strict total order
(`test_strength_lattice_ordering`, and `test_semantics_doc_states_the_lattice_the_code_defines`
holds this sentence to the order the code defines). Comparison against anything that is not a
`Strength` is refused rather than coerced (`test_strength_comparison_rejects_foreign_types`).

**What a comparison means.** `a < b` orders the evidence-gathering method recorded on the result:

- `unattainable` — capability analysis stopped evaluation before an engine ran.
- `observed` — a record or temporal conclusion was reached from the supplied trace.
- `recounted` — a conclusion was reached by perturbing a reason set the *system* recounted, rather
  than one enumerated from a model encoding. The same probe as `probed`, over evidence that is
  second-hand about the thing it describes: only the `artifact` basis has such evidence, and §3
  (*The inference artefact*) is where the rung is defined.
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

**And it is only one of the two coordinates.** A chain ranks how far a claim was pushed and cannot
say what the claim was *about*; three shipped situations are about something other than the system's
own executions, and §10 is the dimension that carries it. The lattice itself did not move — no
member, no re-ranking — and a basis is deliberately not comparable to a rung.

### Four outcomes that must never collapse

`not applicable`, `unattainable`, `not evaluated` and `violated` are four distinct report categories
(`test_the_four_unresolved_outcomes_are_four_distinct_report_categories`), every result lands in
exactly one, and the counts reconcile against the total rather than merely summing to something
plausible (`test_counts_reconcile_against_both_totals`). `not applicable` is one category reached by
two independent gates, split into two rows below because they are two different instructions; the
result's own summary says which gate answered. They differ in what a reader should do next:

| Outcome | What happened | What to do next |
|---|---|---|
| **not applicable — class** | The duty is limited to a regulatory class, and the system was not declared to be in it — either no class was declared at all, or a different one was. Nothing about the system was checked. reasonsmith never infers the class. | Declare the class and re-run, or establish that the duty genuinely does not reach the system. Read the declared-scope line first: an undeclared system is neither placed in scope nor cleared. |
| **not applicable — domain** | The duty is about a kind of decision the system was not declared to make — either no decision domain was declared at all, or none of the ones declared is one the duty is about. Nothing about the system was checked. reasonsmith never infers the domain. | Declare the domain and re-run (`--system-domain`), or establish that the duty genuinely does not govern this kind of decision. Two things this does *not* say: that the system is compliant, and that any regulator agrees with the classification — the domain vocabulary is the pack author's (`docs/authoring-packs.md`). |
| **unattainable — declared basis** | The signals the duty needs are outside the system's declared capability set. Computed as a set difference, *without executing the system*. | Change the system. |
| **unattainable — trace basis** | No record in the supplied trace carries the required signals; the adapter derived its capability set from that trace. This does not establish that the system cannot emit them. | Supply a longer trace or an explicit capability declaration. Change the system only if further evidence confirms the signals are absent. |
| **not evaluated** | The duty reaches the system, the system can emit the signals, and no engine here established anything: an empty trace, an unparseable formula, a solver timeout, an unmodelled construct. `strength=None`, which is deliberately not a rung on the lattice. | Fix the evidence or the specification and re-run. This is a gap in the audit, not a finding about the system. |
| **violated** | An engine produced a witness: a record, a trace step, or an input that fails the property. | Fix the system. Of these four report outcomes, this is the only one that fails a `check` run. |

Collapsing any two of them loses that instruction. "Unattainable" read as "violated" sends someone to
fix a system that is behaving as designed; "not evaluated" read as "satisfied" is the single overclaim
this tool exists to prevent; "not applicable" read as "satisfied" clears a duty nobody checked.

**Why an undeclared domain is `not applicable` and not `inconclusive`.** The two are not
interchangeable: `inconclusive` says a duty that *does* reach the system was not resolved, and
`not_applicable` says the duty's reach was never established over this system, so nothing was
checked. Neither is a perfect fit — with no declaration, reasonsmith does not *know* the duty fails
to reach — and the choice is made on what each answer instructs a reader to do. `inconclusive` sends
someone to look for better evidence about a system the duty may not govern at all, and it would put
every domain-limited duty into the unresolved column of a run against a system nobody classified.
`not_applicable` sends them to declare what the system decides, which is the actual missing input,
and it carries no strength, so nothing can be read from it as a finding
(`test_an_undeclared_system_cannot_reach_satisfied_on_a_domain_limited_duty`). It is also what the
class gate already answers for an undeclared class, and a reader who has learned one of the two
gates should not have to learn the other separately. What stops that reading as *cleared* is the
same thing that stops it for the class: the reason string names which of the two ways the duty
failed to reach, and `LIMITS` carries all four on every report
(`test_limits_cover_both_ways_a_requirement_becomes_not_applicable`).

**A duty with no domain is a wildcard, and that is deliberate.** `domains = []` means the duty is
about no particular kind of decision — GDPR Article 22 governs a solely-automated decision whatever
it is about — and such a duty is answered on its evidence against a system that declares nothing
(`test_a_duty_with_no_domain_still_reaches_a_system_that_declares_none`). The wildcard is safe only
because it cannot be reached by omission: `domains` is a required field with no default, so a pack
that has not classified a requirement fails to load rather than being guessed for
(`test_a_pack_that_has_not_classified_a_requirement_is_refused`).

**A run that skipped duties for a missing declaration does not read like a run that checked them.**
A duty reported not applicable *solely* because the system declared no decision domain is a missing
input, not an answer, and it is flagged as one on the result itself
(`report.UNDECLARED_DOMAIN_KEY`). The text report, the HTML dossier and the CLI's stderr each carry
a line naming how many duties that was and what to declare to check them; a duty skipped because the
system declared a domain that is simply not this duty's raises no such line, because that one was
answered (`test_a_run_that_skipped_duties_for_a_missing_declaration_says_so`). The exit code is
unchanged, which is why the notice exists.

### A duty whose trigger never fired is not evaluated, at every rung

Some clauses only bite in some circumstances. 12 CFR 1002.9(b)(2) governs, by its own words, "the
statement of reasons required by paragraph (a)(2)(i)", so a creditor that lawfully took the
(a)(2)(ii) disclosure branch has no such statement and the clause does not reach that notification.
That trigger is expressible — it is an implication whose antecedent is
`present(artifact_logs_reason_explanation)` — and formalising it removed a false violation on a
binding duty (`test_a_creditor_who_took_the_disclosure_branch_is_not_violated`).

**The outcome that used to produce was `satisfied`, and it was not the truth.** Two traces got the
same verdict at the same strength: one where the duty imposed a requirement and every record met it,
and one where the antecedent never held, so the duty imposed nothing and the wording of no statement
was ever examined. No field of the result distinguished them.

The rule now: **where a requirement's property is an implication and the engine's evidence domain
contains no element satisfying its antecedent, the result is `not evaluated`, `strength=None`,
naming the antecedent that never fired and the domain that was searched**
(`test_a_duty_whose_trigger_never_fires_is_not_evaluated_at_any_rung`). It is written once — the
antecedent is a fact about the formula, the same subtree whichever engine parsed it
(`rulelang.implication_antecedent`), and the refusal is worded once against the result model
(`report.not_evaluated_for_unreachable_trigger`,
`test_the_language_names_the_antecedent_whatever_the_arrow_was_written_as`). Each rung asks it of
the domain it quantifies over, and the domain travels on the result:

| Rung | The domain the antecedent was looked for in | Test |
|---|---|---|
| `proved` | every input the declared logic and constraints admit — the solver is asked whether premises ∧ antecedent is satisfiable, which is the premise check one quantifier deeper | `test_an_antecedent_no_admissible_input_reaches_is_not_evaluated_at_proved` |
| `proved`, over a trace | the same domain: `always(f)` is decided by deciding `f`, so the reduction inherits the refusal rather than repeating it | `test_the_temporal_reduction_inherits_the_refusal` |
| `probed` | the decisions the search replayed — the interpreter already evaluates the antecedent to answer the implication, so it is counted in the same walk | `test_a_search_that_never_reached_the_antecedent_is_not_evaluated_at_probed` |
| `observed` | the decisions of the supplied trace — the antecedent is monitored as a sub-formula, at the same threshold satisfaction is read at | `test_an_antecedent_false_at_every_position_is_not_evaluated_at_observed` |
| `probed`, over certificates | the certified decisions of the trace — the antecedent is counted in the same walk that decides the property against the measured count | `test_a_certified_trace_that_never_reached_the_antecedent_is_not_evaluated` |

**Why the argument for tolerating it did not survive.** It was a trace argument: reporting the
vacuous case `satisfied` is literally true of what was monitored — the observed engine's claim is
non-negative robustness at every step, which held — and misleading only about what was learned.
That reading does not exist at `proved`, where there is no monitor, no record and no robustness,
and the claim is universal over the whole declared input space. A creditor whose rules state no
reasons at all was reported *violated* on 12 CFR 1002.9(a)(2) for giving neither reasons nor a
disclosure, and `satisfied` at `proved` on 12 CFR 1002.9(b)(2) for the specificity of the statement
it never made, in the same five lines of one report. So the argument for tolerating the weak case
was the argument against tolerating the strong one, and both moved together
(`test_the_solver_and_the_monitor_no_longer_disagree_about_the_same_formula`).

**What this costs, stated rather than hidden.** Duties that used to land in the `satisfied` column
land in `not evaluated`, and headline counts and exit codes moved with them. A creditor lawfully on
the (a)(2)(ii) disclosure branch is one of them: that system is *not* in breach, and it no longer
gets a clean line on this duty either. `not applicable` is still the honest answer there and **the
result model still cannot reach it**. Applicability here is a per-*requirement*, per-*system*
question, decided from the declared regulatory class and decision domain before any engine runs.
Both gates are about the system, not about the record: neither can say that a duty reached this
system and then imposed nothing on *this decision*. There is no per-record equivalent, and a
formula is Boolean per record with no third value to return. What changed is that the case is no
longer reported as an answer; the reader is told the trigger never fired and over what, which is
what the summary and `report.VACUOUS_TRIGGER_KEY` carry.

Two shapes the guard deliberately does not reach, and neither is an oversight
(`test_a_property_that_is_not_one_implication_has_no_antecedent_to_be_unreachable`). `eventually(f)`
is not stripped the way `always(f)` is: its vacuity is a claim about a position that never existed
rather than about a trigger that never fired, and the two need different sentences. A conjunction of
implications has several antecedents and a vacuity per conjunct, which is a finer report than one
`strength=None` can carry. A property that is not an implication at all is untouched at every rung
(`test_a_property_with_no_implication_is_untouched_at_proved`).

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
- reasonsmith does not infer a system's decision domain either, and — separately — the domain
  vocabulary it compares against is written by this repository and by no regulation
  (`reasonsmith.spec.DECISION_DOMAINS`, `docs/authoring-packs.md`). A not-applicable verdict on that
  gate is a statement about a classification a pack author made, never a finding that a statute does
  not govern the system, and nothing checks that a system declaring `consumer-credit` issues credit
  (`test_report_limits_exclude_legal_determination_and_scope_inference`,
  `test_a_domain_outside_the_vocabulary_is_refused`, `test_the_two_domain_gates_never_disagree`).
- reasonsmith does not measure elapsed time. Every verdict is counted on the record index (§2), so
  a deadline duty is answered by whatever duration the system computes about itself. A record may
  now state which event its clock started at, and nothing reads those timestamps: a duty asked for
  on that domain is not evaluated rather than answered off decision counts
  (`test_a_duty_needing_a_clock_is_not_evaluated_and_never_satisfied`,
  `test_only_the_ordinal_domain_has_a_time_axis`).
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
| `logical` routes to proved with exposed logic, probed with only `decide()`, and the observed engine off a trace | `test_property_holds_for_all_inputs_proved`, `test_an_opaque_system_reaches_probed_through_the_report`, `test_a_logical_duty_is_answered_from_a_trace_when_there_is_nothing_to_reason_over` |
| Every valid formalism has an engine that reads a trace, so no fragment is left unreadable | `test_every_valid_formalism_has_an_engine_that_reads_a_trace`, `test_a_formalism_without_an_engine_is_not_evaluated` |
| A system with neither logic nor decisions is not evaluated, and the proof rung still names the missing interface when asked | `test_system_without_logic_or_a_trace_is_not_evaluated`, `test_the_proof_rung_still_names_the_missing_logic_when_it_is_asked_directly` |
| A universal prohibition is never proved on the strength of a sample; a trace answers it at `observed` and no higher | `test_gdpr_art22_without_exposed_logic_is_never_proved_on_the_strength_of_a_sample` |
| The trace rung does not reach every logical shape, and says so rather than guessing | `test_the_trace_rung_does_not_reach_every_logical_shape_and_says_so`, `test_the_monitor_reads_the_spec_as_written_so_implication_is_spelled_with_an_arrow` |
| A duty whose trigger never fired is not evaluated at every rung, naming the antecedent and the domain searched | `test_a_duty_whose_trigger_never_fires_is_not_evaluated_at_any_rung`, `test_an_antecedent_no_admissible_input_reaches_is_not_evaluated_at_proved`, `test_the_temporal_reduction_inherits_the_refusal`, `test_a_search_that_never_reached_the_antecedent_is_not_evaluated_at_probed`, `test_an_antecedent_false_at_every_position_is_not_evaluated_at_observed`, `test_a_certified_trace_that_never_reached_the_antecedent_is_not_evaluated` |
| The guard is one rule against the property language, and an earned verdict still reaches its rung | `test_the_language_names_the_antecedent_whatever_the_arrow_was_written_as`, `test_a_property_that_is_not_one_implication_has_no_antecedent_to_be_unreachable`, `test_a_satisfaction_whose_antecedent_does_fire_still_reaches_proved`, `test_a_property_with_no_implication_is_untouched_at_proved`, `test_widening_the_declared_input_space_alone_turns_the_refusal_into_a_violation` |
| 12 CFR 1002.9(b)(2) is falsifiable on a plain decision log, and the disclosure branch is no longer violated | `test_a_statement_the_clause_calls_insufficient_is_violated_on_a_bare_log`, `test_a_statement_resting_on_internal_standards_or_policies_is_violated`, `test_a_statement_naming_a_principal_factor_is_satisfied`, `test_a_creditor_who_took_the_disclosure_branch_is_not_violated` |
| Every forbidden wording is the clause's own, and the one derived reading is named as one | `test_the_forbidden_wordings_are_the_clauses_own` |
| The specificity duty leaves the record fragment, so a one-decision log no longer answers it | `test_a_single_decision_log_is_not_evaluated_never_satisfied` |
| One property language: the loader classifies the fragment and refuses a mismatch, prose and definitely non-Boolean roots included | `test_the_loader_refuses_a_spec_that_is_not_in_the_declared_fragment`, `test_the_loader_refuses_prose_where_a_property_belongs`, `test_the_loader_refuses_quoted_prose_as_a_non_boolean_property`, `test_the_loader_refuses_arithmetic_as_a_non_boolean_property` |
| A signal the property reads unconditionally must be gated by `requires` | `test_the_loader_refuses_a_spec_reading_an_ungated_signal` |
| A branch of an either/or is not gated, so neither branch alone makes the duty unattainable | `test_the_loader_lets_a_disjunct_go_ungated_but_not_the_rest_of_the_property`, `test_neither_branch_signal_gates_the_content_duty` |
| The exemption reaches an either/or only: a disjunction over magnitudes gates its names, and a name every branch reads stays gated | `test_a_disjunction_of_magnitudes_gates_its_signals`, `test_a_name_every_disjunct_reads_is_still_gated` |
| Either lawful branch of 12 CFR 1002.9(a)(2) satisfies the content duty, and neither branch violates it | `test_a_creditor_giving_the_specific_reasons_is_satisfied`, `test_a_creditor_disclosing_the_right_to_request_reasons_is_satisfied`, `test_a_creditor_giving_neither_branch_is_violated` |
| Quantified over the trace, the 12 CFR 1002.9(a)(2) content duty is not evaluated on a single-decision log rather than satisfied | `test_a_single_decision_trace_is_not_evaluated_never_satisfied` |
| The same presence property is observed off a trace, probed against `decide()`, and proved against `logic()` | `test_a_record_duty_reaches_proved_when_the_system_exposes_its_logic`, `test_a_record_duty_reaches_probed_when_the_system_can_only_be_re_run` |
| The ladder takes the strongest evidence produced, not the strongest engine available | `test_a_record_duty_the_solver_cannot_reach_falls_to_the_engine_that_can` |
| A name the declared directions give the system no notion of is refused a proof, and a declared output the rules never settle is too | `test_a_magnitude_the_rules_never_compute_is_not_proved_violated`, `test_a_declared_output_the_rules_never_settle_is_refused_a_proof` |
| A declared input is quantified over where the property also reads a name the rules settle, or reads its free names as flags rather than magnitudes | `test_article_22_still_quantifies_over_flags_the_rules_never_assign`, `test_property_holds_for_all_inputs_proved` |
| A name the type table lists and the rules neither read nor write carries no `proved` verdict, in either direction | `test_a_logged_magnitude_is_not_an_input_because_the_type_table_names_it`, `test_a_constraint_restating_the_duty_cannot_prove_the_system_satisfies_it` |
| Directions are derived from the rules, must name declared variables, and the sort heuristic filters declared and undeclared logic alike | `test_computes_is_derived_from_the_rules_and_must_name_declared_variables`, `test_logic_that_declares_no_directions_keeps_the_sort_heuristic` |
| The two declarations together bound what the system has, and a `computes` that is a bare string is refused rather than read as its characters | `test_a_computed_name_outside_the_type_table_is_an_output_not_an_unknown`, `test_computes_declared_as_a_string_is_refused_rather_than_read_as_characters` |
| An engine whose interface raises establishes nothing, and the duty still lands on the rung that answered | `test_a_record_duty_survives_a_system_whose_logic_raises`, `test_a_logical_duty_survives_a_system_whose_logic_raises`, `test_a_logic_failure_is_named_when_no_rung_produced_evidence`, `test_a_raising_logic_is_attempted_once_per_evaluation` |
| Building the ladder reads the callable surface and never executes the system | `test_building_the_ladder_never_executes_the_system` |
| An installed engine plug-in joins the ladder, discharges a duty, and names itself in the result | `test_an_installed_engine_joins_the_ladder_and_discharges_a_duty` |
| A plug-in cannot report above the ceiling it declared | `test_a_result_claiming_above_the_declared_ceiling_is_refused`, `test_a_plugin_result_must_declare_a_ceiling`, `test_an_overclaiming_plugin_reports_not_evaluated_rather_than_proved` |
| A plug-in that raises, times out, returns the wrong type, or cannot be imported is not evaluated, never satisfied and never violated | `test_a_broken_plugin_establishes_nothing`, `test_a_broken_plugin_cannot_fail_a_duty_the_builtin_satisfies`, `test_a_plugin_that_cannot_be_imported_is_skipped`, `test_a_plugin_without_a_declared_ceiling_gets_no_rung` |
| A plug-in cannot shadow a built-in engine or pack name | `test_a_plugin_shadowing_a_builtin_engine_is_refused`, `test_a_pack_shadowing_a_builtin_pack_name_is_refused` |
| An installed pack loads through the one loader and is held to every rule an in-tree one is | `test_an_installed_pack_loads_by_name`, `test_an_installed_pack_may_be_a_callable`, `test_an_installed_pack_is_held_to_every_rule_an_in_tree_one_is` |
| With no plug-in installed the ladder is the built-in ladder | `test_with_no_plugin_installed_the_ladder_is_the_builtin_ladder` |
| A malformed trace still raises and names the system | `test_a_trace_of_the_wrong_shape_names_the_system` |
| A presence proof requires the rules to assign the signal on every path | `test_a_record_duty_the_solver_cannot_reach_falls_to_the_engine_that_can`, `test_presence_is_not_proved_when_only_one_branch_assigns_the_signal` |
| A temporal duty reaches proved only as `always(f)` over a state property; every other shape stops at observed | `test_only_always_reaches_the_temporal_proof_rung`, `test_a_nested_temporal_operator_does_not_reduce` |
| A proved temporal violation is existential and says so: it is about the system as built, not about the trace supplied | `test_a_temporal_violation_names_the_trace_it_is_and_is_not_about` |
| A counterfactual duty is proved by encoding the declared rules twice, and two copies of one rule block do not collide | `test_two_copies_of_one_rule_block_do_not_collide`, `test_a_rule_set_ignoring_the_protected_variable_is_unsat_on_the_negation`, `test_a_rule_set_reading_the_protected_variable_yields_a_witness_pair` |
| A system that accepts the protected variable and provably never lets it move the outcome is satisfied at proved | `test_a_system_accepting_the_protected_variable_and_ignoring_it_is_satisfied`, `test_the_shipped_duty_is_satisfied_by_a_system_that_provably_ignores_the_basis` |
| A system whose declared logic has no notion of the protected variable is unattainable, never satisfied — unawareness is not a discharge | `test_a_system_with_no_notion_of_the_protected_variable_is_unattainable`, `test_the_two_cases_reach_different_verdicts_on_the_same_rules`, `test_a_system_declaring_no_directions_is_not_evaluated` |
| A counterfactual violation names an admissible pair, and both halves of it are replayed against the system | `test_a_rule_set_reading_the_protected_variable_is_violated_at_proved`, `test_the_witness_pair_is_replayed_on_both_halves` |
| The counterfactual fragment has no trace rung, and no engine can evaluate the atom against a decision record | `test_the_ladder_for_this_fragment_carries_no_trace_rung`, `test_no_engine_can_evaluate_the_atom_against_a_decision_record`, `test_a_log_only_system_is_never_answered_from_its_trace`, `test_the_counterfactual_fragment_is_the_one_a_trace_cannot_answer` |
| The atom is the whole of a spec or no part of one, and both its arguments are distinct signal names | `test_the_atom_is_the_whole_spec_or_no_part_of_one`, `test_both_arguments_are_signal_names_and_must_differ`, `test_the_atom_classifies_into_its_own_fragment_and_not_into_logical` |
| The paired replay takes the protected values from the declared constraints and never from the trace, and reports what it searched | `test_paired_replay_takes_no_protected_value_from_the_trace`, `test_paired_replay_reaches_probed_when_the_proof_rung_cannot`, `test_paired_replay_finds_a_disagreement_and_verifies_it` |
| A probed counterfactual verdict is a bounded search and the proved rung can find what it misses | `test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach` |
| A declaration admitting no pair that differs in the protected variable is not evaluated, never satisfied | `test_constraints_pinning_the_protected_variable_are_not_a_proof`, `test_rules_assigning_the_protected_variable_are_not_a_proof` |
| The protected variable is gated as an input the procedure accepts, never as a field a decision record must carry | `test_a_system_that_never_logs_the_protected_variable_is_still_answered` |
| Exactly one shipped signal is outside the paper's Section 6.3 taxonomy, and it is the protected variable | `test_exactly_one_shipped_signal_is_outside_the_paper_s_taxonomy`, `test_the_shipped_duty_is_the_only_counterfactual_requirement` |
| The solver's blank string is Python's blank string, so a provable blank reason is a violation | `test_the_solvers_blank_string_is_pythons_blank_string`, `test_a_presence_proof_refuses_the_blank_string_the_solver_could_choose` |
| `contains()` takes a signal name and a literal ASCII phrase, and every other shape is refused | `test_a_malformed_contains_atom_is_refused_rather_than_guessed_at`, `test_a_contains_atom_is_a_boolean_property_outside_the_record_fragment`, `test_the_phrase_is_not_a_signal_the_property_reads` |
| The solver's ASCII case fold is the interpreter's, over a generated corpus | `test_the_solvers_fold_is_the_interpreters_fold`, `test_the_fold_is_ascii_case_and_reaches_no_further` |
| A record carrying no statement carries no phrase, for the solver too; a statement in parts is read part by part and never joined; any other present value is refused | `test_a_record_carrying_no_statement_carries_no_phrase`, `test_the_solver_finds_no_phrase_in_a_string_the_record_does_not_carry`, `test_a_statement_given_in_parts_is_read_part_by_part`, `test_the_parts_of_a_statement_are_never_joined`, `test_a_present_value_that_is_not_a_statement_is_refused`, `test_a_non_text_value_makes_the_duty_not_evaluated_never_satisfied` |
| A forbidden phrase in the trace is an observed violation, and a statement naming a factor is satisfied | `test_a_forbidden_phrase_in_the_trace_is_an_observed_violation`, `test_a_statement_naming_a_factor_is_observed_satisfied` |
| Rewriting for rtamt skips a call head a phrase merely quotes | `test_a_call_head_a_phrase_merely_quotes_is_not_rewritten` |
| Exposed rules that can write a forbidden phrase are proved to violate; a signal the rules do not type as text is refused | `test_a_forbidden_phrase_the_rules_can_write_is_proved_to_violate`, `test_rules_that_never_write_a_forbidden_phrase_are_proved_to_satisfy`, `test_the_solver_refuses_a_signal_it_cannot_read_as_text` |
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
| A value that is not a statement is not evaluated on the probed rung as it is on the observed one, never counted and passed over | `test_a_non_text_value_is_not_evaluated_on_every_rung` |
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
| A system exposing no logic is not proved, and the proof rung names the interface it wanted | `test_the_proof_rung_still_names_the_missing_logic_when_it_is_asked_directly` |
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
| An undeclared system never reaches `satisfied` on a domain-limited duty, and a declared mismatch is worded apart from it | `test_an_undeclared_system_cannot_reach_satisfied_on_a_domain_limited_duty`, `test_a_system_in_another_domain_is_not_applicable_rather_than_judged` |
| A duty with no domain still reaches a system that declares none, and matching is intersection | `test_a_duty_with_no_domain_still_reaches_a_system_that_declares_none`, `test_matching_is_intersection_so_one_shared_domain_is_enough` |
| A pack that has not classified a requirement fails to load; there is no default domain | `test_a_pack_that_has_not_classified_a_requirement_is_refused`, `test_every_shipped_pack_classifies_every_requirement` |
| A misspelled decision domain is refused on both sides, and a domain list is domain names and nothing else | `test_a_domain_outside_the_vocabulary_is_refused`, `test_a_domain_list_is_domain_names_and_nothing_else` |
| The whole-pack plan and the single-requirement path give the same applicability answer, and neither runs an out-of-reach system | `test_the_two_domain_gates_never_disagree`, `test_an_undeclared_domain_never_runs_the_system` |
| A run that skipped duties for an undeclared domain says so in every rendering, and a declared mismatch raises no such notice | `test_a_run_that_skipped_duties_for_a_missing_declaration_says_so` |
| The certificate engine reaches a duty at all: the demonstration's own `APP-1042` is reported violated, and form completeness and reason fidelity are separate verdicts | `test_the_demonstrations_own_decision_is_reported_violated`, `test_form_completeness_and_reason_fidelity_are_now_separate_verdicts`, `test_the_cli_reports_the_demonstration_decision_violated` |
| A system that cannot supply the oracle is unattainable, and the adequacy duty is never downgraded to the presence check | `test_a_system_exposing_no_oracle_is_unattainable_and_names_the_signal`, `test_the_adequacy_duty_is_never_downgraded_to_the_presence_check` |
| The deleted-reason count is measured, never read from the system's own record | `test_a_logged_completeness_count_never_settles_the_duty` |
| A certificate verdict carries its probe budget, and exact inference behind a decision still reaches probed and no higher | `test_the_certificate_verdict_carries_its_probe_budget`, `test_an_engine_that_deletes_nothing_is_probed_and_never_proved` |
| A decision whose reasons were never enumerated buys no verdict, and never `satisfied` | `test_a_decision_whose_reasons_were_never_enumerated_cannot_buy_satisfied` |
| No artefact, a broken artefact, or a property the engine cannot ground ⇒ not evaluated | `test_a_trace_with_no_artifact_is_not_evaluated_never_satisfied`, `test_an_artifact_that_raises_or_is_the_wrong_shape_is_not_evaluated`, `test_the_engine_refuses_a_property_it_cannot_ground` |
| A reason-deletion certificate detects a dropped reason and excludes compliance certification beyond its measured input | `test_a_perturbed_engine_that_drops_a_reason_fails`, `test_certificate_limits_exclude_compliance_certification`, `test_certificate_carries_its_limits` |
| The deletion probe is one-directional, says so on the instrument, and flags the engine where a deletion moved its answer up rather than counting a retraction silently | `test_the_certificate_limits_state_the_probe_is_one_directional`, `test_a_retracted_reason_is_reported_deleted_and_the_engine_is_flagged_non_monotone` |
| The inference artefact is reasonsmith's own abstraction, and a ground program is one adapter satisfying it | `test_the_ground_program_family_is_one_adapter_and_the_protocol_names_no_representation`, `test_the_protocol_is_satisfiable_without_a_ground_program`, `test_switching_a_fact_off_does_not_re_enumerate_the_reasons` |
| An artefact the deletion definition of a reason does not apply to is not evaluated — declared non-monotone, declaring nothing, or contradicted by the probe — and never violated or satisfied | `test_an_artefact_declaring_non_monotone_inference_is_not_evaluated_and_names_why`, `test_an_artefact_that_declares_nothing_is_not_evaluated_rather_than_assumed_monotone`, `test_a_declaration_the_probe_contradicts_is_refused_rather_than_trusted`, `test_the_refusal_survives_a_whole_conformance_run_and_reaches_no_weaker_duty`, `test_a_certificate_over_a_non_monotone_artefact_carries_no_verdict` |
| A reason set the system recounted reports at `recounted`, one rung below an enumerated one, and the same probe still finds a breach | `test_a_recounted_reason_set_reports_one_rung_below_an_enumerated_one`, `test_a_recounted_reason_the_answer_does_not_depend_on_is_still_a_breach` |
| A family that does not declare its reason set exact claims the weaker rung, and no result may claim above the flag | `test_a_family_that_does_not_say_claims_the_weaker_rung`, `test_a_recounted_reason_set_cannot_be_reported_at_the_enumerated_rung` |
| A recounted verdict is never rendered as a probed one, in any surface | `test_a_recounted_verdict_is_never_rendered_as_a_probed_one` |
| The declaration can be refuted by the measurement and never confirmed by it, and a monotone system's verdict is unchanged | `test_the_absence_of_the_fingerprint_is_not_evidence_of_monotonicity`, `test_a_declared_monotone_system_reaches_the_verdict_it_always_did`, `test_a_declared_monotone_certificate_still_reports_pass_or_fail` |
| A reason the probe cannot separate is never promoted to `deleted`, on an exhaustive enumeration or any other — the licence in `sufficient-reasons.md` is deliberately unused | `test_a_reason_the_probe_cannot_separate_is_never_promoted_to_deleted` |
| Every private fact of a reason is switched off, so coverage does not depend on what a system's fields are called | `test_every_private_fact_of_a_reason_is_switched_off` |
| A report carries no narrative it did not measure | `test_report_for_an_arbitrary_system_carries_no_narrative_it_did_not_measure` |
| One run renders as five audience artefacts, and no two audiences disagree about a verdict | `test_the_five_audiences_all_render`, `test_no_audience_sees_a_different_verdict_from_another` |
| No audience projection drops the limits, or the notice that duties went unchecked | `test_every_audience_keeps_the_limits`, `test_every_audience_keeps_the_notice_that_duties_went_unchecked` |
| The affected-individual artefact carries no system internals, asserted as an exclusion | `test_the_affected_individual_view_leaks_no_system_internals` |
| The affected-individual artefact is a derivation and not a subset of an expert one, emits no heading it has nothing to put under, and does not let the disclaimer dominate its page | `test_the_lay_view_derives_content_no_expert_view_carries`, `test_the_lay_view_never_puts_a_heading_over_an_empty_box`, `test_the_lay_page_does_not_let_the_disclaimer_dominate` |
| Two audiences differ by content and not by framing, and an unknown audience is refused rather than widened | `test_two_audiences_differ_by_content_not_framing`, `test_an_unknown_audience_is_refused_rather_than_widened`, `test_the_cli_offers_the_five_audiences_and_refuses_a_sixth` |
| The unprojected rendering is the full report and is the auditor's | `test_the_default_rendering_is_the_full_report_and_the_auditors` |
| A pack is jointly satisfiable, or its unsatisfiable core names the duties that cannot hold together | `test_every_shipped_pack_is_jointly_satisfiable`, `test_a_contradictory_pack_is_reported_unsatisfiable_with_its_core` |
| Two requirements carrying the same property are found equivalent by the tool, with no human reading either TOML block | `test_the_eu_ai_act_logging_duties_are_reported_equivalent` |
| Vacuity coincides with the unreachable-trigger rule on the case that rule already handles, and the case is exercised | `test_vacuity_coincides_with_the_unreachable_trigger_rule`, `test_the_unreachable_trigger_case_is_actually_exercised` |
| The general vacuity rule catches a vacuous pass the trigger rule does not, and reports none on the shipped packs' own formulas | `test_the_general_rule_catches_a_vacuous_pass_the_trigger_rule_does_not`, `test_no_shipped_pack_is_vacuous_on_its_own_formulas` |
| A question the analysis cannot encode is skipped by name and never answered | `test_the_counterfactual_fragment_is_skipped_by_name_and_never_answered` |
| The temporal fragment is decided as a finite-trace formula, so the shipped `until` duty is no longer skipped by every question the analysis asks | `test_the_until_duty_is_no_longer_skipped_by_every_question_the_analysis_asks`, `test_every_shipped_temporal_duty_is_satisfiable_by_some_non_empty_finite_trace` |
| The finite-trace backend and rtamt cannot disagree about a shipped temporal duty | `test_the_ltlf_backend_agrees_with_the_monitor` |
| The temporal reading is future-only, non-empty, and refuses a question over the procedure's ceiling rather than running it | `test_a_past_operator_is_skipped_by_name_rather_than_rendered`, `test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable`, `test_a_question_over_the_atom_budget_is_refused_by_name`, `test_a_pair_the_procedure_refuses_never_renders_as_a_pair_it_cleared` |
| A counterfactual property reaches no trace logic, and a shared abstraction makes an entailment between two duties mean something | `test_the_counterfactual_atom_reaches_no_trace_logic`, `test_the_same_subexpression_is_the_same_atom_across_a_pack`, `test_the_phrase_atom_carries_the_axiom_the_z3_encoding_carries` |
| The temporal backend is an optional extra whose absence is a note, never a weaker answer | `test_the_analysis_says_so_when_the_extra_is_absent` |
| A mutation score travels with its limit, a system without rules gets none, and a duty no mutant moves is named | `test_a_mutation_score_travels_with_its_limit_and_a_system_without_rules_gets_none`, `test_a_duty_no_mutant_moves_is_named_as_having_no_discriminating_power` |
| An evidence basis is a kind and never a rank: two bases do not compare, and neither does a basis against a strength | `test_the_evidence_bases_are_not_ordered`, `test_a_basis_is_never_compared_against_a_strength`, `test_no_rendering_draws_a_basis_as_a_rung` |
| A result cannot carry a rung its basis does not admit, and the basis is derived from the duty rather than declared | `test_a_result_cannot_carry_a_rung_its_basis_does_not_admit`, `test_the_basis_is_derived_from_the_duty_and_never_declared`, `test_every_basis_admits_unattainable_so_the_capability_gate_is_never_bypassed` |
| The rungs a basis advertises are the rungs the engine ladder can reach, in both directions | `test_the_basis_admits_exactly_the_rungs_the_ladder_can_reach`, `test_an_assessment_duty_reaches_no_engine_at_all` |
| The three pressures are discharged: a graded duty is counted apart from an unsettled one, a counterfactual duty is never observed, and the certificate duty's ceiling is named as the duty's | `test_a_graded_duty_is_counted_apart_from_a_duty_no_engine_settled`, `test_a_counterfactual_duty_is_never_observed_however_long_the_trace`, `test_the_certificate_dutys_ceiling_is_named_as_the_dutys_and_not_the_systems` |
| The basis changed no verdict, the behavioural basis renders as it always did, and the shipped census is pinned | `test_the_basis_changed_no_verdict_and_no_strength`, `test_the_behavioural_basis_says_nothing_and_the_other_three_name_their_ceiling`, `test_exactly_two_shipped_duties_are_not_on_the_behavioural_basis`, `test_the_json_envelope_carries_the_basis_on_every_result` |
| No audience mistakes a kind for a rank, and the lay reader is shown no basis at all | `test_the_lay_audience_is_never_shown_an_evidence_basis` |
| This document is linked, and every test it names exists | `test_semantics_doc_is_linked_from_the_readmes`, `test_every_test_named_in_the_semantics_doc_exists` |

---

## 7. Who the report is for

`reasonsmith check --audience {developer,deployer,auditor,regulator,affected-individual}` renders
one conformance run five ways. **The projection changes what is shown and never what is claimed.**
Nothing is recomputed per reader: every part of every artefact is a part of the single
`ConformanceReport` the run already produced, selected by an `AudienceProjection`
(`src/reasonsmith/render.py`). A verdict a regulator is shown is the verdict a developer is shown
(`test_no_audience_sees_a_different_verdict_from_another`), and dropping the flag renders the full
report unchanged (`test_the_default_rendering_is_the_full_report_and_the_auditors`) — which is why
every generated document under `docs/` still regenerates byte-for-byte.

**The table below is authored, not derived.** It is the same kind of choice a pack author makes
when they pick a threshold: nothing in the law, in the packs or in the evidence says a deployer
should not see a counterexample. It is written here so it can be argued with, rather than left to
be reverse-engineered from a dataclass.

| Shown | developer | deployer | auditor | regulator | affected-individual |
|---|---|---|---|---|---|
| verdict | ✓ | ✓ | ✓ | ✓ | ✓ |
| limits, and the duties-not-checked notice | ✓ | ✓ | ✓ | ✓ | ✓ |
| evidence strength (tier, lattice) | ✓ | ✓ | ✓ | ✓ | — |
| declared scope/domains, headline, counts | ✓ | ✓ | ✓ | ✓ | — |
| binding vs interpretive, scope and domain limits | — | ✓ | ✓ | ✓ | — |
| required signals, signals absent from the trace | ✓ | — | ✓ | — | — |
| missing capability signals | ✓ | ✓ | ✓ | — | — |
| evidence summary | ✓ | ✓ | ✓ | ✓ | — |
| probe budget | ✓ | ✓ | ✓ | ✓ | — |
| counterexamples and trace witnesses | ✓ | — | ✓ | — | — |
| the plain-language account of what the system recorded | — | — | — | — | ✓ |

The reasoning, row by row:

- **auditor** is the full report, by identity: `AUDIENCES["auditor"] is _FULL`. An auditor's
  question is *what is the complete evidentiary basis*, and the report this package already
  emitted is the answer to it. That is the honest reason the no-flag default did not have to
  change to acquire an audience — not a coincidence worth hiding behind a duplicate table.
- **developer** asks *which signal is missing and where*, so it keeps every signal name, the
  absent-from-trace finding, the witness records and the counterexample inputs. It drops the
  binding/interpretive tag and the scope and domain limits: those decide whether a duty reaches
  this system, which is not a thing a developer changes by editing the system.
- **deployer** asks *does this duty reach my deployment, and what must I declare or procure*. It
  keeps the legal classification and the missing-capability finding, and drops the diagnostic
  signal lists and the witnesses. The witnesses are the sharper call: a witness table inlines
  real decision records, which in a consumer-credit deployment are personal data about
  applicants, and an operator does not need them to act.
- **regulator** asks *which duties were checked, how far does the claim reach, and what was not
  determined*. It keeps the strength, the legal classification, the evidence summaries, the probe
  budgets — the bound on a `probed` claim is exactly "how far does this reach" — and the limits.
  It drops signal names and witnesses: the internal architecture of a system and the personal
  data of the people it decided about are not what makes a claim's reach legible.
- **affected-individual** is the narrowest artefact and the one with a hard rule around it: it
  carries no system internals at all — no counterexamples, no probe budgets, no signal names, no
  solver output, and no strength vocabulary, because being told a duty is `probed` hands a person
  this tool's evidence model instead of an answer. `test_the_affected_individual_view_leaks_no_system_internals`
  asserts that as an *exclusion* over the run's own data rather than as a list of what should be
  present, so a later change that adds a leak fails rather than passes. It is also the one
  audience whose projection **emits**: `plain_account` turns on `render._lay_sections`, and every
  other row of the table above suppresses. Which is the point of the last row, and the answer to
  a defect this table used to describe as a design: built out of suppression flags alone, this
  artefact was the developer's report with parts removed — its word set a strict subset of the
  developer's, its difference empty — so the reader least able to fill a gap in was the one
  handed the most gaps. `test_the_lay_view_derives_content_no_expert_view_carries` is that
  measurement, kept as an assertion.

What the account may say is fixed by the same rule as everything else here, and is narrower than
the reader would like:

- **The system's own words, and the engines' own measurements. Nothing else.** The decision and
  the reason are quoted out of the decision record the run already read
  (`ConformanceReport.decisions`, `report.DECISION_RECORD_SIGNAL` and `report.REASON_SIGNAL`); a
  reason the stated ones left out is named with the label `engines/certificate.py` gave it when
  it re-ran the system's own inference. No sentence in it paraphrases a statute, explains a
  decision, or advises. This projection still will not manufacture the adverse-action statement a
  creditor owes a person — quoting the log is not writing one — and a report that read no
  decision record says exactly that rather than going quiet.
- **Absence of a finding is never completeness.** A run where no certificate measured whether the
  stated reasons were all the reasons prints a section saying so, because silence there reads to
  this reader as a clean result, and it is not one
  (`test_the_lay_view_never_puts_a_heading_over_an_empty_box`).
- **The limits are kept whole and folded.** No projection may drop a word of them
  (`test_every_audience_keeps_the_limits`), and on a page addressed to a layperson a 222-word
  legal caveat was also the largest thing on it. The HTML rendering puts them in a native
  `<details>` for this audience only, so they are one click and no scroll away
  (`test_the_lay_page_does_not_let_the_disclaimer_dominate`). The text rendering keeps them last
  and whole, where they are still the longest single block — the console has no fold, and
  shortening them is not on offer.
- **`--json` is not projected.** It stays the complete machine record, so a pipeline parsing it
  never loses fields to a display flag — and so `--audience affected-individual --json` is not a
  redaction. Redaction is a security property; this is a presentation one, and the two must not
  be confused. `ConformanceReport.decisions` is not in it either, for the opposite reason: the
  JSON is the findings record, and the decisions are an input the run read, not a finding it
  made. The envelope carries its own shape version, `schema_version`, so a consumer can tell one
  release's shape from another's without inferring it from the package version. It increments
  when a key is removed, renamed, or changes type or meaning, and not when one is added;
  `test_version_2_is_this_shape` pins the key set at each level to the current number, so a
  shape change made without moving it fails the suite.

---

## 8. What a *pack* means, checked against itself

Everything above is about a system's evidence. `reasonsmith validate-pack <pack> --analyse`
(`src/reasonsmith/analysis.py`) asks four questions about the duties themselves, which no `check`
run can answer because none of them is about any system.

The encoding is **`engines/proved.py`'s**, reached through the same `_ast_to_z3` and the same
`_Scope`. Exactly two things are said differently, and only where there is no system to say them
about: with no rule block, `present(signal)` and `contains(signal, "phrase")` have nothing to be
established by, so each becomes one uninterpreted Boolean constant shared across the whole pack,
with the single axiom `rulelang.contains_literal` itself implements — a value the record does not
carry contains no phrase. Every connective, comparison and arithmetic operator stays the engine's.
That matters for the reason the ASCII fold matters: a second encoding that disagreed with the first
would report findings about a pack the engines do not run.

**Joint satisfiability.** Is there any decision record at all that discharges every requirement of
the pack at once? A pack whose duties contradict each other reports systems violated for a reason
that is the pack's, and the unsatisfiable core names which duties cannot hold together
(`test_every_shipped_pack_is_jointly_satisfiable`,
`test_a_contradictory_pack_is_reported_unsatisfiable_with_its_core`).

**Subsumption and equivalence.** Does one requirement's property entail another's? An equivalence
reported here holds under *every* interpretation of the record atoms, so it holds for every system:
no system can satisfy one of the pair and violate the other, and a reader must not take two
agreeing verdicts for two independent checks. The shipped instance is EU AI Act Article 12(1) and
12(2), whose properties are byte-identical — a fact `docs/refinement.md` recorded in prose after a
human read the TOML, and which the tool now finds on its own
(`test_the_eu_ai_act_logging_duties_are_reported_equivalent`). The abstraction is **sound for what
it reports and incomplete for what it does not**: two properties it does not relate are not thereby
distinguishable by any system.

### The temporal fragment, decided as a finite-trace formula

Everything above decides one decision *record*. A `temporal` spec is not a property of one record,
so for a long time the analysis reduced the one shape that is — `always(f)` with `f` free of
temporal operators, through `engines/temporal.state_property_under_always` — and reported every
other shape skipped by name. `ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out` is a shipped
binding duty written with `until`, and no question this section asks could say anything about it at
all.

`src/reasonsmith/ltlf.py` closes that by handing the formula to a published decision procedure for
linear temporal logic over **finite** traces, which is the semantics a decision log has and the same
one `engines/temporal.py` claims for its reduction. It is **a syntax mapping and an emptiness
question**, on exactly the terms §2 sets for rtamt: `to_ltlf` renders a `spec` in the installed
procedure's syntax, a formula is satisfiable exactly when the automaton that procedure builds has an
accepting state, entailment is `left & !right` unsatisfiable, and equivalence is entailment both
ways. No temporal semantics, automaton construction, tableau or monitor is implemented in this
repository, and none may be
(`test_each_operator_of_the_fragment_has_one_ltlf_spelling`).

**The two backends must not be able to disagree, and that is the acceptance test.** rtamt scores
robustness over real-valued signals; the finite-trace procedure accepts or rejects a word over
abstracted atoms. They answer the same question about the same trace only while the two syntax
mappings render the operators the same way — and a `until` rendered as a `release`, an `always` that
lost a position or an implication turned round would be invisible in either backend alone. This is
the defect `test_the_solvers_fold_is_the_interpreters_fold` guards for `contains()`, in the same
shape: a generated corpus of traces per shipped temporal duty, both backends asked, and a failure at
the first trace on which they part (`test_the_ltlf_backend_agrees_with_the_monitor`). Only the
definite verdicts are compared — where rtamt reports NOT EVALUATED it made no claim — and the
comparisons that did happen are counted, because a differential test that quietly compares nothing
passes forever.

**Four things this reading costs, stated rather than left to be discovered.**

- **It is propositional, so every magnitude becomes an opaque atom.** `x <= 30` bears no relation to
  `x <= 90` here. `reasonsmith.ltlf.LTLF_ABSTRACTION_LIMIT` travels on every answer that rests on
  it, and the soundness story is the one `_PackScope` already tells: an entailment reported holds
  under every interpretation of the atoms and therefore for every system, and two duties it does not
  relate are not thereby distinguishable by any system. Satisfiability is reported only in the
  **affirmative**, because a model found over abstracted atoms may assign them an arithmetic no
  system could produce — so a negative would not be a claim about the pack. This is why the backend
  sits *beside* rtamt rather than replacing it: rtamt keeps every magnitude, this keeps every
  position, and neither subsumes the other.
- **Only the future fragment.** The installed procedure decides LTLf, which has no past operators,
  so a spec using `once`, `historically`, `prev`, `since`, `rise` or `fall` is skipped **by name**
  into `PackAnalysis.skipped`. Rendering one into a future operator would be implementing its
  semantics (`test_a_past_operator_is_skipped_by_name_rather_than_rendered`). No shipped duty uses
  one.
- **Every question is asked over a non-empty trace.** LTLf as the installed procedure implements it
  admits the empty trace, on which `always(f)` holds whatever `f` says — so without this every
  `always` duty in every pack would be reported satisfiable by a trace no monitor ever reads.
  `ltlf.NON_EMPTY` is the LTLf formula for "there is a position", conjoined into every question. It
  is a formula of the logic and not a construction over its automata
  (`test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable`).
- **There is a ceiling, and questions over it are refused by name rather than run.** The procedure
  enumerates the powerset of the atoms as the automaton's alphabet, which on this tree costs about
  9 s at five atoms and more than 90 s at six. There is no wall clock anywhere in this package — the
  same limit `docs/authoring-engines.md` states for a plug-in — so `ltlf.ATOM_BUDGET` is checked
  before the automaton is built (`test_a_question_over_the_atom_budget_is_refused_by_name`). Every
  shipped temporal duty is three or four atoms and is decided; every *pair* of them is seven, so the
  pack's temporal entailment questions are all reported **not decided either way**, which is a
  different fact from "no temporal duty entails another" and never renders as it
  (`test_a_pair_the_procedure_refuses_never_renders_as_a_pair_it_cleared`).

**No three-valued verdict is computed here, and that is a decision.** The runtime-verification
literature (Bauer, Leucker and Schallhart) distinguishes *satisfied on this finite prefix* from
*satisfied on every extension of it*, and that distinction is real for this package: a decision log
is a finite trace and §2 already says the trace is a sample. The installed procedure exposes an
automaton and no monitor construction over it, so the distinction is **not available from the tool**
and is not synthesised from one — a three-valued verdict this repository computed for itself would
be the temporal semantics it has just spent this section not implementing. Nothing on the strength
lattice (§4) moves for it either. A procedure that reports it is what would close this.

**The backend is an optional extra and its absence is a note.** `pip install reasonsmith` stays a
two-command demo; `pip install reasonsmith[ltlf]` adds the procedure. Nothing in `check`, in any
engine or in any shipped example touches it. With it absent, `PackAnalysis.temporal` is `None`,
`ltlf.UNAVAILABLE_NOTE` is printed, and no temporal question is answered from a weaker substitute
wearing the same words (`test_the_analysis_says_so_when_the_extra_is_absent`).

### Vacuity, defined for this evidence model

Kupferman and Vardi define vacuity against model checking a transition system, and Beer et al. gave
the subformula-replacement formulation this uses. Over a finite trace plus this repository's Z3
encoding it needs its own statement, because a loose one produces false alarms and an analysis that
cries wolf is an analysis nobody reads. The definition, restricted to the fragments this repository
ships:

> A requirement is **vacuously discharged** on a given evidence domain when some subformula of its
> `spec` can be replaced by *any* well-formed formula of the same fragment without changing the
> verdict.

Three things settle what that means here.

- **The domain is named on every finding.** With no system it is every assignment to the signals
  the properties read, where only a tautologous property is vacuous — and none of the shipped packs
  is (`test_no_shipped_pack_is_vacuous_on_its_own_formulas`). With a system exposing `logic()` it is
  the domain the proof rung itself quantifies over: the inputs the declared logic and constraints
  admit.
- **The check is two-point and it is exact, not a heuristic.** The target is one AST *occurrence*,
  so it occurs once, so the property is monotone or antitone in it; every replacement's value lies
  pointwise between the two Boolean constants, and a verdict equal at both ends is equal
  throughout. Only the outermost replaceable occurrence is reported: a subformula of a replaceable
  subformula is replaceable too and says nothing new.
- **Only the satisfied side is reported**, which is the restriction `engines/proved.py` already
  observes when it asks about an unreachable antecedent, and for the same reason: a violated
  verdict names a witness, and a witness is evidence about the system whatever else in the property
  could have been different.

**It coincides with the rule that was already here, and that agreement is the acceptance test.**
§4 (*A duty whose trigger never fired is not evaluated, at every rung*) refuses an implication whose
antecedent nothing in an engine's domain satisfies. That is exactly the case where the implication's
*consequent* is replaceable: if the antecedent is false everywhere the implication holds whatever
the consequent says, and conversely, taking the replacement to be a contradiction gives that the
antecedent is false everywhere. `test_vacuity_coincides_with_the_unreachable_trigger_rule` asserts
the two agree on every shipped implication against a system whose trigger fires and one whose never
does, and `test_the_unreachable_trigger_case_is_actually_exercised` keeps the agreement from being
between two rules that both always say no. Should they ever disagree, the divergence is a finding to
report here — not a definition to widen on either side.

**The general rule catches vacuous passes the special case does not.** Against the shipped symbolic
rule set, `ecoa_reg_b_1002_9_a_1_timing_of_notice` is `proved` satisfied and its trigger does fire,
so §4's rule says nothing about it — and its ninety-day counteroffer branch is nevertheless
replaceable by any formula, because that system's own batch window bounds every notice below thirty
days and the first disjunct settles the duty on every admissible input
(`test_the_general_rule_catches_a_vacuous_pass_the_trigger_rule_does_not`). That is a fact about
this system and this duty together, and it is not a defect in either.

### Mutation coverage, and what a score is not

With a system, the analysis mutates the rule block that system exposes through `logic()` — one
change per mutant: a comparison swapped for its neighbour or its opposite, a conjunction for a
disjunction, a number moved by one, a recorded statement blanked — rebuilds it as a `RulesAdapter`
over the mutated rules, re-runs the whole pack, and counts the mutants whose verdict or strength
each duty noticed. A duty no mutant moves has no discriminating power against these mutants, and is
named as such.

**A mutation score is not a coverage claim**, and `analysis.MUTATION_LIMIT` says so on every
analysis that carries one (`test_a_mutation_score_travels_with_its_limit_and_a_system_without_rules_gets_none`). Two limits, both plain:

- It reaches **only a system that exposes its decision logic as a rule block**, which is not most
  audited systems. A decision log, a probabilistic scorer and a language model have nothing to
  mutate, and every duty gets no score at all rather than a low one.
- Where it runs, the number is sensitivity to **these** mutants and to no others. It does not
  measure how much of a system a duty covers, and a duty scoring 1.0 is not thereby a good duty.

The mutant is a fresh adapter over the mutated rules rather than the original system with its
`logic()` swapped, so its `decide()` and its `logic()` are the same mutated program; the baseline is
the same construction over the unmutated rules. Otherwise the proof rung would report the
divergence between a mutated declaration and an unmutated procedure, and the count would measure
that instead.

The measured scores against the shipped symbolic rule set are in `RESULTS.md`, with the commit they
were taken at, because a number belongs where its provenance can travel with it.

### Where these questions come from

None of the four is invented here, and naming the sources is also how a reader checks that the
definitions were not bent to fit the code.

- **Vacuity.** O. Kupferman and M. Y. Vardi, *Vacuity detection in temporal model checking*
  (STTT 4(2), 2003; first at CHARME 1999) give the formulation used above — a subformula does not
  affect a property when replacing it changes nothing — and I. Beer, S. Ben-David, C. Eisner and
  Y. Rodeh, *Efficient detection of vacuity in temporal model checking* (Formal Methods in System
  Design 18(2), 2001) give the single-occurrence replacement check that makes it decidable in
  practice. §8 restricts both to the fragments of `rulelang.py`, over a finite trace and this
  repository's Z3 encoding, because the original setting is model checking a transition system and
  a definition carried across unexamined would report vacuity where there is none.
- **Satisfiability and subsumption of a rule set** are the oldest questions asked of a formalised
  regulation, and the framing this repository works in is T. J. M. Bench-Capon and F. P. Coenen,
  *Isomorphism and legal knowledge based systems* (Artificial Intelligence and Law 1(1), 1992):
  a legal knowledge base should stay *isomorphic* to its source — one rule per provision, in the
  source's own structure, so that a change in the law is a local change in the model and a lawyer
  can check one against the other. That is what `verbatim_text` and `drift.py` are for. Every
  requirement carries the provision's own words and its citation, and the monthly drift check
  re-fetches the official text and reports `match`, `differ` or `could-not-verify` per requirement
  without ever editing a pack. `--analyse` is the other half of the same discipline: isomorphism
  keeps a pack faithful to the source, and these checks ask whether the formulas it grew are
  consistent, non-redundant and doing work.

---

## 9. Open-textured predicates

Twenty-one of the twenty-nine shipped requirements are presence checks. The fourth column of
[`refinement.md`](refinement.md) says the same thing over and over about the rest — *meaningful*,
*sufficiently detailed*, *adequate*, *appropriate*, *without undue delay* were not modelled — and a
`present(signal)` atom stood in for each. That is not a bad proxy for those predicates. It is a
refusal to model them at all, and the largest single gap this tool has.

This section is the semantics of the machinery for them. **No shipped duty uses it**
(`test_no_shipped_pack_uses_either_open_texture_construct`), and which statutory predicate becomes
the first graded one is a legal reading rather than an engineering decision.

Two constructs answer different halves of the problem and compose rather than compete.

### `undetermined(signal, "predicate", "authority")` — the predicate nothing here settles

Some predicates are open-textured because their application to facts is contested and is settled by
an institution rather than by a computation. The construct says so in the property itself, naming
the predicate and **who would settle it**, and the result carries both
(`test_an_undetermined_atom_is_reported_undetermined_and_names_its_authority`).

The verdict is `inconclusive` at `strength=None` — this package's *not evaluated* — and the path is
the one `not_evaluated_for_unreachable_trigger` already established rather than a mechanism beside
it. Roughly three quarters of this behaviour already happened, incidentally: a duty whose predicate
nobody had narrowed fell down whichever un-evaluated path its shape happened to take, and the report
said an engine had fallen short rather than that the *law* had not been narrowed. What the construct
adds is that the pack states which predicate is open-textured, and the reader is told who resolves
it.

Three things it is deliberately not. Not `unattainable`: the gap is in the formalisation, not in the
system, and telling an adopter to change a system because a statute uses the word *meaningful* is
the wrong instruction. Not `not applicable`: the duty reaches the system, and only its application
to these facts is unsettled. And never `satisfied` or `violated` at any strength, because nothing
here applied the predicate — which is why `rulelang.eval_expression` **refuses** the atom rather
than answering it (`test_an_undetermined_atom_is_refused_by_the_two_valued_interpreter`). Every
trace-reading engine evaluates through that interpreter, so the refusal is a fact about the code
rather than a convention `report._engine_ladder` is trusted to keep — the same argument the
counterfactual atom's refusal rests on.

One atom leaves the whole formula unsettled, and `classify_fragment` says so before anything else
except the counterfactual question
(`test_an_undetermined_duty_dominates_the_settleable_parts_of_its_formula`). Answering the presence
conjunct of `present(r) and undetermined(r, "meaningful", …)` and reporting that as the duty's
verdict is the substitution presence-as-a-proxy already is.

### `degree(signal, "predicate")` — vagueness, which is not missing information

`undetermined()` is the conservative reading. It is also not the whole problem: *sufficiently
detailed* has no sharp boundary **even when every fact is known**, which is exactly the case
two-valued logic mishandles and many-valued logic exists for. `degree(signal, "predicate")` is an
atom whose value is a truth degree in [0, 1]; `reasonsmith.manyvalued` is the reading.

Four things are declared and none is defaulted.

**The algebra is a stated parameter of the pack.** Which residuated lattice the connectives are read
over decides what a conjunction of two `0.5`s means — Łukasiewicz says `0`, Gödel says `0.5`,
product says `0.25` (`test_the_three_algebras_disagree_about_a_conjunction_of_two_halves`) — so a
pack shipping a graded duty without `[grading] algebra` is refused at load, naming what is missing
(`test_a_pack_shipping_a_graded_duty_without_an_algebra_is_refused_at_load`), and a name outside
`manyvalued.ALGEBRAS` is refused where it is written
(`test_a_pack_declaring_an_algebra_this_package_cannot_read_is_refused`). The three shipped members
are the three fundamental continuous t-norms, each stored with its residuum, and each is checked
against the residuation law rather than asserted to satisfy it
(`test_each_algebra_is_a_residuated_lattice_on_the_grid`). A fourth member is a row in that table
and nothing else.

**The degree has a declared source, and it travels with the verdict.** A degree a system asserts
about itself is the `reason_is_specific` self-declaration wearing a lattice's clothes, so a
`Grading` is supplied to `check_conformance` beside the pack — third-party evidence, in the way a
decision trace is first-party evidence — and it names the authority that fixed the scale, what the
scale is, and how the degrees were obtained (`test_a_grading_must_state_who_fixed_the_scale`). The
result model refuses a degree that does not carry all three
(`test_a_result_cannot_carry_a_degree_without_the_source_that_fixed_it`), the same shape
`PROBE_BUDGET_FIELDS` already forces on a bounded search.

**The degree is quantified over the trace by the infimum**, which is the graded reading of "holds at
every decision" and the lattice meet in every algebra here
(`test_the_degree_of_a_trace_is_the_infimum_of_its_records`). It is deliberately not an average: an
average lets a long run of compliant decisions pay for a bad one, which is not what a universal duty
says. An empty trace therefore yields **no degree at all** rather than the top of the lattice —
having observed nothing is not evidence graded 1.0, and answering `1.0` there would be
`combine_verdicts`' vacuous `satisfied` rewritten as a number
(`test_a_graded_duty_with_no_grading_or_no_trace_is_not_evaluated`).

**A predicate nobody assessed is not a predicate assessed as false.** A grading that scores no
degree for an atom the property reads leaves the duty *not evaluated*, never at `0.0`
(`test_an_ungraded_atom_is_not_evaluated_and_never_a_degree_of_zero`).

**The connectives above a graded atom are the algebra's, including equivalence.** Conjunction,
disjunction and negation are the t-norm's, its dual and the one the residuum induces; an implication
is the residuum; and `φ <=> ψ` is the **biresiduum** `(φ → ψ) ⊗ (ψ → φ)`, which under Łukasiewicz
works out to `1 − |x − y|`
(`test_a_graded_equivalence_is_the_algebra_s_biresiduum`,
`test_lukasiewicz_equivalence_is_one_minus_the_distance`). It is derived from the residuum each
`Algebra` already stores rather than added as a fourth independent operation, for the reason
`negation` is derived: a member of that table stays internally consistent by construction. It is
reached only because `preprocess_spec` emits `Iff(...)` for `<=>` and `<->` rather than collapsing
them to `==` before the parse (§2, and
`test_the_rewriter_never_collapses_equivalence_to_a_comparison`). A crisp `==` the author actually
wrote is still a comparison of two degrees, is still a threshold, and is still refused, naming what
was written (`test_a_graded_comparison_the_author_wrote_is_still_refused`) — the point of the
distinction is that the author who wrote `<=>` no longer receives that refusal.

Everything in a graded formula with no `degree()` atom under it is answered by the two-valued
interpreter every other engine already uses, and mapped to `1.0`/`0.0`. That is not an optimisation:
it is what keeps `present()`'s treatment of a blank string and `contains()`' ASCII fold meaning the
same thing inside a graded formula and outside one
(`test_the_crisp_parts_of_a_graded_formula_mean_what_they_mean_everywhere_else`).

### The presentation rule, decided before anything renders a degree

**A truth degree is a distinct evidence basis and never a rescaled verdict.** A reader handed `0.7`
reads *seventy percent compliant*. [`authoring-packs.md`](authoring-packs.md) already forbids that
move for a group-parity duty, and the objection is stronger here, because a degree looks like a
measurement of the duty itself rather than of a rate the system declared. The rule, in four parts:

1. **A degree is never rendered alone.** The numeral, the algebra it was combined over, and the
   authority, scale and method that fixed it are one sentence. `render.degree_sentence` is the only
   place any rendering formats a degree, and
   `report.RequirementResult._validate_truth_degree` refuses a result that could not fill it — so
   the sentence can never be short of its parts and no surface can print the number by another route
   (`test_no_rendering_prints_a_bare_degree_without_the_source_that_fixed_it`, which checks the text
   report, the HTML dossier, the JSON envelope and all five audience projections).
2. **A degree is never a percentage and never a score.** It is not scaled to 100, not drawn as a
   bar, and not compared against another duty's.
3. **A degree carries no rung of the evidence lattice.** A result carrying one carries no
   `strength`, refused in the result model
   (`test_a_result_carrying_a_degree_cannot_carry_a_strength`), so nobody can read the number as a
   fraction of a proof. **The strength lattice did not move**: no member was added, and `graded` is
   not a rung. What such a duty *does* carry is the `assessment` evidence basis of §10, which is a
   kind and not a rank, and which is what stops a graded duty being counted as one an engine failed
   to settle (`test_a_graded_duty_is_counted_apart_from_a_duty_no_engine_settled`).
4. **A lay reader is shown the duty as unsettled, in words, and never the number**
   (`test_the_lay_audience_is_shown_the_duty_as_unsettled_and_never_the_number`). The
   affected-individual projection already suppresses an engine's account and already reports a
   `strength=None` result as a duty nothing here could settle; a degree shown there would be read as
   a score whatever sentence surrounded it.

### What a graded duty's verdict is, and why it is not derived from the degree

`inconclusive` at `strength=None`, with the degree carried as a measurement beside it. That is the
design and not a stub.

Turning a degree into `satisfied` needs a threshold. No statute states one for *sufficiently
detailed*, so a cut-off written into a shipped pack would be the pack author's number presented as
the regulation's — the objection [`authoring-packs.md`](authoring-packs.md) already makes about an
invented bound, arriving on a lattice instead of as a constant in a `spec`. The property language
refuses to let a pack state one at all: a `degree()` atom under a comparison or under arithmetic is
refused at load (`test_a_graded_atom_under_arithmetic_or_a_comparison_is_refused`), because
`degree(x, "p") >= 0.8` *is* the claim that eight tenths discharges the duty.

So the machinery measures, the measurement travels with its algebra and its source, and what
discharges the duty is a legal reading this tool does not make.

### The failure mode this is designed against

A graded semantics makes every duty *answerable*. That would destroy the single most valuable
property this tool has: **it refuses rather than guessing.** `unattainable` and `not evaluated` stay
reachable and are not quietly replaced by a low truth degree.

The order in `report._evaluate_requirement` is what enforces it. Both open-texture fragments are
dispatched **after** the capability gate, so a system that can show nothing is `unattainable`
exactly as it was before any of this existed, and never a low degree
(`test_a_system_that_can_show_nothing_is_unattainable_and_never_graded`). Neither fragment reaches
an engine at all: no rung of the ladder may claim to have settled a predicate this tool refuses to
settle.

### Two limits, and one thing that is now a decision rather than an omission

- **A graded atom under a temporal operator is refused at load**
  (`test_a_graded_atom_under_a_temporal_operator_is_refused_at_load`). A many-valued reading of
  `always` or `until` is a temporal semantics, and this repository implements none at any rung —
  rtamt monitors and `flloat` decides. The graded fragment is a property of one decision record,
  quantified over the trace by the infimum, and nothing here reads a degree across positions.
- **A spec using both constructs is refused**
  (`test_a_spec_using_both_open_texture_atoms_is_refused`). One says nothing here settles the
  predicate and the other asks for it to be graded; a formula carrying both would be classified
  `graded` and never graded in fact, which is a pack author told a semantics ran that did not.
- **A two-valued duty cannot acquire a degree**, and the gate is `classify_fragment`, exactly as it
  is for the counterfactual atom: a spec with no `degree()` atom is never classified `graded`, and a
  requirement carrying an algebra beside a two-valued formalism is refused
  (`test_a_two_valued_duty_cannot_acquire_a_degree`). A pack that declares an algebra hands it to
  its graded requirements and to no others, so shipping one graded duty leaves its presence checks
  as two-valued as they were
  (`test_a_pack_declaring_an_algebra_leaves_its_two_valued_duties_two_valued`).

---

## 10. The evidence basis: what the claim is about, beside how far it was pushed

§4's lattice is a **chain**, and a chain ranks one thing along one axis. Three shipped situations
are not on that axis at all, and each of them was, before this section, a sentence in a module
docstring that no result, no count and no rendering carried:

- a **counterfactual** duty is a property of a *pair* of executions, so `_engine_ladder` gives it
  two rungs and no trace rung beneath them;
- the **certificate** duty is measured against the inference artefact behind a decision, so its
  ladder reaches neither the trace rung beneath it nor the proof rung above it;
- a **graded** duty (§9) is `inconclusive` at `strength=None`, which made it indistinguishable in
  the counts and in the headline from a duty an engine merely failed to settle.

The answer is a second coordinate and **not** four more members of the lattice.
`verdict.EvidenceBasis` says what a duty's evidence is *about*; `Strength` says how far a claim
about it was pushed. The lattice did not move for any of the three: no member was added for them,
no member was re-ranked, and `test_semantics_doc_states_the_lattice_the_code_defines` generates §4's
sentence from `Strength` itself. It has moved **once** since, and the distinction this section draws
is what decided that it should: `recounted` is evidence about the *same* object as `artifact` —
the inference behind a decision — reached less deeply, so it is a rung on that row and not a fifth
basis (§3, *The inference artefact*). Evidence about a different object is a basis; evidence about
the same object, less deeply, is a rung. That is the test to apply to the next candidate.

### The four bases, and the literature each names

| Basis | What the evidence is about | Rungs it admits | Named after |
|---|---|---|---|
| `behavioural` | the system's own executions, one at a time | `unattainable`, `observed`, `probed`, `proved` | a **trace property** — Alpern & Schneider, *Defining Liveness*, IPL 21(4), 1985 |
| `relational` | a *pair* of executions | `unattainable`, `probed`, `proved` | a **2-safety property** — Terauchi & Aiken, SAS 2005; a hyperproperty rather than a trace property — Clarkson & Schneider, JCS 18(6), 2010; self-composition as the proof method — Barthe, D'Argenio & Rezk, CSFW 2004; the duty itself — Kusner, Loftus, Russell & Silva, *Counterfactual Fairness*, NeurIPS 2017 |
| `artifact` | the inference *behind* a decision, not what was decided | `unattainable`, `recounted`, `probed` | the **abductive explanation** — Ignatiev, Narodytska & Marques-Silva, AAAI 2019 (`docs/sufficient-reasons.md` §9 for the rest); the model-precise rather than behaviour-sampled side of formal XAI — Marques-Silva & Ignatiev, AAAI 2022; and, for the `recounted` rung, the **faithfulness** of a self-reported rationale — Jacovi & Goldberg, ACL 2020; erasure as its measurement — DeYoung et al., ACL 2020; the failure it measures — Turpin, Michael, Perez & Bowman, NeurIPS 2023 |
| `assessment` | how an open-textured predicate applies, per a named authority | `unattainable` alone | a **truth degree over a residuated lattice** — Hájek, *Metamathematics of Fuzzy Logic*, 1998; degree of truth is not degree of belief — Dubois & Prade, AMAI 32, 2001 |

Every row's rung list is read off what an engine can actually reach, and the two are held together
in both directions: no ladder may offer a rung its duty's basis refuses, and no basis may advertise
a rung *above* the strongest any shipped ladder offers
(`test_the_basis_admits_exactly_the_rungs_the_ladder_can_reach`). The second direction is a ceiling
check rather than an equality because a ladder entry is chosen without executing the system, so the
certificate branch cannot know whether the artefact behind a decision will enumerate its reasons or
recount them and declares the stronger of the two; that the lower rung is reachable is shown by
running the engine instead (`test_a_recounted_reason_set_reports_one_rung_below_an_enumerated_one`). `unattainable` is in every row
because it is not an engine's conclusion — the capability gate is a set difference over declared
signal names, identical for every duty, and it runs before any basis is consulted
(`test_every_basis_admits_unattainable_so_the_capability_gate_is_never_bypassed`). The `assessment`
basis reaches no engine at all, which is §9's guarantee restated in the result model
(`test_an_assessment_duty_reaches_no_engine_at_all`).

### A basis is a kind and never a rank

This is the whole reason the answer is a dimension rather than four more rungs, and it is
structural rather than conventional:

1. **The members carry no order.** `<`, `<=`, `>` and `>=` raise `TypeError` between two bases and
   between a basis and a strength, so nothing can sort them into a ladder, and no basis has a
   `rank` (`test_the_evidence_bases_are_not_ordered`, `test_a_basis_is_never_compared_against_a_strength`).
2. **A result may not carry a rung its basis does not admit.** `RequirementResult.__post_init__`
   refuses one, so a counterfactual duty cannot be reported `observed`, a certificate duty cannot
   be reported `proved` or `observed`, and an assessment duty cannot carry a rung at all
   (`test_a_result_cannot_carry_a_rung_its_basis_does_not_admit`). Three sentences that lived in
   three module docstrings are now one refusal.
3. **The basis is derived from the duty and never declared.** It is a function of the requirement
   alone — the certificate signal, then the fragment — so it is not a pack field, not a system's
   self-description, and not a function of which engine happened to answer
   (`test_the_basis_is_derived_from_the_duty_and_never_declared`). A declared basis would let a
   pack author or an adapter widen what a duty may claim, which is the move refusal 2 exists to
   stop.
4. **No rendering draws a basis as a rung.** `render.basis_sentence` is the only place any
   rendering words one — the discipline `render.degree_sentence` already carries for a degree — and
   the basis word never appears inside a step of the drawn lattice
   (`test_no_rendering_draws_a_basis_as_a_rung`).

### What each reader is shown

The rule is that the basis is only ever shown to explain a **ceiling**, so the behavioural basis —
every `record`, `logical` and `temporal` duty, which is every shipped duty but two — renders exactly
as it always did, with no sentence and the four-rung track that has always been drawn
(`test_the_behavioural_basis_says_nothing_and_the_other_three_name_their_ceiling`). For the other
three:

- **Text report.** One line under the verdict line, naming the basis and the rungs this duty can
  reach. It sits there because what it explains is the tier tag on the line above: `[PROBED]` with
  `proved` greyed out beside it is an instruction to expose more of the system, and for a
  certificate duty that instruction is false.
- **HTML dossier.** The strength-lattice track draws the rungs *this duty's basis admits* and no
  others, with the same sentence under it. Drawing all four for a duty that can reach two showed a
  reader two steps the system looked one exposure away from, when nothing it could expose would
  reach them (`test_the_certificate_dutys_ceiling_is_named_as_the_dutys_and_not_the_systems`).
- **Counts and headline.** `on_an_assessment` is a category of its own, split out of
  `not evaluated`. The two look identical on the result — `strength=None`, `inconclusive` — and
  mean opposite things: `not evaluated` says something fell short and instructs a reader to fix the
  evidence or the specification (§4), while a duty on the `assessment` basis had no rung to reach
  and nothing fell short (`test_a_graded_duty_is_counted_apart_from_a_duty_no_engine_settled`).
  It is deliberately **not** a rung and not a verdict, and it is drawn with no icon from the
  lattice.
- **The lay projection.** The affected individual is shown no basis at all, on the same flag that
  already withholds the strength (`test_the_lay_audience_is_never_shown_an_evidence_basis`). This
  is §9's presentation rule 4 applied to the other coordinate: a reader not shown the rungs cannot
  be shown a sentence about which of them are out of reach, and a bare word like `artifact` beside
  a verdict would be read as a grade of the answer whatever sentence surrounded it.
- **JSON.** Every result carries `basis`. It is an added key rather than a removed or retyped one,
  so `JSON_SCHEMA_VERSION` did not move, and the decision was made in
  `tests/test_json_schema_version.py` rather than skipped.

### What this does not do

- **It changes no verdict and no strength.** Nothing here measures anything; it describes evidence
  that was already measured. Every shipped duty against every shipped example system reports what
  it reported before (`test_the_basis_changed_no_verdict_and_no_strength`), and the change is
  visible in the generated documents as added sentences and shortened lattice tracks and in nothing
  else.
- **It does not rank a basis against a basis, or a duty against a duty.** §4 already says a
  strength is not comparable across requirements as a quality measure. A basis is not comparable at
  all: `artifact` is not more or less than `observed`, it is about something else, and a report
  whose duties sit on three bases has no aggregate to compute over them.
- **It adds no engine, no rung and no duty.** Two shipped duties are not on the behavioural basis
  and there is no shipped graded one, which is the census
  `test_exactly_two_shipped_duties_are_not_on_the_behavioural_basis` pins, on the shape
  `test_exactly_one_shipped_signal_is_outside_the_paper_s_taxonomy` already uses. A third arriving
  is a decision rather than a side effect of a pack edit.
- **It does not accommodate a basis nobody has.** Two more are foreseeable — evidence with a
  statistical (ε, δ) claim, and a certificate over a non-proof artefact such as a reason trace —
  and neither is designed for here. The first would be a fifth member of `EvidenceBasis` with its
  own row in `BASIS_RUNGS`, its own sentence and its own literature; the second is a widening of
  the `artifact` basis, which `docs/semantics.md` §3 (*The inference artefact*) already says cannot
  happen until the strength lattice can express an extracted reason. Neither is a reason to build
  anything today, and building for a pressure nobody has felt is what this repository spends its
  refusals avoiding.
