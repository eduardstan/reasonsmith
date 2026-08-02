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
```

A `[[requirement]]` block carries **exactly** these fields: `id`, `source_document`,
`article_clause`, `verbatim_text`, `stakeholder`, `formalism`, `spec`, `rationale`, `requires`,
`binding`, `scope`. Omitting one, or adding a field nothing reads, is a load-time error — an
omitted field would break source traceability, and an unread field would look like data the
codebase acts on when it does not.

## What each field is for

| Field | Meaning |
|---|---|
| `id` | A stable, unique identifier. Duplicate ids are rejected. |
| `source_document`, `article_clause` | The statute and clause the duty comes from. Together they are the citation a finding is reported against. |
| `verbatim_text` | The exact words of the clause, quoted for the report. |
| `stakeholder` | Whose interest the duty protects. |
| `formalism` | Which **fragment** of the property language `spec` is written in: `record` (a conjunction of `present(signal)` atoms), `temporal` (anything using a temporal operator), `logical` (any other property of one decision record). It says what the property *is*; it does not decide which engine answers it. The loader parses `spec`, works out the fragment and refuses a mismatch. |
| `spec` | The property, as a formula. Never prose — see "One property language" below. |
| `rationale` | What the duty asks, in English, for a human reading the pack. Nothing derives a verdict from its wording. |
| `requires` | The signal names the system must be capable of emitting for the requirement to be checkable at all. A system missing one is reported unattainable on the missing signal, without being run. It is a conjunction — see "An either/or clause" below before listing a branch of one here. |
| `binding` | Whether this duty is a legally binding obligation (`true`) or an interpretive recital/guidance item (`false`). |
| `scope` | The regulatory class the duty is limited to, from the fixed vocabulary `prohibited`, `high-risk`, `limited-risk`, `minimal-risk`, `general-purpose`; `""` means the duty is not class-limited. |

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
`implies`, `abs`, `min`, `max`. Every name in it is
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

**The fragment does not pick the engine.** How strongly a duty can be discharged is a fact about the
system under test, not about the pack: `report._engine_ladder` collects every engine the fragment
and the system's exposed surface allow, and takes the strongest evidence produced. A presence
property is `observed` against a trace, `probed` against a system exposing `decide()`, and `proved`
against one exposing `logic()`. `docs/semantics.md` §3.5 states the rule and its limits.

If a duty cannot be written in this language, that is a finding to record in `docs/semantics.md` —
not a reason to widen the language until it fits. Widening it to accommodate one stubborn duty is
how a property language becomes an untyped string again.

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
`present()` express a clause that only bites in some circumstances — read `docs/semantics.md` §4 on
what a vacuously satisfied duty does *not* tell a reader before relying on that.

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

## binding and scope have no default

Neither field has a default, here or in the loader. Defaulting a missing `binding` to `true`
would silently promote an unclassified item to a legal obligation, and defaulting it to `false`
would silently demote a statutory duty out of the compliance headline. Defaulting a missing
`scope` to `""` would leave an unclassified duty reachable for every system. A pack that has not
classified a requirement is a pack that must say so and be fixed, not one the code guesses for.

## A number in a `spec` is a parameter of the check, never a fact about the law

A `temporal` or `logical` spec can bound a measured quantity, and a statute rarely states the bound.
Where the clause names one — the 30 and 90 days of 12 CFR 1002.9(a)(1) — the quotation carries it and
the spec repeats it. Where it does not, the threshold is the pack author's, and writing one into a
requirement quoting a statute presents an invented figure as the regulation's. Prefer a bound the
record itself supplies: `gdpr_recital71_error_risk_minimised` compares a declared deviation against
the decision's own margin (`always(scope_statements_declared_deviation <=
artifact_logs_decision_margin)`), so the duty needs no invented number at all. If a constant is
unavoidable, say in the pack description what it is, what its default is, and why it was chosen.

## Verbatim text must be traceable to the print

`verbatim_text` is quoted in reports, so it must be a character-faithful quotation of the official
statutory text — never a paraphrase. `docs/legal-sources.md` is the retrieval record for the official
text behind the shipped packs and the worked example, and the shipped packs have tests that compare
their quotations with that record. A new pack that quotes a statute should record its source the
same way so a reviewer can verify the quotation against the print; `validate-pack` checks that the
field is nonblank, not that it matches an external source. A requirement with a blank source
document, clause or quotation is malformed rather than merely incomplete, because it cannot be
checked against the print at all.
