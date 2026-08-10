# Authoring a requirement pack

A requirement pack is a TOML file the loader reads into `Requirement` and `Pack` structures
(`src/reasonsmith/spec.py`). Every requirement must be traceable to its statutory source: that is
the point of a pack, and it is why the loader refuses a pack that omits or adds a field rather
than guessing what a missing or unread field meant.

This guide documents the *fields*. The *method* — how a clause of law becomes a formula, and what
that formula does not discharge — is in [`refinement.md`](refinement.md), which carries one row per
shipped requirement and a fourth column naming what the refinement deliberately left out. Read it
before writing a `spec`, and add your requirement's row in the same commit: a test fails if a pack
gains a requirement that record does not name.

Validate your pack before shipping it — the CLI accepts the same names and files a `check` run
loads, because both go through the same loader:

```sh
python -m reasonsmith.cli validate-pack my_pack.toml
# after `pip install -e ".[dev]"` the same command is available as:
reasonsmith validate-pack my_pack.toml
```

`validate-pack` accepts one or more pack names or paths, prints what each pack contains, and exits
0. It stops at the first pack the loader refuses and exits 1, naming the file and, when a
`[[requirement]]` is at fault, its block and id.

Add `--analyse` to have the pack checked against *itself* rather than only parsed: whether its
requirements are jointly satisfiable, which of them entail or are equivalent to which, and which
are vacuously discharged. Two of those catch mistakes this guide can only warn about — a second
requirement whose property is the first one written differently, and a duty whose property no
evidence could make matter. Findings do not change the exit code; they are for you to read.
Add `--system-module <module>:<attribute>` as well — which imports and executes that module — and
vacuity is asked over the inputs that system's declared logic admits, and each duty gets a mutation
score against single-point mutants of that system's rules. `docs/semantics.md` §8 states what each
answer means, and what a mutation score is not.

## Structure

```toml
[pack]
id = "my_pack"
title = "A human-readable title"
description = "What the pack covers, and any sharp edge in it."

[source]
document = "Official statute name"
publication = "Official collection"
url = "https://..."

[[requirement]]
id = "unique_requirement_id"
source_document = "Statute name"
article_clause = "Exact clause citation"
verbatim_text = """Exact text of the clause"""
stakeholder = "affected individual"
formalism = "record"          # which fragment of the property language `spec` is written in
spec = "present(signal_a) and present(signal_b)"
rationale = "What the duty asks, in English."
requires = ["signal_a", "signal_b"]
binding = true                # true = legal obligation, false = interpretive recital/guidance
scope = "high-risk"           # or "" for a duty that is not class-limited
domains = ["consumer-credit"] # or [] for a duty that is about no particular kind of decision
deontic_type = "obligation"   # what kind of normative sentence the clause is
defeasibility = "strict"      # whether the clause states an exception, and whether `spec` carries it
```

A `[[requirement]]` block carries **exactly** these fields: `id`, `source_document`,
`article_clause`, `verbatim_text`, `stakeholder`, `formalism`, `spec`, `rationale`, `requires`,
`binding`, `scope`, `domains`, `deontic_type`, `defeasibility`. Omitting one, or adding a field nothing reads, is a load-time error — an
omitted field would break source traceability, and an unread field would look like data the
codebase acts on when it does not.

## What each field is for

