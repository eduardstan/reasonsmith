# Roadmap

This file exists so a contributor or a reviewer can see what is missing without access to anyone's
private backlog. Every objective below is a gap this repository's own documents already state, and
each one cites where. Nothing here is aspirational: an item is on this list because a committed
document names it as a limit, not because it would be nice to have.

Each objective gives a **measurable outcome** — a check that fails today and would pass when the
objective is met — and what it **depends on**. Where the honest answer is that an objective is
blocked, or deliberately not started, that is written down rather than left as an implied "soon".

Current state, for scale: **4 packs, 19 requirements, 5 engines** (`record`, `observed`, `probed`,
`certificate` — also at `probed` — and `proved`). `reasonsmith validate-pack ecoa eu_ai_act gdpr table7` prints what each contains.

---

## 1. A temporal engine above `observed`

**The gap.** A temporal duty never rises above `observed`, whatever the system exposes. The solver
and the replay search both reason about one decision at a time and have nothing to say about a
formula quantified over a trace, so there is no rung above `observed` for the two shipped `temporal`
requirements — `ecoa_reg_b_1002_9_a_1_timing_of_notice` and `gdpr_recital71_error_risk_minimised` —
even against a system that exposes `logic()`.

Stated in [`docs/semantics.md`](docs/semantics.md) §3.5, and pinned by
`test_a_temporal_duty_never_rises_above_observed`.

**Measurable outcome.** Both shipped temporal requirements report at `probed` or `proved` against
`docs/adapters/symbolic_rules.py`, and `test_a_temporal_duty_never_rises_above_observed` is
*replaced* by a test pinning the new ceiling rather than deleted — a removed ceiling test is how a
ceiling stops being checked.

**Depends on.** Nothing structural: the engine ladder
([#47](https://github.com/eduardstan/reasonsmith/pull/47)) already collects engines from the
system's exposed surface rather than from the pack, so a new engine is reached the moment it exists —
and it need not be vendored here, since an engine installed through the `reasonsmith.engines`
entry-point group joins the same ladder ([`docs/authoring-engines.md`](docs/authoring-engines.md)).
What it needs is the reasoning itself — a bounded search over generated traces, or a solver encoding
of a trace-wide formula — and, before it can ship, its own soundness paragraph in
`docs/semantics.md` §3 naming the test that fails if the claim becomes false.

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
