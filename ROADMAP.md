# Roadmap

This file exists so a contributor or a reviewer can see what is missing without access to anyone's
private backlog. Every objective below is a gap this repository's own documents already state, and
each one cites where. Nothing here is aspirational: an item is on this list because a committed
document names it as a limit, not because it would be nice to have.

Each objective gives a **measurable outcome** — a check that fails today and would pass when the
objective is met — and what it **depends on**. Where the honest answer is that an objective is
blocked, or deliberately not started, that is written down rather than left as an implied "soon".

Current state, for scale: **4 packs, 19 requirements, 6 engines** (`record`, `observed`, `probed`,
`certificate` — also at `probed` — `proved`, and the temporal proof engine, also at `proved`).
`reasonsmith validate-pack ecoa eu_ai_act gdpr table7` prints what each contains.

---

## 1. A temporal engine above `observed` — closed, for one shape of duty

**What closed it.** `engines/temporal.py` proves an `always(f)` whose `f` is a property of a single
decision, by the one reduction that is exact over a finite trace: `always(f)` holds iff `f` holds at
every position, and every position is a decision the system's exposed `logic()` admits. Both shipped
temporal requirements — `ecoa_reg_b_1002_9_a_1_timing_of_notice` and
`gdpr_recital71_error_risk_minimised` — now report `proved` against
`reasonsmith.examples.symbolic_rules`, and `test_a_temporal_duty_never_rises_above_observed` was
replaced by `test_only_always_reaches_the_temporal_proof_rung`, which pins the new ceiling from both
sides. The soundness paragraph is [`docs/semantics.md`](docs/semantics.md) §3, *`proved`, over a
trace*.

**What is left, and it is not this objective.** The rung reaches exactly one temporal shape.
`eventually(f)` asserts that some position *exists*, which is a fact about the trace a system emitted
rather than about the decisions its logic admits, so nothing reasoning about one decision at a time
establishes it and it stays at `observed`. Closing *that* needs the reasoning this objective did not
need — a bounded search over generated traces, or a finite-trace decision procedure — and no shipped
duty uses the operator, so it waits for one, on the same terms as objective 2.

## 2. `until` and `since` in the temporal fragment

**The gap.** `TEMPORAL_OPERATORS` holds the prefix call forms a Python parser accepts, so rtamt's
infix `until` and `since` are not in this property language.

Stated in [`docs/semantics.md`](docs/semantics.md) §2.

**Measurable outcome.** A shipped requirement whose `spec` uses one of the two, accepted by
`load_pack`, monitored by the observed engine, and carrying its own row in `docs/refinement.md`.

**Depends on — and is deliberately blocked by — objective 4.** No shipped duty needs either
operator. `docs/semantics.md` §2 says a pack needing one is a finding to record there, not a reason
to widen the language until it fits, because widening a property language to accommodate one
stubborn duty is how it becomes an untyped string again. So this objective waits for a real duty
that cannot be written without it. It is on the roadmap to be found, not to be started.

## 3. A fairness property, anywhere

**The gap.** No requirement in any shipped pack checks a fairness property. GDPR Recital 71's
prevention of discriminatory effects on the listed protected grounds — racial or ethnic origin,
political opinion, religion, trade union membership, genetic or health status, sexual orientation —
is not formalised here or anywhere else in the packs; the one requirement quoting that recital's
second paragraph formalises the *error* limb and nothing else.

Stated in [`docs/refinement.md`](docs/refinement.md), the GDPR Recital 71 row of column four.

**Measurable outcome.** At least one shipped requirement whose property compares an outcome across
groups rather than checking that a fairness field is non-empty, with a `docs/refinement.md` row
naming what it does not capture — and the sentence *no fairness property is checked by any
requirement in this repository* removed from that document because it has stopped being true.

**Depends on.** A design answer before any code: `conformance.stratified()` already computes
per-group figures, but it does so over reason-deletion certificates and produces statistics, not a
requirement verdict, and that path still does not meet a duty. What a single certificate takes to
become a verdict is now shown by `engines/certificate.py` — one decision at a time, grounding one
measured signal — and a group statistic is not that. Deciding whether a protected attribute may be a
signal in a decision record at all — and what it means for a property to read one — is the work.
It also depends on the four-outcome discipline of `docs/semantics.md` §4 holding: a fairness
property that cannot be evaluated must report *not evaluated*, never `satisfied`.

## 4. Breadth: more regulations than four

**The gap.** Four packs ship — Table 7, EU AI Act, GDPR, ECOA/Reg B — and only three of them quote
statute at all. Whether a fifth is worth more than depth on the four is a judgement this project has
not made in public.

**Measurable outcome.** Each additional pack lands with: a retrieval record in
[`docs/legal-sources.md`](docs/legal-sources.md); verbatim quotes that
`test_pack_quotes_found_verbatim_in_legal_sources_report` accepts character-for-character; a live
source `python -m reasonsmith.drift` can re-fetch, so the monthly statute-drift workflow covers it;
and one `docs/refinement.md` row per requirement, whose fourth column names a specific gap rather
than saying "some aspects are not captured".

**Depends on.** Proposals, which is the one item on this list a stranger unblocks rather than
waits on. The intake is the Discussion
[*Which regulation should the next pack cover?*](https://github.com/eduardstan/reasonsmith/discussions/54)
and the [pack proposal template](.github/ISSUE_TEMPLATE/pack_proposal.yml); the rules a pack must
satisfy are in [`docs/authoring-packs.md`](docs/authoring-packs.md).

---

## What is deliberately not on this roadmap

Kept here so a proposal for one of these gets an answer rather than silence:

- **Web or GUI dashboards.** The `--html` report is one static offline file, not a served
  application.
- **Reimplementing `nesyarena`'s IR or oracle engines.** They are depended on, pinned to
  `nesyarena==0.1.0`, never vendored.
- **Automated legal opinions, or any un-hedged compliance guarantee.** reasonsmith reports what a
  specification asks and how a verdict was reached. Whether a legal duty is discharged is a
  determination it does not make; that sentence travels on every emitted report.

`CONTRIBUTING.md` has the development setup, the verification commands, and the standing rules a
change must respect.