| Field | Meaning |
|---|---|
| `id` | A stable, unique identifier. Duplicate ids are rejected. |
| `source_document`, `article_clause` | The statute and clause the duty comes from. Together they are the citation a finding is reported against. |
| `verbatim_text` | The exact words of the clause, quoted for the report. |
| `stakeholder` | Whose interest the duty protects. |
| `formalism` | Which **fragment** of the property language `spec` is written in: `record` (a conjunction of `present(signal)` atoms), `temporal` (anything using a temporal operator), `logical` (any other property of one decision record), `counterfactual` (the one relational atom), `undetermined` and `graded` (predicates the law states without a sharp boundary — see "A predicate the law states without a boundary" below). It says what the property *is*; it does not decide which engine answers it. The loader parses `spec`, works out the fragment and refuses a mismatch. |
| `spec` | The property, as a formula. Never prose — see "One property language" below. |
| `rationale` | What the duty asks, in English, for a human reading the pack. Nothing derives a verdict from its wording. |
| `requires` | The signal names the system must be capable of emitting for the requirement to be checkable at all. A system missing one is reported unattainable on the missing signal, without being run. It is a conjunction — see "An either/or clause" below before listing a branch of one here. |
| `binding` | Whether this duty is a legally binding obligation (`true`) or an interpretive recital/guidance item (`false`). |
| `scope` | The regulatory class the duty is limited to, from the fixed vocabulary `prohibited`, `high-risk`, `limited-risk`, `minimal-risk`, `general-purpose`; `""` means the duty is not class-limited. |
| `deontic_type` | What kind of normative sentence the **clause** is, from `reasonsmith.spec.DEONTIC_TYPES`: `obligation`, `permission`, `prohibition`, or `reparation` (a duty whose antecedent is a violation or a harm). It classifies the clause and not the property, and the two may differ — see "the two classifications no engine reads" below. |
| `defeasibility` | Whether the clause states something that switches the duty off, and whether `spec` carries it, from `reasonsmith.spec.DEFEASIBILITY_CLASSES`: `strict`, `defeasible-modelled`, `defeasible-unmodelled`, `trigger-unmodelled`. |
| `domains` | The kinds of decision the duty is about, from `reasonsmith.spec.DECISION_DOMAINS`; `[]` means the duty is about no particular kind. A different axis from `scope`, gated separately, and matched by intersection — see "the decision-domain vocabulary is yours, not the regulation's" below before writing one. |

Signal names conventionally start with the Section 6.3 taxonomy prefixes (`provenance_`,
`artifact_logs_`, `stability_signals_`, `scope_statements_`). The loader enforces nothing here: a
name outside the taxonomy is allowed and simply never supplied by an adapter that does not emit it.
The packs shipped in this repository are held to the prefixes by
`test_pack_loads_and_validates`, so a signal added to one of them must carry a taxonomy prefix —
including the free names a `logical` requirement's `spec` reads.

## One property language

Every `spec`, in every fragment, is a formula in the language of `src/reasonsmith/rulelang.py`:
presence atoms (`present(signal)`), phrase atoms (`contains(signal, "literal")`), comparisons over
signal values, boolean connectives and arrows, the temporal operators, and the rulelang calls
`implies`, `abs`, `min`, `max`. The arrows are `->` / `=>` / ` implies ` for implication and `<=>` /
`<->` for equivalence; both are connectives and neither is a comparison, so `<=>` is admitted in a
graded `spec` where `==` between two degrees is not (below, and [`semantics.md`](semantics.md) §2). Every name in it is
resolved against the decision record the system produces, so the names in `spec`, the names in
`requires` and the names the system's `logic()` declares are one vocabulary, not three — and the
loader refuses a `spec` reading an *unconditional* signal `requires` does not gate.

Two load-time checks make `formalism` mean something:

- **The spec must be in the language.** Prose in `spec` is a load error. It used to be the norm for
  a `record` duty — nothing parsed that field, so prose and an STL formula sat three lines apart in
  packs and a reader could not tell which was checked.
- **The declared fragment must be the one the formula belongs to**, exactly. An STL formula labelled
  `record` is refused rather than silently answered by a presence check nobody wrote. The match is
  exact and not merely compatible: a presence conjunction is also a well-formed `logical` property,
  and accepting it as one would cost the record engine's per-signal, per-record diagnostics.

