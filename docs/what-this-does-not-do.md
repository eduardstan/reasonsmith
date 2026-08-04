# What this does not do

Every compliance checker returns a green tick. This page is the four things reasonsmith cannot do,
stated together, with the numbers. Nothing here is new: each item is already stated in a committed
document in this repository, cited beside it, and each of those documents names the test or the
measured run that keeps the claim honest. If one of these gets closed, this page says when and by
what rather than quietly losing the paragraph.

Read it beside [`docs/semantics.md`](semantics.md), which states what each verdict *does* mean, one
engine at a time.

---

## 1. It takes the system's word about what it is

A system declares the semantics its inference implements, the deviation it reports from that
semantics, and the decision domain it operates in. **No engine here measures any of those against
the system's behaviour.**

This is measured, not feared. The run in
[`docs/findings-nesyarena.md`](findings-nesyarena.md) drove five real `nesyarena` provenances
through three packs, and finding 1 is its most important result: **two systems whose decisions
disagree with the semantics they claim were reported satisfied on every duty this tool could
check, with verdicts identical to the exact oracle's.** `top-1-proofs` returns a different
decision from its claimed semantics on **8 of 16 instances — half the battery** — and
`min-max-prob` deviates on **16 of 16**, flipping four decisions the other way. Both cleared.

Read a satisfied row as *the record has the fields*, never as *the system computes what it says it
computes*.

**What has changed since that finding, and what has not.** One duty now reads a system's
approximation error rather than ignoring it: `gdpr_recital71_error_risk_minimised` compares the
deviation a system declares about itself against that decision's own margin. It closes nothing
here, and the finding says so — the number it reads is still the system's own, so it rewards the
measurement and not the accuracy, and a system that under-reports passes. The open objective is
[`ROADMAP.md`](../ROADMAP.md) §5, whose measurable outcome is a check that fails today: drive two
systems differing *only* in whether their inference matches their declared semantics, and the two
reports come back identical.

The same shape covers the domain gate. `--system-domain consumer-credit` is what puts a system
inside a duty about credit decisions, and **nothing checks that a system declaring it issues
credit** ([`docs/findings-nesyarena.md`](findings-nesyarena.md), finding 3;
[`docs/authoring-packs.md`](authoring-packs.md)).

## 2. Depth is uneven, and here is the shape of it

Five packs ship, with 29 requirements between them. Counted by the fragment each property is
written in:

| formalism | requirements | what it asks |
|---|---:|---|
| `record` | 21 | a conjunction of `present(signal)` — the field is there |
| `logical` | 3 | any other property of one decision record |
| `temporal` | 4 | a property over the trace |
| `counterfactual` | 1 | invariance under one named protected variable |
| `undetermined` | 0 | a predicate no engine here settles, and who does |
| `graded` | 0 | a truth degree over an algebra the pack declares |

**Three quarters of the shipped duties are presence checks.** Reproduce the count with
`reasonsmith validate-pack ecoa eu_ai_act gdpr gpai table7`, which prints each requirement's
formalism.

That is not an accident of laziness: `packs/gpai.toml`'s eight Article 53 and 55 duties are
document-production duties, for which presence is the correct refinement and no stronger property
exists to write. But the consequence is real and [`ROADMAP.md`](../ROADMAP.md) §4 states it in its
own words: *"Breadth bought that way is real breadth and it is not depth."* A battery of engines
that mostly agrees by construction differentiates few systems, and the ratio moved the wrong way
when the fifth pack shipped — from 13 of 19 to 21 of 28.

Presence is also not adequacy, at the level of the individual duty: a reason field that is filled
in is not a reason that is sufficient. Where a clause supplies its own list of insufficient
wordings, this tool uses it and can go no further
([`docs/refinement.md`](refinement.md), *presence is not adequacy*). The two zero rows above are the
machinery for the rest of that problem, shipped with no duty on it: a pack can now say that
*meaningful* is open-textured and name who settles it, or carry a truth degree for it, and neither
turns the adjective into a verdict — a graded duty is reported *not evaluated* with its degree
beside it as a measurement ([`docs/semantics.md`](semantics.md) §9). Which clause gets the first one
is a legal reading ([`ROADMAP.md`](../ROADMAP.md) §6).

## 3. A rung is not a grade

`unattainable < observed < probed < proved` ranks **how a conclusion was reached**, never **what it
was reached about**. [`docs/semantics.md`](semantics.md) §4, *The lattice*, states the consequence,
and it is quoted rather than paraphrased here:

> It is not a confidence score, and it does not rank how much a reader should believe anything. A
> `proved` verdict over logic that has nothing to do with the deployed system is worth less than an
> `observed` verdict over a year of production decisions; the lattice cannot see that, because it
> ranks *how the conclusion was reached* and not *what it was reached about*. Strength is also not
> comparable across requirements as a quality measure: a duty that can only be discharged by a
> record check is not a weaker duty, and it can never rise above `observed`.

So a report full of `proved` verdicts is not a better report than one full of `observed` verdicts.
It is a report about a system that exposed more, and the question of whether what it exposed is the
system that runs in production is question 1 above.

**And a basis is not a rung.** Two shipped duties are not about the system's executions at all —
one is about a *pair* of them and one is about the inference artefact behind a decision — so
neither can reach every rung whatever the system exposes. `relational` and `artifact` name what the
evidence is about; they do not sit above or below `observed`, they are not ordered against each
other, and comparing two of them raises rather than answering
([`docs/semantics.md`](semantics.md) §10). A ceiling on one of those duties is a fact about the
duty, and a report that showed it as an unfinished ladder was telling a reader to expose more of a
system that could expose nothing further.

## 4. The strongest results need a system that exposes its inference, and most do not

`probed` needs a system that can be re-run on an input it has not seen. `proved` needs one that
exposes its decision rules. **A system that is only a decision log reaches `observed` and no
further, whatever the pack asks** — and most audited systems are only a decision log.

This is pinned, not merely observed: the shipped neural example
([`src/reasonsmith/examples/neural_scorer.py`](../src/reasonsmith/examples/neural_scorer.py))
is served behind an inference API and exports a log, and
`test_the_neural_system_cannot_be_raised_above_observed` in
`tests/test_docs_three_systems.py` fails if any change raises that ceiling. Raising a rung means
changing the *system*, never the adapter.

It shows up on real systems too. In the `nesyarena` run, **zero results landed at `probed` and zero
at `proved`** across five systems and three packs — the Z3 engine and the replay engine never ran
([`docs/findings-nesyarena.md`](findings-nesyarena.md), finding 2). The reason-deletion certificate
that the README leads with is the sharpest result this tool produces, and it is reachable only
because that system exposes the inference artefact behind each decision. A system that cannot be
opened up is reported `unattainable` on that duty and is never quietly returned to the presence
check beside it ([`docs/semantics.md`](semantics.md) §3, *certificate*).

---

**And the standing one, on every report this tool prints:** nothing here determines whether a legal
duty is discharged. That is not a limitation this page can engineer away — it is what the tool is
for. It reports what a formal specification asks and how the verdict was reached.