There are three further fragments and each behaves unlike the first three.
`counterfactually_invariant(outcome_signal, protected_signal)` — hold every input fixed, move one
named variable, and the decision must not move — is a property of a *pair* of executions and
classifies into `counterfactual`. Both arguments are signal names and never expressions, the two
must differ, and **the atom is the whole of a `spec` or no part of one**: a conjunction, a negation
or a temporal quantification over it is a load error rather than a duty nothing can answer. Its
ladder has no trace rung at all, so a system exposing neither `logic()` nor `decide()` is reported
*not evaluated* however long its log, and a system whose declared logic has no notion of the
protected variable is reported *unattainable* rather than satisfied. Writing one means reading
`docs/semantics.md` §3, *counterfactual*, first — in particular that the protected variable is an
input the decision procedure accepts and **not** a field a decision record should be made to carry.
Both names still belong in `requires` — the protected one is what the engine reports as missing
when a system has no notion of it — but it is the single name the capability gate does not
subtract, so a duty written this way never tells an adopter to start logging a prohibited basis.

The fifth and sixth are `undetermined` and `graded`, for predicates the law states without a sharp
boundary; both are below, under *A predicate the law states without a boundary*.

**The fragment does not pick the engine.** How strongly a duty can be discharged is a fact about the
system under test, not about the pack: `report._engine_ladder` collects every engine the fragment
and the system's exposed surface allow, and takes the strongest evidence produced. A presence
property is `observed` against a trace, `probed` against a system exposing `decide()`, and `proved`
against one exposing `logic()`. `docs/semantics.md` §3.5 states the rule, its limits, and the one
duty given a ladder of a single rung — where a weaker engine would answer a *different* property
under the same duty's name rather than the same one with weaker evidence.

If a duty cannot be written in this language, that is a finding to record in `docs/semantics.md` —
not a reason to widen the language until it fits. Widening it to accommodate one stubborn duty is
how a property language becomes an untyped string again.

## A predicate the law states without a boundary — two ways to write it

Most of what a shipped pack has left out is not a construct. It is a *predicate*: *meaningful*,
*sufficiently detailed*, *adequate*, *appropriate*. Twenty-one of the twenty-nine shipped
requirements are presence checks and the fourth column of [`refinement.md`](refinement.md) says so
row after row. There are two ways to write one, and both are the fifth and sixth fragments.

**`undetermined(signal, "predicate", "authority")`** says this tool does not settle the predicate
and names who does. The duty is reported *not evaluated*, the result names both, and the reader is
told that nothing here says the duty is met and nothing here says it is breached. One such atom
anywhere leaves the whole formula unsettled, so `present(r) and undetermined(r, "meaningful", …)` is
not answered by its presence conjunct. Use it when the honest answer is that applying the predicate
to these facts is somebody else's job — a supervisory authority, a court, a published guideline —
and name that body specifically enough that a reader knows where to take it. The signal argument
still belongs in `requires`: a system that cannot emit the thing the predicate is about is
`unattainable`, and that answer is not displaced by this construct.

**`degree(signal, "predicate")`** says the predicate is *vague* rather than merely unsettled — that
it has no sharp boundary even when every fact is known — and asks for a truth degree. Writing one
commits the pack to two further things:

- **Declare the algebra.** A `[grading]` table at pack level, `algebra = "lukasiewicz"` /
  `"godel"` / `"product"`. A pack with a graded duty and no such table is refused at load, because
  which residuated lattice the connectives are read over decides what a conjunction of two `0.5`s
  means and no reader could tell which one answered. The declaration reaches the pack's graded
  requirements and no others, so a pack that ships one graded duty leaves its presence checks
  exactly as two-valued as they were.
- **Know that the pack does not supply the degrees.** They come from a
  `reasonsmith.manyvalued.Grading` a *caller* passes to `check_conformance`, naming the authority
  that fixed the scale, what the scale is and how the degrees were obtained. A degree the audited
  system asserts about itself is the `reason_is_specific` self-declaration wearing a lattice's
  clothes (*a phrase in a `spec`*, below), and this design refuses it in the same terms.

Two shapes are load errors, and both are the same refusal. A `degree()` atom under a **comparison or
arithmetic** — `degree(r, "detailed") >= 0.8`, and `degree(r, "detailed") == degree(q, "adequate")`
with it — states a threshold, which is the pack author's number presented as the regulation's, and is
exactly the hazard *a number in a `spec`* describes arriving on a lattice. Equivalence is not that
comparison: `degree(r, "detailed") <=> degree(q, "adequate")` is a connective, read over the
algebra's **biresiduum** `(φ → ψ) ⊗ (ψ → φ)` in the way an implication is read over its residuum, and
is admitted. The difference is what the author wrote, and `==` still gets the refusal. A `degree()` atom under a **temporal operator** asks for a many-valued reading of
`always` or `until`, and this repository implements no temporal semantics at any rung.

**Nothing turns a degree into a verdict**, here or anywhere. A graded duty is reported *not
evaluated* with the degree carried beside it as a measurement, and what discharges the duty is a
legal reading. Read [`semantics.md`](semantics.md) §9 in full before writing either atom — in
particular the presentation rule, which is why a degree never appears in a report without the
authority, scale, method and algebra that fixed it.

## A phrase in a `spec` is the clause's own words, never the pack's

`contains(signal, "phrase")` asks whether the text a record carries for a signal carries a phrase.
It is how a duty escapes *presence is not adequacy* — a reason field containing `"n/a"` is present,
and 12 CFR 1002.9(b)(2) does not accept it — but the escape is narrow and the discipline is the same
as for a number.

**Only a clause that supplies its own constraint may use it.** 12 CFR 1002.9(b)(2) names two
statements that are *insufficient*, so `ecoa_reg_b_1002_9_b_2_specific_reasons` can check that
neither was made without anyone deciding what *specific* means. A phrase you chose because it seemed
like a bad reason is an invented standard presented as the regulation's, exactly like an invented
threshold. Quote the clause in `verbatim_text`, put the phrase in the `spec`, and if the phrase is a
*reading* of the clause rather than a contiguous quotation — the ECOA duty distributes
`internal standards or policies` into two — say so in `rationale`.

**Never ask the system to grade itself.** A signal such as `reason_is_specific` would make the
verdict a restatement of the system's own opinion of itself. reasonsmith checks what a system says,
not whether it was honest (`docs/semantics.md` §3), and a self-declared adequacy flag is not an
adequacy check.

**What the atom does and does not do.** It is a substring test with ASCII case folding: it does not
paraphrase, so a clause's meaning expressed in other words passes. A non-ASCII phrase is refused at
load time, because the fold must stay reproducible character-for-character by the solver. A record
carrying no value for the signal contains no phrase, which is what lets an implication guarded by
`present()` express a clause that only bites in some circumstances — read `docs/semantics.md` §4
before relying on that: a duty whose trigger fires nowhere is reported *not evaluated* at every
rung, so a pack that guards a duty this way buys the correct absence of a false violation and loses
the clean line the duty used to get where the clause never bit.

## An either/or clause

A clause that offers a lawful choice — "and either: (i) … or (ii) …" — becomes a disjunction in
`spec`, and the disjuncts **must not** go in `requires`. `requires` is a conjunction: a system
missing any one of its names is reported unattainable without being run, so gating both branches
reports a system that lawfully supplied one of them unattainable, and gating one reports the
creditor that took the other. List only what the clause demands whichever branch was taken. The
loader knows the difference and exempts a signal read only inside a disjunction; everything else is
gated as before.

The exemption is an either/or exemption, not an `or` exemption. Two conditions narrow it, and both
are checked by `rulelang.unconditional_signal_names`. Every branch of the disjunction must be
settled by `present()` atoms alone: `(latency <= 30) or (latency <= 90)` gates `latency`, because a
magnitude has to be readable before either operand exists, and a system that cannot emit it belongs
in the unattainable answer rather than in a run that comes back not evaluated. And a name occurring
in *every* branch is needed whichever branch settles the formula, so it stays gated — the exemption
is the disjunction's names minus the names common to all of its branches.

Three consequences to write down rather than discover. A branch signal no `requires` names is never
asked for by the unattainable analysis, so a system that declares *neither* branch is judged on its
trace and reported violated rather than unattainable — say so in the pack description, as
`packs/ecoa.toml` does. A typo inside a disjunct is not caught at load time; it becomes a branch
nothing can ever satisfy. And a disjunction is not a conjunction of `present()` atoms, so the duty
leaves the `record` fragment: written as `temporal`, it is quantified over the trace, and the
observed engine reports a log holding a single decision not evaluated rather than satisfied or
violated. `ecoa_reg_b_1002_9_a_2_written_statement` is the worked example, and `docs/refinement.md`
records what its disjunction still does not capture.

## The two classifications no engine reads

`deontic_type` and `defeasibility` are carried by the loader and read by nothing else. They exist
so that one recurring claim about the shipped packs — *the general rule is formalised, the
exception is not* — can be counted rather than repeated, and the count is
`docs/refinement.md`, **The defeasibility census**. Read that section before writing either field;
it states what each member claims, and the discipline the classification is held to. Three rules
matter when you are the one writing them:

- **Classify the clause, not your property.** GDPR Article 22(1) is a `prohibition` even though the
  property shipped for it is a presence check on a log. Where the two disagree, that disagreement
  belongs in the fourth column of the refinement record, and this field is what makes it countable.
- **A defeater is not a trigger.** *Unless notice is provided in accordance with paragraph (c)* is
  a defeater — it overrides an otherwise-applicable duty, and it is what
  `defeasible-modelled`/`defeasible-unmodelled` are about. *When adverse action is taken* is a
  trigger: a condition of application, expressible today as the antecedent of an implication if a
  signal for it exists. A clause with both is classified by its defeater.
- **Only sourced exceptions count.** A defeater counts where the clause states it in your
  `verbatim_text`, or in a clause `docs/legal-sources.md` retrieved. An exception you know about
  from memory is a reason to retrieve the clause, not a reason to write
  `defeasible-unmodelled`.

Nothing here reasons defeasibly, and neither field changes any verdict. A pack that writes
`defeasible-modelled` is claiming its own `spec` carries the exception, in the ordinary
propositional structure the language already has — the way
`gdpr_art22_1_no_prohibited_decision_for_any_input` carries Article 22(2)'s three bases.

## binding, scope and domains have no default

None of the three has a default, here or in the loader, and neither does either classification above. Defaulting a missing `binding` to `true`
would silently promote an unclassified item to a legal obligation, and defaulting it to `false`
would silently demote a statutory duty out of the compliance headline. Defaulting a missing
`scope` to `""`, or a missing `domains` to `[]`, would leave an unclassified duty reachable for
every system — and in the `domains` case that is exactly the false positive the gate exists to
stop, reintroduced as a default and invisible, because an omitted field would then be
indistinguishable from a deliberate `[]`. A pack that has not classified a requirement is a pack
that must say so and be fixed, not one the code guesses for
(`test_a_pack_that_has_not_classified_a_requirement_is_refused`).

## The decision-domain vocabulary is yours, not the regulation's

`scope` and `domains` look alike and are not alike. The five regulatory classes are *one statute's
own vocabulary*: the EU AI Act defines prohibited, high-risk and the rest, so a pack quoting the
Act can quote its classes too. **No statute defines a list of decision domains.** Consumer credit,
employment, housing, insurance, healthcare and criminal justice are carved differently by every
regime that carves them at all; the GDPR is not domain-limited in the first place, and the AI Act
works from Annex III use-cases rather than subject matters. `DECISION_DOMAINS` is therefore a list
this repository wrote, it is deliberately coarse, and it is wrong somewhere.

Write one into a requirement anyway, when the duty is genuinely about a subject matter — but owe it
the same discipline this guide already demands of an invented threshold (*a number in a `spec`*,
below). **Say in the pack description that the classification is the pack author's and not the
regulation's**, exactly as `packs/ecoa.toml` and `packs/table7.toml` do; a shipped pack that limits
a duty to a domain without saying so fails
`test_every_shipped_pack_classifies_every_requirement`. What the gate buys is one guarantee and
not a taxonomy:

> A system that has not declared its domain is never reported `satisfied` on a domain-limited duty.

Three rules follow from that, and each is a test:

- **Undeclared is `not_applicable`, not `inconclusive`.** The duty did not reach the system, so
  nothing about the system was checked and no strength may be claimed — the same answer, and the
  same wording discipline, the class gate already gives an undeclared class. The reason string says
  which of the two ways it failed to reach, so *not applicable* is never read as *cleared*
  (`docs/semantics.md` §4, `test_an_undeclared_system_cannot_reach_satisfied_on_a_domain_limited_duty`).
- **`domains = []` is a wildcard, and it is a classification.** A duty about no particular kind of
  decision reaches every system, including one that declares nothing — GDPR Article 22 governs a
  solely-automated decision whatever it is about. That behaviour is safe only because it has to be
  written down: the field is required, so the wildcard is never reached by forgetting
  (`test_a_duty_with_no_domain_still_reaches_a_system_that_declares_none`).
- **Matching is intersection, and one shared domain is enough.** A duty may govern several domains
  and a system may decide in several. Demanding that the system's declaration be a subset of the
  duty's would put a lender that also underwrites insurance out of Regulation B's reach, which is
  wrong in the direction that matters — it would clear a duty that does govern the system
  (`test_matching_is_intersection_so_one_shared_domain_is_enough`).

A caller declares the other side with `--system-domain` (repeat it for a system that makes more
than one kind of decision), or by setting `system_domains` on an adapter. Both sides are checked
against the vocabulary, so a misspelling is refused where it is written rather than silently
matching nothing.

## A number in a `spec` is a parameter of the check, never a fact about the law

A `temporal` or `logical` spec can bound a measured quantity, and a statute rarely states the bound.
Where the clause names one — the 30 and 90 days of 12 CFR 1002.9(a)(1) — the quotation carries it and
the spec repeats it. Where it does not, the threshold is the pack author's, and writing one into a
requirement quoting a statute presents an invented figure as the regulation's. Prefer a bound the
record itself supplies: `gdpr_recital71_error_risk_minimised` compares a declared deviation against
the decision's own margin (`always(scope_statements_declared_deviation <=
artifact_logs_decision_margin)`), so the duty needs no invented number at all. If a constant is
unavoidable, say in the pack description what it is, what its default is, and why it was chosen.

## A group rate is not a fact about a decision, and nothing here checks one

The rule above — prefer a bound the record supplies — has a limit worth writing down, because the
place an author is most likely to reach for it is the place it fails. Nothing stops you writing a
group-parity duty today. A `logical` spec such as

```
abs(scope_statements_group_a_approval_rate - scope_statements_group_b_approval_rate) <= 0.05
```

with both names in `requires` loads, validates and runs, and a report comes back with a verdict on
it. **Do not read that verdict as a fairness finding.** Both operands are numbers the system
supplied about itself, so the check compares a self-declaration with a self-declaration. Run the
same system against a log declaring `0.80` and `0.79` and the duty is `satisfied` at `observed`;
run it against a log declaring `0.80` and `0.40` and the same duty is `violated`. Nothing in
reasonsmith recomputed either pair from the decisions in the trace, so what moved was the
declaration and not the behaviour. This is the same objection as a `reason_is_specific` flag
(*a phrase in a `spec`*, above), arriving as a number rather than a boolean and therefore looking
like a measurement.

There is no guard against this, and you should not expect one to catch you. Two protections do
exist, and both are narrower than the hazard:

- **The `requires` gate.** A system that declares neither rate is reported unattainable and is never
  run, so it cannot reach `satisfied` on the duty — the same guarantee the domain gate buys. What it
  does not do is judge a rate that *is* declared: a system willing to state a flattering figure is
  exactly the system the gate lets through.
- **The computed-magnitude guard on `proved`.** The proof rung refuses a property that reads free
  names as magnitudes when the system's declared rules assign none of them, on the ground that
  arithmetic over numbers nobody computed is not a fact about the system
  (`docs/semantics.md` §3.5, *When the magnitudes are not the system's own*). So a parity spec does
  not reach `proved` through a system whose rules never derive the rates. It says nothing about the
  `observed` rung, which reads the trace as written and answers.

The reason this is not merely unimplemented is that a group rate is a **population** statistic and
every engine here answers about **one decision record**, or — since the counterfactual fragment
shipped — about **one pair** of them. Neither is a population. `ROADMAP.md` objective 3 now records
that no group-statistical criterion can earn a verdict on this evidence model and why, and the GDPR
Recital 71 row of [`refinement.md`](refinement.md) records that no *distributional* fairness
property is checked here. Read both before deciding a parity spec is close enough: this gap is not
scheduled to close, and a duty that shipped in its place answers a different and much narrower
question.

The encoding gives you a second, quieter symptom, and it is worth knowing what you are looking at
when you hit it. A property of one record can only read a field of that record, so a population
figure has to be repeated identically in every line of the log. The trace then contains the same
statistic three times, not three measurements, and the violated finding reads `failed at decision
step(s) [0, 1, 2]` — three breaching decisions, when there was one number. The step indices in a
parity finding count records, not findings, and they will overstate the breach every time.

## Verbatim text must be traceable to the print

`verbatim_text` is quoted in reports, so it must be a character-faithful quotation of the official
statutory text — never a paraphrase. `docs/legal-sources.md` is the retrieval record for the official
text behind the shipped packs and the worked example, and the shipped packs have tests that compare
their quotations with that record. A new pack that quotes a statute should record its source the
same way so a reviewer can verify the quotation against the print; `validate-pack` checks that the
field is nonblank, not that it matches an external source. A requirement with a blank source
document, clause or quotation is malformed rather than merely incomplete, because it cannot be
checked against the print at all.

## Shipping a pack as its own package

A pack does not have to live in this tree. Declare it in the `reasonsmith.packs` entry-point group
and `load_pack` resolves it by name once your package is installed:

```toml
# your package's pyproject.toml
[project.entry-points."reasonsmith.packs"]
my_pack = "my_package:PACK_PATH"
```

The entry point resolves to a path to the TOML file, or to a zero-argument callable returning one —
the second form is how a package that ships its pack inside a wheel points at it
(`importlib.resources` is the usual way to produce that path).

Nothing else changes. There is one loader and one lookup order — a built-in pack file first, then an
installed package's, then the name read as a path — so an externally provided pack is refused by
exactly the checks an in-tree one is: the exact field set, the fragment classification, the
`requires` gate, all of it. Validate it the same way, by name:

```sh
reasonsmith validate-pack my_pack
```

A built-in wins a name collision: an entry point named for a shipped pack is refused with a warning
and the built-in stands, so installing a package can never change what `load_pack("gdpr")` means.

Engines install the same way, through `reasonsmith.engines` — see
[`authoring-engines.md`](authoring-engines.md), which is also where the discipline lives: what a
plug-in may claim, and what a `proved` from an engine this repository never audited is worth.

For the model-free autoformalisation verification gates, see [`autoformalization.md`](autoformalization.md).
